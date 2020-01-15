import re
from django.db.models import F, Q

from evennia.locks.lockhandler import LockException
from evennia.utils.validatorfuncs import lock as validate_lock
from evennia.utils.ansi import ANSIString

from athanor.utils.online import puppets as online_puppets
from athanor.utils.time import utcnow
from athanor.gamedb.scripts import AthanorOptionScript

from athanor_forum.models import ForumCategoryBridge, ForumBoardBridge, ForumThreadBridge, ForumPost, ForumThreadRead


class AthanorForumCategory(AthanorOptionScript):
    # The Regex to use for Forum Category names.
    re_name = re.compile(r"^[a-zA-Z]{0,3}$")

    # The regex to use for Forum Category abbreviations.
    re_abbr = re.compile(r"^[a-zA-Z]{0,3}$")

    lockstring = "see:all();create:perm(Admin);delete:perm(Admin);admin:perm(Admin)"

    def create_bridge(self, key, clean_key, abbr, clean_abbr):
        if hasattr(self, 'forum_category_bridge'):
            return
        ForumCategoryBridge.objects.create(db_script=self, db_name=clean_key, db_cabbr=abbr, db_iname=clean_key.lower(),
                                           db_cname=key, db_abbr=clean_abbr, db_iabbr=clean_abbr.lower())

    def setup_locks(self):
        self.locks.add(self.lockstring)

    def __str__(self):
        return self.key

    @classmethod
    def create_forum_category(cls, key, abbr, **kwargs):
        key = ANSIString(key)
        abbr = ANSIString(abbr)
        clean_key = str(key.clean())
        clean_abbr = str(abbr.clean())
        if '|' in clean_key:
            raise ValueError("Malformed ANSI in ForumCategory Name.")
        if not cls.re_abbr.match(clean_abbr):
            raise ValueError("Abbreviations must be between 0-3 alphabetical characters.")
        if ForumCategoryBridge.objects.filter(Q(db_iname=clean_key.lower()) | Q(db_iabbr=clean_abbr.lower())).count():
            raise ValueError("Name or Abbreviation conflicts with another ForumCategory.")
        script, errors = cls.create(clean_key, persistent=True, **kwargs)
        if script:
            script.create_bridge(key.raw(), clean_key, abbr.raw(), clean_abbr)
            script.setup_locks()
        else:
            raise ValueError(errors)
        return script


