from django.db import models
from django.conf import settings
from athanor.utils.time import utcnow
from evennia.typeclasses.models import TypedObject, SharedMemoryModel
from athanor.access.models import AbstractACLEntry


class BoardDB(TypedObject):
    """
    Component for Entities which ARE a BBS  Board.
    Beware, the NameComponent is considered case-insensitively unique per board Owner.
    """
    __settingsclasspath__ = settings.BASE_BOARD_TYPECLASS
    __defaultclasspath__ = "athanor_bbs.boards.boards.DefaultBoard"
    __applabel__ = "boards"

    db_identity = models.ForeignKey('identities.IdentityDB', related_name='boards', on_delete=models.PROTECT)
    db_order = models.PositiveIntegerField(default=0)
    db_ikey = models.CharField(max_length=255)
    db_ckey = models.CharField(max_length=255)
    db_next_post_number = models.PositiveIntegerField(default=0, null=False)
    ignoring = models.ManyToManyField('identities.IdentityDB', related_name='ignored_boards')

    class Meta:
        unique_together = (('db_identity', 'db_order'), ('db_identity', 'db_ikey'))

    @property
    def alias(self):
        return f"{self.db_identity.db_abbr_global}{self.db_order}"


class BoardACL(AbstractACLEntry):
    resource = models.ForeignKey('boards.BoardDB', related_name='acl_entries', on_delete=models.CASCADE)

    class Meta:
        unique_together = (('resource', 'identity', 'mode'),)


class BoardTopic(SharedMemoryModel):
    db_board = models.ForeignKey('boards.BoardDB', related_name='topics', on_delete=models.CASCADE)
    db_creator = models.ForeignKey('identities.IdentityDB', null=True, related_name='bbs_topics', on_delete=models.PROTECT)
    db_name = models.CharField(max_length=255, blank=False, null=False)
    db_cname = models.CharField(max_length=255, blank=False, null=False)
    db_date_created = models.DateTimeField(null=False)
    db_date_modified = models.DateTimeField(null=False)
    db_date_latest = models.DateTimeField(null=False)
    db_order = models.PositiveIntegerField(null=False)

    class Meta:
        verbose_name = 'Topics'
        verbose_name_plural = 'Topics'
        unique_together = (('db_board', 'db_order'), )

    @classmethod
    def validate_key(cls, key_text, rename_from=None):
        return key_text

    @classmethod
    def validate_order(cls, order_text, rename_from=None):
        return int(order_text)

    def __str__(self):
        return self.db_name

    def post_alias(self):
        return f"{self.db_board.alias}/{self.db_order}"

    def can_edit(self, checker=None):
        if self.owner.account_stub.account == checker:
            return True
        return self.board.check_permission(checker=checker, type="admin")

    def edit_post(self, find=None, replace=None):
        if not find:
            raise ValueError("No text entered to find.")
        if not replace:
            replace = ''
        self.date_modified = utcnow()
        self.text = self.text.replace(find, replace)

    def update_read(self, account):
        acc_read, created = self.read.get_or_create(account=account)
        acc_read.date_read = utcnow()
        acc_read.save()

    def fullname(self, mode=""):
        return f"{mode} Board Post: ({self.db_board.alias.db_abbr_global}/{self.db_order}): {self.db_cname}"

    def generate_substitutions(self, viewer):
        return {'name': self.db_name,
                'cname': self.db_cname,
                'typename': 'BBS Post',
                'fullname': self.fullname}


class BoardPost(SharedMemoryModel):
    db_topic = models.ForeignKey('boards.BoardTopic', related_name='topics', on_delete=models.CASCADE)
    db_author = models.ForeignKey('identities.IdentityDB', null=True, related_name='bbs_posts',
                                  on_delete=models.PROTECT)
    db_name = models.CharField(max_length=255, blank=False, null=False)
    db_cname = models.CharField(max_length=255, blank=False, null=False)
    db_date_created = models.DateTimeField(null=False)
    db_date_modified = models.DateTimeField(null=False)
    db_order = models.PositiveIntegerField(null=False)
    db_body = models.TextField(null=False, blank=False)
    db_cbody = models.TextField(null=False, blank=False)

    class Meta:
        verbose_name = 'Post'
        verbose_name_plural = 'Posts'
        unique_together = (('db_topic', 'db_order'),)


class TopicRead(models.Model):
    identity = models.ForeignKey('identities.IdentityDB', related_name='bbs_topic_read', on_delete=models.CASCADE)
    topic = models.ForeignKey(BoardTopic, related_name='readers', on_delete=models.CASCADE)
    date_read = models.DateTimeField(null=True)

    class Meta:
        unique_together = (('identity', 'topic'),)
