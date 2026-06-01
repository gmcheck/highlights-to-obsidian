from functools import partial
from calibre.gui2.actions import InterfaceAction
from calibre_plugins.highlights_to_obsidian.main import MainDialog
import calibre_plugins.highlights_to_obsidian.button_actions as b_acts


class MenuButton(InterfaceAction):
    name = 'Send Highlights to Obsidian'
    action_add_menu = True

    action_spec = ('H2O', None,
                   'Highlights to Obsidian Menu', None)

    def __init__(self, parent, site_customization):
        super().__init__(parent, site_customization)
        self.new_highlights_action = None
        self.new_selected_action = None
        self.all_highlights_action = None
        self.all_selected_action = None
        self.user_config_action = None
        self.open_help_action = None

    def genesis(self):
        icon = get_icons('images/icon.png', 'Highlights to Obsidian Icon')

        self.qaction.setIcon(icon)
        self.qaction.triggered.connect(self.send_new_selected)

        ma = partial(self.create_menu_action, self.qaction.menu())
        un = "Highlights to Obsidian: Menu Button: "

        self.new_highlights_action = ma(
            un + "Send New", "Send New Highlights",
            description="Send new highlights (all books)",
            shortcut=None, triggered=self.send_new)

        self.new_selected_action = ma(
            un + "Send New Selected", "Send New (Selected Books)",
            description="Send new highlights of selected books only",
            shortcut=None, triggered=self.send_new_selected)

        self.qaction.menu().addSeparator()

        self.all_highlights_action = ma(
            un + "Send All", "Send All Highlights",
            description="Send all highlights of all books",
            shortcut=None, triggered=self.send_all)

        self.all_selected_action = ma(
            un + "Send All Selected", "Send All (Selected Books)",
            description="Send all highlights of selected books",
            shortcut=None, triggered=self.send_all_selected)

        self.qaction.menu().addSeparator()

        ocd = "Open config settings for Highlights to Obsidian"
        self.user_config_action = ma(
            un + "Config", "Config",
            description=ocd, shortcut=False, triggered=self.open_config)

        hd = "Open help menu for Highlights to Obsidian"
        self.open_help_action = ma(
            un + "Help", "Help",
            description=hd, shortcut=False, triggered=self.open_help)

    def send_new(self):
        b_acts.send_new_highlights(self.gui, self.gui.current_db.new_api)

    def send_new_selected(self):
        b_acts.send_new_selected_highlights(self.gui, self.gui.current_db.new_api)

    def send_all(self):
        b_acts.send_all_highlights(self.gui, self.gui.current_db.new_api)

    def send_all_selected(self):
        b_acts.send_all_selected_highlights(self.gui, self.gui.current_db.new_api)

    def open_config(self):
        do_user_config = self.interface_action_base_plugin.do_user_config
        do_user_config(parent=self.gui)

    def open_help(self):
        b_acts.help_menu(self.gui)

    def apply_settings(self):
        from calibre_plugins.highlights_to_obsidian.config import prefs
        pass
