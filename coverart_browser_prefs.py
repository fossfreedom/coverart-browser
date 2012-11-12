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
                LOCALE_DOMAIN = 'coverart_browser')

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
                PANED_POSITION='paned-position',
                SORT_BY_ALBUM='sort-by-album',
                SORT_BY_ARTIST='sort-by-artist',
                SORT_BY_RATING='sort-by-rating',
                SORT_BY_YEAR='sort-by-year',
                SORT_ORDER='sort-order',
                YEAR_SORT_VISIBLE='year-sort-visible',
                RATING_SORT_VISIBLE='rating-sort-visible',
                GENRE_FILTER_VISIBLE='genre-filter-visible',
                RATING='rating-threshold',
                AUTOSTART='autostart',
                TOOLBAR_POS='toolbar-pos')

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

        toggle_text_loading = builder.get_object(
            'display_text_loading_checkbox')
        self.settings.bind(gs.PluginKey.DISPLAY_TEXT_LOADING,
        toggle_text_loading, 'active', Gio.SettingsBindFlags.DEFAULT)

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

        rated_box = builder.get_object('rated_box')
        self.stars = ReactiveStar()
        
        self.stars.connect('changed', self.rating_changed_callback)

        rated_box.pack_start(self.stars, False, False, 1)

        self.stars.set_rating(self.settings[gs.PluginKey.RATING])
        
        autostart = builder.get_object('autostart_checkbox')
        self.settings.bind(gs.PluginKey.AUTOSTART,
            autostart, 'active', Gio.SettingsBindFlags.DEFAULT)

        year_sort_visible = builder.get_object('year_sort_checkbox')
        self.settings.bind(gs.PluginKey.YEAR_SORT_VISIBLE,
            year_sort_visible, 'active', Gio.SettingsBindFlags.DEFAULT)

        rating_sort_visible = builder.get_object('rating_sort_checkbox')
        self.settings.bind(gs.PluginKey.RATING_SORT_VISIBLE,
            rating_sort_visible, 'active', Gio.SettingsBindFlags.DEFAULT)

        genre_filter_visible = builder.get_object('genre_filter_checkbox')
        self.settings.bind(gs.PluginKey.GENRE_FILTER_VISIBLE,
            genre_filter_visible, 'active', Gio.SettingsBindFlags.DEFAULT)

        self.toolbar_left_radio=builder.get_object('toolbar_left_radio')
        self.toolbar_right_radio=builder.get_object('toolbar_right_radio')
        self.toolbar_main_radio=builder.get_object('toolbar_main_radio')

        toolbar_pos = self.settings[gs.PluginKey.TOOLBAR_POS]
        if toolbar_pos == 0:
            self.toolbar_main_radio.set_active(True)
        if toolbar_pos == 1:
            self.toolbar_left_radio.set_active(True)
        if toolbar_pos == 2:
            self.toolbar_right_radio.set_active(True)

        # return the dialog
        return builder.get_object('maingrid')

    def toolbar_callback( self, radio ):
        gs = GSetting()
        if radio == self.toolbar_main_radio:
            self.settings[gs.PluginKey.TOOLBAR_POS] = 0
        if radio == self.toolbar_left_radio:
            self.settings[gs.PluginKey.TOOLBAR_POS] = 1
        if radio == self.toolbar_right_radio:
            self.settings[gs.PluginKey.TOOLBAR_POS] = 2

    def rating_changed_callback(self, stars):
        print "rating_changed_callback"
        gs = GSetting()
        self.settings[gs.PluginKey.RATING] = self.stars.get_rating()
