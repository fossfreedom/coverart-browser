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
from gi.repository import RB

import rb

class SearchPreferences(GObject.Object, PeasGtk.Configurable):
    '''
    Preferences for the CoverArt Browser Plugins. It holds the settings for
    the plugin and also is the responsible of creating the preferences dialog.
    '''
    __gtype_name__ = 'CoverArtSearchPreferences'
    object = GObject.property(type=GObject.Object)

    def __init__(self):
        '''
        Initialises the preferences, getting an instance of the settings saved
        by Gio.
        '''
        GObject.Object.__init__(self)
        gs = GSetting()
        self.settings = gs.get_setting(gs.Path.PLUGIN)

    def do_create_configure_widget(self):
        '''
        Creates the plugin's preferences dialog
        '''
        # create the ui
        builder = Gtk.Builder()
        builder.add_from_file(rb.find_plugin_file(self,
            'ui/coverart_album_search_prefs.ui'))
        builder.connect_signals(self)

        gs = GSetting()
        # bind the toggles to the settings
        embedded_search = builder.get_object('embedded_checkbox')
        self.settings.bind(gs.PluginKey.EMBEDDED_SEARCH,
            embedded_search, 'active', Gio.SettingsBindFlags.DEFAULT)
        
        discogs_search = builder.get_object('discogs_checkbox')
        self.settings.bind(gs.PluginKey.DISCOGS_SEARCH,
            discogs_search, 'active', Gio.SettingsBindFlags.DEFAULT)
            
        # return the dialog
        return builder.get_object('maingrid')
