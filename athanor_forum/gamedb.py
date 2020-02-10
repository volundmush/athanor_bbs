import re
from django.db.models import F, Q

from evennia.locks.lockhandler import LockException
from evennia.utils.validatorfuncs import lock as validate_lock
from evennia.utils.ansi import ANSIString
from evennia.utils.utils import lazy_property

import athanor
from athanor.utils.online import puppets as online_puppets
from athanor.utils.time import utcnow
from athanor.gamedb.scripts import AthanorOptionScript
from athanor.gamedb.base import HasOps

from athanor_forum.models import ForumCategoryBridge, ForumBoardBridge, ForumPost, ForumPostRead
from athanor_forum import messages as fmsg


class HasBoardOps(HasOps):
    grant_msg = fmsg.Grant
    revoke_msg = fmsg.Revoke
    ban_msg = fmsg.Ban
    unban_msg = fmsg.Unban

    def get_enactor(self, session):
        return session.get_puppet()

    def parent_position(self, user, position):
        return self.parent.check_position(user, position)


class AthanorForumCategory(HasBoardOps, AthanorOptionScript):
    # The Regex to use for Forum Category names.
    re_name = re.compile(r"(?i)^([A-Z]|[0-9]|\.|-|')+( ([A-Z]|[0-9]|\.|-|')+)*$")

    # The regex to use for Forum Category abbreviations.
    re_abbr = re.compile(r"^[a-zA-Z]{0,3}$")

    lockstring = "moderator:false();operator:false()"
    examine_type = 'forum_category'
    examine_caller_type = 'account'
    access_hierarchy = ['moderator', 'operator']
    access_breakdown = {
        'moderator': {
            'lock': 'pperm(Moderator)'
        },
        'operator': {
            'lock': 'pperm(Admin)'
        }
    }

    @property
    def parent(self):
        return athanor.CONTROLLER_MANAGER.get('forum')

    @property
    def fullname(self):
        prefix = f"({self.abbr}) " if self.abbr else ''
        return f'Forum Category: {prefix}{self.key}'

    def generate_substitutions(self, viewer):
        return {'name': self.key,
                'cname': self.bridge.cname,
                'typename': 'Forum Category',
                'fullname': self.fullname}

    @property
    def bridge(self):
        return self.forum_category_bridge

    @property
    def cname(self):
        return self.bridge.db_cname

    @property
    def abbr(self):
        return self.bridge.db_abbr

    @property
    def boards(self):
        return [board.db_script for board in self.bridge.boards.all().order_by('db_order')]

    def is_visible(self, user):
        if self.check_position(user, 'moderator'):
            return True
        for board in self.boards:
            if board.check_position(user, 'reader'):
                return True
        return False

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
        if '|' in clean_key or '|' in clean_abbr:
            raise ValueError("Malformed ANSI in ForumCategory Name or Prefix.")
        if not cls.re_name.match(clean_key):
            raise ValueError("Forum Categories must have simpler names than that!")
        if not cls.re_abbr.match(clean_abbr):
            raise ValueError("Prefixes must be between 0-3 alphabetical characters.")
        if ForumCategoryBridge.objects.filter(Q(db_iname=clean_key.lower()) | Q(db_iabbr=clean_abbr.lower())).count():
            raise ValueError("Name or Prefix conflicts with another ForumCategory.")
        script, errors = cls.create(clean_key, persistent=True, **kwargs)
        if script:
            script.create_bridge(key.raw(), clean_key, abbr.raw(), clean_abbr)
            script.setup_locks()
        else:
            raise ValueError(errors)
        return script

    def rename(self, key):
        key = ANSIString(key)
        clean_key = str(key.clean())
        iclean_key = clean_key.lower()
        if '|' in clean_key:
            raise ValueError("Malformed ANSI in ForumCategory Name.")
        if not self.re_name.match(clean_key):
            raise ValueError("Forum Categories must have simpler names than that!")
        if ForumCategoryBridge.objects.filter(db_iname=iclean_key).count():
            raise ValueError("Name conflicts with another ForumCategory.")
        bridge = self.bridge
        bridge.db_name = clean_key
        self.key = clean_key
        bridge.db_iname = iclean_key
        bridge.db_cname = key
        bridge.save_name()
        return key

    def change_prefix(self, new_prefix):
        abbr = ANSIString(new_prefix)
        clean_abbr = str(abbr.clean())
        iclean_abbr = clean_abbr.lower()
        if '|' in clean_abbr:
            raise ValueError("Malformed ANSI in ForumCategory Prefix.")
        if not self.re_abbr.match(clean_abbr):
            raise ValueError("Prefixes must be between 0-3 alphabetical characters.")
        if ForumCategoryBridge.objects.filter(db_iabbr=iclean_abbr.lower()).count():
            raise ValueError("Name or Prefix conflicts with another ForumCategory.")
        bridge = self.bridge
        bridge.db_abbr = clean_abbr
        self.key = clean_abbr
        bridge.db_iabbr = iclean_abbr
        bridge.db_cabbr = abbr
        bridge.save_abbr()
        return abbr


