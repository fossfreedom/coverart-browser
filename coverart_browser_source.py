# -*- Mode: python; coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
#
# Copyright (C) 2012 - fossfreedom
# Copyright (C) 2012 - Agustin Carrasco
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of thie GNU General Public License as published by
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

import rb

from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gio
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import RB

from coverart_album import AlbumManager
from coverart_entryview import CoverArtEntryView as EV
from coverart_search import CoverSearchPane
from coverart_browser_prefs import GSetting
from coverart_browser_prefs import CoverLocale
from stars import ReactiveStar
from coverart_timer import ttimer
from coverart_widgets import PlaylistPopupButton
from coverart_widgets import GenrePopupButton
from coverart_widgets import DecadePopupButton


class CoverArtBrowserSource(RB.Source):
    '''
    Source utilized by the plugin to show all it's ui.
    '''
    custom_statusbar_enabled = GObject.property(type=bool, default=False)
    display_bottom_enabled = GObject.property(type=bool, default=False)
    rating_threshold = GObject.property(type=float, default=0)
    toolbar_pos = GObject.property(type=str, default='main')
    sort_order = GObject.property(type=bool, default=False)

    # unique instance of the source
    instance = None

    def __init__(self, **kargs):
        '''
        Initializes the source.
        '''
        super(CoverArtBrowserSource, self).__init__(
            **kargs)

        # create source_source_settings and connect the source's properties
        self.gs = GSetting()

        self._connect_properties()

        self.filter_type = 'all'
        self.search_text = ''
        self.hasActivated = False
        self.last_toolbar_pos = None
        self.last_width = 0
        self.quick_search_idle = 0
        self.last_selected_album = None
        self.click_count = 0

    def _connect_properties(self):
        '''
        Connects the source properties to the saved preferences.
        '''
        print "CoverArtBrowser DEBUG - _connect_properties"
        setting = self.gs.get_setting(self.gs.Path.PLUGIN)

        setting.bind(self.gs.PluginKey.CUSTOM_STATUSBAR, self,
            'custom_statusbar_enabled', Gio.SettingsBindFlags.GET)
        setting.bind(self.gs.PluginKey.DISPLAY_BOTTOM, self,
            'display_bottom_enabled', Gio.SettingsBindFlags.GET)
        setting.bind(self.gs.PluginKey.RATING, self,
            'rating_threshold', Gio.SettingsBindFlags.GET)
        setting.bind(self.gs.PluginKey.TOOLBAR_POS, self,
            'toolbar_pos', Gio.SettingsBindFlags.GET)
        setting.bind(self.gs.PluginKey.SORT_ORDER, self, 'sort_order',
            Gio.SettingsBindFlags.DEFAULT)

        print "CoverArtBrowser DEBUG - end _connect_properties"

    def do_get_status(self, *args):
        '''
        Method called by Rhythmbox to figure out what to show on this source
        statusbar.
        If the custom statusbar is disabled, the source will
        show the selected album info.
        Also, it makes sure to show the progress on the album loading.s
        '''
        try:
            progress = self.album_manager.progress
            progress_text = _('Loading...') if progress < 1 else ''
        except:
            progress = 1
            progress_text = ''

        return (self.status, progress_text, progress)

    def do_show_popup(self):
        '''
        Method called by Rhythmbox when an action on our source prompts it
        to show a popup.
        '''
        print "CoverArtBrowser DEBUG - do_show_popup"
        self.source_menu.popup(None, None, None, None, 0,
            Gtk.get_current_event_time())

        print "CoverArtBrowser DEBUG - end do_show_popup"
        return True

    def do_selected(self):
        '''
        Called by Rhythmbox when the source is selected. It makes sure to
        create the ui the first time the source is showed.
        '''
        print "CoverArtBrowser DEBUG - do_selected"

        # first time of activation -> add graphical stuff
        if not self.hasActivated:
            self.do_impl_activate()

            #indicate that the source was activated before
            self.hasActivated = True

        print "CoverArtBrowser DEBUG - end do_selected"

    def do_impl_activate(self):
        '''
        Called by do_selected the first time the source is activated.
        It creates all the source ui and connects the necesary signals for it
        correct behavior.
        '''
        print "CoverArtBrowser DEBUG - do_impl_activate"

        # initialise some variables
        self.plugin = self.props.plugin
        self.shell = self.props.shell
        self.status = ''
        self.search_text = ''
        self.actiongroup = Gtk.ActionGroup('coverplaylist_submenu')
        self.favourite_actiongroup = Gtk.ActionGroup(
            'favourite_coverplaylist_submenu')
        uim = self.shell.props.ui_manager
        uim.insert_action_group(self.actiongroup)
        uim.insert_action_group(self.favourite_actiongroup)

        self.coversearchtimer = ttimer(30, -1, self.update_request_status_bar,
            None)

        # connect properties signals
        self.connect('notify::custom-statusbar-enabled',
            self.on_notify_custom_statusbar_enabled)

        self.connect('notify::display-bottom-enabled',
            self.on_notify_display_bottom_enabled)

        self.connect('notify::rating-threshold',
            self.on_notify_rating_threshold)

        #indicate that the source was activated before
        self.hasActivated = True

        self._create_ui()
        self._setup_source()
        self._apply_settings()

        print "CoverArtBrowser DEBUG - end do_impl_activate"

    def _create_ui(self):
        '''
        Creates the ui for the source and saves the important widgets onto
        properties.
        '''
        print "CoverArtBrowser DEBUG - _create_ui"

        # dialog has not been created so lets do so.
        cl = CoverLocale()
        ui = Gtk.Builder()
        ui.set_translation_domain(cl.Locale.LOCALE_DOMAIN)
        ui.add_from_file(rb.find_plugin_file(self.plugin,
            'ui/coverart_browser.ui'))

        self.toolbar_box = ui.get_object('toolbar_box')

        si = Gtk.Builder()
        si.set_translation_domain(cl.Locale.LOCALE_DOMAIN)
        si.add_from_file(rb.find_plugin_file(self.plugin,
            'ui/coverart_sidebar.ui'))

        # load the page and put it in the source
        self.sidebar = si.get_object('main_box')

        # load the page and put it in the source
        self.page = ui.get_object('main_box')
        self.pack_start(self.page, True, True, 0)

        # get widgets for main icon-view
        self.status_label = ui.get_object('status_label')
        self.covers_view = ui.get_object('covers_view')
        self.popup_menu = ui.get_object('popup_menu')
        self.cover_search_menu_item = ui.get_object('cover_search_menu_item')
        self.status_label = ui.get_object('status_label')
        self.request_status_box = ui.get_object('request_status_box')
        self.request_spinner = ui.get_object('request_spinner')
        self.request_statusbar = ui.get_object('request_statusbar')
        self.request_cancel_button = ui.get_object('request_cancel_button')
        self.paned = ui.get_object('paned')
        self.bottom_box = ui.get_object('bottom_box')
        self.bottom_expander = ui.get_object('bottom_expander')
        self.notebook = ui.get_object('bottom_notebook')

        # get widgets for source popup
        self.source_menu = ui.get_object('source_menu')
        self.source_menu_search_all_item = ui.get_object(
            'source_search_menu_item')
        self.play_favourites_album_menu_item = ui.get_object(
            'play_favourites_album_menu_item')
        self.queue_favourites_album_menu_item = ui.get_object(
            'queue_favourites_album_menu_item')
        self.favourite_playlist_menu_item = ui.get_object(
            'favourite_playlist_menu_item')
        self.playlist_sub_menu_item = ui.get_object('playlist_sub_menu_item')
        self.favourite_playlist_sub_menu_item = ui.get_object(
            'favourite_playlist_sub_menu_item')

        # get widgets for filter popup
        self.filter_menu = ui.get_object('filter_menu')
        self.filter_menu_all_item = ui.get_object('filter_all_menu_item')
        self.filter_menu_artist_item = ui.get_object('filter_artist_menu_item')
        self.filter_menu_album_artist_item = ui.get_object(
            'filter_album_artist_menu_item')
        self.filter_menu_album_item = ui.get_object('filter_album_menu_item')
        self.filter_menu_track_title_item = ui.get_object(
            'filter_track_title_menu_item')

        # quick search entry
        self.quick_search = ui.get_object('quick_search_entry')
        self.quick_search_box = ui.get_object('quick_search_box')

        self.ui = ui
        self.si = si

        print "CoverArtBrowser DEBUG - end _create_ui"

    def _toolbar(self, ui):
        '''
        setup toolbar ui - called for sidebar and main-view
        '''
        print "CoverArtBrowser DEBUG - _toolbar"

        # dialog has not been created so lets do so.
        cl = CoverLocale()

        # get widgets for main icon-view
        # the first part is to first remove the current search-entry
        # before recreating it again - we have to do this to ensure
        # the locale is set correctly i.e. the overall ui is coverart
        # locale but the search-entry uses rhythmbox translation
        align = ui.get_object('entry_search_alignment')
        align.remove(align.get_child())
        cl.switch_locale(cl.Locale.RB)
        self.search_entry = RB.SearchEntry(has_popup=True)
        align.add(self.search_entry)
        align.show_all()
        cl.switch_locale(cl.Locale.LOCALE_DOMAIN)

        self.search_entry.connect('search', self.searchchanged_callback)
        self.search_entry.connect('show-popup',
            self.search_show_popup_callback)

        self.sort_by = ui.get_object('sort_by')
        self.sort_by.initialise(self.plugin, self.shell,
            self.sorting_criteria_changed)
        self.sort_order_button = ui.get_object('sort_order')
        self.sort_order_button.initialise(self.plugin,
            self.sorting_direction_changed, self.sort_order)

        # get widget for search and apply some workarounds
        search_entry = ui.get_object('search_entry')
        search_entry.set_placeholder(_('Search album'))
        search_entry.show_all()
        self.search_entry.set_placeholder(ui.get_object(
            'filter_all_menu_item').get_label())

        # genre
        genre_button = ui.get_object('genre_button')
        genre_button.initialise(self.plugin, self.shell,
            self.genre_filter_callback)

        # get playlist popup
        playlist_button = ui.get_object('playlist_button')
        playlist_button.initialise(self.plugin, self.shell,
            self.filter_by_model)

        # decade
        decade_button = ui.get_object('decade_button')
        decade_button.initialise(self.plugin, self.shell,
            self.decade_filter_callback)

        print "CoverArtBrowser DEBUG - end _toolbar"

    def _setup_source(self):
        '''
        Setups the differents parts of the source so they are ready to be used
        by the user. It also creates and configure some custom widgets.
        '''
        print "CoverArtBrowser DEBUG - _setup_source"

        # setup iconview drag&drop support
        self.covers_view.enable_model_drag_dest([], Gdk.DragAction.COPY)
        self.covers_view.drag_dest_add_image_targets()
        self.covers_view.drag_dest_add_text_targets()
        self.covers_view.connect('drag-drop', self.on_drag_drop)
        self.covers_view.connect('drag-data-received',
            self.on_drag_data_received)

        # setup entry-view objects and widgets
        y = self.gs.get_value(self.gs.Path.PLUGIN,
            self.gs.PluginKey.PANED_POSITION)
        self.paned.set_position(y)

        # create entry view. Don't allow to reorder until the load is finished
        self.entry_view = EV(self.shell, self)
        self.entry_view.set_columns_clickable(False)
        self.shell.props.library_source.get_entry_view().set_columns_clickable(
            False)

        self.stars = ReactiveStar()
        self.stars.set_rating(0)
        a = Gtk.Alignment.new(0.5, 0.5, 0, 0)
        a.add(self.stars)

        self.stars.connect('changed', self.rating_changed_callback)

        vbox = Gtk.Box()
        vbox.set_orientation(Gtk.Orientation.VERTICAL)
        vbox.pack_start(self.entry_view, True, True, 0)
        vbox.pack_start(a, False, False, 1)
        vbox.show_all()
        self.notebook.append_page(vbox, Gtk.Label(_("Tracks")))

        # create an album manager
        self.album_manager = AlbumManager(self.plugin, self.covers_view)

        # setup cover search pane
        try:
            color = self.covers_view.get_style_context().get_background_color(
                Gtk.StateFlags.SELECTED)
            color = '#%s%s%s' % (
                str(hex(int(color.red * 255))).replace('0x', ''),
                str(hex(int(color.green * 255))).replace('0x', ''),
                str(hex(int(color.blue * 255))).replace('0x', ''))
        except:
            color = '#0000FF'

        self.cover_search_pane = CoverSearchPane(self.plugin,
            self.album_manager, color)
        self.notebook.append_page(self.cover_search_pane, Gtk.Label(
            _("Covers")))

        # connect a signal to when the info of albums is ready
        self.load_fin_id = self.album_manager.loader.connect(
            'model-load-finished', self.load_finished_callback)

        # prompt the loader to load the albums
        self.album_manager.loader.load_albums(self.props.query_model)

        # set the model to the view
        self.covers_view.set_model(self.album_manager.model.store)

        print "CoverArtBrowser DEBUG - end _setup_source"

    def _apply_settings(self):
        '''
        Applies all the settings related to the source and connects those that
        must be updated when the preferences dialog changes it's values. Also
        enables differents parts of the ui if the settings says so.
        '''
        print "CoverArtBrowser DEBUG - _apply_settings"

        # connect some signals to the loader to keep the source informed
        self.si.connect_signals(self)
        self.ui.connect_signals(self)
        self.album_mod_id = self.album_manager.model.connect('album-updated',
            self.on_album_updated)
        self.notify_prog_id = self.album_manager.connect(
            'notify::progress', lambda *args: self.notify_status_changed())
        self.toolbar_pos_id = self.connect('notify::toolbar-pos',
            self.on_notify_toolbar_pos)

        # enable some ui if necesary
        self.on_notify_rating_threshold(_)
        self.on_notify_display_bottom_enabled(_)
        self.on_notify_toolbar_pos()
        #self.sorting_direction_changed(_, True)

        print "CoverArtBrowser DEBUG - end _apply_settings"

    def load_finished_callback(self, _):
        '''
        Callback called when the loader finishes loading albums into the
        covers view model.
        '''
        print "CoverArtBrowser DEBUG - load_finished_callback"

        if not self.request_status_box.get_visible():
            # it should only be enabled if no cover request is going on
            self.source_menu_search_all_item.set_sensitive(True)

        # enable sorting on the entryview
        self.entry_view.set_columns_clickable(True)
        self.shell.props.library_source.get_entry_view().set_columns_clickable(
            True)

        print "CoverArtBrowser DEBUG - end load_finished_callback"

    def on_notify_custom_statusbar_enabled(self, *args):
        '''
        Callback for when the option to show the custom statusbar is enabled
        or disabled from the plugin's preferences dialog.
        '''
        print "CoverArtBrowser DEBUG - on_notify_custom_statusbar_enabled"

        if self.custom_statusbar_enabled:
            self.status = ''
            self.notify_status_changed()
        else:
            self.status_label.hide()

        self.selectionchanged_callback(self.covers_view)

        print "CoverArtBrowser DEBUG - end on_notify_custom_statusbar_enabled"

    def on_notify_rating_threshold(self, *args):
        '''
        Callback called when the option rating threshold is changed
        on the plugin's preferences dialog
        If the threshold is zero then the rating menu options in the
        coverview should not be enabled
        '''
        print "CoverArtBrowser DEBUG - on_notify_rating_threshold"

        if self.rating_threshold > 0:
            enable_menus = True
        else:
            enable_menus = False

        self.play_favourites_album_menu_item.set_sensitive(enable_menus)
        self.queue_favourites_album_menu_item.set_sensitive(enable_menus)
        self.favourite_playlist_menu_item.set_sensitive(enable_menus)

        print "CoverArtBrowser DEBUG - end on_notify_rating_threshold"

    def on_notify_toolbar_pos(self, *args):
        '''
        Callback called when the toolbar position is changed in
        preferences
        '''
        print "CoverArtBrowser DEBUG - on_notify_toolbar_pos"

        if self.last_toolbar_pos == 'left':
            self.shell.remove_widget(self.sidebar, RB.ShellUILocation.SIDEBAR)

        if self.last_toolbar_pos == 'right':
            self.shell.remove_widget(self.sidebar,
                RB.ShellUILocation.RIGHT_SIDEBAR)

        if self.toolbar_pos == 'main':
            self._toolbar(self.ui)
            self.toolbar_box.set_visible(True)

        if self.toolbar_pos == 'left':
            self.toolbar_box.set_visible(False)
            self._toolbar(self.si)
            self.shell.add_widget(self.sidebar,
                        RB.ShellUILocation.SIDEBAR,
                        expand=False,
                        fill=False)

        if self.toolbar_pos == 'right':
            self.toolbar_box.set_visible(False)
            self._toolbar(self.si)
            self.shell.add_widget(self.sidebar,
                        RB.ShellUILocation.RIGHT_SIDEBAR,
                        expand=False,
                        fill=False)

        self.last_toolbar_pos = self.toolbar_pos

        print "CoverArtBrowser DEBUG - end on_notify_toolbar_pos"

    def on_notify_display_bottom_enabled(self, *args):
        '''
        Callback called when the option 'display tracks' is enabled or disabled
        on the plugin's preferences dialog
        '''
        print "CoverArtBrowser DEBUG - on_notify_display_bottom_enabled"

        if self.display_bottom_enabled:
            # make the entry view visible
            self.bottom_box.set_visible(True)

            self.bottom_expander_expanded_callback(
                self.bottom_expander, None)

            # update it with the current selected album
            self.selectionchanged_callback(self.covers_view)

        else:
            if self.bottom_expander.get_expanded():
                y = self.paned.get_position()
                self.gs.set_value(self.gs.Path.PLUGIN,
                                  self.gs.PluginKey.PANED_POSITION,
                                  y)

            self.bottom_box.set_visible(False)

        print "CoverArtBrowser DEBUG - end on_notify_display_bottom_enabled"

    def paned_button_press_callback(self, *args):
        '''
        This callback allows or denies the paned handle to move depending on
        the expanded state of the entry_view
        '''
        print "CoverArtBrowser DEBUG - paned_button_press_callback"
        return not self.bottom_expander.get_expanded()

    def on_paned_button_release_event(self, *args):
        '''
        Callback when the paned handle is released from its mouse click.
        '''

        print "CoverArtBrowser DEBUG - on_paned_button_release_event"

        if self.bottom_expander.get_expanded():
            # save the new position
            new_y = self.paned.get_position()
            self.gs.set_value(self.gs.Path.PLUGIN,
                self.gs.PluginKey.PANED_POSITION, new_y)

        print "CoverArtBrowser DEBUG - end on_paned_button_release_event"

    def on_album_updated(self, model, path, tree_iter):
        '''
        Callback called by the album loader when one of the albums managed
        by him gets modified in some way.
        '''
        album = model.get_from_path(path)
        selected = self.get_selected_albums()

        if album in selected:
            # update the selection since it may have changed
            self.selectionchanged_callback(self.covers_view)

            if album is selected[0] and \
                self.notebook.get_current_page() == \
                self.notebook.page_num(self.cover_search_pane):
                # also, if it's the first, update the cover search pane
                self.cover_search_pane.clear()
                self.cover_search_pane.do_search(album)

    def on_overlay_key_press(self, overlay, event, *args):
        if not self.quick_search_box.get_visible() and \
            event.keyval not in [Gdk.KEY_Shift_L, Gdk.KEY_Shift_R,
            Gdk.KEY_Control_L, Gdk.KEY_Control_R, Gdk.KEY_Escape]:
            # grab focus, redirect the pressed key and make the quick search
            # entry visible
            self.quick_search.grab_focus()
            self.quick_search.im_context_filter_keypress(event)
            self.quick_search_box.show_all()

        elif event.keyval == Gdk.KEY_Escape:
            self.hide_quick_search()

        return False

    def on_quick_search_focus_lost(self, quick_search, event, *args):
        self.hide_quick_search()

        return False

    def show_properties_menu_item_callback(self, menu_item):
        '''
        Callback called when the show album properties option is selected from
        the cover view popup. It shows a SongInfo dialog showing the selected
        albums' entries info, which can be modified.
        '''
        print "CoverArtBrowser DEBUG - show_properties_menu_item_callback"

        self.entry_view.select_all()

        info_dialog = RB.SongInfo(source=self, entry_view=self.entry_view)

        info_dialog.show_all()

        print "CoverArtBrowser DEBUG - end show_properties_menu_item_callback"

    def search_show_popup_callback(self, entry):
        '''
        Callback called by the search entry when the magnifier is clicked.
        It prompts the user through a popup to select a filter type.
        '''
        print "CoverArtBrowser DEBUG - search_show_popup_callback"

        self.filter_menu.popup(None, None, None, None, 0,
            Gtk.get_current_event_time())

        print "CoverArtBrowser DEBUG - end search_show_popup_callback"

    def searchchanged_callback(self, entry, text):
        '''
        Callback called by the search entry when a new search must
        be performed.
        '''
        print "CoverArtBrowser DEBUG - searchchanged_callback"
        self.search_text = text
        self.album_manager.model.replace_filter(self.filter_type, text)

        print "CoverArtBrowser DEBUG - end searchchanged_callback"

    def filter_menu_callback(self, radiomenu):
        '''
        Callback called when an item from the filters popup menu is clicked.
        It changes the current filter type for the search to the one selected
        on the popup.
        '''
        print "CoverArtBrowser DEBUG - filter_menu_callback"

        # remove old filter
        self.album_manager.model.remove_filter(self.filter_type, False)

        # radiomenu is of type GtkRadioMenuItem

        if radiomenu == self.filter_menu_all_item:
            self.filter_type = 'all'
        elif radiomenu == self.filter_menu_album_item:
            self.filter_type = 'album_name'
        elif radiomenu == self.filter_menu_artist_item:
            self.filter_type = 'artist'
        elif radiomenu == self.filter_menu_album_artist_item:
            self.filter_type = 'album_artist'
        elif radiomenu == self.filter_menu_track_title_item:
            self.filter_type = 'track'
        else:
            assert "unknown radiomenu"

        if self.search_text == '':
            self.search_entry.set_placeholder(radiomenu.get_label())

        self.searchchanged_callback(_, self.search_text)

        print "CoverArtBrowser DEBUG - end filter_menu_callback"

    def filter_by_model(self, model=None):
        '''
        resets what is displayed in the coverview with contents from the
        new query_model
        '''
        print "CoverArtBrowser DEBUG - reset_coverview"
        if not model:
            self.album_manager.model.remove_filter('model')
        else:
            self.album_manager.model.replace_filter('model', model)

        print "CoverArtBrowser DEBUG - end reset_coverview"

    def update_iconview_callback(self, scrolled, *args):
        '''
        Callback called by the cover view when its view port gets resized.
        It forces the cover_view to redraw it's contents to fill the available
        space.
        '''
        width = scrolled.get_allocated_width()

        if width != self.last_width:
            # don't need to reacommodate if the bottom pane is being resized
            print "CoverArtBrowser DEBUG - update_iconview_callback"
            self.covers_view.set_columns(0)
            self.covers_view.set_columns(-1)

            # update width
            self.last_width = width

    def mouseclick_callback(self, iconview, event):
        '''
        Callback called when the user clicks somewhere on the cover_view.
        If it's a right click, it shows a popup showing different actions to
        perform with the selected album.
        '''
        print "CoverArtBrowser DEBUG - mouseclick_callback()"
        x = int(event.x)
        y = int(event.y)
        pthinfo = iconview.get_path_at_pos(x, y)

        if event.type is Gdk.EventType.BUTTON_PRESS and pthinfo:
            if event.triggers_context_menu():
                # to show the context menu
                # if the item being clicked isn't selected, we should clear
                # the current selection
                if len(iconview.get_selected_items()) > 0 and \
                    not iconview.path_is_selected(pthinfo):
                    iconview.unselect_all()

                iconview.select_path(pthinfo)
                iconview.set_cursor(pthinfo, None, False)

                self.popup_menu.popup(None, None, None, None, event.button,
                    event.time)

            else:
                # to expand the entry view
                ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
                shift = event.state & Gdk.ModifierType.SHIFT_MASK

                self.click_count += 1

                if not ctrl and not shift and self.click_count == 1:
                    album = self.album_manager.model.get_from_path(pthinfo)\
                        if pthinfo else None
                    Gdk.threads_add_timeout(GLib.PRIORITY_DEFAULT_IDLE, 250,
                        self._timeout_expand, album)

        print "CoverArtBrowser DEBUG - end mouseclick_callback()"

    def _timeout_expand(self, album):
        '''
        helper function - if the entry is manually expanded
        then if necessary scroll the view to the last selected album
        '''
        print "CoverArtBrowser DEBUG - _timeout_expand"

        if album and self.click_count == 1 \
            and self.last_selected_album is album:
            # check if it's a second or third click on the album and expand
            # or collapse the entry view accordingly
            self.bottom_expander.set_expanded(
                not self.bottom_expander.get_expanded())

        # update the selected album
        selected = self.get_selected_albums()
        self.last_selected_album = selected[0] if len(selected) == 1 else None

        # clear the click count
        self.click_count = 0

    def item_activated_callback(self, iconview, path):
        '''
        Callback called when the cover view is double clicked or space-bar
        is pressed. It plays the selected album
        '''
        print "CoverArtBrowser DEBUG - item_activated_callback"
        self.play_selected_album()

        return True

    def get_selected_albums(self):
        '''
        Retrieves the currently selected albums on the cover_view.
        '''
        selected_albums = []

        for selected in self.covers_view.get_selected_items():
            selected_albums.append(self.album_manager.model.get_from_path(
                selected))

        return selected_albums

    def play_selected_album(self, favourites=False):
        '''
        Utilitary method that plays all entries from an album into the play
        queue.
        '''
        # callback when play an album
        print "CoverArtBrowser DEBUG - play_selected_album"

        # clear the queue
        play_queue = self.shell.props.queue_source
        for row in play_queue.props.query_model:
            play_queue.remove_entry(row[0])

        self.queue_selected_album(play_queue, favourites)

        # Start the music
        player = self.shell.props.shell_player
        player.stop()
        player.set_playing_source(self.shell.props.queue_source)
        player.playpause(True)
        print "CoverArtBrowser DEBUG - end play_selected_album"

    def queue_selected_album(self, source, favourites=False):
        '''
        Utilitary method that queues all entries from an album into the play
        queue.
        '''
        print "CoverArtBrowser DEBUG - queue_selected_album"

        selected_albums = self.get_selected_albums()
        threshold = self.rating_threshold if favourites else 0

        for album in selected_albums:
            # Retrieve and sort the entries of the album
            tracks = album.get_tracks(threshold)

            # Add the songs to the play queue
            for track in tracks:
                source.add_entry(track.entry, -1)

        print "CoverArtBrowser DEBUG - end queue_select_album"

    def play_album_menu_item_callback(self, _):
        '''
        Callback called when the play album item from the cover view popup is
        selected. It cleans the play queue and queues the selected album.
        '''
        print "CoverArtBrowser DEBUG - play_album_menu_item_callback"

        self.play_selected_album()

        print "CoverArtBrowser DEBUG - end play_album_menu_item_callback"

    def queue_album_menu_item_callback(self, _):
        '''
        Callback called when the queue album item from the cover view popup is
        selected. It queues the selected album at the end of the play queue.
        '''
        print "CoverArtBrowser DEBUG - queue_album_menu_item_callback()"

        self.queue_selected_album(self.shell.props.queue_source)

        print "CoverArtBrowser DEBUG - end queue_album_menu_item_callback()"

    def queue_favourites_album_menu_item_callback(self, _):
        '''
        Callback called when the queue-favourites album item from the cover
        view popup is selected. It queues the selected album at the end of the
        play queue.
        '''
        print '''CoverArtBrowser DEBUG -
            queue_favourites_album_menu_item_callback()'''

        self.queue_selected_album(self.shell.props.queue_source, True)

        print '''CoverArtBrowser DEBUG -
            end queue_favourites_album_menu_item_callback()'''

    def play_favourites_album_menu_item_callback(self, _):
        '''
        Callback called when the play favourites album item from the cover view
        popup is selected. It queues the selected album at the end of the play
        queue.
        '''
        print '''CoverArtBrowser DEBUG -
            play_favourites_album_menu_item_callback()'''

        self.play_selected_album(True)

        print '''CoverArtBrowser DEBUG -
            end play_favourites_album_menu_item_callback()'''

    def playlist_menu_item_callback(self, menu_item):
        print "CoverArtBrowser DEBUG - playlist_menu_item_callback"

        self.playlist_fillmenu(self.playlist_sub_menu_item,
                               self.actiongroup,
                               self.add_to_static_playlist_menu_item_callback)

    def favourite_playlist_menu_item_callback(self, menu_item):
        print "CoverArtBrowser DEBUG - favourite_playlist_menu_item_callback"

        self.playlist_fillmenu(self.favourite_playlist_sub_menu_item,
                               self.favourite_actiongroup,
                               self.add_to_static_playlist_menu_item_callback,
                               True)

    def playlist_fillmenu(self, menubar, actiongroup, func, favourite=False):
        print "CoverArtBrowser DEBUG - playlist_fillmenu"

        uim = self.shell.props.ui_manager

        playlist_manager = self.shell.props.playlist_manager
        playlists_entries = playlist_manager.get_playlists()

        #tidy up old playlists menu items before recreating the list
        for action in actiongroup.list_actions():
            actiongroup.remove_action(action)

        count = 0

        for menu_item in menubar:
            if count > 1:  # ignore the first two menu items
                menubar.remove(menu_item)
            count += 1

            menubar.show_all()
            uim.ensure_update()

        if playlists_entries:
            for playlist in playlists_entries:
                if playlist.props.is_local and \
                    isinstance(playlist, RB.StaticPlaylistSource):

                    new_menu_item = Gtk.MenuItem(label=playlist.props.name)

                    action = Gtk.Action(label=playlist.props.name,
                        name=playlist.props.name,
                       tooltip='', stock_id=Gtk.STOCK_CLEAR)
                    action.connect('activate', func, playlist, favourite)
                    new_menu_item.set_related_action(action)
                    menubar.append(new_menu_item)
                    actiongroup.add_action(action)

            menubar.show_all()
            uim.ensure_update()

    def add_to_static_playlist_menu_item_callback(self, action, playlist,
        favourite):
        print '''CoverArtBrowser DEBUG -
            add_to_static_playlist_menu_item_callback'''
        self.queue_selected_album(playlist, favourite)

    def add_playlist_menu_item_callback(self, menu_item):
        print '''CoverArtBrowser DEBUG - add_playlist_menu_item_callback'''
        playlist_manager = self.shell.props.playlist_manager
        playlist = playlist_manager.new_playlist('', False)

        self.queue_selected_album(playlist, False)

    def favourite_add_playlist_menu_item_callback(self, menu_item):
        print '''CoverArtBrowser DEBUG -
         favourite_add_playlist_menu_item_callback'''
        playlist_manager = self.shell.props.playlist_manager
        playlist = playlist_manager.new_playlist('', False)

        self.queue_selected_album(playlist, True)

    def cover_search_menu_item_callback(self, menu_item):
        '''
        Callback called when the search cover option is selected from the
        cover view popup. It prompts the album loader to retrieve the selected
        album cover
        '''
        print "CoverArtBrowser DEBUG - cover_search_menu_item_callback()"
        selected_albums = self.get_selected_albums()

        self.request_status_box.show_all()
        self.source_menu_search_all_item.set_sensitive(False)
        self.cover_search_menu_item.set_sensitive(False)

        self.coversearchtimer.Start()

        self.album_manager.cover_man.search_covers(selected_albums,
            self.update_request_status_bar)

        print "CoverArtBrowser DEBUG - end cover_search_menu_item_callback()"

    def search_all_covers_callback(self, _):
        '''
        Callback called when the search all covers option is selected from the
        source's popup. It prompts the album loader to request ALL album's
        covers
        '''
        print "CoverArtBrowser DEBUG - search_all_covers_callback()"
        self.request_status_box.show_all()
        self.source_menu_search_all_item.set_sensitive(False)
        self.cover_search_menu_item.set_sensitive(False)

        self.coversearchtimer.Start()

        self.album_manager.cover_man.search_covers(
            callback=self.update_request_status_bar)

        print "CoverArtBrowser DEBUG - end search_all_covers_callback()"

    def update_request_status_bar(self, album):
        '''
        Callback called by the album loader starts performing a new cover
        request. It prompts the source to change the content of the request
        statusbar.
        '''
        print "CoverArtBrowser DEBUG - update_request_status_bar"

        if album:
            Gdk.threads_enter()
            self.request_statusbar.set_text(
                (_('Requesting cover for %s - %s...') % (album.name,
                album.artist)).decode('UTF-8'))
            Gdk.threads_leave()
            if self.coversearchtimer:
                self.coversearchtimer.Stop()
                self.coversearchtimer.Start()
        else:
            Gdk.threads_enter()
            self.request_status_box.hide()
            self.source_menu_search_all_item.set_sensitive(True)
            self.cover_search_menu_item.set_sensitive(True)
            self.request_cancel_button.set_sensitive(True)
            self.coversearchtimer.Stop()
            Gdk.threads_leave()
        print "CoverArtBrowser DEBUG - end update_request_status_bar"

    def cancel_request_callback(self, _):
        '''
        Callback connected to the cancel button on the request statusbar.
        When called, it prompts the album loader to cancel the full cover
        search after the current cover.
        '''
        print "CoverArtBrowser DEBUG - cancel_request_callback"

        self.request_cancel_button.set_sensitive(False)
        self.album_manager.cover_man.cancel_cover_request()

        print "CoverArtBrowser DEBUG - end cancel_request_callback"

    def selectionchanged_callback(self, widget):
        '''
        Callback called when an item from the cover view gets selected.
        It changes the content of the statusbar (which statusbar is dependant
        on the custom_statusbar_enabled property) to show info about the
        current selected album.
        '''
        print "CoverArtBrowser DEBUG - selectionchanged_callback"

        # clear the entry view
        self.entry_view.clear()

        selected = self.get_selected_albums()

        cover_search_pane_visible = self.notebook.get_current_page() == \
            self.notebook.page_num(self.cover_search_pane)

        if not selected:
            # if no album selected, clean the status and the cover tab if
            # if selected
            self.update_statusbar()

            if cover_search_pane_visible:
                self.cover_search_pane.clear()

            return
        elif len(selected) == 1:
            self.stars.set_rating(selected[0].rating)

            if selected[0] is not self.last_selected_album:
                # when the selection changes we've to take into account two
                # things
                if not self.click_count:
                    # we may be using the arrows, so if there is no mouse
                    # involved, we should change the last selected
                    self.last_selected_album = selected[0]
                else:
                    # we may've doing a fast change after a valid second click,
                    # so it shouldn't be considered a double click
                    self.click_count -= 1
        else:
            self.stars.set_rating(0)

        track_count = 0
        duration = 0

        for album in selected:
            # Calculate duration and number of tracks from that album
            track_count += album.track_count
            duration += album.duration / 60

            # add the album to the entry_view
            self.entry_view.add_album(album)

        # now lets build up a status label containing some 'interesting stuff'
        # about the album
        if len(selected) == 1:
            status = (_('%s by %s') % (album.name, album.artist)).decode(
                'UTF-8')
        else:
            status = (_('%d selected albums ') % (len(selected))).decode(
                'UTF-8')

        if track_count == 1:
            status += (_(' with 1 track')).decode('UTF-8')
        else:
            status += (_(' with %d tracks') % track_count).decode('UTF-8')

        if duration == 1:
            status += (_(' and a duration of 1 minute')).decode('UTF-8')
        else:
            status += (_(' and a duration of %d minutes') % duration).decode(
                'UTF-8')

        self.update_statusbar(status)

        # update the cover search pane with the first selected album
        if cover_search_pane_visible:
            self.cover_search_pane.do_search(selected[0])

        print "CoverArtBrowser DEBUG - end selectionchanged_callback"

    def update_statusbar(self, status=''):
        '''
        Utility method that updates the status bar.
        '''
        print "CoverArtBrowser DEBUG - update_statusbar"

        if self.custom_statusbar_enabled:
            # if the custom statusbar is enabled... use it.
            self.status_label.set_text(status)
            self.status_label.show()
        else:
            # use the global statusbar from Rhythmbox
            self.status = status
            self.notify_status_changed()

        print "CoverArtBrowser DEBUG - end update_statusbar"

    def bottom_expander_expanded_callback(self, action, param):
        '''
        Callback connected to expanded signal of the paned GtkExpander
        '''
        print "CoverArtBrowser DEBUG - bottom_expander_expanded_callback"

        expand = action.get_expanded()

        if not expand:
            # move the lower pane to the bottom since it's collapsed
            (x, y) = Gtk.Widget.get_toplevel(self.status_label).get_size()
            new_y = self.paned.get_position()
            self.gs.set_value(self.gs.Path.PLUGIN,
                self.gs.PluginKey.PANED_POSITION, new_y)
            self.paned.set_position(y - 10)
        else:
            # restitute the lower pane to it's expanded size
            new_y = self.gs.get_value(self.gs.Path.PLUGIN,
                self.gs.PluginKey.PANED_POSITION)

            if new_y == 0:
                # if there isn't a saved size, use half of the space
                (x, y) = Gtk.Widget.get_toplevel(self.status_label).get_size()
                new_y = (y / 2)
                self.gs.set_value(self.gs.Path.PLUGIN,
                    self.gs.PluginKey.PANED_POSITION, new_y)

            self.paned.set_position(new_y)

            # acomodate the viewport if there's an album selected
            if self.last_selected_album:
                def scroll_to_album(*args):
                    # acomodate the viewport if there's an album selected
                    path = self.album_manager.model.get_path(
                        self.last_selected_album)

                    self.covers_view.scroll_to_path(path, False, 0, 0)

                    return False

                Gdk.threads_add_idle(GObject.PRIORITY_DEFAULT_IDLE,
                    scroll_to_album, None)

        print "CoverArtBrowser DEBUG - end bottom_expander_expanded_callback"

    def sorting_criteria_changed(self, sort_by):
        '''
        Callback called when a radio corresponding to a sorting order is
        toggled. It changes the sorting function and reorders the cover model.
        '''
        print "CoverArtBrowser DEBUG - sorting_criteria_changed"

        #if not radio.get_active():
        #    return

        print "sorting by %s" % sort_by
        self.sort_prop = sort_by
        self.album_manager.model.sort(self.sort_prop, self.sort_order)

        print "CoverArtBrowser DEBUG - end sorting_criteria_changed"

    def sorting_direction_changed(self, sort_by):
        '''
        Callback called when the sort toggle button is
        toggled. It changes the sorting direction and reorders the cover model
        '''
        print "CoverArtBrowser DEBUG - sorting_direction_changed"

        self.album_manager.model.sort(getattr(self, 'sort_prop', 'name'),
            sort_by)

        print "CoverArtBrowser DEBUG - end sorting_direction_changed"

    def on_drag_drop(self, widget, context, x, y, time):
        '''
        Callback called when a drag operation finishes over the cover view
        of the source. It decides if the dropped item can be processed as
        an image to use as a cover.
        '''
        print "CoverArtBrowser DEBUG - on_drag_drop"

        # stop the propagation of the signal (deactivates superclass callback)
        widget.stop_emission('drag-drop')

        # obtain the path of the icon over which the drag operation finished
        path, pos = widget.get_dest_item_at_pos(x, y)
        result = path is not None

        if result:
            target = self.covers_view.drag_dest_find_target(context, None)
            widget.drag_get_data(context, target, time)

        print "CoverArtBrowser DEBUG - end on_drag_drop"

        return result

    def on_drag_data_received(self, widget, drag_context, x, y, data, info,
        time):
        '''
        Callback called when the drag source has prepared the data (pixbuf)
        for us to use.
        '''
        print "CoverArtBrowser DEBUG - on_drag_data_received"

        # stop the propagation of the signal (deactivates superclass callback)
        widget.stop_emission('drag-data-received')

        # get the album and the info and ask the loader to update the cover
        path, pos = widget.get_dest_item_at_pos(x, y)
        album = widget.get_model()[path][2]

        pixbuf = data.get_pixbuf()

        if pixbuf:
            self.album_manager.cover_man.update_cover(album, pixbuf)
        else:
            uri = data.get_text()
            self.album_manager.cover_man.update_cover(album, uri=uri)

        # call the context drag_finished to inform the source about it
        drag_context.finish(True, False, time)

        print "CoverArtBrowser DEBUG - end on_drag_data_received"

    def notebook_switch_page_callback(self, notebook, page, page_num):
        '''
        Callback called when the notebook page gets switched. It initiates
        the cover search when the cover search pane's page is selected.
        '''
        print "CoverArtBrowser DEBUG - notebook_switch_page_callback"

        if page_num == 1:
            selected_albums = self.get_selected_albums()

            if selected_albums:
                self.cover_search_pane.do_search(selected_albums[0])

        print "CoverArtBrowser DEBUG - end notebook_switch_page_callback"

    def rating_changed_callback(self, widget):
        '''
        Callback called when the Rating stars is changed
        '''
        print "CoverArtBrowser DEBUG - rating_changed_callback"

        rating = widget.get_rating()

        for album in self.get_selected_albums():
            album.rating = rating

        print "CoverArtBrowser DEBUG - end rating_changed_callback"

    def genre_filter_callback(self, genre):
        if not genre:
            self.album_manager.model.remove_filter('genre')
        else:
            self.album_manager.model.replace_filter('genre', genre)

    def decade_filter_callback(self, decade):
        if not decade:
            self.album_manager.model.remove_filter('decade')
        else:
            self.album_manager.model.replace_filter('decade', decade)

    def select_album(self, album):
        path = self.album_manager.model.get_path(album)

        self.covers_view.unselect_all()
        self.covers_view.select_path(path)
        self.covers_view.set_cursor(path, None, False)
        self.covers_view.scroll_to_path(path, True, 0.5, 0.5)

    def hide_quick_search(self):
        self.quick_search_box.hide()
        self.covers_view.grab_focus()
        self.quick_search.props.text = ''

    def add_hide_on_timeout(self):
        self.quick_search_idle += 1

        def hide_on_timeout(*args):
            self.quick_search_idle -= 1

            if not self.quick_search_idle:
                self.hide_quick_search()

            return False

        Gdk.threads_add_timeout_seconds(GLib.PRIORITY_DEFAULT_IDLE, 4,
            hide_on_timeout, None)

    def on_quick_search(self, quick_search, *args):
        if self.quick_search_box.get_visible():
            # quick search on album names
            search_text = quick_search.props.text
            album = self.album_manager.model.find_first_visible('album_name',
                search_text)

            if album:
                self.select_album(album)

            # add a timeout to hide the search entry
            self.add_hide_on_timeout()

    def on_quick_search_up_down(self, quick_search, event, *args):
        arrow = False

        try:
            current = self.get_selected_albums()[0]
            search_text = quick_search.props.text
            album = None

            if event.keyval == Gdk.KEY_Up:
                arrow = True
                album = self.album_manager.model.find_first_visible(
                    'album_name', search_text, current, True)
            elif event.keyval == Gdk.KEY_Down:
                arrow = True
                album = self.album_manager.model.find_first_visible(
                    'album_name', search_text, current)

            if album:
                self.select_album(album)
        except:
            pass

        if arrow:
            self.add_hide_on_timeout()

        return arrow

    @classmethod
    def get_instance(cls, **kwargs):
        '''
        Returns the unique instance of the manager.
        '''
        if not cls.instance:
            cls.instance = CoverArtBrowserSource(**kwargs)

        return cls.instance


GObject.type_register(CoverArtBrowserSource)
