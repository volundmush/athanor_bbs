from evennia.utils.logger import log_trace
from evennia.utils.utils import class_from_module

from athanor.utils.text import partial_match
from athanor.controllers.base import AthanorController
from athanor.utils.time import utcnow

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
        if isinstance(category, AthanorForumCategory):
            return category
        if isinstance(category, ForumCategoryBridge):
            return category.db_script
        if not (candidates := self.visible_categories(session)):
            raise ValueError("No Board Categories visible!")
        if not (found := partial_match(category, candidates)):
            raise ValueError(f"Category '{category}' not found!")
        return found

    def rename_category(self, session, category=None, new_name=None):
        if not (enactor := self.get_user(session)) and self.parent_operator(enactor):
            raise ValueError("Permission denied!")
        category = self.find_category(enactor, category)
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
        if not (enactor := self.get_user(session)):
            raise ValueError("Permission denied!")
        category = self.find_category(enactor, category)
        return category.lock(session, new_locks)

    def lock_board(self, session, category, board, new_locks):
        if not (enactor := self.get_user(session)):
            raise ValueError("Permission denied!")
        board = self.find_board(enactor, board)
        return board.lock(session, new_locks)

    def boards(self):
        return AthanorForumBoard.objects.filter_family().order_by('forum_board_bridge__db_category__db_name',
                                                                  'forum_board_bridge__db_order')

    def visible_boards(self, user):
        return [board for board in self.boards() if board.is_user(user)]

    def find_board(self, user, find_name=None):
        if not find_name:
            raise ValueError("No board entered to find!")
        if isinstance(find_name, AthanorForumBoard):
            return find_name
        if isinstance(find_name, ForumBoardBridge):
            return find_name.db_script
        if not (boards := self.visible_boards(user)):
            raise ValueError("No applicable Forum Boards.")
        board_dict = {board.prefix_order.upper(): board for board in boards}
        if not (found := board_dict.get(find_name.upper(), None)):
            raise ValueError("Board '%s' not found!" % find_name)
        return found

    def create_board(self, session, category, name=None, order=None):
        if not (enactor := self.get_user(session)):
            raise ValueError("Permission denied!")
        category = self.find_category(session, category)
        if not category.is_operator(enactor):
            raise ValueError("Permission denied!")
        typeclass = self.board_typeclass
        new_board = typeclass.create_forum_board(key=name, order=order, category=category)
        entities = {'enactor': enactor, 'target': new_board}
        fmsg.Create(entities).send()
        return new_board

    def delete_board(self, session, board, verify):
        if not (enactor := self.get_user(session)):
            raise ValueError("Permission denied!")
        board = self.find_board(enactor, board)
        if not board.parent_operator(enactor):
            raise ValueError("Permission denied!")

    def rename_board(self, session, name=None, new_name=None):
        if not (enactor := self.get_user(session)):
            raise ValueError("Permission denied!")
        board = self.find_board(enactor, name)
        if not board.parent_operator(enactor):
            raise ValueError("Permission denied!")
        old_name = board.key
        board.change_key(new_name)
        entities = {'enactor': enactor, 'target': board}
        fmsg.Rename(entities, old_name=old_name).send()

    def order_board(self, session, name=None, order=None):
        if not (enactor := self.get_user(session)):
            raise ValueError("Permission denied!")
        board = self.find_board(enactor, name)
        if not board.parent_operator(enactor):
            raise ValueError("Permission denied!")
        old_order = board.order
        new_order = board.change_order(order)
        entities = {'enactor': enactor, 'target': board}
        fmsg.Order(entities, old_order=old_order).send()

    def create_post(self, session, board=None, subject=None, text=None, announce=True, date=None):
        if not (enactor := self.get_user(session)):
            raise ValueError("Permission denied!")
        board = self.find_board(enactor, board)
        if not board.check_permission(enactor, mode='post'):
            raise ValueError("Permission denied!")
        if not subject:
            raise ValueError("Posts must have a subject!")
        if not text:
            raise ValueError("Posts must have a text body!")
        new_post = board.create_post(subject=subject, text=text, owner=enactor, date=date)
        if announce:
            entities = {'enactor': enactor, 'target': board, 'post': new_post}
            pass  # do something!
        return new_post

    def rename_post(self, session, board=None, post=None, new_name=None):
        if not (enactor := self.get_user(session)):
            raise ValueError("Permission denied!")
        board = self.find_board(enactor, board)
        post = board.find_post(enactor, post)

    def delete_post(self, session, board=None, post=None, name_confirm=None):
        if not (enactor := self.get_user(session)):
            raise ValueError("Permission denied!")
        board = self.find_board(enactor, board)
        post = board.find_post(enactor, post)

    def edit_post(self, session, board=None, post=None, seek_text=None, replace_text=None):
        if not (enactor := self.get_user(session)):
            raise ValueError("Permission denied!")
        board = self.find_board(enactor, board)
        post = board.find_post(enactor, post)
        if not post.can_edit(enactor):
            raise ValueError("Permission denied.")
        post.edit_post(find=seek_text, replace=replace_text)

    def config_category(self, session, category, config_op, config_val):
        category = self.find_category(session, category)
        category.config(session, config_op, config_val)

    def config_board(self, session, board, config_op, config_val):
        board = self.find_board(session, board)
        board.config(session, config_op, config_val)