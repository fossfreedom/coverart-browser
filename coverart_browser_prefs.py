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

class GSetting:
    """ A python singleton """

    # storage for the instance reference
    __instance = None

    class __impl:
        """ Implementation of the singleton interface """
        # below public variables and methods that can be called for GSetting
        def __init__(self):
            ##
            self.Path=self._enum(   PLUGIN='org.gnome.rhythmbox.plugins.coverart_browser',
                                    RBSOURCE='org.gnome.rhythmbox.sources')

            self.RBSourceKey=self._enum(VISIBLE_COLS='visible-columns')

            self.PluginKey=self._enum(  CUSTOM_STATUSBAR = 'custom-statusbar',
                                        DISPLAY_TRACKS = 'display-tracks',
                                        DISPLAY_TEXT = 'display-text',
                                        DISPLAY_TEXT_LOADING = 'display-text-loading',
                                        DISPLAY_TEXT_ELLIPSIZE = 'display-text-ellipsize',
                                        DISPLAY_TEXT_ELLIPSIZE_LENGTH = 'display-text-ellipsize-length'
                                     )

            self.setting={}

        def get_setting(self, path):
            try:
                setting = self.setting[path]
            except:
                self.setting[path]=Gio.Settings(path)
                setting = self.setting[path]

            return setting

        def get_value(self, path, key):
            
            return self.get_setting(path).get_value(key) 
 
        def _enum(self, **enums):
            return type('Enum', (), enums)

    def __init__(self):
        """ Create singleton instance """
        # Check whether we already have an instance
        if GSetting.__instance is None:
            # Create and remember instance
            GSetting.__instance = GSetting.__impl()

        # Store instance reference as the only member in the handle
        self.__dict__['_GSetting__instance'] = GSetting.__instance

    def __getattr__(self, attr):
        """ Delegate access to implementation """
        return getattr(self.__instance, attr)

    def __setattr__(self, attr, value):
        """ Delegate access to implementation """
        return setattr(self.__instance, attr, value)
        
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
        gs = GSetting()
        self.settings = gs.get_setting(gs.Path.PLUGIN)

    def do_create_configure_widget(self):
        '''
        Creates the plugin's preferences dialog
        '''
        # create the ui
        builder = Gtk.Builder()
        builder.add_from_file(rb.find_plugin_file(self, 'coverart_browser_prefs.ui'))

        gs = GSetting()
        # bind the toggles to the settings
        toggle_statusbar = builder.get_object('custom_statusbar_checkbox')
        self.settings.bind( gs.PluginKey.CUSTOM_STATUSBAR,
                            toggle_statusbar, 'active',
                            Gio.SettingsBindFlags.DEFAULT)

        toggle_tracks = builder.get_object('display_tracks_checkbox')
        self.settings.bind( gs.PluginKey.DISPLAY_TRACKS,
                            toggle_tracks, 'active',
                            Gio.SettingsBindFlags.DEFAULT)

        toggle_text = builder.get_object('display_text_checkbox')
        self.settings.bind( gs.PluginKey.DISPLAY_TEXT,
                            toggle_text, 'active',
                            Gio.SettingsBindFlags.DEFAULT)

        box_text = builder.get_object('display_text_box')
        self.settings.bind( gs.PluginKey.DISPLAY_TEXT,
                            box_text, 'sensitive',
                            Gio.SettingsBindFlags.GET)

        toggle_text_loading = builder.get_object(
            'display_text_loading_checkbox')
        self.settings.bind( gs.PluginKey.DISPLAY_TEXT_LOADING,
                            toggle_text_loading, 'active',
                            Gio.SettingsBindFlags.DEFAULT)

        toggle_text_ellipsize = builder.get_object(
            'display_text_ellipsize_checkbox')
        self.settings.bind( gs.PluginKey.DISPLAY_TEXT_ELLIPSIZE,
                            toggle_text_ellipsize, 'active',
                            Gio.SettingsBindFlags.DEFAULT)

        box_text_ellipsize_length = builder.get_object(
            'display_text_ellipsize_length_box')
        self.settings.bind( gs.PluginKey.DISPLAY_TEXT_ELLIPSIZE,
                            box_text_ellipsize_length, 'sensitive',
                            Gio.SettingsBindFlags.GET)

        spinner_text_ellipsize_length = builder.get_object(
            'display_text_ellipsize_length_spin')
        self.settings.bind( gs.PluginKey.DISPLAY_TEXT_ELLIPSIZE_LENGTH,
                            spinner_text_ellipsize_length, 'value',
                            Gio.SettingsBindFlags.DEFAULT)

        # return the dialog
        return builder.get_object('main_box')
