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
from coverart_widgets import SearchEntry
from coverart_widgets import QuickSearchEntry
from coverart_widgets import ProxyPopupButton
from coverart_widgets import EnhancedIconView
from coverart_widgets import PanedCollapsible
from coverart_controllers import PlaylistPopupController
from coverart_controllers import GenrePopupController
from coverart_controllers import SortPopupController
from coverart_controllers import DecadePopupController
from coverart_controllers import SortOrderToggleController
from coverart_controllers import AlbumSearchEntryController
from coverart_controllers import AlbumQuickSearchController
from coverart_utils import Theme
from stars import ReactiveStar

class CoverArtBrowserSource(RB.Source):
    '''
    Source utilized by the plugin to show all it's ui.
    '''
    custom_statusbar_enabled = GObject.property(type=bool, default=False)
    rating_threshold = GObject.property(type=float, default=0)

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

        self.hasActivated = False
        self.last_width = 0
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
        setting.bind(self.gs.PluginKey.RATING, self,
            'rating_threshold', Gio.SettingsBindFlags.GET)

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

        # connect properties signals
        self.connect('notify::custom-statusbar-enabled',
            self.on_notify_custom_statusbar_enabled)

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
        ui.connect_signals(self)

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

        # quick search
        self.quick_search = ui.get_object('quick_search_entry')

        print "CoverArtBrowser DEBUG - end _create_ui"

    def _setup_source(self):
        '''
        Setups the differents parts of the source so they are ready to be used
        by the user. It also creates and configure some custom widgets.
        '''
        print "CoverArtBrowser DEBUG - _setup_source"

        # setup iconview popup
        self.covers_view.popup = self.popup_menu

        # setup iconview drag&drop support
        self.covers_view.enable_model_drag_dest([], Gdk.DragAction.COPY)
        self.covers_view.drag_dest_add_image_targets()
        self.covers_view.drag_dest_add_text_targets()
        self.covers_view.connect('drag-drop', self.on_drag_drop)
        self.covers_view.connect('drag-data-received',
            self.on_drag_data_received)

        # setup entry-view objects and widgets
        setting = self.gs.get_setting(self.gs.Path.PLUGIN)
        setting.bind(self.gs.PluginKey.PANED_POSITION,
            self.paned, 'collapsible-y', Gio.SettingsBindFlags.DEFAULT)
        setting.bind(self.gs.PluginKey.DISPLAY_BOTTOM,
            self.paned.get_child2(), 'visible', Gio.SettingsBindFlags.DEFAULT)

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

        # initialise the toolbar manager
        self._toolbar_manager = ToolbarManager(self.plugin, self.page,
            self.album_manager.model)

        # initialise the variables of the quick search
        self.quick_search_controller = AlbumQuickSearchController(
            self.album_manager)
        self.quick_search_controller.connect_quick_search(self.quick_search)

        print "CoverArtBrowser DEBUG - end _setup_source"

    def _apply_settings(self):
        '''
        Applies all the settings related to the source and connects those that
        must be updated when the preferences dialog changes it's values. Also
        enables differents parts of the ui if the settings says so.
        '''
        print "CoverArtBrowser DEBUG - _apply_settings"

        # connect some signals to the loader to keep the source informed
        self.album_mod_id = self.album_manager.model.connect('album-updated',
            self.on_album_updated)
        self.notify_prog_id = self.album_manager.connect(
            'notify::progress', lambda *args: self.notify_status_changed())

        # enable some ui if necesary
        self.on_notify_rating_threshold(_)

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

    def item_clicked_callback(self, iconview, event, path):
        '''
        Callback called when the user clicks somewhere on the cover_view.
        Along with _timeout_expand, takes care of showing/hiding the bottom
        pane after a second click on a selected album.
        '''
        # to expand the entry view
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        shift = event.state & Gdk.ModifierType.SHIFT_MASK

        self.click_count += 1 if not ctrl and not shift else 0

        if self.click_count == 1:
            album = self.album_manager.model.get_from_path(path)\
                if path else None
            Gdk.threads_add_timeout(GLib.PRIORITY_DEFAULT_IDLE, 250,
                self._timeout_expand, album)

    def _timeout_expand(self, album):
        '''
        helper function - if the entry is manually expanded
        then if necessary scroll the view to the last selected album
        '''
        if album and self.click_count == 1 \
            and self.last_selected_album is album:
            # check if it's a second or third click on the album and expand
            # or collapse the entry view accordingly
            self.paned.expand()

        # update the selected album
        selected = self.covers_view.get_selected_objects()
        self.last_selected_album = selected[0] if len(selected) == 1 else None

        # clear the click count
        self.click_count = 0

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

    def on_album_updated(self, model, path, tree_iter):
        '''
        Callback called by the album loader when one of the albums managed
        by him gets modified in some way.
        '''
        album = model.get_from_path(path)
        selected = self.covers_view.get_selected_objects()

        if album in selected:
            # update the selection since it may have changed
            self.selectionchanged_callback(self.covers_view)

            if album is selected[0] and \
                self.notebook.get_current_page() == \
                self.notebook.page_num(self.cover_search_pane):
                # also, if it's the first, update the cover search pane
                self.cover_search_pane.clear()
                self.cover_search_pane.do_search(album)

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

    def item_activated_callback(self, iconview, path):
        '''
        Callback called when the cover view is double clicked or space-bar
        is pressed. It plays the selected album
        '''
        self.play_selected_album()

        return True

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

        selected_albums = self.covers_view.get_selected_objects()
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
        selected_albums = self.covers_view.get_selected_objects()

        self.request_status_box.show_all()

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
            self.request_statusbar.set_text(
                (_('Requesting cover for %s - %s...') % (album.name,
                album.artist)).decode('UTF-8'))
        else:
            self.request_status_box.hide()
            self.source_menu_search_all_item.set_sensitive(True)
            self.cover_search_menu_item.set_sensitive(True)
            self.request_cancel_button.set_sensitive(True)
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

        selected = self.covers_view.get_selected_objects()

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

    def bottom_expander_expanded_callback(self, paned, expand):
        '''
        Callback connected to expanded signal of the paned GtkExpander
        '''
        if expand:
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
            selected_albums = self.covers_view.get_selected_objects()

            if selected_albums:
                self.cover_search_pane.do_search(selected_albums[0])

        print "CoverArtBrowser DEBUG - end notebook_switch_page_callback"

    def rating_changed_callback(self, widget):
        '''
        Callback called when the Rating stars is changed
        '''
        print "CoverArtBrowser DEBUG - rating_changed_callback"

        rating = widget.get_rating()

        for album in self.covers_view.get_selected_objects():
            album.rating = rating

        print "CoverArtBrowser DEBUG - end rating_changed_callback"

    @classmethod
    def get_instance(cls, **kwargs):
        '''
        Returns the unique instance of the manager.
        '''
        if not cls.instance:
            cls.instance = CoverArtBrowserSource(**kwargs)

        return cls.instance


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
        for button, controller in controllers.iteritems():
            if button != 'search':
                builder.get_object(button).controller = controller

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
        for controller in controllers.values():
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


