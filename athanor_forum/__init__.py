from collections import defaultdict


def init_settings(settings):
    settings.FORUM_CATEGORY_TYPECLASS = "athanor_forum.gamedb.AthanorForumCategory"
    settings.FORUM_BOARD_TYPECLASS = "athanor_forum.gamedb.AthanorForumBoard"
    settings.INSTALLED_APPS.append("athanor_forum")
    settings.CONTROLLERS['forum'] = {
        'class': 'athanor_forum.controllers.AthanorForumController'
    }