from evennia.server.plugins import EvPlugin, EvPluginRequirement
from typing import List


class AthanorBBS(EvPlugin):

    @property
    def name(self) -> str:
        return "athanor_bbs"

    @property
    def requirements(self) -> List[EvPluginRequirement]:
        return [
            EvPluginRequirement('athanor', ver_min="0.0.1")
        ]

    def at_init_settings(self, settings):
        settings.BASE_BOARD_TYPECLASS = "athanor_bbs.boards.boards.DefaultBoard"
        settings.INSTALLED_APPS.append("athanor_bbs.boards")
        settings.CONTROLLERS['board'] = {
            'controller': 'athanor_bbs.boards.controller.AthanorBoardController',
            'backend': 'athanor_bbs.boards.controller.AthanorBBSControllerBackend'
        }
        settings.CMDSETS["account"].append("athanor_bbs.boards.cmdsets.AthanorAccountBoardCmdSet")
        settings.CMDSETS["playtime"].append("athanor_bbs.boards.cmdsets.AthanorCharacterBoardCmdSet")
