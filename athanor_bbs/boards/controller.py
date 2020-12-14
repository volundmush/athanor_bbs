from evennia.utils.ansi import ANSIString

from athanor.utils.controllers import AthanorController, AthanorControllerBackend

from athanor_bbs.boards.models import BoardTopic, BoardPost, BoardACL, TopicRead
from athanor_bbs.boards.boards import DefaultBoard
from athanor_bbs.boards import messages as fmsg


class AthanorBoardController(AthanorController):
    system_name = 'FORUM'

    def __init__(self, key, manager, backend):
        super().__init__(key, manager, backend)
        self.load()

    def create_board(self, session, owner, name, order: int=0):
        pass

    def rename_board(self, session, board, new_name):
        pass

    def reorder_board(self, session, board, new_order):
        enactor = self._enactor(session)
        board = self.find_board(enactor, name)
        if not board.parent_position(enactor, 'operator'):
            raise ValueError("Permission denied!")
        old_order = board.order
        new_order = board.change_order(order)
        entities = {'enactor': enactor, 'target': board}
        fmsg.Order(entities, old_order=old_order).send()

    def lock_board(self, session, board, new_locks):
        enactor = self._enactor(session)
        board = self.find_board(enactor, board)
        return board.lock(session, new_locks)

    def all(self):
        return self.backend.all()

    def count(self):
        return self.backend.count()

    def visible_boards(self, user):
        return [board for board in self.all() if board.check_acl(user, 'read')]

    def find_board(self, user, find_name=None):
        if not find_name:
            raise ValueError("No board entered to find!")
        if isinstance(find_name, DefaultBoard):
            return find_name
        if not (boards := self.visible_boards(user)):
            raise ValueError("No applicable BBS Boards.")
        board_dict = {board.prefix_order.upper(): board for board in boards}
        if not (found := board_dict.get(find_name.upper(), None)):
            raise ValueError("Board '%s' not found!" % find_name)
        return found

    def delete_board(self, session, board, verify):
        enactor = self._enactor(session)
        board = self.find_board(enactor, board)
        if not board.parent_position(enactor, 'operator'):
            raise ValueError("Permission denied!")

    def create_post(self, session, board, topic, subject=None, text=None, announce=True, date=None):
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
        message.append(styling.styled_header('BBS Categories'))
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
        message.append(styling.styled_header('BBS Boards'))
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
        message.append(styling.styled_header(f'BBS Posts on {board.prefix_order}: {board.key}'))
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
        message.append(styling.styled_header(f'BBS Post - {post.board.db_script.cname}'))
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


class AthanorBoardControllerBackend(AthanorControllerBackend):
    typeclass_defs = [
        ('board_typeclass', 'BASE_BOARD_TYPECLASS', DefaultBoard)
    ]

    def __init__(self, frontend):
        super().__init__(frontend)
        self.board_typeclass = None
        self.load()

    def all(self):
        return DefaultBoard.objects.all_family()

    def count(self):
        return DefaultBoard.objects.all_family().count()

    def create_board(self, owner, name, order: int=0) -> DefaultBoard:
        pass