class AthanorForumBoard(HasBoardOps, AthanorOptionScript):
    re_name = re.compile(r"(?i)^([A-Z]|[0-9]|\.|-|')+( ([A-Z]|[0-9]|\.|-|')+)*$")
    lockstring = "reader:all();poster:all();moderator:false();operator:false()"
    examine_type = 'forum_board'
    examine_caller_type = 'account'
    lock_options = ['reader', 'poster', 'moderator', 'operator']
    access_hierarchy = ['reader', 'poster', 'moderator', 'operator']
    access_breakdown = {
        'reader': {
        },
        'poster': {
        },
        'moderator': {
            "lock": 'pperm(Moderator)'
        },
        "operator": {
            'lock': 'pperm(Admin)'
        }
    }
    operations = {
        'ban': 'moderator',
        'lock': 'operator',
        'config': 'operator'
    }

    @lazy_property
    def ignore_list(self):
        return self.get_or_create_attribute(key='ignore_list', default=set())

    def fullname(self):
        return f"Forum Board: ({self.prefix_order}): {self.key}"

    def generate_substitutions(self, viewer):
        return {'name': self.key,
                'cname': self.bridge.cname,
                'typename': 'Forum Board',
                'fullname': self.fullname}

    def setup_locks(self):
        self.locks.add(self.lockstring)

    @property
    def bridge(self):
        return self.forum_board_bridge

    @property
    def category(self):
        return self.bridge.db_category.db_script

    @property
    def cname(self):
        return self.bridge.db_cname

    @property
    def posts(self):
        return self.bridge.posts

    @property
    def parent(self):
        return self.bridge.db_category.db_script

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

    @lazy_property
    def next_post_id(self):
        return self.get_or_create_attribute(key='next_post_id', default=1)

    def create_post(self, account, character, subject, text, date=None):
        if not date:
            date = utcnow()
        name = ANSIString(subject)
        if '|' in name:
            raise ValueError("Malformed ANSI in post subject!")
        cname = name.raw()
        next = self.next_post_id
        new_post = self.posts.create(account=account, character=character, name=name.clean(), cname=cname, order=next,
                                     body=text, date_created=date, date_modified=date)
        new_post.update_read(account)
        next += 1
        return new_post

    @property
    def prefix_order(self):
        bridge = self.forum_board_bridge
        return f'{bridge.category.db_abbr}{bridge.db_order}'

    @property
    def main_posts(self):
        return self.forum_board_bridge.posts.filter(parent=None)

    def character_join(self, character):
        self.forum_board_bridge.ignore_list.remove(character)

    def character_leave(self, character):
        self.forum_board_bridge.ignore_list.add(character)

    def parse_postnums(self, account, check=None):
        if not check:
            raise ValueError("No posts entered to check.")
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
                fullnums += self.unread_posts(account).values_list('order', flat=True)
        posts = self.posts.filter(order__in=fullnums).order_by('order')
        if not posts:
            raise ValueError("posts not found!")
        return posts

    def check_permission(self, checker=None, mode="read", checkadmin=True):
        if checker.locks.check_lockstring(checker, 'dummy:perm(Admin)'):
            return True
        if self.locks.check(checker.account, "admin") and checkadmin:
            return True
        elif self.locks.check(checker.account, mode):
            return True
        else:
            return False

    def unread_posts(self, account):
        return self.bridge.posts.exclude(read__account=account, date_modified__lte=F('read__date_read')).order_by(
            'order')

    def display_permissions(self, looker=None):
        if not looker:
            return " "
        acc = ""
        for perm in (('read', 'R'), ('post', 'P'), ('admin', 'A')):
            if self.check_permission(checker=looker, mode=perm[0], checkadmin=False):
                acc += perm[1]
            else:
                acc += " "
        return acc

    def listeners(self):
        return [char for char in online_puppets() if self.check_permission(checker=char)
                and char not in self.ignore_list.all()]

    def squish_posts(self):
        for count, post in enumerate(self.posts.order_by('date_created')):
            if post.order != count + 1:
                post.order = count + 1

    def last_post(self):
        post = self.posts.order_by('date_created').first()
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