class AthanorForumBoard(AthanorOptionScript):
    re_name = re.compile(r"(?i)^([A-Z]|[0-9]|\.|-|')+( ([A-Z]|[0-9]|\.|-|')+)*$")
    lockstring = "read:all();post:all();admin:perm(Admin)"

    def setup_locks(self):
        self.locks.add(self.lockstring)

    def create_bridge(self, category, key, clean_key, order):
        if hasattr(self, 'forum_board_bridge'):
            return
        ForumBoardBridge.objects.create(db_script=self, db_name=clean_key, db_category=category.forum_category_bridge,
                                        db_order=order, db_iname=clean_key.lower(), db_cname=key)

    @classmethod
    def create_forum_board(cls, category, key, order, **kwargs):
        key = ANSIString(key)
        clean_key = str(key.clean())
        if '|' in clean_key:
            raise ValueError("Malformed ANSI in ForumCategory Name.")
        if not cls.re_name.match(clean_key):
            raise ValueError("Forum Board Names must <qualifier>")
        if ForumBoardBridge.objects.filter(db_category=category.forum_category_bridge).filter(
                Q(db_iname=clean_key.lower()) | Q(db_order=order)).count():
            raise ValueError("Name or Order conflicts with another Forum Board in this category.")
        script, errors = cls.create(clean_key, persistent=True, **kwargs)
        if script:
            script.create_bridge(category, key.raw(), clean_key, order)
            script.setup_locks()
        else:
            raise ValueError(errors)
        return script

    def __str__(self):
        return self.key

    @property
    def prefix_order(self):
        bridge = self.forum_board_bridge
        return f'{bridge.category.db_abbr}{bridge.db_order}'

    @property
    def main_threads(self):
        return self.forum_board_bridge.threads.filter(parent=None)

    def character_join(self, character):
        self.forum_board_bridge.ignore_list.remove(character)

    def character_leave(self, character):
        self.forum_board_bridge.ignore_list.add(character)

    def parse_threadnums(self, account, check=None):
        if not check:
            raise ValueError("No threads entered to check.")
        fullnums = []
        for arg in check.split(','):
            arg = arg.strip()
            if re.match(r"^\d+-\d+$", arg):
                numsplit = arg.split('-')
                numsplit2 = []
                for num in numsplit:
                    numsplit2.append(int(num))
                lo, hi = min(numsplit2), max(numsplit2)
                fullnums += range(lo, hi + 1)
            if re.match(r"^\d+$", arg):
                fullnums.append(int(arg))
            if re.match(r"^U$", arg.upper()):
                fullnums += self.unread_posts(account).values_list('db_order', flat=True)
        threads = self.threads.filter(db_order__in=fullnums).order_by('db_order')
        if not threads:
            raise ValueError("Threads not found!")
        return threads

    def check_permission(self, checker=None, mode="read", checkadmin=True):
        if checker.locks.check_lockstring(checker, 'dummy:perm(Admin)'):
            return True
        if self.locks.check(checker.account, "admin") and checkadmin:
            return True
        elif self.locks.check(checker.account, mode):
            return True
        else:
            return False

    def unread_threads(self, account):
        return self.forum_board_bridge.threads.exclude(read__account=account, db_date_modified__lte=F('read__date_read')).order_by(
            'db_order')

    def display_permissions(self, looker=None):
        if not looker:
            return " "
        acc = ""
        if self.check_permission(checker=looker, mode="read", checkadmin=False):
            acc += "R"
        else:
            acc += " "
        if self.check_permission(checker=looker, mode="post", checkadmin=False):
            acc += "P"
        else:
            acc += " "
        if self.check_permission(checker=looker, mode="admin", checkadmin=False):
            acc += "A"
        else:
            acc += " "
        return acc

    def listeners(self):
        return [char for char in online_puppets() if self.check_permission(checker=char)
                and char not in self.ignore_list.all()]

    def squish_posts(self):
        for count, post in enumerate(self.posts.order_by('db_date_created')):
            if post.order != count + 1:
                post.order = count + 1

    def last_post(self):
        post = self.posts.order_by('db_date_created').first()
        if post:
            return post
        return None

    def change_key(self, new_key):
        new_key = self.validate_key(new_key, self.category, self)
        self.key = new_key
        return new_key

    def change_order(self, new_order):
        pass

    def change_locks(self, new_locks):
        if not new_locks:
            raise ValueError("No locks entered!")
        new_locks = validate_lock(new_locks, option_key='BBS Board Locks',
                                  access_options=['read', 'post', 'admin'])
        try:
            self.locks.add(new_locks)
        except LockException as e:
            raise ValueError(str(e))
        return new_locks


class AthanorForumThread(AthanorOptionScript):
    re_name = re.compile(r"(?i)^([A-Z]|[0-9]|\.|-|')+( ([A-Z]|[0-9]|\.|-|')+)*$")

    def create_bridge(self, board, key, clean_key, order, account, obj, date_created, date_modified):
        if hasattr(self, 'forum_category_bridge'):
            return
        if not date_created:
            date_created = utcnow()
        if not date_modified:
            date_modified = utcnow()
        ForumThreadBridge.objects.create(db_script=self, db_name=clean_key, db_order=order, db_object=obj, db_cname=key,
                                         db_board=board.forum_board_bridge,  db_iname=clean_key.lower(),
                                         db_date_created=date_created, db_account=account,
                                         db_date_modified=date_modified)

    @classmethod
    def create_forum_thread(cls, board, key, order, account, obj, date_created, date_modified, **kwargs):
        key = ANSIString(key)
        clean_key = str(key.clean())
        if '|' in clean_key:
            raise ValueError("Malformed ANSI in Forum Thread Name.")
        if not cls.re_name.match(clean_key):
            raise ValueError("Forum Thread Names must <qualifier>")
        if ForumThreadBridge.objects.filter(db_board=board.forum_board_bridge).filter(
                Q(db_iname=clean_key.lower()) | Q(db_order=order)).count():
            raise ValueError("Name or Order conflicts with another Forum Thread on this Board.")
        script, errors = cls.create(clean_key, persistent=True, **kwargs)
        if script:
            script.create_bridge(board, key.raw(), clean_key, order, account, obj, date_created, date_modified)
        else:
            raise ValueError(errors)
        return script

    def __str__(self):
        return self.key
