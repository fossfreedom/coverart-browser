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
from coverart_browser_prefs import Preferences
from coverart_widgets import SearchEntry
from coverart_widgets import QuickSearchEntry
from coverart_widgets import ProxyPopupButton
from coverart_widgets import PanedCollapsible
from coverart_controllers import PlaylistPopupController
from coverart_controllers import GenrePopupController
from coverart_controllers import SortPopupController
from coverart_controllers import PropertiesMenuController
from coverart_controllers import DecadePopupController
from coverart_controllers import SortOrderToggleController
from coverart_controllers import AlbumSearchEntryController
from coverart_controllers import AlbumQuickSearchController
from coverart_controllers import ViewController
from coverart_utils import Theme
from coverart_export import CoverArtExport
from stars import ReactiveStar
from coverart_rb3compat import Menu
from coverart_rb3compat import ActionGroup
from coverart_covericonview import CoverIconView
from coverart_covericonview import CoverIconView
from coverart_coverflowview import CoverFlowView
from coverart_artistview import ArtistView
from coverart_browser_prefs import webkit_support

import coverart_rb3compat as rb3compat
import random

class CoverArtBrowserSource(RB.Source):
    '''
    Source utilized by the plugin to show all it's ui.
    '''
    rating_threshold = GObject.property(type=float, default=0)
    artist_paned_pos = GObject.property(type=int, default=150)
    
    # unique instance of the source
    instance = None

    def __init__(self, **kargs):
        '''
        Initializes the source.
        '''
        super(CoverArtBrowserSource, self).__init__(**kargs)

        # create source_source_settings and connect the source's properties
        self.gs = GSetting()

        self._connect_properties()

        self.hasActivated = False
        self.last_width = 0
        self.last_selected_album = None
        self.click_count = 0
        self.favourites = False
        self.task_progress = None
        
    def _connect_properties(self):
        '''
        Connects the source properties to the saved preferences.
        '''
        print("CoverArtBrowser DEBUG - _connect_properties")
        setting = self.gs.get_setting(self.gs.Path.PLUGIN)

        setting.bind(
            self.gs.PluginKey.RATING,
            self,
            'rating_threshold',
            Gio.SettingsBindFlags.GET)

        print("CoverArtBrowser DEBUG - end _connect_properties")

    def do_get_status(self, *args):
        '''
        Method called by Rhythmbox to figure out what to show on this source
        statusbar.
        If the custom statusbar is disabled, the source will
        show the selected album info.
        Also, it makes sure to show the progress on the album loading
        '''
        
        try:
            # this will only work for RB3.0 and later
            if not self.task_progress:
                self.task_progress = RB.TaskProgressSimple.new()
        except:
            pass
            
        try:
            progress = self.album_manager.progress
            progress_text = _('Loading...') if progress < 1 else ''
            try:
                # this will only work for RB3.0 and later
                if progress < 1:
                    if self.task_progress.props.task_outcome != RB.TaskOutcome.COMPLETE:
                        self.props.shell.props.task_list.add_task(self.task_progress)
            
                    self.task_progress.props.task_progress = progress
                    self.task_progress.props.task_label=progress_text
                else:
                    self.task_progress.props.task_outcome = RB.TaskOutcome.COMPLETE
            except:
                pass
        except:
            progress = 1
            progress_text = ''
            try:
                # this will only work for RB3.0 and later
                self.task_progress.props.task_outcome = RB.TaskOutcome.COMPLETE
            except:
                pass

        return (self.status, progress_text, progress)

    def do_selected(self):
        '''
        Called by Rhythmbox when the source is selected. It makes sure to
        create the ui the first time the source is showed.
        '''
        print("CoverArtBrowser DEBUG - do_selected")

        # first time of activation -> add graphical stuff
        if not self.hasActivated:
            self.do_impl_activate()

            # indicate that the source was activated before
            self.hasActivated = True

        print("CoverArtBrowser DEBUG - end do_selected")

    def do_impl_activate(self):
        '''
        Called by do_selected the first time the source is activated.
        It creates all the source ui and connects the necesary signals for it
        correct behavior.
        '''
        print("CoverArtBrowser DEBUG - do_impl_activate")

        # initialise some variables
        self.plugin = self.props.plugin
        self.shell = self.props.shell
        self.status = ''
        self.search_text = ''
        self.actiongroup = ActionGroup(self.shell, 'coverplaylist_submenu')
        self._browser_preferences = None
        self._search_preferences = None
        
        # indicate that the source was activated before
        self.hasActivated = True

        self._create_ui()
        self._setup_source()
        self._apply_settings()

        print("CoverArtBrowser DEBUG - end do_impl_activate")

    def _create_ui(self):
        '''
        Creates the ui for the source and saves the important widgets onto
        properties.
        '''
        print("CoverArtBrowser DEBUG - _create_ui")

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

        # get widgets for the artist paned
        self.artist_paned = ui.get_object('vertical_paned')
        self.artist_treeview = ui.get_object('artist_treeview')
        self.artist_scrolledwindow = ui.get_object('artist_scrolledwindow')

        # get widgets for main icon-view
        self.status_label = ui.get_object('status_label')

        window = ui.get_object('scrolled_window')
        
        self.viewmgr = ViewManager(self, window)
                
        self.popup_menu = Menu(self.plugin, self.shell)
        self.popup_menu.load_from_file('ui/coverart_browser_pop_rb2.ui',
            'ui/coverart_browser_pop_rb3.ui')
        signals = \
            { 'play_album_menu_item': self.play_album_menu_item_callback,
              'queue_album_menu_item': self.queue_album_menu_item_callback,
              'playlist_menu_item': self.playlist_menu_item_callback,
              'new_playlist': self.add_playlist_menu_item_callback,
              'cover_search_menu_item': self.cover_search_menu_item_callback,
              'export_embed_menu_item': self.export_embed_menu_item_callback,
              'show_properties_menu_item': self.show_properties_menu_item_callback}
              
        self.popup_menu.connect_signals(signals)
        
        self.status_label = ui.get_object('status_label')
        self.request_status_box = ui.get_object('request_status_box')
        self.request_spinner = ui.get_object('request_spinner')
        self.request_statusbar = ui.get_object('request_statusbar')
        self.request_cancel_button = ui.get_object('request_cancel_button')
        self.paned = ui.get_object('paned')
        self.notebook = ui.get_object('bottom_notebook')

        # quick search
        self.quick_search = ui.get_object('quick_search_entry')

        print("CoverArtBrowser DEBUG - end _create_ui")

    def _setup_source(self):
        '''
        Setups the differents parts of the source so they are ready to be used
        by the user. It also creates and configure some custom widgets.
        '''
        print("CoverArtBrowser DEBUG - _setup_source")
 
        # setup iconview popup
        self.viewmgr.current_view.set_popup_menu(self.popup_menu)
        
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
        self.album_manager = AlbumManager(self.plugin, self.viewmgr.current_view)
        self.viewmgr.current_view.initialise(self)
        # setup cover search pane
        colour = self.viewmgr.get_selection_colour()

        self.cover_search_pane = CoverSearchPane(self.plugin,
            self.album_manager, colour)
        self.notebook.append_page(self.cover_search_pane, Gtk.Label(
            _("Covers")))

        # connect a signal to when the info of albums is ready
        self.load_fin_id = self.album_manager.loader.connect(
            'model-load-finished', self.load_finished_callback)

        # prompt the loader to load the albums
        self.album_manager.loader.load_albums(self.props.base_query_model)

        # initialise the toolbar manager
        self._toolbar_manager = ToolbarManager(self.plugin, self.page,
            self.album_manager.model, self.viewmgr)

        # initialise the variables of the quick search
        self.quick_search_controller = AlbumQuickSearchController(
            self.album_manager)
        self.quick_search_controller.connect_quick_search(self.quick_search)

        # set sensitivity of export menu item for iconview
        self.popup_menu.set_sensitive('export_embed_menu_item', 
            CoverArtExport(self.plugin,
                self.shell, self.album_manager).is_search_plugin_enabled())
        
        # setup the statusbar component
        self.statusbar = Statusbar(self)

        # setup the artist paned
        artist_pview = None
        for view in self.shell.props.library_source.get_property_views():
            if view.props.title == _("Artist"):
                artist_pview = view
                break

        assert artist_pview, "cannot find artist property view"

        self.artist_treeview.set_model(artist_pview.get_model())
        setting.bind(self.gs.PluginKey.ARTIST_PANED_POSITION,
            self, 'artist-paned-pos', Gio.SettingsBindFlags.DEFAULT)

        self.artist_paned.connect('button-release-event', 
            self.artist_paned_button_release_callback)

        print("CoverArtBrowser DEBUG - end _setup_source")
        
    def artist_paned_button_release_callback(self, *args):
        '''
        Callback when the artist paned handle is released from its mouse click.
        '''
        self.artist_paned_pos = self.artist_paned.get_position()

    def display_quick_artist_filter_callback(self):
        if self.artist_treeview.get_visible():
            self.artist_treeview.set_visible(False)
            self.artist_scrolledwindow.set_visible(False)
            self.artist_treeview.get_selection().unselect_all()
            self.album_manager.model.remove_filter('quick_artist')
        else:
            self.artist_scrolledwindow.set_visible(True)
            self.artist_treeview.set_visible(True)
            
            self.artist_paned.set_position(self.artist_paned_pos)
        
    def on_artist_treeview_selection_changed(self, view):
        model, artist_iter = view.get_selected()
        if artist_iter:
            artist = model[artist_iter][0]

            cl = CoverLocale()
            cl.switch_locale(cl.Locale.RB)
            #. TRANSLATORS - "All" is used in the context of "All artist names"
            if artist == _('All'):
                self.album_manager.model.remove_filter('quick_artist')
            else:
                self.album_manager.model.replace_filter('quick_artist', artist)

            cl.switch_locale(cl.Locale.LOCALE_DOMAIN)
            
    def _apply_settings(self):
        '''
        Applies all the settings related to the source and connects those that
        must be updated when the preferences dialog changes it's values. Also
        enables differents parts of the ui if the settings says so.
        '''
        print("CoverArtBrowser DEBUG - _apply_settings")

        # connect some signals to the loader to keep the source informed
        self.album_mod_id = self.album_manager.model.connect('album-updated',
            self.on_album_updated)
        
        self.notify_prog_id = self.album_manager.connect(
            'notify::progress', lambda *args: self.notify_status_changed())

        print("CoverArtBrowser DEBUG - end _apply_settings")

    def load_finished_callback(self, _):
        '''
        Callback called when the loader finishes loading albums into the
        covers view model.
        '''
        print("CoverArtBrowser DEBUG - load_finished_callback")

        #if not self.request_status_box.get_visible():
            # it should only be enabled if no cover request is going on
            #self.source_menu_search_all_item.set_sensitive(True)

        # enable sorting on the entryview
        self.entry_view.set_columns_clickable(True)
        self.shell.props.library_source.get_entry_view().set_columns_clickable(
            True)

        print("CoverArtBrowser DEBUG - end load_finished_callback")

    def get_entry_view(self):
        return self.entry_view

    def on_album_updated(self, model, path, tree_iter):
        '''
        Callback called by the album loader when one of the albums managed
        by him gets modified in some way.
        '''
        album = model.get_from_path(path)
        selected = self.viewmgr.current_view.get_selected_objects()

        if album in selected:
            # update the selection since it may have changed
            self.viewmgr.current_view.selectionchanged_callback()

            if album is selected[0] and \
                self.notebook.get_current_page() == \
                self.notebook.page_num(self.cover_search_pane):
                # also, if it's the first, update the cover search pane
                self.cover_search_pane.clear()
                self.cover_search_pane.do_search(album)

    def show_properties_menu_item_callback(self, *args):
        '''
        Callback called when the show album properties option is selected from
        the cover view popup. It shows a SongInfo dialog showing the selected
        albums' entries info, which can be modified.
        '''
        print("CoverArtBrowser DEBUG - show_properties_menu_item_callback")

        self.entry_view.select_all()

        info_dialog = RB.SongInfo(source=self, entry_view=self.entry_view)

        info_dialog.show_all()

        print("CoverArtBrowser DEBUG - end show_properties_menu_item_callback")

    def play_selected_album(self, favourites=False):
        '''
        Utilitary method that plays all entries from an album into the play
        queue.
        '''
        # callback when play an album
        print("CoverArtBrowser DEBUG - play_selected_album")

        query_model = RB.RhythmDBQueryModel.new_empty(self.shell.props.db)
        self.queue_selected_album(query_model)

        self.props.query_model = query_model

        # Start the music
        player = self.shell.props.shell_player

        player.play_entry(query_model[0][0], self)

        print("CoverArtBrowser DEBUG - end play_selected_album")

    def queue_selected_album(self, source, favourites=False):
        '''
        Utilitary method that queues all entries from an album into the play
        queue.
        '''
        print("CoverArtBrowser DEBUG - queue_selected_album")

        selected_albums = self.viewmgr.current_view.get_selected_objects()
        threshold = self.rating_threshold if favourites else 0
        
        for album in selected_albums:
            # Retrieve and sort the entries of the album
            tracks = album.get_tracks(threshold)

            # Add the songs to the play queue
            for track in tracks:
                source.add_entry(track.entry, -1)

        print("CoverArtBrowser DEBUG - end queue_select_album")

    def play_album_menu_item_callback(self, *args):
        '''
        Callback called when the play album item from the cover view popup is
        selected. It cleans the play queue and queues the selected album.
        '''
        print("CoverArtBrowser DEBUG - play_album_menu_item_callback")

        self.play_selected_album(self.favourites)

        print("CoverArtBrowser DEBUG - end play_album_menu_item_callback")

    def queue_album_menu_item_callback(self, *args):
        '''
        Callback called when the queue album item from the cover view popup is
        selected. It queues the selected album at the end of the play queue.
        '''
        print("CoverArtBrowser DEBUG - queue_album_menu_item_callback()")
        self.queue_selected_album(self.shell.props.queue_source, self.favourites)

        print("CoverArtBrowser DEBUG - end queue_album_menu_item_callback()")

    def playlist_menu_item_callback(self, *args):
        print("CoverArtBrowser DEBUG - playlist_menu_item_callback")

        self.playlist_fillmenu(self.popup_menu, 'playlist_submenu', 'playlist_section',
                               self.actiongroup,
                               self.add_to_static_playlist_menu_item_callback,
                               self.favourites)

    def playlist_fillmenu(self, popup_menu, menubar, section_name,
        actiongroup, func, favourite=False):
        print("CoverArtBrowser DEBUG - playlist_fillmenu")

        playlist_manager = self.shell.props.playlist_manager
        playlists_entries = playlist_manager.get_playlists()

        # tidy up old playlists menu items before recreating the list
        actiongroup.remove_actions()
        popup_menu.remove_menu_items(menubar, section_name)

        if playlists_entries:
            for playlist in playlists_entries:
                if playlist.props.is_local and \
                    isinstance(playlist, RB.StaticPlaylistSource):

                    args=(playlist, favourite)
                    action = actiongroup.add_action(func=func,
                        action_name=playlist.props.name,
                        playlist=playlist,favourite=favourite,
                        label=playlist.props.name)
                        
                    popup_menu.add_menu_item( menubar, section_name,
                        action )

    def add_to_static_playlist_menu_item_callback(self, action, param, args):
        print('''CoverArtBrowser DEBUG -
            add_to_static_playlist_menu_item_callback''')
            
        playlist=args['playlist']
        favourite = args['favourite']
        
        self.queue_selected_album(playlist, favourite)

    def add_playlist_menu_item_callback(self, *args):
        print('''CoverArtBrowser DEBUG - add_playlist_menu_item_callback''')
        playlist_manager = self.shell.props.playlist_manager
        playlist = playlist_manager.new_playlist('', False)

        self.queue_selected_album(playlist, self.favourites)

    def play_random_album_menu_item_callback(self, favourites=False):
        print('''CoverArtBrowser DEBUG - play_random_album_menu_item_callback''')
        query_model = RB.RhythmDBQueryModel.new_empty(self.shell.props.db)

        num_albums = len(self.album_manager.model.store)

        #random_list = []
        selected_albums = []

        gs = GSetting()
        settings = gs.get_setting(gs.Path.PLUGIN)        
        to_queue = settings[gs.PluginKey.RANDOM]

        if num_albums <= to_queue:
            dialog = Gtk.MessageDialog(None,
                    Gtk.DialogFlags.MODAL,
                    Gtk.MessageType.INFO,
                    Gtk.ButtonsType.OK,
                    _("The number of albums to randomly play is less than that displayed."))

            dialog.run()
            dialog.destroy()
            return
            
        album_col = self.album_manager.model.columns['album']

        chosen = {}

        # now loop through finding unique random albums
        # i.e. ensure we dont queue the same album twice
        
        for loop in range(0, to_queue):
            while True:
                pos = random.randint(0, num_albums - 1)
                if pos not in chosen:
                    chosen[pos] = None
                    selected_albums.append(self.album_manager.model.store[pos][album_col])
                    break

        threshold = self.rating_threshold if favourites else 0

        for album in selected_albums:
            # Retrieve and sort the entries of the album
            tracks = album.get_tracks(threshold)

            # Add the songs to the play queue
            for track in tracks:
                query_model.add_entry(track.entry, -1)

        self.props.query_model = query_model

        # Start the music
        player = self.shell.props.shell_player

        player.play_entry(query_model[0][0], self)

        print("CoverArtBrowser DEBUG - end play_selected_album")

    def cover_search_menu_item_callback(self, *args):
        '''
        Callback called when the search cover option is selected from the
        cover view popup. It prompts the album loader to retrieve the selected
        album cover
        '''
        print("CoverArtBrowser DEBUG - cover_search_menu_item_callback()")
        selected_albums = self.viewmgr.current_view.get_selected_objects()

        self.request_status_box.show_all()

        self.album_manager.cover_man.search_covers(selected_albums,
            self.update_request_status_bar)

        print("CoverArtBrowser DEBUG - end cover_search_menu_item_callback()")

    def export_embed_menu_item_callback(self, *args):
        '''
        Callback called when the export and embed coverart option
        is selected from the cover view popup.
        It prompts the exporter to copy and embed art for the albums chosen
        '''
        print("CoverArtBrowser DEBUG - export_embed_menu_item_callback()")
        selected_albums = self.viewmgr.current_view.get_selected_objects()

        CoverArtExport(self.plugin,
            self.shell, self.album_manager).embed_albums(selected_albums)

        print("CoverArtBrowser DEBUG - export_embed_menu_item_callback()")

    def update_request_status_bar(self, album):
        '''
        Callback called by the album loader starts performing a new cover
        request. It prompts the source to change the content of the request
        statusbar.
        '''
        print("CoverArtBrowser DEBUG - update_request_status_bar")

        if album:
            self.request_statusbar.set_text(
                rb3compat.unicodedecode(_('Requesting cover for %s - %s...') % (album.name,
                album.artist), 'UTF-8'))
        else:
            self.request_status_box.hide()
            self.popup_menu.set_sensitive('cover_search_menu_item', True)
            self.request_cancel_button.set_sensitive(True)
        print("CoverArtBrowser DEBUG - end update_request_status_bar")

    def cancel_request_callback(self, _):
        '''
        Callback connected to the cancel button on the request statusbar.
        When called, it prompts the album loader to cancel the full cover
        search after the current cover.
        '''
        print("CoverArtBrowser DEBUG - cancel_request_callback")

        self.request_cancel_button.set_sensitive(False)
        self.album_manager.cover_man.cancel_cover_request()

        print("CoverArtBrowser DEBUG - end cancel_request_callback")

    def notebook_switch_page_callback(self, notebook, page, page_num):
        '''
        Callback called when the notebook page gets switched. It initiates
        the cover search when the cover search pane's page is selected.
        '''
        print("CoverArtBrowser DEBUG - notebook_switch_page_callback")

        if page_num == 1:
            selected_albums = self.viewmgr.current_view.get_selected_objects()

            if selected_albums:
                self.cover_search_pane.do_search(selected_albums[0])

        print("CoverArtBrowser DEBUG - end notebook_switch_page_callback")

    def rating_changed_callback(self, widget):
        '''
        Callback called when the Rating stars is changed
        '''
        print("CoverArtBrowser DEBUG - rating_changed_callback")

        rating = widget.get_rating()

        for album in self.viewmgr.current_view.get_selected_objects():
            album.rating = rating

        print("CoverArtBrowser DEBUG - end rating_changed_callback")

    def show_hide_pane(self, params):
        '''
        helper function - if the entry is manually expanded
        then if necessary scroll the view to the last selected album
        params is "album" or a tuple of "album" and "force_expand" boolean
        '''
        
        if isinstance(params, tuple):
            album, force = params
        else:
            album = params
            force = PanedCollapsible.Paned.DEFAULT
        
        if (album and self.click_count == 1 \
            and self.last_selected_album is album) or force != PanedCollapsible.Paned.DEFAULT:
            # check if it's a second or third click on the album and expand
            # or collapse the entry view accordingly
            self.paned.expand(force)

        # update the selected album
        selected = self.viewmgr.current_view.get_selected_objects()
        self.last_selected_album = selected[0] if len(selected) == 1 else None

        # clear the click count
        self.click_count = 0

    def update_with_selection(self):
        '''
        Update the source view when an item gets selected.
        '''
        selected = self.viewmgr.current_view.get_selected_objects()

        # clear the entry view
        self.entry_view.clear()

        cover_search_pane_visible = self.notebook.get_current_page() == \
            self.notebook.page_num(self.cover_search_pane)

        if not selected:
            # clean cover tab if selected
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

        for album in selected:
            # add the album to the entry_view
            self.entry_view.add_album(album)

        # update the cover search pane with the first selected album
        if cover_search_pane_visible:
            self.cover_search_pane.do_search(selected[0])

        self.statusbar.emit('display-status', self.viewmgr.current_view)

    def propertiesbutton_callback(self, choice):
        
        if choice == 'download':
            self.request_status_box.show_all()
            self.album_manager.cover_man.search_covers(
                callback=self.update_request_status_bar)
        elif choice == 'random':
            self.play_random_album_menu_item_callback()
        elif choice == 'random favourite':
            self.play_random_album_menu_item_callback(True)
        elif choice == 'favourite':
            self.favourites = not self.favourites
            self.viewmgr.current_view.set_popup_menu(self.popup_menu)
        elif choice == 'quick artist':
            self.display_quick_artist_filter_callback()
        elif choice == 'browser prefs':
            if not self._browser_preferences:
                self._browser_preferences = Preferences()
                
            self._browser_preferences.display_preferences_dialog(self.plugin)
        elif choice == 'search prefs':
            try:
                if not self._search_preferences:                
                    from gi.repository import Peas
                    peas = Peas.Engine.get_default()
                    plugin_info = peas.get_plugin_info('coverart_search_providers')
                    module_name = plugin_info.get_module_name()
                    mod = __import__(module_name)
                    sp = getattr(mod, "SearchPreferences")
                    self._search_preferences = sp()
                    self._search_preferences.plugin_info = plugin_info

                self._search_preferences.display_preferences_dialog(self._search_preferences)
            except:
                dialog = Gtk.MessageDialog(None,
                    Gtk.DialogFlags.MODAL,
                    Gtk.MessageType.INFO,
                    Gtk.ButtonsType.OK,
                    _("Please install and activate the latest version of the Coverart Search Providers plugin"))

                dialog.run()
                dialog.destroy()
        else:
            assert 1==2, ("unknown choice %s", choice)

    @classmethod
    def get_instance(cls, **kwargs):
        '''
        Returns the unique instance of the manager.
        '''
        if not cls.instance:
            cls.instance = CoverArtBrowserSource(**kwargs)

        return cls.instance

