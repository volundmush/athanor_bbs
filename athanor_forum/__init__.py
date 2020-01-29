from collections import defaultdict


def init_settings(settings):
    settings.INSTALLED_APPS.append("athanor_forum")
    settings.CONTROLLERS['forum'] = {
        'class': 'athanor_forum.controllers.AthanorForumController'
    }