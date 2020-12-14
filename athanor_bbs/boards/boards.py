import re
from django.conf import settings
from django.db.models import F, Q


from evennia.locks.lockhandler import LockException
from evennia.utils.validatorfuncs import lock as validate_lock
from evennia.utils.utils import lazy_property, class_from_module
from evennia.typeclasses.models import TypeclassBase
from evennia.typeclasses.managers import TypeclassManager

from athanor.utils.online import puppets as online_puppets
from athanor.utils.time import utcnow
from athanor.utils.text import clean_and_ansi

from athanor_bbs.boards.models import BoardDB
from athanor_bbs.boards import messages as fmsg
from athanor_bbs.boards.handlers import BoardAcccessHandler
from athanor.access.acl import ACLMixin


class DefaultBoard(ACLMixin, BoardDB, metaclass=TypeclassBase):
    post_class = class_from_module(settings.BASE_BBS_POST_TYPECLASS)
    objects = TypeclassManager()

    re_name = re.compile(r"(?i)^([A-Z]|[0-9]|\.|-|')+( ([A-Z]|[0-9]|\.|-|')+)*$")

    @lazy_property
    def acl(self):
        return BoardAcccessHandler(self)

    def at_first_save(self):
        pass

    def fullname(self):
        return f"BBS Board: ({self.prefix_order}): {self.key}"

    def generate_substitutions(self, viewer):
        return {'name': self.key,
                'cname': self.ckey,
                'typename': 'BBS Board',
                'fullname': self.fullname}

    @classmethod
    def create(cls, identity, key, order, **kwargs):
        clean_key, key = clean_and_ansi(key, thing_name='BBS Board')
        if not cls.re_name.match(clean_key):
            raise ValueError("BBS Board Names must <qualifier>")
        if (conflict := identity.owned_boards.filter(Q(db_key__iexact=clean_key) | Q(db_order=order)).first()):
            raise ValueError(f"Name or Order conflicts with another BBS Board in this category: {conflict}")
        board = cls(db_key=clean_key, db_ckey=key, db_order=order, db_owner=identity)
        board.save()
        return board

    def __str__(self):
        return self.key

    def create_post(self, poster, subject, text, date=None):
        if not date:
            date = utcnow()
        order = self.next_post_number
        new_post = self.post_class.create(self, poster, subject, text, date, order)
        self.next_post_number = order + 1
        return new_post

    @property
    def prefix_order(self):
        return f'{self.owner.db_abbreviation}{self.db_order}'

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
                fullnums += self.unread_posts(account).values_list('db_order', flat=True)
        posts = self.posts.filter(db_order__in=fullnums).order_by('db_order')
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
        return self.posts.exclude(read__account=account, date_modified__lte=F('read__date_read')).order_by(
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
