# -*- Mode: python; coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
#
# Copyright (C) 2012 - fossfreedom
# Copyright (C) 2012 - Agustin Carrasco
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301  USA.

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import RB
from gi.repository import Gio

from coverart_browser_prefs import GSetting
from coverart_browser_prefs import CoverLocale
from coverart_utils import Theme
from coverart_controllers import PlaylistPopupController
from coverart_controllers import GenrePopupController
from coverart_controllers import SortPopupController
from coverart_controllers import ArtistSortPopupController
from coverart_controllers import PropertiesMenuController
from coverart_controllers import DecadePopupController
from coverart_controllers import SortOrderToggleController
from coverart_controllers import ArtistSortOrderToggleController
from coverart_controllers import AlbumSearchEntryController
from coverart_widgets import SearchEntry
from coverart_browser_prefs import webkit_support
import rb


class Toolbar(GObject.Object):
    def __init__(self, plugin, mainbox, controllers):
        super(Toolbar, self).__init__()

        self.plugin = plugin
        self.mainbox = mainbox
        cl = CoverLocale()

        ui_file = rb.find_plugin_file(plugin, self.ui)

        # create the toolbar
        builder = Gtk.Builder()
        builder.set_translation_domain(cl.Locale.LOCALE_DOMAIN)
        print (ui_file)
        builder.add_from_file(ui_file)

        # assign the controllers to the buttons
        for button, controller in controllers.items():
            if button != 'search':
                builder.get_object(button).controller = controller

        if not webkit_support():
            # button = builder.get_object('flowview_button')
            #button.set_visible(False)
            separator = builder.get_object('properties_separator')
            if separator:
                separator.set_visible(False)

        # workaround to translate the search entry tooltips
        cl.switch_locale(cl.Locale.RB)
        search_entry = SearchEntry(has_popup=True)
        search_entry.show_all()
        cl.switch_locale(cl.Locale.LOCALE_DOMAIN)

        # add it to the ui
        align = builder.get_object('entry_search_alignment')
        align.add(search_entry)

        # assign the controller
        search_entry.controller = controllers['search']

        Theme(self.plugin).connect('theme_changed', self._theme_changed,
                                   controllers)

        self.builder = builder.get_object('toolbar')

        # now theme the toolbar including child objects such as the button popups
        style_context = self.builder.get_style_context()
        style_context.add_class(Gtk.STYLE_CLASS_TOOLBAR)

        view_button = builder.get_object(ToolbarObject.VIEW)
        view_button.set_visible(not self.plugin.using_headerbar)

    def _theme_changed(self, toolbar, controllers):
        for controller in list(controllers.values()):
            controller.update_images(True)


class TopToolbar(Toolbar):
    ui = 'ui/coverart_topbar.ui'
    name = 'main'

    def hide(self):
        if self.builder.get_visible():
            self.builder.hide()

    def show(self):
        self.mainbox.pack_start(self.builder, False, True, 0)
        self.mainbox.reorder_child(self.builder, 0)
        self.builder.show()


class LeftToolbar(Toolbar):
    ui = 'ui/coverart_leftsidebar.ui'
    name = 'left'

    def hide(self):
        if self.builder.get_visible():
            self.builder.hide()
            self.plugin.shell.remove_widget(self.builder,
                                            RB.ShellUILocation.SIDEBAR)

    def show(self):
        self.plugin.shell.add_widget(self.builder,
                                     RB.ShellUILocation.SIDEBAR, expand=False, fill=False)
        self.builder.show()


class RightToolbar(Toolbar):
    ui = 'ui/coverart_rightsidebar.ui'
    name = 'right'

    def hide(self):
        if self.builder.get_visible():
            self.builder.hide()
            self.plugin.shell.remove_widget(self.builder,
                                            RB.ShellUILocation.RIGHT_SIDEBAR)

    def show(self):
        self.plugin.shell.add_widget(self.builder,
                                     RB.ShellUILocation.RIGHT_SIDEBAR, expand=False, fill=False)
        self.builder.show()


