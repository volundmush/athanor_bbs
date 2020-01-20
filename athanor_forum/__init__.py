from collections import defaultdict


def init_settings(settings):
    settings.INSTALLED_APPS.append("athanor_forum")
    settings.GLOBAL_SCRIPTS['forum'] = {
        'typeclass': 'athanor_forum.controllers.AthanorForumController',
        'repeats': -1, 'interval': 60, 'desc': 'Forum BBS API',
        'locks': "admin:perm(Admin)",
    }