class Statusbar(GObject.Object):
    # signals
    __gsignals__ = {
        'display-status': (GObject.SIGNAL_RUN_LAST, None, (object,))
    }
    
    custom_statusbar_enabled = GObject.property(type=bool, default=False)

    def __init__(self, source):
        super(Statusbar, self).__init__()

        self.status = ''

        self._source_statusbar = SourceStatusBar(source)
        self._custom_statusbar = CustomStatusBar(source.status_label)
        self.current_statusbar = self._source_statusbar

        self._connect_signals(source)
        self._connect_properties()

    def _connect_properties(self):
        gs = GSetting()
        settings = gs.get_setting(gs.Path.PLUGIN)

        settings.bind(gs.PluginKey.CUSTOM_STATUSBAR, self,
            'custom_statusbar_enabled', Gio.SettingsBindFlags.GET)

    def _connect_signals(self, source):
        self.connect('notify::custom-statusbar-enabled',
            self._custom_statusbar_enabled_changed)
        self.connect('display-status', self._update)

    def _custom_statusbar_enabled_changed(self, *args):
        self.current_statusbar.hide()

        if self.custom_statusbar_enabled:
            self.current_statusbar = self._custom_statusbar
        else:
            self.current_statusbar = self._source_statusbar

        self.current_statusbar.show()
        self.current_statusbar.update(self.status)

    def _generate_status(self, albums=None):
        self.status = ''

        if albums:
            track_count = 0
            duration = 0

            for album in albums:
                # Calculate duration and number of tracks from that album
                track_count += album.track_count
                duration += album.duration / 60

            # now lets build up a status label containing some
            # 'interesting stuff' about the album
            if len(albums) == 1:
                #. TRANSLATORS - for example "abba's greatest hits by ABBA"
                self.status = rb3compat.unicodedecode(_('%s by %s') % 
                        (album.name, album.artist), 'UTF-8')
            else:
                #. TRANSLATORS - the number of albums that have been selected/highlighted
                self.status = rb3compat.unicodedecode(_('%d selected albums') % 
                        (len(albums)), 'UTF-8')

            if track_count == 1:
                self.status += rb3compat.unicodedecode(_(' with 1 track'), 'UTF-8')
            else:
                self.status += rb3compat.unicodedecode(_(' with %d tracks') % 
                        track_count, 'UTF-8')

            if duration == 1:
                self.status += rb3compat.unicodedecode(_(' and a duration of 1 minute'), 'UTF-8')
            else:
                self.status += rb3compat.unicodedecode(_(' and a duration of %d minutes') % 
                        duration, 'UTF-8')

    def _update(self, widget, current_view):
        albums = current_view.get_selected_objects()
        self._generate_status(albums)
        self.current_statusbar.update(self.status)
        
