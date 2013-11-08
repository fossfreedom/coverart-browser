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
from coverart_controllers import PropertiesMenuController
from coverart_controllers import DecadePopupController
from coverart_controllers import SortOrderToggleController
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

        builder.add_from_file(ui_file)

        # assign the controllers to the buttons
        for button, controller in controllers.items():
            if button != 'search':
                builder.get_object(button).controller = controller

        if not webkit_support():
            button = builder.get_object('flowview_button')
            button.set_visible(False)
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

        self.builder = builder.get_object('main_box')

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
    ui = 'ui/coverart_sidebar.ui'
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
    ui = 'ui/coverart_sidebar.ui'
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
    #properties
    
    PROPERTIES='properties_button'
    SORT_BY='sort_by'
    SORT_ORDER='sort_order'
    GENRE='genre_button'
    PLAYLIST='playlist_button'
    DECADE='decade_button'
    SEARCH='search'
    ICONVIEW='iconview_button'
    FLOWVIEW='flowview_button'
    ARTISTVIEW='artistview_button'
    

class ToolbarManager(GObject.Object):
    # properties
    toolbar_pos = GObject.property(type=str, default=TopToolbar.name)
    
    def __init__(self, plugin, main_box, album_model, viewmgr):
        super(ToolbarManager, self).__init__()
        self.plugin = plugin
        # create the buttons controllers
        controllers = self._create_controllers(plugin, album_model, viewmgr)

        # initialize toolbars
        self._bars = {}
        self._bars[TopToolbar.name] = TopToolbar(plugin, main_box,
            controllers)
        self._bars[LeftToolbar.name] = LeftToolbar(plugin, main_box,
            controllers)
        self._bars[RightToolbar.name] = RightToolbar(plugin, main_box,
            controllers)

        self.last_toolbar_pos = None
        # connect signal and properties
        self._connect_signals()
        self._connect_properties()
        
        self._controllers = controllers
        
    def set_visible(self, visibility, toolbar_object=None):
        '''
        set the visibility of the toolbar object
        
        :param visibility: `bool` value corresponding to Gtk visible value.
        :param toolbar_object: `ToolbarObject` to set the visibility or
           None if visibility is to apply to all objects in the toolbar
        
        '''
        
        if toolbar_object:
            self._controllers[toolbar_object].visible = visibility
        else:
            for controller in self._controllers:
                self._controllers[controller].visible = visibility

    def _connect_signals(self):
        self.connect('notify::toolbar-pos', self._on_notify_toolbar_pos)

    def _connect_properties(self):
        gs = GSetting()
        setting = gs.get_setting(gs.Path.PLUGIN)
        setting.bind(gs.PluginKey.TOOLBAR_POS, self, 'toolbar_pos',
            Gio.SettingsBindFlags.GET)
            
    def _create_controllers(self, plugin, album_model, viewmgr):
        controllers = {}
        
        controllers[ToolbarObject.PROPERTIES] = \
            PropertiesMenuController(plugin, viewmgr.source)
        controllers[ToolbarObject.SORT_BY] = \
            SortPopupController(plugin, album_model)
        controllers[ToolbarObject.SORT_ORDER] = \
            SortOrderToggleController(plugin, album_model)
        controllers[ToolbarObject.GENRE] = \
            GenrePopupController(plugin, album_model)
        controllers[ToolbarObject.PLAYLIST] = \
            PlaylistPopupController(plugin, album_model)
        controllers[ToolbarObject.DECADE] = \
            DecadePopupController(plugin, album_model)
        controllers[ToolbarObject.SEARCH] = \
            AlbumSearchEntryController(album_model)
        
        controllers[ToolbarObject.ICONVIEW] = viewmgr.controller
        controllers[ToolbarObject.FLOWVIEW] = viewmgr.controller
        controllers[ToolbarObject.ARTISTVIEW] = viewmgr.controller

        return controllers

    def _on_notify_toolbar_pos(self, *args):
        if self.last_toolbar_pos:
            self._bars[self.last_toolbar_pos].hide()

        self._bars[self.toolbar_pos].show()

        self.last_toolbar_pos = self.toolbar_pos
