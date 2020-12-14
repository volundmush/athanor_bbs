from evennia.typeclasses.models import TypeclassBase
from evennia.typeclasses.managers import TypeclassManager

from athanor.utils.time import utcnow


class DefaultPost(BBSPostDB, metaclass=TypeclassBase):
    objects = TypeclassManager()

    def at_first_save(self):
        pass

    @classmethod
    def create(cls, board, poster, subject, text, date, order):

        new_post = cls(db_board=board, db_poster=poster, db_key=subject, db_body=text, db_date_created=date,
                       db_date_modified=date, db_order=order)
        new_post.save()
        return new_post

    def __str__(self):
        return self.db_key

    def post_alias(self):
        return f"{self.db_board.prefix_order}/{self.db_order}"

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

    def fullname(self):
        return f"BBS Post: ({self.db_board.prefix_order}/{self.db_order}): {self.name}"

    def generate_substitutions(self, viewer):
        return {'name': self.name,
                'cname': self.cname,
                'typename': 'BBS Post',
                'fullname': self.fullname}
