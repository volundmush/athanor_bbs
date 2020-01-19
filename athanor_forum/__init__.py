from collections import defaultdict


def load(settings):
    settings.INSTALLED_APPS.extend(["athanor_forum"])
    settings.GLOBAL_SCRIPTS['forum'] = {
        'typeclass': 'athanor_forum.controllers.AthanorForumController',
        'repeats': -1, 'interval': 60, 'desc': 'Forum BBS API',
        'locks': "admin:perm(Admin)",
    }
    settings.CHANNEL_SYSTEMS = defaultdict(dict)

    settings.CHANNEL_SYSTEMS['account'] = {
        'channel_typeclass': 'athanor_channels.gamedb.AthannorAccountChannel'
    }