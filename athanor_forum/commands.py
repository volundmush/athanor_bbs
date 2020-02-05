from django.conf import settings

import evennia
from evennia.utils.utils import class_from_module
from evennia.utils.ansi import ANSIString

from athanor.commands.command import AthanorCommand


class ForumCommand(AthanorCommand):
    """
    Class for the Board System commands.
    """
    help_category = "Forum"
    system_name = "FORUM"
    locks = 'cmd:all()'


class CmdForumCategory(ForumCommand):
    """
    All BBS Boards exist under BBS Categories, which consist of a unique name and
    maximum 3-letter prefix.

    Commands:
        @fcategory
            List all Categories.
        @fcategory/create <category>=<prefix>
            Create a new Category.
        @fcategory/rename <category>=<new name>
            Renames a category.
        @fcategory/prefix <category=<new prefix>
            Change a category prefix.
        @fcategory/lock <category>=<lock string>
            Standard Evennia locks. See access types below.

    Locks:
        see
            Who can see this category. This supersedes all Board-specific locks for child boards.
        manage
            Who has authority over this Category. Can create/delete/rename/modify boards within.
    """
    key = "@fcategory"
    aliases = ['+bbcat']
    locks = 'cmd:oper(forum_category_admin)'
    switch_options = ('create', 'delete', 'rename', 'prefix', 'lock', 'config')

    def switch_main(self):
        self.msg(self.controllers.get('forum').render_category_list(self.session))

    def switch_create(self):
        self.controllers.get('forum').create_category(self.session, self.lhs, self.rhs)

    def switch_delete(self):
        self.controllers.get('forum').delete_category(self.session, self.lhs, self.rhs)

    def switch_rename(self):
        self.controllers.get('forum').rename_category(self.session, self.lhs, self.rhs)

    def switch_prefix(self):
        self.controllers.get('forum').prefix_category(self.session, self.lhs, self.rhs)

    def switch_lock(self):
        self.controllers.get('forum').lock_category(self.session, self.lhs, self.rhs)

    def switch_config(self):
        self.controllers.get('forum').config_category(self.session, self.lhs, self.rhs)


class CmdForumAdmin(ForumCommand):
    """
    The BBS is a global, multi-threaded board with a rich set of features that grew
    from a rewrite of Myrddin's classical BBS. It shares almost identical command
    syntax and appearance.

    Managing Boards - Requires Permissions
        @fboard - Show all forum and locks.
        @fboard/create <category>=<boardname/<order> - Creates a new board.
        @fboard/delete <board>=<full name> - Deletes a board.
        @fboard/rename <board>=<new name> - Renames a board.
        @fboard/order <board>=<new order> - Change a board's order.
        @fboard/lock <board>=<lock string> - Lock a board.
        @fboard/config <board>=<option>,<val> - Change whether a board is
            mandatory or not. mandatory forums with unread content
            insistently announce that connected accounts must read them
            and cannot be skipped with @fread/catchup.

    Securing Boards
        The default lock for a board is:
            read:all();write:all();admin:oper(forum_board_operate)

        Example lockstring for a staff announcement board:
            read:all();write:perm(Admin);admin:perm(Admin) or perm(BBS_Admin)

    Board Membership
        @fboard/join <alias> - Join a board.
        @fboard/leave <alias> - Leave a board.
    """

    key = "@fboard"
    aliases = ['+bboard']

    switch_options = ['create', 'delete', 'rename', 'order', 'lock', 'unlock', 'config', 'join', 'leave']

    def switch_main(self):
        self.msg(self.controllers.get('forum').render_board_list(self.session))

    def switch_create(self):
        if '/' not in self.rhs:
            raise ValueError("Usage: +bbadmin/create <category>=<board name>/<board order>")
        name, order = self.rhs.split('/', 1)
        self.controllers.get('forum').create_board(self.session, category=self.lhs, name=name, order=order)

    def switch_delete(self):
        self.controllers.get('forum').delete_board(self.session, name=self.lhs, verify=self.rhs)

    def switch_rename(self):
        self.controllers.get('forum').rename_board(self.session, name=self.lhs, new_name=self.rhs)

    def switch_config(self):
        self.controllers.get('forum').config_board(self.session, name=self.lhs, new_name=self.rhs)

    def switch_order(self):
        self.controllers.get('forum').order_board(self.session, name=self.rhs, order=self.lhs)

    def switch_lock(self):
        self.controllers.get('forum').lock_board(self.session, name=self.rhs, lock=self.lhs)

    def switch_join(self):
        board = self.controllers.get('forum').find_board(self.session, self.args, visible_only=False)
        board.ignore_list.remove(self.caller)

    def switch_leave(self):
        board = self.controllers.get('forum').find_board(self.session, self.args)
        if board.mandatory:
            raise ValueError("Cannot leave mandatory forum!")
        board.ignore_list.add(self.caller)


