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
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import PeasGtk

import rb

PATH = 'org.gnome.rhythmbox.plugins.coverart_browser'
CUSTOM_STATUSBAR = 'custom-statusbar'
DISPLAY_TRACKS = 'display-tracks'
DISPLAY_TEXT = 'display-text'
DISPLAY_TEXT_LOADING = 'display-text-loading'
DIALOG_FILE = 'coverart_browser_prefs.ui'


class Preferences(GObject.Object, PeasGtk.Configurable):
    '''
    Preferences for the CoverArt Browser Plugins. It holds the settings for
    the plugin and also is the responsible of creating the preferences dialog.
    '''
    __gtype_name__ = 'CoverArtBrowserPreferences'
    object = GObject.property(type=GObject.Object)

    def __init__(self):
        '''
        Initialises the preferences, getting an instance of the settings saved
        by Gio.
        '''
        GObject.Object.__init__(self)
        self.settings = Gio.Settings(PATH)

    def do_create_configure_widget(self):
        '''
        Creates the plugin's preferences dialog
        '''
        # create the ui
        builder = Gtk.Builder()
        builder.add_from_file(rb.find_plugin_file(self, DIALOG_FILE))

        # bind the toggles to the settings
        toggle_statusbar = builder.get_object('custom_statusbar_checkbox')
        self.settings.bind(CUSTOM_STATUSBAR, toggle_statusbar, 'active',
            Gio.SettingsBindFlags.DEFAULT)

        toggle_tracks = builder.get_object('display_tracks_checkbox')
        self.settings.bind(DISPLAY_TRACKS, toggle_tracks, 'active',
            Gio.SettingsBindFlags.DEFAULT)

        toggle_text = builder.get_object('display_text_checkbox')
        self.settings.bind(DISPLAY_TEXT, toggle_text, 'active',
            Gio.SettingsBindFlags.DEFAULT)

        toggle_text_loading = builder.get_object(
            'display_text_loading_checkbox')
        self.settings.bind(DISPLAY_TEXT_LOADING, toggle_text_loading, 'active',
            Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind(DISPLAY_TEXT, toggle_text_loading, 'sensitive',
            Gio.SettingsBindFlags.GET)

        # return the dialog
        return builder.get_object('main_box')
