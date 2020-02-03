from django.db import models
from evennia.typeclasses.models import SharedMemoryModel
from athanor.utils.time import utcnow


class ForumCategoryBridge(SharedMemoryModel):
    db_script = models.OneToOneField('scripts.ScriptDB', related_name='forum_category_bridge', primary_key=True,
                                     on_delete=models.CASCADE)
    db_name = models.CharField(max_length=255, blank=False, null=False)
    db_iname = models.CharField(max_length=255, blank=False, null=False, unique=True)
    db_cname = models.CharField(max_length=255, blank=False, null=False)
    db_abbr = models.CharField(max_length=5, blank=True, null=False)
    db_iabbr = models.CharField(max_length=5, unique=True, blank=True, null=False)
    db_cabbr = models.CharField(max_length=50, blank=False, null=False)

    class Meta:
        verbose_name = 'ForumCategory'
        verbose_name_plural = 'ForumCategories'

    def __str__(self):
        return str(self.db_name)


class ForumBoardBridge(SharedMemoryModel):
    db_script = models.OneToOneField('scripts.ScriptDB', related_name='forum_board_bridge', primary_key=True,
                                     on_delete=models.CASCADE)
    db_category = models.ForeignKey(ForumCategoryBridge, related_name='boards', null=False, on_delete=models.CASCADE)
    db_name = models.CharField(max_length=255, blank=False, null=False)
    db_iname = models.CharField(max_length=255, blank=False, null=False)
    db_cname = models.CharField(max_length=255, blank=False, null=False)
    db_order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return str(self.db_name)

    class Meta:
        verbose_name = 'Forum'
        verbose_name_plural = 'Forums'
        unique_together = (('db_category', 'db_order'), ('db_category', 'db_iname'))


class ForumPost(models.Model):
    account = models.ForeignKey('accounts.AccountDB', related_name='+', null=True, on_delete=models.SET_NULL)
    object = models.ForeignKey('objects.ObjectDB', related_name='+', null=True, on_delete=models.SET_NULL)
    date_created = models.DateTimeField(null=False)
    board = models.ForeignKey(ForumBoardBridge, related_name='posts', on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=False, null=False)
    cname = models.CharField(max_length=255, blank=False, null=False)
    date_modified = models.DateTimeField(null=False)
    order = models.PositiveIntegerField(null=False)
    body = models.TextField(null=False, blank=False)

    class Meta:
        verbose_name = 'Post'
        verbose_name_plural = 'Posts'
        unique_together = (('board', 'order'), )

    @classmethod
    def validate_key(cls, key_text, rename_from=None):
        return key_text

    @classmethod
    def validate_order(cls, order_text, rename_from=None):
        return int(order_text)

    @classmethod
    def create(cls, *args, **kwargs):
        board = kwargs.get('board', None)
        if not isinstance(board, ForumThreadBridge):
            raise ValueError("Posts must be linked to a board!")

        owner = kwargs.get('owner', None)
        key = kwargs.get('key', None)
        key = cls.validate_key(key)

        text = kwargs.get('text', None)
        if not text:
            raise ValueError("Post body is empty!")

        order = kwargs.get('order', None)
        if order:
            order = cls.validate_order(order)
        else:
            last_post = board.last_post()
            if last_post:
                order = last_post.order + 1
            else:
                order = 1

        new_post = cls(db_key=key, db_order=order, db_board=board, db_owner=owner, db_text=text)
        new_post.save()
        return new_post

    def __str__(self):
        return self.subject

    def post_alias(self):
        return f"{self.board.alias}/{self.order}"

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


class ForumPostRead(models.Model):
    account = models.ForeignKey('accounts.AccountDB', related_name='forum_read', on_delete=models.CASCADE)
    thread = models.ForeignKey(ForumPost, related_name='read', on_delete=models.CASCADE)
    date_read = models.DateTimeField(null=True)

    class Meta:
        unique_together = (('account', 'thread'),)