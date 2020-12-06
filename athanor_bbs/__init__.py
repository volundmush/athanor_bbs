PLUGIN_NAME = "athanor_bbs"

LOAD_PRIORITY = 0


def init_settings(settings):
    settings.BASE_BOARD_TYPECLASS = "athanor_bbs.boards.boards.DefaultBoard"
    settings.INSTALLED_APPS.append("athanor_bbs.boards")
    settings.CONTROLLERS['board'] = 'athanor_bbs.boards.controller.AthanorBoardController'
    settings.CMDSETS["ACCOUNT"].append("athanor_bbs.boards.cmdsets.AthanorAccountBoardCmdSet")
    settings.CMDSETS["CHARACTER"].append("athanor_bbs.boards.cmdsets.AthanorCharacterBoardCmdSet")
