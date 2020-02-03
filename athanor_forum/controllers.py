from evennia.utils.logger import log_trace
from evennia.utils.utils import class_from_module

from athanor.utils.text import partial_match
from athanor.controllers.base import AthanorController

from athanor_forum.models import ForumCategoryBridge, ForumBoardBridge, ForumPost, ForumPostRead
from athanor_forum.gamedb import AthanorForumCategory, AthanorForumBoard, HasBoardOps
from athanor_forum import messages as fmsg

class AthanorForumController(HasBoardOps, AthanorController):
    system_name = 'FORUM'

    def do_load(self):
        from django.conf import settings

        try:
            category_typeclass = settings.FORUM_CATEGORY_TYPECLASS
            self.category_typeclass = class_from_module(category_typeclass, defaultpaths=settings.TYPECLASS_PATHS)
        except Exception:
            log_trace()
            self.category_typeclass = AthanorForumCategory

        try:
            board_typeclass = settings.FORUM_BOARD_TYPECLASS
            self.board_typeclass = class_from_module(board_typeclass, defaultpaths=settings.TYPECLASS_PATHS)
        except Exception:
            log_trace()
            self.board_typeclass = AthanorForumBoard

    def parent_operator(self, user):
        return user.lock_check(f"oper({self.operate_operation})")

    def parent_user(self, user):
        return user.lock_check(f"oper({self.use_operation})") or self.parent_moderator(user)

    def categories(self):
        return AthanorForumCategory.objects.filter_family().order_by('db_name')

    def visible_categories(self, user):
        return [cat for cat in self.categories() if cat.is_visible(user)]

    def get_user(self, session):
        return session.get_puppet()

    def create_category(self, session, name, abbr=''):
        if not (enactor := self.get_user(session)) and self.parent_operator(enactor):
            raise ValueError("Permission denied!")
        new_category = self.category_typeclass.create_forum_category(key=name, abbr=abbr)
        entities = {'enactor': enactor, 'target': new_category}
        fmsg.Create(entities).send()
        return new_category

    def find_category(self, user, category=None):
        if not category:
            raise ValueError("Must enter a category name!")
        if not (candidates := self.visible_categories(session)):
            raise ValueError("No Board Categories visible!")
        if not (found := partial_match(category, candidates)):
            raise ValueError(f"Category '{category}' not found!")
        return found

    def rename_category(self, session, category=None, new_name=None):
        if not (enactor := self.get_user(session)) and self.parent_operator(enactor):
            raise ValueError("Permission denied!")
        category = self.find_category(session, category)
        old_name = category.key
        old_abbr = category.abbr
        new_name = category.rename(new_name)
        entities = {'enactor': enactor, 'target': category}
        fmsg.Rename(entities, old_name=old_name, old_abbr=old_abbr).send()

    def prefix_category(self, session, category=None, new_prefix=None):
        if not (enactor := self.get_user(session)) and self.parent_operator(enactor):
            raise ValueError("Permission denied!")
        category = self.find_category(session, category)
        old_abbr = category.abbr
        new_prefix = category.change_prefix(new_prefix)
        entities = {'enactor': enactor, 'target': category}
        fmsg.Rename(entities, old_name=old_name, old_abbr=old_abbr).send()

    def rename_board(self, session, category, board, new_name):
        category = self.find_category(session, category)
        return category.rename_board(session, board, new_name)

    def delete_category(self, session, category, abbr=None):
        if not (enactor := self.get_user(session)) and self.parent_operator(enactor):
            raise ValueError("Permission denied!")
        category_found = self.find_category(session, category)
        if not category == category_found.key:
            raise ValueError("Names must be exact for verification.")
        if not abbr:
            raise ValueError("Must provide prefix for verification!")
        if not abbr == category_found.abbr:
            raise ValueError("Must provide exact prefix for verification!")
        entities = {'enactor': enactor, 'target': category_found}
        fmsg.Delete(entities).send()
        category_found.delete()

    def lock_category(self, session, category, new_locks):
        category = self.find_category(session, category)
        return category.lock(session, new_locks)

    def lock_board(self, session, category, board, new_locks):
        category = self.find_category(session, category)
        return category.lock_board(session, board, new_locks)

    def boards(self):
        return AthanorForumBoard.objects.filter_family().order_by('forum_board_bridge__db_category__db_name',
                                                                  'forum_board_bridge__db_order')

    def visible_boards(self, user):
        return [board for board in self.boards() if board.is_user(user)]

    def find_board(self, session, find_name=None, visible_only=True):
        if not find_name:
            raise ValueError("No board entered to find!")
        if isinstance(find_name, ForumBoardBridge):
            return find_name.db_script
        if isinstance(find_name, AthanorForumBoard):
            return find_name
        if not (boards := self.visible_boards(session) if visible_only else self.usable_boards(session)):
            raise ValueError("No applicable Forum Boards.")
        board_dict = {board.prefix_order.upper(): board for board in boards}
        if not (found := board_dict.get(find_name.upper(), None)):
            raise ValueError("Board '%s' not found!" % find_name)
        return found

    def create_board(self, session, category, name=None, order=None):
        category = self.find_category(session, category)
        if not category.access(session, 'create'):
            raise ValueError("Permission denied!")
        typeclass = self.board_typeclass
        new_board = typeclass.create_forum_board(key=name, order=order, category=category)
        announce = f"BBS Board Created: ({category}) - {new_board.prefix_order}: {new_board.key}"
        self.alert(announce, enactor=session)
        self.msg_target(announce, session)
        return new_board

    def delete_board(self, session, name=None, verify=None):
        board = self.find_board(session, name)
        if not verify == board.key:
            raise ValueError("Entered name must match board name exactly!")
        if not board.forum_board_bridge.category.db_script.access(session, 'delete'):
            raise ValueError("Permission denied!")
        announce = f"Deleted BBS Board ({board.category.key}) - {board.alias}: {board.key}"
        self.alert(announce, enactor=session)
        self.msg_target(announce, session)
        board.delete()

    def rename_board(self, session, name=None, new_name=None):
        board = self.find_board(session, name)
        if not board.forum_board_bridge.category.db_script.access('admin', session):
            raise ValueError("Permission denied!")
        old_name = board.key
        board.change_key(new_name)
        announce = f"Renamed BBS Board ({board.category.key}) - {board.alias}: {old_name} to: {board.key}"
        self.alert(announce, enactor=session)
        self.msg_target(announce, session)

    def order_board(self, session, name=None, order=None):
        board = self.find_board(session, name)
        if not board.category.access('admin', session):
            raise ValueError("Permission denied!")
        old_order = board.order
        order = board.change_order(order)
        announce = f"Re-Ordered BBS Board ({board.category.key}) - {board.alias}: {old_order} to: {order}"
        self.alert(announce, enactor=session)
        self.msg_target(announce, session)

    def lock_board(self, session, name=None, lock=None):
        board = self.find_board(session, name)
        if not board.category.access('admin', session):
            raise ValueError("Permission denied!")
        lock = board.change_locks(lock)
        announce = f"BBS Board ({board.category.key}) - {board.alias}: {board.key} lock changed to: {lock}"
        self.alert(announce, enactor=session)
        self.msg_target(announce, session)

    def create_thread(self, session, board=None, subject=None, text=None, announce=True, date=None, no_post=False):
        board = self.find_board(session, board)
        new_thread = self.thread_typeclass.create_forum_thread(key=subject, text=text, owner=session.full_stub, board=board, date=date)
        if not no_post:
            new_post = self.create_post(session, board=board, thread=new_thread, subject=subject, text=text,
                                        announce=False, date=date)
        if announce:
            pass  # do something!
        return new_thread

    def rename_thread(self, session, board=None, thread=None, new_name=None):
        board = self.find_board(session, board)
        thread = board.find_thread(session, thread)


    def delete_thread(self, session, board=None, thread=None, name_confirm=None):
        board = self.find_board(session, board)
        thread = board.find_thread(session, thread)


    def create_post(self, session, board=None, thread=None, subject=None, text=None, announce=True, date=None):
        board = self.find_board(session, board)
        thread = board.find_thread(session, thread)
        new_post = thread.create_post(text=text, owner=session, date=date)
        if announce:
            pass  # do something!
        return new_post

    def edit_post(self, session, board=None, thread=None, post=None, seek_text=None, replace_text=None):
        board = self.find_board(session, board)
        thread = board.find_thread(session, thread)
        post = thread.find_post(session, post)
        if not post.can_edit(session):
            raise ValueError("Permission denied.")
        post.edit_post(find=seek_text, replace=replace_text)
        announce = f"Post edited!"
        self.msg_target(announce, session)

    def delete_post(self, session, board=None, thread=None, post=None, verify_string=None):
        board = self.find_board(session, board)
        thread = board.find_thread(session, thread)
        post = thread.find_post(session, post)

    def set_mandatory(self, character, board=None, value=None):
        board = self.find_board(character, board)