class SourceStatusBar(object):
    def __init__(self, source):
        self._source = source

    def show(self):
        pass

    def hide(self):
        self.update('')

    def update(self, status):
        self._source.status = status
        self._source.notify_status_changed()


class CustomStatusBar(object):
    def __init__(self, status_label):
        self._label = status_label

    def show(self):
        self._label.show()

    def hide(self):
        self._label.hide()

    def update(self, status):
        self._label.set_text(status)


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
            button = builder.get_object('iconview_button')
            button.set_visible(False)
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

    def _connect_signals(self):
        self.connect('notify::toolbar-pos', self._on_notify_toolbar_pos)

    def _connect_properties(self):
        gs = GSetting()
        setting = gs.get_setting(gs.Path.PLUGIN)
        setting.bind(gs.PluginKey.TOOLBAR_POS, self, 'toolbar_pos',
            Gio.SettingsBindFlags.GET)

    def _create_controllers(self, plugin, album_model, viewmgr):
        controllers = {}
        controllers['properties_button'] = PropertiesMenuController(plugin, viewmgr.source)
        controllers['sort_by'] = SortPopupController(plugin, album_model)
        controllers['sort_order'] = SortOrderToggleController(plugin,
            album_model)
        controllers['genre_button'] = GenrePopupController(plugin, album_model)
        controllers['playlist_button'] = PlaylistPopupController(plugin,
            album_model)
        controllers['decade_button'] = DecadePopupController(plugin,
            album_model)
        controllers['search'] = AlbumSearchEntryController(album_model)
        
        controllers['iconview_button'] = viewmgr.controller
        controllers['flowview_button'] = viewmgr.controller
        #controllers['artistview_button'] = viewmgr.controller

        return controllers

    def _on_notify_toolbar_pos(self, *args):
        if self.last_toolbar_pos:
            self._bars[self.last_toolbar_pos].hide()

        self._bars[self.toolbar_pos].show()

        self.last_toolbar_pos = self.toolbar_pos


