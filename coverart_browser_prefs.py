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
import locale
import gettext
from stars import ReactiveStar
from stars import StarSize


class CoverLocale:
    '''
    This class manages the locale
    '''
    # storage for the instance reference
    __instance = None

    class __impl:
        """ Implementation of the singleton interface """
        # below public variables and methods that can be called for CoverLocale
        def __init__(self):
            '''
            Initializes the singleton interface, asigning all the constants
            used to access the plugin's settings.
            '''
            self.Locale = self._enum(
                RB='rhythmbox',
                LOCALE_DOMAIN='coverart_browser')

        def switch_locale(self, locale_type):
            '''
            Change the locale
            '''
            locale.setlocale(locale.LC_ALL, '')
            locale.bindtextdomain(locale_type, RB.locale_dir())
            locale.textdomain(locale_type)
            gettext.bindtextdomain(locale_type, RB.locale_dir())
            gettext.textdomain(locale_type)
            gettext.install(locale_type)

        def _enum(self, **enums):
            '''
            Create an enumn.
            '''
            return type('Enum', (), enums)

    def __init__(self):
        """ Create singleton instance """
        # Check whether we already have an instance
        if CoverLocale.__instance is None:
            # Create and remember instance
            CoverLocale.__instance = CoverLocale.__impl()

        # Store instance reference as the only member in the handle
        self.__dict__['_CoverLocale__instance'] = CoverLocale.__instance

    def __getattr__(self, attr):
        """ Delegate access to implementation """
        return getattr(self.__instance, attr)

    def __setattr__(self, attr, value):
        """ Delegate access to implementation """
        return setattr(self.__instance, attr, value)