class CmdForumPost(ForumCommand):
    """
    The BBS is a global, multi-threaded board with a rich set of features that grew
    from a rewrite of Myrddin's classical BBS.

    Writing Posts
        @fpost <board>/<title>=<text> - Creates a new post on <board> called <title> with the text <text>.
        @fpost/rename <board>/<post>=<new title> - Changes the title/subject of a thread.
        @fpost/move <board>/<post>=<destination board> - Relocate a thread if you have permission.
        @fpost/delete <board>/<post> - Remove a post. Requires permissions.
        @fpost/edit <board>/<post>=<before>^^^<after>
    """
    key = '@fthread'
    aliases = ['+bbpost']
    switch_options = ('rename', 'move', 'delete', 'edit')
    lhs_delim = '/'

    def switch_main(self):
        if '/' not in self.lhs:
            raise ValueError("Usage: +bbpost <board>/<subject>=<post text>")
        self.controllers.get('forum').create_post(self.caller, board=self.lhslist[0], subject=self.lhslist[1],
                                                  text=self.rhs)

    def switch_rename(self):
        if '/' not in self.lhs or '^^^' not in self.rhs:
            raise ValueError("Usage: +bbpost/edit <board>/<post>=<search>^^^<replace>")
        search, replace = self.rhs.split('^^^', 1)
        self.controllers.get('forum').edit_post(self.caller, board=self.lhslist[0], post=self.lhslist[1],
                                                seek_text=search, replace_text=replace)

    def switch_move(self):
        if '/' not in self.lhs:
            raise ValueError("Usage: +bbpost/move <board>/<post>=<destination board>")
        self.controllers.get('forum').move_post(self.caller, board=self.lhslist[0], post=self.lhslist[1],
                                                destination=self.rhs)

    def switch_delete(self):
        if '/' not in self.lhs:
            raise ValueError("Usage: +bbpost/move <board>/<post>")
        self.controllers.get('forum').delete_post(self.caller, board=self.lhslist[0], post=self.lhslist[1])


class CmdForumRead(ForumCommand):
    """
    The BBS is a global, multi-threaded board with a rich set of features that grew
    from a rewrite of Myrddin's classical BBS.

    Reading Posts
        @fread - Show all message boards and brief information.
        @fread <board> - Shows a board's messages. <board> must be the ID such as AB1 or 3, not name.
        @fread <board>/<threads> - Read a message. <list> is comma-seperated.
            Entries can be single numbers, number ranges (ie. 1-6), or u (for 'all
            unread'), in any combination or order - duplicates will not be shown.
        @fread/next - shows first available unread message.
        @fread/new - Same as /next.
        @fread/catchup <board> - Mark all threads on a board as read. use /catchup all to
            mark the entire forum as read.
        @fread/scan - Lists unread messages in compact form.
    """
    key = '@fread'
    aliases = ['+bbread']
    switch_options = ('catchup', 'scan', 'next', 'new')

    def switch_main(self):
        if not self.args:
            return self.msg(self.controllers.get('forum').render_board_list(self.session))
        if '/' not in self.args:
            return self.msg(self.controllers.get('forum').render_board(self.session, self.args))
        board, posts = self.args.split('/', 1)
        return self.msg(self.controllers.get('forum').display_posts(self.session, board, posts))

    def switch_catchup(self):
        if not self.args:
            raise ValueError("Usage: +bbcatchup <board or all>")
        if self.args.lower() == 'all':
            boards = self.controllers.get('forum').visible_boards(self.caller, check_admin=True)
        else:
            boards = list()
            for arg in self.lhslist:
                found_board = self.controllers.get('forum').find_board(self.caller, arg)
                if found_board not in boards:
                    boards.append(found_board)
        for board in boards:
            if board.mandatory:
                self.msg("Cannot skip a Mandatory board!", system_alert=self.system_name)
                continue
            unread = board.unread_posts(self.account)
            for post in unread:
                post.update_read(self.account)
            self.msg(f"Skipped {len(unread)} posts on Board '{board.prefix_order} - {board.key}'")

    def switch_scan(self):
        boards = self.controllers.get('forum').visible_boards(self.caller, check_admin=True)
        unread = dict()
        show_boards = list()
        for board in boards:
            b_unread = board.unread_posts(self.account)
            if b_unread:
                show_boards.append(board)
                unread[board] = b_unread
        if not show_boards:
            raise ValueError("No unread posts to scan for!")
        this_cat = None
        message = list()
        total_unread = 0
        message.append(self.styled_header('Unread Post Scan'))
        for board in show_boards:
            if this_cat != board.category:
                message.append(self.styled_separator(board.category.key))
                this_cat = board.category
            this_unread = len(unread[board])
            total_unread += this_unread
            unread_nums = ', '.join(p.order for p in unread[board])
            message.append(f"{board.key} ({board.prefix_order}): {this_unread} Unread: ({unread_nums})")
        message.append(self.styled_footer(f"Total Unread: {total_unread}"))
        return '\n'.join(str(l) for l in message)

    def switch_next(self):
        boards = self.controllers.get('forum').visible_boards(self.caller, check_admin=True)
        for board in boards:
            b_unread = board.unread_posts(self.account).first()
            if b_unread:
                self.render_post(b_unread)
                b_unread.update_read(self.account)
                return
        raise ValueError("No unread posts to scan for!")

    def switch_new(self):
        self.switch_next()


FORUM_COMMANDS = [CmdForumCategory, CmdForumAdmin, CmdForumPost, CmdForumRead]