class ViewManager(GObject.Object):
    # signals
    __gsignals__ = {
        'new-view': (GObject.SIGNAL_RUN_LAST, None, ())
        }
    
    # properties
    view_name = GObject.property(type=str, default=CoverIconView.name)
    
    def __init__(self, source, window):
        super(ViewManager, self).__init__()

        self.source = source
        self.window = window
        
        # initialize views
        self._views = {}
        ui = Gtk.Builder()
        ui.add_from_file(rb.find_plugin_file(source.plugin,
            'ui/coverart_iconview.ui'))
        self._views[CoverIconView.name] = ui.get_object('covers_view')
        self._views[CoverFlowView.name] = CoverFlowView()
        self._views[ArtistView.name] = ArtistView()
        self._lastview = None

        self.controller = ViewController(source.plugin, self)
        self.controller.add_key_pair(CoverFlowView.name, 'flowview_button')
        self.controller.add_key_pair(CoverIconView.name, 'iconview_button')
        self.controller.add_key_pair(ArtistView.name, 'artistview_button')

        # connect signal and properties
        self._connect_signals()
        self._connect_properties()
        self._lastview = self.view_name
        window.add(self.current_view.view)
        window.show_all()
        
    @property
    def current_view(self):
        return self._views[self.view_name]

    def _connect_signals(self):
        self.connect('notify::view-name', self.on_notify_view_name)
        
    def _connect_properties(self):
        gs = GSetting()
        setting = gs.get_setting(gs.Path.PLUGIN)
        setting.bind(gs.PluginKey.VIEW_NAME, self, 'view_name',
            Gio.SettingsBindFlags.DEFAULT)

    def on_notify_view_name(self, *args):
        if self._lastview and self.view_name != self._lastview:

            selected = self._views[self._lastview].get_selected_objects()
            current_album = None
            if len(selected) > 0:
                current_album = self._views[self._lastview].get_selected_objects()[0]
                
            self.window.remove(self._views[self._lastview].view)
            self.window.add(self._views[self.view_name].view)
            self.window.show_all()
            self.click_count = 0
            
            self._views[self._lastview].panedposition = self.source.paned.get_expansion_status()
            self._views[self.view_name].switch_to_view(self.source, current_album)
            self.source.paned.expand(self._views[self.view_name].panedposition)
            
            self._lastview = self.view_name
            self.current_view.set_popup_menu(self.source.popup_menu)
            self.source.album_manager.current_view = self.current_view
            
            gs = GSetting()
            setting = gs.get_setting(gs.Path.PLUGIN)
            setting[gs.PluginKey.VIEW_NAME] = self.view_name

        self.emit('new-view')
            
    def get_view_icon_name(self, view_name):
        return self._views[view_name].get_view_icon_name()

    def get_selection_colour(self):
        try:
            colour = self._views[CoverIconView.name].view.get_style_context().get_background_color(
                Gtk.StateFlags.SELECTED)
            colour = '#%s%s%s' % (
                str(hex(int(colour.red * 255))).replace('0x', ''),
                str(hex(int(colour.green * 255))).replace('0x', ''),
                str(hex(int(colour.blue * 255))).replace('0x', ''))
        except:
            colour = '#0000FF'

        return colour
        
GObject.type_register(CoverArtBrowserSource)
