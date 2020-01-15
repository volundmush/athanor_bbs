from django.conf import settings

import evennia
from evennia.utils.utils import class_from_module
from evennia.utils.ansi import ANSIString

from athanor.commands.command import AthanorCommand


class ForumCommand(AthanorCommand):
    """
    Class for the Board System commands.
    """
    help_category = "Communications"
    system_name = "FORUM"
    locks = 'cmd:all()'

    def switch_main_board_columns(self):
        return self.styled_columns(f"{'ID':<6}{'Name':<31}{'Mem':<4}{'#Mess':>6}{'#Unrd':>6} Perm")

    def display_board_row(self, account, board):
        bri = board.forum_board_bridge
        if bri.mandatory:
            member = 'MND'
        else:
            member = 'No' if account in bri.ignore_list.all() else 'Yes'
        return f"{board.prefix_order:<6}{board.key:<31}{member:<4} {bri.threads.count():>5} {board.unread_threads(account).count():>5} {str(board.locks)}"

    def switch_main_read(self):
        boards = evennia.GLOBAL_SCRIPTS.forum.visible_boards(self.caller, check_admin=True)
        message = list()
        message.append(self.styled_header('Forum Boards'))
        message.append(self.switch_main_board_columns())
        message.append(self._blank_separator)
        this_cat = None
        for board in boards:
            if this_cat != board.forum_board_bridge.category:
                message.append(self.styled_separator(board.forum_board_bridge.category.cname))
                this_cat = board.forum_board_bridge.category
            message.append(self.display_board_row(self.account, board))
        message.append(self._blank_footer)
        self.msg('\n'.join(str(l) for l in message))


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
    locks = 'cmd:perm(Admin) or perm(forum_admin)'
    switch_options = ('create', 'delete', 'rename', 'prefix', 'lock')

    def display_category_row(self, category):
        bri = category.forum_category_bridge
        cabbr = ANSIString(bri.cabbr)
        cname = ANSIString(bri.cname)
        return f"{cabbr:<7}{cname:<27}{bri.boards.count():<7}{str(category.locks):<30}"

    def switch_main(self):
        cats = evennia.GLOBAL_SCRIPTS.forum.visible_categories(self.caller)
        message = list()
        message.append(self.styled_header('Forum Categories'))
        message.append(self.styled_columns(f"{'Prefix':<7}{'Name':<27}{'Boards':<7}{'Locks':<30}"))
        message.append(self._blank_separator)
        for cat in cats:
            message.append(self.display_category_row(cat))
        message.append(self._blank_footer)
        self.msg('\n'.join(str(l) for l in message))

    def switch_create(self):
        evennia.GLOBAL_SCRIPTS.forum.create_category(self.caller, self.lhs, self.rhs)

    def switch_delete(self):
        evennia.GLOBAL_SCRIPTS.forum.delete_category(self.caller, self.lhs, self.rhs)

    def switch_rename(self):
        evennia.GLOBAL_SCRIPTS.forum.rename_category(self.caller, self.lhs, self.rhs)

    def switch_prefix(self):
        evennia.GLOBAL_SCRIPTS.forum.prefix_category(self.caller, self.lhs, self.rhs)

    def switch_lock(self):
        evennia.GLOBAL_SCRIPTS.forum.lock_category(self.caller, self.lhs, self.rhs)


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
        @fboard/mandatory <board>=<1 or 0> - Change whether a board is
            mandatory or not. mandatory forums with unread content
            insistently announce that connected accounts must read them
            and cannot be skipped with @fread/catchup.

    Securing Boards
        The default lock for a board is:
            read:all();write:all();admin:perm(Admin) or perm(BBS_Admin)

        Example lockstring for a staff announcement board:
            read:all();write:perm(Admin);admin:perm(Admin) or perm(BBS_Admin)

    Board Membership
        @fboard/join <alias> - Join a board.
        @fboard/leave <alias> - Leave a board.
    """

    key = "@fboard"

    player_switches = ['create', 'delete', 'rename', 'order', 'lock', 'unlock', 'mandatory', 'join', 'leave']

    def switch_main(self):
        return self.switch_main_read()

    def switch_create(self):
        if '/' not in self.rhs:
            raise ValueError("Usage: +bbadmin/create <category>=<board name>/<board order>")
        name, order = self.rhs.split('/', 1)
        evennia.GLOBAL_SCRIPTS.forum.create_board(self.caller, category=self.lhs, name=name, order=order)

    def switch_delete(self):
        evennia.GLOBAL_SCRIPTS.forum.delete_board(self.caller, name=self.lhs, verify=self.rhs)

    def switch_rename(self):
        evennia.GLOBAL_SCRIPTS.forum.rename_board(self.caller, name=self.lhs, new_name=self.rhs)

    def switch_mandatory(self):
        evennia.GLOBAL_SCRIPTS.forum.mandatory_board(self.caller, name=self.lhs, new_name=self.rhs)

    def switch_order(self):
        evennia.GLOBAL_SCRIPTS.forum.order_board(self.caller, name=self.rhs, order=self.lhs)

    def switch_lock(self):
        evennia.GLOBAL_SCRIPTS.forum.lock_board(self.caller, name=self.rhs, lock=self.lhs)

    def switch_join(self):
        board = evennia.GLOBAL_SCRIPTS.forum.find_board(self.caller, self.args, visible_only=False)
        board.ignore_list.remove(self.caller)

    def switch_leave(self):
        board = evennia.GLOBAL_SCRIPTS.forum.find_board(self.caller, self.args)
        if board.mandatory:
            raise ValueError("Cannot leave mandatory forum!")
        board.ignore_list.add(self.caller)


class CmdForumThread(ForumCommand):
    """
    The BBS is a global, multi-threaded board with a rich set of features that grew
    from a rewrite of Myrddin's classical BBS.

    Writing Posts
        @fthread <board>/<title>=<text> - Creates a new Thread on <board> called <title> with a starting post containing <text>.
        @fthread/rename <board>/<thread>=<new title> - Changes the title/subject of a thread.
        @fthread/move <board>/<thread>=<destination board> - Relocate a thread if you have permission.
        @fthread/delete <board>/<thread> - Remove an ENTIRE thread and all posts under it. Requires permissions.
    """
    key = '@fthread'
    switch_options = ('rename', 'move', 'delete')

    def switch_main(self):
        if '/' not in self.lhs:
            raise ValueError("Usage: +bbpost <board>/<subject>=<post text>")
        board, subject = self.lhs.split('/', 1)
        evennia.GLOBAL_SCRIPTS.forum.create_post(self.caller, board=board, subject=subject, text=self.rhs)

    def switch_rename(self):
        if '/' not in self.lhs or '^^^' not in self.rhs:
            raise ValueError("Usage: +bbpost/edit <board>/<post>=<search>^^^<replace>")
        board, post = self.lhs.split('/', 1)
        search, replace = self.rhs.split('^^^', 1)
        evennia.GLOBAL_SCRIPTS.forum.edit_post(self.caller, board=board, post=post, seek_text=search,
                                              replace_text=replace)

    def switch_move(self):
        if '/' not in self.lhs:
            raise ValueError("Usage: +bbpost/move <board>/<post>=<destination board>")
        board, post = self.lhs.split('/', 1)
        evennia.GLOBAL_SCRIPTS.forum.move_post(self.caller, board=board, post=post, destination=self.rhs)

    def switch_delete(self):
        if '/' not in self.lhs:
            raise ValueError("Usage: +bbpost/move <board>/<post>")
        board, post = self.lhs.split('/', 1)
        evennia.GLOBAL_SCRIPTS.forum.delete_post(self.caller, board=board, post=post)


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
            return self.switch_main_read()
        if not self.lhs:
            return self.error("Usage: @fread <board>/<thread>")
        if '/' not in self.lhs:
            return self.display_board()
        return self.display_posts()

    def display_board(self):
        board = evennia.GLOBAL_SCRIPTS.forum.find_board(self.caller, find_name=self.lhs)
        threads = board.threads.order_by('db_order')
        message = list()
        message.append(self.styled_header(f'Forum Threads on {board.prefix_order}: {board.key}'))
        message.append(self.styled_columns(f"{'ID':<10}Rd {'Title':<35}{'PostDate':<12}Author"))
        message.append(self._blank_separator)
        unread = board.unread_threads(self.account)
        for thread in threads:
            id = f"{thread.board.prefix_order}/{thread.order}"
            rd = 'U ' if thread in unread else ''
            subject = thread.key[:34].ljust(34)
            post_date = self.account.localize_timestring(thread.date_created, time_format='%b %d %Y')
            author = thread.entity
            message.append(f"{id:<10}{rd:<3}{subject:<35}{post_date:<12}{author}")
        message.append(self._blank_footer)
        self.msg('\n'.join(str(l) for l in message))

    def render_post(self, post):
        message = list()
        message.append(self.styled_separator(f"|w{post.entity}|n posted on {post.date_created}:"))
        message.append(post.body)
        return message

    def render_thread(self, thread):
        message = list()
        message.append(self.styled_header(f'Forum Thread - {thread.board.key}'))
        msg = f"{thread.board.prefix_order}/{thread.order}"[:25].ljust(25)
        message.append(f"Message: {msg} Created       Author")
        subj = thread.key[:34].ljust(34)
        disp_time = self.account.localize_timestring(thread.date_created, time_format='%b %d %Y').ljust(13)
        message.append(f"{subj} {disp_time} {thread.entity}")
        for post in thread.posts.all().order_by('db_order'):
            message += self.render_post(post)
        message.append(self._blank_separator)
        return '\n'.join(str(l) for l in message)

    def display_posts(self):
        board, threads = self.lhs.split('/', 1)
        board = evennia.GLOBAL_SCRIPTS.forum.find_board(self.caller, find_name=board)
        threads = board.parse_threadnums(self.account, threads)
        for thread in threads:
            self.msg(self.render_thread(thread))
            thread.update_read(self.account)

    def switch_catchup(self):
        if not self.args:
            raise ValueError("Usage: +bbcatchup <board or all>")
        if self.args.lower() == 'all':
            boards = evennia.GLOBAL_SCRIPTS.forum.visible_boards(self.caller, check_admin=True)
        else:
            boards = list()
            for arg in self.lhslist:
                found_board = evennia.GLOBAL_SCRIPTS.forum.find_board(self.caller, arg)
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
        boards = evennia.GLOBAL_SCRIPTS.forum.visible_boards(self.caller, check_admin=True)
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
        boards = evennia.GLOBAL_SCRIPTS.forum.visible_boards(self.caller, check_admin=True)
        for board in boards:
            b_unread = board.unread_posts(self.account).first()
            if b_unread:
                self.render_post(b_unread)
                b_unread.update_read(self.account)
                return
        raise ValueError("No unread posts to scan for!")

    def switch_new(self):
        self.switch_next()


FORUM_COMMANDS = [CmdForumCategory, CmdForumAdmin, CmdForumThread, CmdForumRead]
