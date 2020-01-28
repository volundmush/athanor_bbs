
def init_settings(settings):
    settings.INSTALLED_APPS.append("athanor_forum")
    settings.CONTROLLER['forum'] = {
        'class': 'athanor_forum.controllers.AthanorForumController'
    }
