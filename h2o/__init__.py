# this plugin's code is based on Kovid Goyal's example plugin at
# https://manual.calibre-ebook.com/creating_plugins.html

from calibre.customize import InterfaceActionBase
from calibre_plugins.highlights_to_obsidian.version import _version, version


class HighlightsToObsidianPlugin(InterfaceActionBase):
    name                = 'Highlights to Obsidian'
    description         = 'Automatically send highlights from calibre to obsidian.md'
    supported_platforms = ['windows', 'osx', 'linux']
    author              = 'jm289765'
    version             = _version
    actual_plugin       = 'calibre_plugins.highlights_to_obsidian.menu_button:MenuButton'
    minimum_calibre_version = (6, 10, 0)

    def is_customizable(self):
        return True

    def config_widget(self):
        # don't move this import statement
        from calibre_plugins.highlights_to_obsidian.config import ConfigWidget
        return ConfigWidget()

    def save_settings(self, config_widget):
        config_widget.save_settings()

        ac = self.actual_plugin_
        if ac is not None:
            ac.apply_settings()
