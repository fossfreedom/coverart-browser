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
import locale
import gettext
import os
import shutil
import webbrowser

from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import PeasGtk
from gi.repository import Peas
from gi.repository import RB
from gi.repository import Gdk
from gi.repository import GLib

import rb
from stars import ReactiveStar
from stars import StarSize
import coverart_rb3compat as rb3compat


def webkit_support():
    '''
    function that returns True/False if webkit technology is supported
    '''
    gs = GSetting()
    settings = gs.get_setting(gs.Path.PLUGIN)
    return settings[gs.PluginKey.WEBKIT]


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
            Initializes the singleton interface, assigning all the constants
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

        def get_locale(self):
            '''
            return the string representation of the users locale
            for example
            en_US
            '''
            return locale.getdefaultlocale()[0]

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
    This class manages the different settings that the plugin has to
    access to read or write.
    '''
    # storage for the instance reference
    __instance = None

    class __impl:
        """ Implementation of the singleton interface """
        # below public variables and methods that can be called for GSetting
        def __init__(self):
            '''
            Initializes the singleton interface, assigning all the constants
            used to access the plugin's settings.
            '''
            self.Path = self._enum(
                PLUGIN='org.gnome.rhythmbox.plugins.coverart_browser',
                RBSOURCE='org.gnome.rhythmbox.sources')

            self.RBSourceKey = self._enum(VISIBLE_COLS='visible-columns')

            self.PluginKey = self._enum(
                CUSTOM_STATUSBAR='custom-statusbar',
                DISPLAY_TEXT='display-text',
                DISPLAY_TEXT_POS='display-text-pos',
                RANDOM='random-queue',
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
                SORT_BY_ARTIST='sort-by-artist',
                SORT_ORDER_ARTIST='sort-order-artist',
                RATING='rating-threshold',
                AUTOSTART='autostart',
                TOOLBAR_POS='toolbar-pos',
                BUTTON_RELIEF='button-relief',
                THEME='theme',
                NEW_GENRE_ICON='new-genre-icon',
                ICON_PADDING='icon-padding',
                ICON_SPACING='icon-spacing',
                ICON_AUTOMATIC='icon-automatic',
                VIEW_NAME='view-name',
                FLOW_APPEARANCE='flow-appearance',
                FLOW_HIDE_CAPTION='flow-hide-caption',
                FLOW_SCALE='flow-scale',
                FLOW_BACKGROUND_COLOUR='flow-background-colour',
                FLOW_AUTOMATIC='flow-automatic',
                FLOW_WIDTH='flow-width',
                FLOW_MAX='flow-max-albums',
                WEBKIT='webkit-support',
                ARTIST_PANED_POSITION='artist-paned-pos',
                USE_FAVOURITES='use-favourites',
                ARTIST_INFO_PANED_POSITION='artist-info-paned-pos',
                LAST_GENRE_FOLDER='last-genre-folder',
                ENTRY_VIEW_MODE='entry-view-mode',
                FOLLOWING='following',
                ACTIVATIONS='activations',
                TEXT_ALIGNMENT='text-alignment')

            self.setting = {}

        def get_setting(self, path):
            '''
            Return an instance of Gio.Settings pointing at the selected path.
            '''
            try:
                setting = self.setting[path]
            except:
                self.setting[path] = Gio.Settings.new(path)
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

    GENRE_POPUP = 1
    GENRE_LIST = 2

    def __init__(self):
        '''
        Initialises the preferences, getting an instance of the settings saved
        by Gio.
        '''
        GObject.Object.__init__(self)
        gs = GSetting()
        self.settings = gs.get_setting(gs.Path.PLUGIN)

        self._first_run = True
        self._cover_size = 0
        self._cover_size_delay = 0

    def do_create_configure_widget(self):
        '''
        Creates the plugin's preferences dialog
        '''
        return self._create_display_contents(self)

    def display_preferences_dialog(self, plugin):
        print("DEBUG - display_preferences_dialog")
        if self._first_run:
            self._first_run = False

            cl = CoverLocale()
            cl.switch_locale(cl.Locale.LOCALE_DOMAIN)

            self._dialog = Gtk.Dialog(modal=True, destroy_with_parent=True)
            self._dialog.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
            self._dialog.set_title(_('Browser Preferences'))
            content_area = self._dialog.get_content_area()
            content_area.pack_start(self._create_display_contents(plugin), True, True, 0)

            helpbutton = self._dialog.add_button(Gtk.STOCK_HELP, Gtk.ResponseType.HELP)
            helpbutton.connect('clicked', self._display_help)

        self._dialog.show_all()

        print("shown")

        while True:
            response = self._dialog.run()

            print("and run")

            if response != Gtk.ResponseType.HELP:
                break

        self._dialog.hide()

        print("DEBUG - display_preferences_dialog end")

    def _display_help(self, *args):
        peas = Peas.Engine.get_default()
        uri = peas.get_plugin_info('coverart_browser').get_help_uri()

        webbrowser.open(uri)

    def _create_display_contents(self, plugin):
        print("DEBUG - create_display_contents")
        # create the ui
        self._first_run = True
        cl = CoverLocale()
        cl.switch_locale(cl.Locale.LOCALE_DOMAIN)
        builder = Gtk.Builder()
        builder.set_translation_domain(cl.Locale.LOCALE_DOMAIN)
        builder.add_from_file(rb.find_plugin_file(plugin,
                                                  'ui/coverart_browser_prefs.ui'))
        self.launchpad_button = builder.get_object('show_launchpad')
        self.launchpad_label = builder.get_object('launchpad_label')

        builder.connect_signals(self)

        # . TRANSLATORS: Do not translate this string.
        translators = _('translator-credits')

        if translators != "translator-credits":
            self.launchpad_label.set_text(translators)
        else:
            self.launchpad_button.set_visible(False)

        gs = GSetting()
        # bind the toggles to the settings
        toggle_statusbar = builder.get_object('custom_statusbar_checkbox')
        self.settings.bind(gs.PluginKey.CUSTOM_STATUSBAR,
                           toggle_statusbar, 'active', Gio.SettingsBindFlags.DEFAULT)

        toggle_text = builder.get_object('display_text_checkbox')
        self.settings.bind(gs.PluginKey.DISPLAY_TEXT, toggle_text, 'active',
                           Gio.SettingsBindFlags.DEFAULT)

        box_text = builder.get_object('display_text_box')
        self.settings.bind(gs.PluginKey.DISPLAY_TEXT, box_text, 'sensitive',
                           Gio.SettingsBindFlags.GET)

        self.display_text_pos = self.settings[gs.PluginKey.DISPLAY_TEXT_POS]
        self.display_text_under_radiobutton = builder.get_object('display_text_under_radiobutton')
        self.display_text_within_radiobutton = builder.get_object('display_text_within_radiobutton')

        if self.display_text_pos:
            self.display_text_under_radiobutton.set_active(True)
        else:
            self.display_text_within_radiobutton.set_active(True)

        random_scale = builder.get_object('random_adjustment')
        self.settings.bind(gs.PluginKey.RANDOM, random_scale, 'value',
                           Gio.SettingsBindFlags.DEFAULT)

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

        # self.settings.bind(gs.PluginKey.COVER_SIZE, cover_size_scale, 'value',
        #                   Gio.SettingsBindFlags.DEFAULT)
        self._cover_size = self.settings[gs.PluginKey.COVER_SIZE]
        cover_size_scale.set_value(self._cover_size)
        cover_size_scale.connect('value-changed', self.on_cover_size_scale_changed)

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

        combo_liststore = builder.get_object('combo_liststore')

        from coverart_utils import Theme

        for theme in Theme(self).themes:
            combo_liststore.append([theme, theme])

        theme_combo = builder.get_object('theme_combobox')
        renderer = Gtk.CellRendererText()
        theme_combo.pack_start(renderer, True)
        theme_combo.add_attribute(renderer, 'text', 1)
        self.settings.bind(gs.PluginKey.THEME, theme_combo,
                           'active-id', Gio.SettingsBindFlags.DEFAULT)

        button_relief = builder.get_object('button_relief_checkbox')
        self.settings.bind(gs.PluginKey.BUTTON_RELIEF, button_relief, 'active',
                           Gio.SettingsBindFlags.DEFAULT)

        # create user data files
        cachedir = RB.user_cache_dir() + "/coverart_browser/usericons"
        if not os.path.exists(cachedir):
            os.makedirs(cachedir)

        popup = cachedir + "/popups.xml"

        temp = RB.find_user_data_file('plugins/coverart_browser/img/usericons/popups.xml')

        # lets see if there is a legacy file - if necessary copy it to the cache dir
        if os.path.isfile(temp) and not os.path.isfile(popup):
            shutil.copyfile(temp, popup)

        if not os.path.isfile(popup):
            template = rb.find_plugin_file(plugin, 'template/popups.xml')
            folder = os.path.split(popup)[0]
            if not os.path.exists(folder):
                os.makedirs(folder)
            shutil.copyfile(template, popup)

        # now prepare the genre tab
        from coverart_utils import GenreConfiguredSpriteSheet
        from coverart_utils import get_stock_size

        self._sheet = GenreConfiguredSpriteSheet(plugin, "genre", get_stock_size())

        self.alt_liststore = builder.get_object('alt_liststore')
        self.alt_user_liststore = builder.get_object('alt_user_liststore')
        self._iters = {}
        for key in list(self._sheet.keys()):
            store_iter = self.alt_liststore.append([key, self._sheet[key]])
            self._iters[(key, self.GENRE_POPUP)] = store_iter

        for key, value in self._sheet.genre_alternate.items():
            if key.genre_type == GenreConfiguredSpriteSheet.GENRE_USER:
                store_iter = self.alt_user_liststore.append([key.name,
                                                             self._sheet[self._sheet.genre_alternate[key]],
                                                             self._sheet.genre_alternate[key]])
                self._iters[(key.name, self.GENRE_LIST)] = store_iter

        self.amend_mode = False
        self.blank_iter = None
        self.genre_combobox = builder.get_object('genre_combobox')
        self.genre_entry = builder.get_object('genre_entry')
        self.genre_view = builder.get_object('genre_view')
        self.save_button = builder.get_object('save_button')
        self.filechooserdialog = builder.get_object('filechooserdialog')
        last_genre_folder = self.settings[gs.PluginKey.LAST_GENRE_FOLDER]
        if last_genre_folder != "":
            self.filechooserdialog.set_current_folder(last_genre_folder)

        padding_scale = builder.get_object('padding_adjustment')
        self.settings.bind(gs.PluginKey.ICON_PADDING, padding_scale, 'value',
                           Gio.SettingsBindFlags.DEFAULT)

        spacing_scale = builder.get_object('spacing_adjustment')
        self.settings.bind(gs.PluginKey.ICON_SPACING, spacing_scale, 'value',
                           Gio.SettingsBindFlags.DEFAULT)

        icon_automatic = builder.get_object('icon_automatic_checkbox')
        self.settings.bind(gs.PluginKey.ICON_AUTOMATIC,
                           icon_automatic, 'active', Gio.SettingsBindFlags.DEFAULT)

        # flow tab
        flow_combo = builder.get_object('flow_combobox')
        renderer = Gtk.CellRendererText()
        flow_combo.pack_start(renderer, True)
        flow_combo.add_attribute(renderer, 'text', 1)
        self.settings.bind(gs.PluginKey.FLOW_APPEARANCE, flow_combo,
                           'active-id', Gio.SettingsBindFlags.DEFAULT)

        flow_hide = builder.get_object('hide_caption_checkbox')
        self.settings.bind(gs.PluginKey.FLOW_HIDE_CAPTION,
                           flow_hide, 'active', Gio.SettingsBindFlags.DEFAULT)

        flow_scale = builder.get_object('cover_scale_adjustment')
        self.settings.bind(gs.PluginKey.FLOW_SCALE, flow_scale, 'value',
                           Gio.SettingsBindFlags.DEFAULT)

        flow_width = builder.get_object('cover_width_adjustment')
        self.settings.bind(gs.PluginKey.FLOW_WIDTH, flow_width, 'value',
                           Gio.SettingsBindFlags.DEFAULT)

        flow_max = builder.get_object('flow_max_adjustment')
        self.settings.bind(gs.PluginKey.FLOW_MAX, flow_max, 'value',
                           Gio.SettingsBindFlags.DEFAULT)

        flow_automatic = builder.get_object('automatic_checkbox')
        self.settings.bind(gs.PluginKey.FLOW_AUTOMATIC,
                           flow_automatic, 'active', Gio.SettingsBindFlags.DEFAULT)

        self.background_colour = self.settings[gs.PluginKey.FLOW_BACKGROUND_COLOUR]
        self.white_radiobutton = builder.get_object('white_radiobutton')
        self.black_radiobutton = builder.get_object('black_radiobutton')

        if self.background_colour == 'W':
            self.white_radiobutton.set_active(True)
        else:
            self.black_radiobutton.set_active(True)

        self.text_alignment = self.settings[gs.PluginKey.TEXT_ALIGNMENT]
        self.text_alignment_left_radiobutton = builder.get_object('left_alignment_radiobutton')
        self.text_alignment_centre_radiobutton = builder.get_object('centre_alignment_radiobutton')
        self.text_alignment_right_radiobutton = builder.get_object('right_alignment_radiobutton')

        if self.text_alignment == 0:
            self.text_alignment_left_radiobutton.set_active(True)
        elif self.text_alignment == 1:
            self.text_alignment_centre_radiobutton.set_active(True)
        else:
            self.text_alignment_right_radiobutton.set_active(True)

        # return the dialog
        self._first_run = False
        print("end create dialog contents")
        return builder.get_object('main_notebook')

    def on_cover_size_scale_changed(self, scale):
        self._cover_size = scale.get_value()

        def delay(*args):
            print('delay')
            print(self._cover_size_delay)
            self._cover_size_delay = self._cover_size_delay + 1

            if self._cover_size_delay >= 8:
                gs = GSetting()
                self.settings[gs.PluginKey.COVER_SIZE] = self._cover_size
                self._cover_size_delay = 0
                return False

            return True

        if self._cover_size_delay == 0:
            Gdk.threads_add_timeout(GLib.PRIORITY_DEFAULT_IDLE, 100, delay, None)
        else:
            self._cover_size_delay = 1

    def on_flow_combobox_changed(self, combobox):
        current_val = combobox.get_model()[combobox.get_active()][0]
        gs = GSetting()
        if self.settings[gs.PluginKey.FLOW_APPEARANCE] != current_val:
            if current_val == 'flow-vert':
                default_size = 150
            else:
                default_size = 600

            self.settings[gs.PluginKey.FLOW_WIDTH] = default_size

            if current_val == 'carousel':
                self.settings[gs.PluginKey.FLOW_HIDE_CAPTION] = True

    def on_background_radio_toggled(self, button):
        if button.get_active():
            gs = GSetting()
            if button == self.white_radiobutton:
                self.settings[gs.PluginKey.FLOW_BACKGROUND_COLOUR] = 'W'
            else:
                self.settings[gs.PluginKey.FLOW_BACKGROUND_COLOUR] = 'B'

    def on_display_text_pos_radio_toggled(self, button):
        if self._first_run:
            return

        if button.get_active():
            gs = GSetting()
            if button == self.display_text_under_radiobutton:
                self.settings[gs.PluginKey.DISPLAY_TEXT_POS] = True
            else:
                self.settings[gs.PluginKey.DISPLAY_TEXT_POS] = False
                self.settings[gs.PluginKey.ADD_SHADOW] = False

    def on_text_alignment_radiobutton_toggled(self, button):
        if self._first_run:
            return

        if button.get_active():
            gs = GSetting()
            if button == self.text_alignment_left_radiobutton:
                self.settings[gs.PluginKey.TEXT_ALIGNMENT] = 0
            elif button == self.text_alignment_centre_radiobutton:
                self.settings[gs.PluginKey.TEXT_ALIGNMENT] = 1
            else:
                self.settings[gs.PluginKey.TEXT_ALIGNMENT] = 2

    def on_add_shadow_checkbox_toggled(self, button):
        if button.get_active():
            # gs = GSetting()
            # self.settings[gs.PluginKey.DISPLAY_TEXT_POS] = True
            self.display_text_under_radiobutton.set_active(True)

    def rating_changed_callback(self, stars):
        print("rating_changed_callback")
        gs = GSetting()
        self.settings[gs.PluginKey.RATING] = self.stars.get_rating()

    def on_save_button_clicked(self, button):
        '''
        action when genre edit area is saved
        '''
        entry_value = self.genre_entry.get_text()
        treeiter = self.genre_combobox.get_active_iter()
        icon_value = self.alt_liststore[treeiter][0]
        # model 0 is the icon name, model 1 is the pixbuf

        if self.amend_mode:
            key = self._sheet.amend_genre_info(self.current_genre,
                                               entry_value, icon_value)

            self.alt_user_liststore[self._iters[(self.current_genre,
                                                 self.GENRE_LIST)]][1] = self._sheet[self._sheet.genre_alternate[key]]
            self.alt_user_liststore[self._iters[(self.current_genre,
                                                 self.GENRE_LIST)]][0] = key.name
            store_iter = self._iters[(self.current_genre, self.GENRE_LIST)]
            del self._iters[(self.current_genre, self.GENRE_LIST)]
            self._iters[(key.name, self.GENRE_LIST)] = store_iter

        else:
            self.amend_mode = True
            key = self._sheet.amend_genre_info('',
                                               entry_value, icon_value)
            self.current_genre = key.name

            store_iter = self.alt_user_liststore.append([key.name,
                                                         self._sheet[self._sheet.genre_alternate[key]],
                                                         self._sheet.genre_alternate[key]])
            self._iters[(key.name, self.GENRE_LIST)] = store_iter
            selection = self.genre_view.get_selection()
            selection.select_iter(store_iter)

        self.save_button.set_sensitive(False)
        self._toggle_new_genre_state()

    def on_genre_filechooserbutton_file_set(self, filechooser):
        '''
        action when genre new icon button is pressed
        '''
        key = self._sheet.add_genre_icon(self.filechooserdialog.get_filename())
        store_iter = self.alt_liststore.append([key.name, self._sheet[key.name]])
        self._iters[(key.name, self.GENRE_POPUP)] = store_iter

        gs = GSetting()
        last_genre_folder = self.filechooserdialog.get_current_folder()

        print(last_genre_folder)
        print(self.filechooserdialog.get_filename())
        if last_genre_folder:
            self.settings[gs.PluginKey.LAST_GENRE_FOLDER] = last_genre_folder

    def on_genre_view_selection_changed(self, view):
        '''
        action when user selects a row in the list of genres
        '''
        model, genre_iter = view.get_selected()
        if genre_iter:
            self.genre_entry.set_text(model[genre_iter][0])
            index = model[genre_iter][2]
            if index != '':
                self.genre_combobox.set_active_iter(self._iters[(index, self.GENRE_POPUP)])
                self.amend_mode = True
                self.current_genre = rb3compat.unicodestr(model[genre_iter][0], 'utf-8')
        else:
            self.genre_entry.set_text('')
            self.genre_combobox.set_active_iter(None)
            self.amend_mode = False

        if self.blank_iter and self.amend_mode:
            try:
                index = model[self.blank_iter][0]
                if index == '':
                    model.remove(self.blank_iter)
                    self.blank_iter = None
            except:
                self.blank_iter = None

    def on_add_button_clicked(self, button):
        '''
        action when a new genre is added to the table
        '''
        self.genre_entry.set_text('')
        self.genre_combobox.set_active(-1)
        self.amend_mode = False
        self.blank_iter = self.alt_user_liststore.append(['', None, ''])
        selection = self.genre_view.get_selection()
        selection.select_iter(self.blank_iter)

    def on_delete_button_clicked(self, button):
        '''
        action when a genre is to be deleted
        '''
        selection = self.genre_view.get_selection()

        model, genre_iter = selection.get_selected()
        if genre_iter:
            index = rb3compat.unicodestr(model[genre_iter][0], 'utf-8')
            model.remove(genre_iter)

            if index:
                del self._iters[(index, self.GENRE_LIST)]
                self._sheet.delete_genre(index)

                self._toggle_new_genre_state()

    def set_save_sensitivity(self, _):
        '''
        action to toggle the state of the save button depending
        upon the values entered in the genre edit fields
        '''
        entry_value = self.genre_entry.get_text()
        treeiter = self.genre_combobox.get_active_iter()

        entry_value = rb3compat.unicodestr(entry_value, 'utf-8')
        enable = False
        try:
            test = self._iters[(entry_value, self.GENRE_LIST)]
            if RB.search_fold(self.current_genre) == RB.search_fold(entry_value):
                # if the current entry is the same then could save
                enable = True
        except:
            # reach here if this is a brand new entry
            enable = True

        if treeiter == None or entry_value == None or entry_value == "":
            # no icon chosen, or no entry value then nothing to save
            enable = False

        self.save_button.set_sensitive(enable)

    def _toggle_new_genre_state(self):
        '''
        fire an event - uses gsettings and an object such as a
        controller connects to receive the signal that a new or amended
        genre has been made
        '''
        gs = GSetting()
        test = self.settings[gs.PluginKey.NEW_GENRE_ICON]

        if test:
            test = False
        else:
            test = True

        self.settings[gs.PluginKey.NEW_GENRE_ICON] = test

    def on_show_launchpad_toggled(self, button):
        self.launchpad_label.set_visible(button.get_active())
