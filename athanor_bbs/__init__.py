from collections import defaultdict


def init_settings(settings):
    settings.FORUM_CATEGORY_TYPECLASS = "athanor_bbs.gamedb.AthanorBBSCategory"
    settings.FORUM_BOARD_TYPECLASS = "athanor_bbs.gamedb.AthanorBBSBoard"
    settings.INSTALLED_APPS.append("athanor_bbs")
    settings.CONTROLLERS['bbs'] = {
        'class': 'athanor_bbs.controllers.AthanorBBSController'
    }
    settings.CMDSETS["CHARACTER"].append("athanor_bbs.cmdsets.AthanorCharacterBBSCmdSet")