class GSetting:
    '''
    This class manages the differentes settings that the plugins haves to
    access to read or write.
    '''
    # storage for the instance reference
    __instance = None

    class __impl:
        """ Implementation of the singleton interface """
        # below public variables and methods that can be called for GSetting
        def __init__(self):
            '''
            Initializes the singleton interface, asigning all the constants
            used to access the plugin's settings.
            '''
            self.Path = self._enum(
                PLUGIN='org.gnome.rhythmbox.plugins.coverart_browser',
                RBSOURCE='org.gnome.rhythmbox.sources')

            self.RBSourceKey = self._enum(VISIBLE_COLS='visible-columns')

            self.PluginKey = self._enum(
                CUSTOM_STATUSBAR='custom-statusbar',
                DISPLAY_BOTTOM='display-bottom',
                DISPLAY_TEXT='display-text',
                DISPLAY_TEXT_LOADING='display-text-loading',
                DISPLAY_TEXT_ELLIPSIZE='display-text-ellipsize',
                DISPLAY_TEXT_ELLIPSIZE_LENGTH='display-text-ellipsize-length',
                DISPLAY_FONT_SIZE='display-font-size',
                COVER_SIZE='cover-size',
                ADD_SHADOW='add-shadow',
                SHADOW_IMAGE='shadow-image',
                PANED_POSITION='paned-position',
                SORT_BY='sort-by',
                SORT_ORDER='sort-order',
                RATING='rating-threshold',
                AUTOSTART='autostart',
                TOOLBAR_POS='toolbar-pos',
                EMBEDDED_SEARCH='embedded-search',
                DISCOGS_SEARCH='discogs-search')

            self.setting = {}

        def get_setting(self, path):
            '''
            Return an instance of Gio.Settings pointing at the selected path.
            '''
            try:
                setting = self.setting[path]
            except:
                self.setting[path] = Gio.Settings(path)
                setting = self.setting[path]

            return setting

        def get_value(self, path, key):
            '''
            Return the value saved on key from the settings path.
            '''
            return self.get_setting(path)[key]

        def set_value(self, path, key, value):
            '''
            Set the passed value to key in the settings path.
            '''
            self.get_setting(path)[key] = value

        def _enum(self, **enums):
            '''
            Create an enumn.
            '''
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
        builder.add_from_file(rb.find_plugin_file(self,
            'ui/coverart_browser_prefs.ui'))
        builder.connect_signals(self)

        gs = GSetting()
        # bind the toggles to the settings
        toggle_statusbar = builder.get_object('custom_statusbar_checkbox')
        self.settings.bind(gs.PluginKey.CUSTOM_STATUSBAR,
            toggle_statusbar, 'active', Gio.SettingsBindFlags.DEFAULT)

        toggle_bottom = builder.get_object('display_bottom_checkbox')
        self.settings.bind(gs.PluginKey.DISPLAY_BOTTOM, toggle_bottom,
        'active', Gio.SettingsBindFlags.DEFAULT)

        toggle_text = builder.get_object('display_text_checkbox')
        self.settings.bind(gs.PluginKey.DISPLAY_TEXT, toggle_text, 'active',
            Gio.SettingsBindFlags.DEFAULT)

        box_text = builder.get_object('display_text_box')
        self.settings.bind(gs.PluginKey.DISPLAY_TEXT, box_text, 'sensitive',
            Gio.SettingsBindFlags.GET)

        toggle_text_ellipsize = builder.get_object(
            'display_text_ellipsize_checkbox')
        self.settings.bind(gs.PluginKey.DISPLAY_TEXT_ELLIPSIZE,
            toggle_text_ellipsize, 'active', Gio.SettingsBindFlags.DEFAULT)

        box_text_ellipsize_length = builder.get_object(
            'display_text_ellipsize_length_box')
        self.settings.bind(gs.PluginKey.DISPLAY_TEXT_ELLIPSIZE,
            box_text_ellipsize_length, 'sensitive', Gio.SettingsBindFlags.GET)

        spinner_text_ellipsize_length = builder.get_object(
            'display_text_ellipsize_length_spin')
        self.settings.bind(gs.PluginKey.DISPLAY_TEXT_ELLIPSIZE_LENGTH,
            spinner_text_ellipsize_length, 'value',
            Gio.SettingsBindFlags.DEFAULT)

        spinner_font_size = builder.get_object(
            'display_font_spin')
        self.settings.bind(gs.PluginKey.DISPLAY_FONT_SIZE,
            spinner_font_size, 'value',
            Gio.SettingsBindFlags.DEFAULT)

        cover_size_scale = builder.get_object('cover_size_adjustment')
        self.settings.bind(gs.PluginKey.COVER_SIZE, cover_size_scale, 'value',
            Gio.SettingsBindFlags.DEFAULT)

        add_shadow = builder.get_object('add_shadow_checkbox')
        self.settings.bind(gs.PluginKey.ADD_SHADOW, add_shadow, 'active',
            Gio.SettingsBindFlags.DEFAULT)

        rated_box = builder.get_object('rated_box')
        self.stars = ReactiveStar(size=StarSize.BIG)

        self.stars.connect('changed', self.rating_changed_callback)

        align = Gtk.Alignment.new(0.5, 0, 0, 0.1)
        align.add(self.stars)
        rated_box.add(align)

        self.stars.set_rating(self.settings[gs.PluginKey.RATING])

        autostart = builder.get_object('autostart_checkbox')
        self.settings.bind(gs.PluginKey.AUTOSTART,
            autostart, 'active', Gio.SettingsBindFlags.DEFAULT)

        embedded_search = builder.get_object('embedded_checkbox')
        self.settings.bind(gs.PluginKey.EMBEDDED_SEARCH,
            embedded_search, 'active', Gio.SettingsBindFlags.DEFAULT)

        discogs_search = builder.get_object('discogs_checkbox')
        self.settings.bind(gs.PluginKey.DISCOGS_SEARCH,
            discogs_search, 'active', Gio.SettingsBindFlags.DEFAULT)

        toolbar_pos_combo = builder.get_object('show_in_combobox')
        renderer = Gtk.CellRendererText()
        toolbar_pos_combo.pack_start(renderer, True)
        toolbar_pos_combo.add_attribute(renderer, 'text', 1)
        self.settings.bind(gs.PluginKey.TOOLBAR_POS, toolbar_pos_combo,
            'active-id', Gio.SettingsBindFlags.DEFAULT)

        light_source_combo = builder.get_object('light_source_combobox')
        renderer = Gtk.CellRendererText()
        light_source_combo.pack_start(renderer, True)
        light_source_combo.add_attribute(renderer, 'text', 1)
        self.settings.bind(gs.PluginKey.SHADOW_IMAGE, light_source_combo,
            'active-id', Gio.SettingsBindFlags.DEFAULT)

        # return the dialog
        return builder.get_object('main_notebook')

    def rating_changed_callback(self, stars):
        print "rating_changed_callback"
        gs = GSetting()
        self.settings[gs.PluginKey.RATING] = self.stars.get_rating()