class ToolbarManager(GObject.Object):
    # properties
    toolbar_pos = GObject.property(type=str, default=TopToolbar.name)

    def __init__(self, plugin, main_box, album_model):
        super(ToolbarManager, self).__init__()
        self.plugin = plugin
        # create the buttons controllers
        controllers = self._create_controllers(plugin, album_model)

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

    def _connect_signals(self):
        self.connect('notify::toolbar-pos', self._on_notify_toolbar_pos)

    def _connect_properties(self):
        gs = GSetting()
        setting = gs.get_setting(gs.Path.PLUGIN)
        setting.bind(gs.PluginKey.TOOLBAR_POS, self, 'toolbar_pos',
            Gio.SettingsBindFlags.GET)

    def _create_controllers(self, plugin, album_model):
        controllers = {}
        controllers['sort_by'] = SortPopupController(plugin, album_model)
        controllers['sort_order'] = SortOrderToggleController(plugin,
            album_model)
        controllers['genre_button'] = GenrePopupController(plugin, album_model)
        controllers['playlist_button'] = PlaylistPopupController(plugin,
            album_model)
        controllers['decade_button'] = DecadePopupController(plugin,
            album_model)
        controllers['search'] = AlbumSearchEntryController(album_model)

        return controllers

    def _on_notify_toolbar_pos(self, *args):
        if self.last_toolbar_pos:
            self._bars[self.last_toolbar_pos].hide()

        self._bars[self.toolbar_pos].show()

        self.last_toolbar_pos = self.toolbar_pos
            
GObject.type_register(CoverArtBrowserSource)
