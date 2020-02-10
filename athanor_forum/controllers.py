from evennia.utils.logger import log_trace
from evennia.utils.utils import class_from_module
from evennia.utils.ansi import ANSIString

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

    def parent_position(self, user, position):
        return user.lock_check(f"pperm(Admin)")

    def categories(self):
        return [cat.db_script for cat in ForumCategoryBridge.objects.all().order_by('db_name')]

    def visible_categories(self, user):
        return [cat for cat in self.categories() if cat.is_visible(user)]

    def _parent_operator(self, session):
        if not (enactor := self.get_enactor(session)) and self.parent_position(enactor, 'operator'):
            raise ValueError("Permission denied!")
        return enactor

    def get_enactor(self, session):
        return session.get_puppet()

    def create_category(self, session, name, abbr=''):
        enactor = self._parent_operator(session)
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
        if not (candidates := self.visible_categories(user)):
            raise ValueError("No Board Categories visible!")
        if not (found := partial_match(category, candidates)):
            raise ValueError(f"Category '{category}' not found!")
        return found

    def _rename_category(self, session, category, new, oper, msg):
        enactor = self._parent_operator(session)
        category = self.find_category(enactor, category)
        old_name = category.fullname
        operation = getattr(category, oper)
        new_name = operation(new)
        entities = {'enactor': enactor, 'target': category}
        msg(entities, old_name=old_name).send()

    def rename_category(self, session, category=None, new_name=None):
        return self._rename_category(session, category, new_name, 'rename', fmsg.Rename)

    def prefix_category(self, session, category=None, new_prefix=None):
        return self._rename_category(session, category, new_prefix, 'change_prefix', fmsg.Rename)

    def delete_category(self, session, category, abbr=None):
        enactor = self._parent_operator(session)
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
        enactor = self._enactor(session)
        category = self.find_category(enactor, category)
        return category.lock(session, new_locks)

    def lock_board(self, session, board, new_locks):
        enactor = self._enactor(session)
        board = self.find_board(enactor, board)
        return board.lock(session, new_locks)

    def boards(self):
        return AthanorForumBoard.objects.filter_family().order_by('forum_board_bridge__db_category__db_name',
                                                                  'forum_board_bridge__db_order')

    def visible_boards(self, user):
        return [board for board in self.boards() if board.check_position(user, 'reader')]

    def _enactor(self, session):
        if not (enactor := self.get_enactor(session)):
            raise ValueError("Permission denied!")
        return enactor

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
        enactor = self._enactor(session)
        category = self.find_category(enactor, category)
        if not category.check_position(enactor, 'operator'):
            raise ValueError("Permission denied!")
        typeclass = self.board_typeclass
        new_board = typeclass.create_forum_board(key=name, order=order, category=category)
        entities = {'enactor': enactor, 'target': new_board}
        fmsg.Create(entities).send()
        return new_board

    def delete_board(self, session, board, verify):
        enactor = self._enactor(session)
        board = self.find_board(enactor, board)
        if not board.parent_position(enactor, 'operator'):
            raise ValueError("Permission denied!")

    def rename_board(self, session, name=None, new_name=None):
        enactor = self._enactor(session)
        board = self.find_board(enactor, name)
        if not board.parent_position(enactor, 'operator'):
            raise ValueError("Permission denied!")
        old_name = board.key
        board.change_key(new_name)
        entities = {'enactor': enactor, 'target': board}
        fmsg.Rename(entities, old_name=old_name).send()

    def order_board(self, session, name=None, order=None):
        enactor = self._enactor(session)
        board = self.find_board(enactor, name)
        if not board.parent_position(enactor, 'operator'):
            raise ValueError("Permission denied!")
        old_order = board.order
        new_order = board.change_order(order)
        entities = {'enactor': enactor, 'target': board}
        fmsg.Order(entities, old_order=old_order).send()

    def create_post(self, session, board=None, subject=None, text=None, announce=True, date=None):
        enactor = self._enactor(session)
        board = self.find_board(enactor, board)
        if not board.check_permission(enactor, mode='post'):
            raise ValueError("Permission denied!")
        if not subject:
            raise ValueError("Posts must have a subject!")
        if not text:
            raise ValueError("Posts must have a text body!")
        new_post = board.create_post(session.account, enactor, subject, text, date=date)
        if announce:
            entities = {'enactor': enactor, 'target': board, 'post': new_post}
            pass  # do something!
        return new_post

    def rename_post(self, session, board=None, post=None, new_name=None):
        enactor = self._enactor(session)
        board = self.find_board(enactor, board)
        post = board.find_post(enactor, post)

    def delete_post(self, session, board=None, post=None, name_confirm=None):
        enactor = self._enactor(session)
        board = self.find_board(enactor, board)
        post = board.find_post(enactor, post)

    def edit_post(self, session, board=None, post=None, seek_text=None, replace_text=None):
        enactor = self._enactor(session)
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

    def render_category_row(self, category):
        bri = category.bridge
        cabbr = ANSIString(bri.cabbr)
        cname = ANSIString(bri.cname)
        return f"{cabbr:<7}{cname:<27}{bri.boards.count():<7}{str(category.locks):<30}"

    def render_category_list(self, session):
        enactor = self._enactor(session)
        cats = self.visible_categories(enactor)
        styling = enactor.styler
        message = list()
        message.append(styling.styled_header('Forum Categories'))
        message.append(styling.styled_columns(f"{'Prefix':<7}{'Name':<27}{'Boards':<7}{'Locks':<30}"))
        message.append(styling.blank_separator)
        for cat in cats:
            message.append(self.render_category_row(cat))
        message.append(styling.blank_footer)
        return '\n'.join(str(l) for l in message)

    def render_board_columns(self, user):
        styling = user.styler
        return styling.styled_columns(f"{'ID':<6}{'Name':<31}{'Mem':<4}{'#Mess':>6}{'#Unrd':>6} Perm")

    def render_board_row(self, enactor, account, board):
        bri = board.bridge
        if board.db.mandatory:
            member = 'MND'
        else:
            member = 'No' if account in board.ignore_list else 'Yes'
        count = bri.posts.count()
        unread = board.unread_posts(account).count()
        perms = board.display_permissions(enactor)
        return f"{board.prefix_order:<6}{board.key:<31}{member:<4} {count:>5} {unread:>5} {perms}"

    def render_board_list(self, session):
        enactor = self._enactor(session)
        boards = self.visible_boards(enactor)
        styling = enactor.styler
        message = list()
        message.append(styling.styled_header('Forum Boards'))
        message.append(self.render_board_columns(enactor))
        message.append(styling.blank_separator)
        this_cat = None
        for board in boards:
            if this_cat != (this_cat := board.category):
                message.append(styling.styled_separator(this_cat.cname))
            message.append(self.render_board_row(enactor, session.account, board))
        message.append(styling.blank_footer)
        return '\n'.join(str(l) for l in message)

    def render_board(self, session, board):
        enactor = self._enactor(session)
        board = self.find_board(enactor, board)
        posts = board.posts.order_by('order')
        styling = enactor.styler
        message = list()
        message.append(styling.styled_header(f'Forum Posts on {board.prefix_order}: {board.key}'))
        message.append(styling.styled_columns(f"{'ID':<10}Rd {'Title':<35}{'PostDate':<12}Author"))
        message.append(styling.blank_separator)
        unread = set(board.unread_posts(session.account))
        for post in posts:
            id = f"{post.board.db_script.prefix_order}/{post.order}"
            rd = 'U ' if post in unread else ''
            subject = post.cname[:34].ljust(34)
            post_date = styling.localize_timestring(post.date_created, time_format='%b %d %Y')
            author = post.character if post.character else 'N/A'
            message.append(f"{id:<10}{rd:<3}{subject:<35}{post_date:<12}{author}")
        message.append(styling.blank_footer)
        return '\n'.join(str(l) for l in message)

    def render_post(self, session, enactor, styling, post):
        message = list()
        message.append(styling.styled_header(f'Forum Post - {post.board.db_script.cname}'))
        msg = f"{post.board.db_script.prefix_order}/{post.order}"[:25].ljust(25)
        message.append(f"Message: {msg} Created       Author")
        subj = post.cname[:34].ljust(34)
        disp_time = styling.localize_timestring(post.date_created, time_format='%b %d %Y').ljust(13)
        message.append(f"{subj} {disp_time} {post.character if post.character else 'N/A'}")
        message.append(styling.blank_separator)
        message.append(post.body)
        message.append(styling.blank_separator)
        return '\n'.join(str(l) for l in message)

    def display_posts(self, session, board, posts):
        enactor = self._enactor(session)
        board = self.find_board(enactor, board)
        posts = board.parse_postnums(enactor, posts)
        message = list()
        styling = enactor.styler
        for post in posts:
            message.append(self.render_post(session, enactor, styling, post))
            post.update_read(session.account)
        return '\n'.join(str(l) for l in message)