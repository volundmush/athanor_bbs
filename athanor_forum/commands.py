from athanor.commands.command import AthanorCommand


class ForumCommand(AthanorCommand):
    """
    Class for the Board System commands.
    """
    help_category = "Forum"
    system_name = "FORUM"
    locks = 'cmd:all()'
    controller_key = 'forum'
    entity_type = None

    def _switch_basic(self, operation):
        target = self.lhs
        op = getattr(self.controller, f"{operation}_{self.entity_type}")
        if not op:
            raise ValueError("Code error! Please contact staff!")
        return (target, op)

    def _switch_single(self, operation):
        target, op = self._switch_basic(operation)
        op(self.session, target, self.rhs)

    def _switch_multi(self, operation):
        target, op = self._switch_basic(operation)
        op(self.session, target, *self.rhslist)

    def switch_revoke(self):
        return self._switch_multi('revoke')

    def switch_grant(self):
        return self._switch_multi('grant')

    def switch_ban(self):
        return self._switch_multi('ban')

    def switch_unban(self):
        return self._switch_single('unban')

    def switch_rename(self):
        return self._switch_single('rename')

    def switch_lock(self):
        return self._switch_single('lock')

    def switch_config(self):
        return self._switch_multi('config')


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
            Sets an Evennia lock string to the category. See below.
            Please use with care.

        @fcategory/grant <category>=<user>,<position>
            Grants a user <position> over category.
            <position> cascades to Boards. Explained below.
            Use @fcategory/revoke with the same syntax to revoke positions.

        @fcategory/ban <target>=<user>,<duration>
            Prevent a specific person from using this category.
            Cascades down to boards.
            <duration> must be a simple string such as 7d (7 days) or 5h.
            Use @fcategory/unban <target>=<user> to rescind a ban early.

    Hierarchy: The Forum System is arranged as Category -> Board.

    Positions:
        Moderator: Moderators can use disciplinary commands on users.
        Operator: Operators can alter configurations and create/delete/change
            resources.
        Positions cascade down to Boards and can be set via Locks.

    """
    key = "@fcategory"
    aliases = ['+bbcat']
    locks = 'cmd:oper(forum_category_admin)'
    entity_type = 'category'
    switch_options = ('create', 'delete', 'rename', 'prefix', 'grant', 'revoke', 'ban', 'unban', 'lock')
    switch_syntax = {
        'create': '<category>=<prefix>',
        'delete': '<category>=<verify name>',
        'rename': '<category>=<new name>',
        'prefix': '<category>=<new prefix>',
        'grant': '<category>=<user>,<position>',
        'revoke': '<category>=<user>,<position>',
        'ban': '<category>=<user>,<duration>',
        'unban': '<category>=<user>',
        'lock': '<category>=<lockstring>'
    }

    def switch_main(self):
        self.msg(self.controller.render_category_list(self.session))

    def switch_create(self):
        self.controller.create_category(self.session, self.lhs, self.rhs)

    def switch_delete(self):
        self.controller.delete_category(self.session, self.lhs, self.rhs)

    def switch_prefix(self):
        self.controller.prefix_category(self.session, self.lhs, self.rhs)


class CmdForumAdmin(ForumCommand):
    """
    The BBS is a global, multi-threaded board with a rich set of features that grew
    from a rewrite of Myrddin's classical BBS. It shares almost identical command
    syntax and appearance.

    Managing Boards - Requires Permissions
        @fboard - Show all forum and locks.
        @fboard/create <category>=<boardname>,<order> - Creates a new board.
        @fboard/delete <board>=<full name> - Deletes a board.
        @fboard/rename <board>=<new name> - Renames a board.
        @fboard/order <board>=<new order> - Change a board's order.
        @fboard/lock <board>=<lock string> - Lock a board.
        @fboard/config <board>=<option>,<val>

    Board Membership
        @fboard/join <alias> - Join a board.
        @fboard/leave <alias> - Leave a board.

    Securing Boards
        The default lock for a board is:
            read:all();write:all();admin:oper(forum_board_operate)

        Example lockstring for a staff announcement board:
            read:all();write:perm(Admin);admin:perm(Admin) or perm(BBS_Admin)
    """

    key = "@fboard"
    aliases = ['+bboard']
    entity_type = 'board'
    switch_options = ('create', 'delete', 'rename', 'order', 'grant', 'revoke', 'ban', 'unban', 'lock', 'join', 'leave')

    switch_syntax = {
        'create': '<category>=<boardname>,<order>',
        'delete': '<board>=<verify name>',
        'rename': '<board>=<new name>',
        'order': '<board>=<new order>',
        'grant': '<board>=<user>,<position>',
        'revoke': '<board>=<user>,<position>',
        'ban': '<board>=<user>,<duration>',
        'unban': '<board>=<user>',
        'lock': '<board>=<lockstring>',
        'join': '<board>',
        'leave': '<board>'
    }

    def switch_main(self):
        self.msg(self.controller.render_board_list(self.session))

    def switch_create(self):
        name, order = self.rhslist
        self.controller.create_board(self.session, category=self.lhs, name=name, order=order)

    def switch_order(self):
        self._switch_single('order')

    def switch_join(self):
        board = self.controller.find_board(self.session, self.args, visible_only=False)
        board.ignore_list.remove(self.caller)

    def switch_leave(self):
        board = self.controller.find_board(self.session, self.args)
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
        @fpost/delete <board>/<post>=<verify name> - Remove a post. Requires permissions.
        @fpost/edit <board>/<post>=<before>^^^<after>
    """
    key = '@fpost'
    aliases = ['+bbpost']
    switch_options = ('edit', 'rename', 'move', 'delete')

    switch_syntax = {
        'rename': '<board>/<post>=<new name>',
        'delete': '<board>/<post>=<verify name>',
        'move': '<board>/<post>=<new board>',
        'edit': '<board>/<post>=<search>^^^<replace>',
        'main': '<board>/<title>=<post text>'
    }

    def switch_main(self):
        junk, subject = self.lhs.split('/', 1)
        subject = subject.strip()
        self.controller.create_post(self.session, board=self.lhslist[0], subject=subject, text=self.rhs)

    def switch_edit(self):
        if '/' not in self.lhs or '^^^' not in self.rhs:
            raise ValueError("Usage: +bbpost/edit <board>/<post>=<search>^^^<replace>")
        search, replace = self.rhs.split('^^^', 1)
        self.controller.edit_post(self.session, board=self.lhslist[0], post=self.lhslist[1],
                                                seek_text=search, replace_text=replace)

    def switch_move(self):
        self.controller.move_post(self.session, board=self.lhslist[0], post=self.lhslist[1],
                                                destination=self.rhs)

    def switch_delete(self):
        self.controller.delete_post(self.session, board=self.lhslist[0], post=self.lhslist[1])


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
            return self.msg(self.controller.render_board_list(self.session))
        if '/' not in self.args:
            return self.msg(self.controller.render_board(self.session, self.args))
        board, posts = self.args.split('/', 1)
        return self.msg(self.controller.display_posts(self.session, board, posts))

    def switch_catchup(self):
        if not self.args:
            raise ValueError("Usage: +bbcatchup <board or all>")
        if self.args.lower() == 'all':
            boards = self.controller.visible_boards(self.caller, check_admin=True)
        else:
            boards = list()
            for arg in self.lhslist:
                found_board = self.controller.find_board(self.caller, arg)
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
        boards = self.controller.visible_boards(self.caller, check_admin=True)
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
        boards = self.controller.visible_boards(self.caller, check_admin=True)
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
