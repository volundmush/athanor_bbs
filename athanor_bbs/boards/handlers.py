from collections import OrderedDict
from athanor.utils.access import AccessHandler


class BoardAcccessHandler(AccessHandler):
    permissions = OrderedDict(
        all="Grants All Permissions, including changing ACL entries and board config.",
        read='Able to see Board and read contained Posts.',
        post="Able to create new posts on this Board.",
        moderate="Able to edit/delete posts you did not create."
    )