class ToolbarObject(object):
    # properties

    PROPERTIES = 'properties_button'
    SORT_BY = 'sort_by'
    SORT_ORDER = 'sort_order'
    SORT_BY_ARTIST = 'sort_by_artist'
    SORT_ORDER_ARTIST = 'sort_order_artist'
    GENRE = 'genre_button'
    PLAYLIST = 'playlist_button'
    DECADE = 'decade_button'
    SEARCH = 'search'
    VIEW = 'view_button'


class ToolbarManager(GObject.Object):
    # properties
    toolbar_pos = GObject.property(type=str, default=TopToolbar.name)

    def __init__(self, plugin, main_box, viewmgr):
        super(ToolbarManager, self).__init__()
        self.plugin = plugin
        # create the buttons controllers
        controllers = self._create_controllers(plugin, viewmgr)

        # initialize toolbars
        self._bars = {}
        self._bars[TopToolbar.name] = TopToolbar(plugin, main_box,
                                                 controllers)
        self._bars[LeftToolbar.name] = LeftToolbar(plugin, main_box,
                                                   controllers)
        self._bars[RightToolbar.name] = RightToolbar(plugin, main_box,
                                                     controllers)

        self.last_toolbar_pos = None

        # if the alternative-toolbar is loaded then lets connect to the toolbar-visibility signal
        # to control our sources toolbar visibility

        if self.plugin.using_alternative_toolbar:
            if self.plugin.using_headerbar:
                self.toolbar_pos = TopToolbar.name # we dont allow other toolbar position with headerbar
                self._on_notify_toolbar_pos()

            self.plugin.shell.alternative_toolbar.connect('toolbar-visibility', self._visibility)

        # connect signal and properties
        self._connect_signals()
        self._connect_properties()

        self._controllers = controllers

    def _visibility(self, altplugin, value):
        if value:
            self._bars[self.toolbar_pos].show()
        else:
            self._bars[self.toolbar_pos].hide()

    def set_enabled(self, enabled, toolbar_object=None):
        '''
        enable or disable the toolbar object.
        
        :param enabled: `bool` value.
        :param toolbar_object: `ToolbarObject` 
           None if enabled is to apply to all objects in the toolbar
        
        '''
        if toolbar_object:
            self._controllers[toolbar_object].enabled = enabled
        else:
            for controller in self._controllers:
                self._controllers[controller].enabled = enabled

    def _connect_signals(self):
        if not self.plugin.using_headerbar:
            self.connect('notify::toolbar-pos', self._on_notify_toolbar_pos)

    def _connect_properties(self):
        if not self.plugin.using_headerbar:
            gs = GSetting()
            setting = gs.get_setting(gs.Path.PLUGIN)
            setting.bind(gs.PluginKey.TOOLBAR_POS, self, 'toolbar_pos',
                         Gio.SettingsBindFlags.GET)

    def _create_controllers(self, plugin, viewmgr):
        controllers = {}

        album_model = viewmgr.source.album_manager.model
        controllers[ToolbarObject.PROPERTIES] = \
            PropertiesMenuController(plugin, viewmgr.source)
        controllers[ToolbarObject.SORT_BY] = \
            SortPopupController(plugin, viewmgr)
        controllers[ToolbarObject.SORT_ORDER] = \
            SortOrderToggleController(plugin, viewmgr)
        controllers[ToolbarObject.SORT_BY_ARTIST] = \
            ArtistSortPopupController(plugin, viewmgr)
        controllers[ToolbarObject.SORT_ORDER_ARTIST] = \
            ArtistSortOrderToggleController(plugin, viewmgr)
        controllers[ToolbarObject.GENRE] = \
            GenrePopupController(plugin, album_model)
        controllers[ToolbarObject.PLAYLIST] = \
            PlaylistPopupController(plugin, album_model)
        controllers[ToolbarObject.DECADE] = \
            DecadePopupController(plugin, album_model)
        controllers[ToolbarObject.SEARCH] = \
            AlbumSearchEntryController(album_model)

        controllers[ToolbarObject.VIEW] = viewmgr.controller

        return controllers

    def _on_notify_toolbar_pos(self, *args):
        if self.last_toolbar_pos:
            self._bars[self.last_toolbar_pos].hide()

        self._bars[self.toolbar_pos].show()

        self.last_toolbar_pos = self.toolbar_pos
