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

from gi.repository import RB
from gi.repository import Gtk
from gi.repository import GObject
from coverart_rb3compat import Menu
from coverart_rb3compat import ActionGroup

import rb

from coverart_browser_prefs import GSetting
from coverart_browser_prefs import CoverLocale
from coverart_external_plugins import CreateExternalPluginMenu
from collections import OrderedDict
from coverart_playlists import LastFMTrackPlaylist
from coverart_playlists import EchoNestPlaylist
from coverart_playlists import EchoNestGenrePlaylist

from gi.repository import GdkPixbuf
from gi.repository import Gdk
from gi.repository import RB

import cairo
from math import pi
    
MIN_IMAGE_SIZE = 100

class ResultsGrid(Gtk.Grid):
        
    # signals
    __gsignals__ = {
        'update-cover': (GObject.SIGNAL_RUN_LAST, None, (GObject.Object,RB.RhythmDBEntry))
        }
    image_width = 0
    
    def __init__(self, *args, **kwargs):
        super(ResultsGrid, self).__init__(*args, **kwargs)

    def initialise(self):
        self.pixbuf = None

        self.oldval = 0
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(350)

        self.image1 = Gtk.Image()
        self.image1.props.hexpand = True
        self.image1.props.vexpand = True
        self.stack.add_named(self.image1, "image1")

        self.image2 = Gtk.Image()
        self.image2.props.hexpand = True
        self.image2.props.vexpand = True
        self.stack.add_named(self.image2, "image2")

        self.frame = Gtk.AspectFrame.new("", 0.5, 0.5, 1, False)
        self.update_cover(None, None, None)
        scroll = Gtk.ScrolledWindow()
        scroll.add_with_viewport(self.stack)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        scroll.set_resize_mode(Gtk.ResizeMode.QUEUE)

        self.frame.add(scroll)
        self._signal_connected = None

        self.attach(self.frame, 3, 0, 1, 1)
        self.connect('update-cover', self.update_cover)

        #lets fix the situation where some-themes background colour is incorrectly defined
        #in these cases the background colour is black
        context = self.get_style_context()
        bg_colour = context.get_background_color(Gtk.StateFlags.NORMAL)
        if bg_colour == Gdk.RGBA(0, 0, 0, 0):
            color = context.get_color(Gtk.StateFlags.NORMAL)
            self.override_background_color(Gtk.StateType.NORMAL, color)

    def update_cover(self, widget, source, entry):
        
        if entry:
            album = source.album_manager.model.get_from_dbentry(entry)
            self.pixbuf = GdkPixbuf.Pixbuf().new_from_file(album.cover.original)
            self.oldval = 0
            self.window_resize(None)
            self.frame.set_shadow_type(Gtk.ShadowType.NONE)
        else:
            self.pixbuf = None
            self.frame.set_shadow_type(Gtk.ShadowType.ETCHED_OUT)

        if self.stack.get_visible_child_name() == "image1":
            self.image1.queue_draw()
        else:
            self.image2.queue_draw()
        
    def window_resize(self, widget):
        alloc = self.get_allocation()
        if alloc.height < 10:
            return
                
        if (alloc.width / 3) <= (MIN_IMAGE_SIZE+30) or \
           (alloc.height) <= (MIN_IMAGE_SIZE+30):
            self.frame.props.visible = False
        else:
            self.frame.props.visible = True

        framealloc = self.frame.get_allocation()
        minval = min(framealloc.width-30, framealloc.height-30)
        if self.oldval == minval:
            return
        self.oldval = minval
        p = self.pixbuf.scale_simple(minval, minval, GdkPixbuf.InterpType.BILINEAR)
        if self.stack.get_visible_child_name() == "image1":
            self.image2.set_from_pixbuf(p)
            self.stack.set_visible_child_name("image2")
        else:
            self.image1.set_from_pixbuf(p)
            self.stack.set_visible_child_name("image1")
            
    def change_view(self, entry_view, show_coverart):
        print ("debug - change_view")
        widget = self.get_child_at(0, 0)
        if widget:
            self.remove(widget)
            
        if not show_coverart:
            widget = self.get_child_at(3, 0)
            if widget:
                self.remove(widget)
            
        entry_view.props.hexpand = True
        entry_view.props.vexpand = True
        self.attach(entry_view, 0, 0, 3, 1)
        
        if show_coverart:
            self.attach(self.frame, 3, 0, 1, 1)
            
        self.show_all()

        
class BaseView(RB.EntryView):

    def __init__(self, shell, source):
        '''
        Initializes the entryview.
        '''
        self.shell = shell
        self.source = source
        self.plugin = self.source.props.plugin

        super(RB.EntryView, self).__init__(db=shell.props.db,
            shell_player=shell.props.shell_player, is_drag_source=True,
            visible_columns=[])

        cl = CoverLocale()
        cl.switch_locale(cl.Locale.RB)

        self.display_columns()
                
        cl.switch_locale(cl.Locale.LOCALE_DOMAIN)

        self.define_menu()

        # connect signals to the shell to know when the playing state changes
        self.shell.props.shell_player.connect('playing-song-changed',
            self.playing_song_changed)
        self.shell.props.shell_player.connect('playing-changed',
            self.playing_changed)

        self.actiongroup = ActionGroup(self.shell, 'coverentryplaylist_submenu')
        
        self.external_plugins = None

        self.qm = RB.RhythmDBQueryModel.new_empty(self.shell.props.db)
        self.set_model(self.qm)

        # connect the sort-order to the library source sort
        library_view = self.shell.props.library_source.get_entry_view()
        library_view.connect('notify::sort-order',
            self._on_library_sorting_changed)
        self._on_library_sorting_changed(library_view,
            library_view.props.sort_order)

         # connect to the sort-order property
        self.connect('notify::sort-order', self._notify_sort_order,
            library_view)
            
        self.echonest_similar_playlist = None
        self.echonest_similar_genre_playlist = None
        self.lastfm_similar_playlist = None
        
        self.set_columns_clickable(False)
        
        self.connect('selection-changed', self.selection_changed)
        
        self.artists = ""

    def __del__(self):
        del self.action_group
        del self.play_action
        del self.queue_action
        
    def define_menu(self):
        pass
        
    def display_columns(self):
        pass
        
    def selection_changed(self, entry_view):
        entries = entry_view.get_selected_entries()
        if entries and len(entries) > 0:
            self.source.entry_view_results.emit('update-cover', self.source, entries[0])

    def add_album(self, album):
        print("CoverArtBrowser DEBUG - add_album()")
        tracks = album.get_tracks()

        for track in tracks:
            self.qm.add_entry(track.entry, -1)

        (_, playing) = self.shell.props.shell_player.get_playing()
        self.playing_changed(self.shell.props.shell_player, playing)
        
        artists = album.artists.split(', ')
        if self.artists == "":
            self.artists = artists
        else:
            self.artists = list(set(self.artists + artists))
            
        print("CoverArtBrowser DEBUG - add_album()")

    def clear(self):
        print("CoverArtBrowser DEBUG - clear()")
        # self.set_model(RB.RhythmDBQueryModel.new_empty(self.shell.props.db))
        for row in self.qm:
            self.qm.remove_entry(row[0])

        self.artists = ""
        
        print("CoverArtBrowser DEBUG - clear()")

    def do_entry_activated(self, entry):
        print("CoverArtBrowser DEBUG - do_entry_activated()")
        self.select_entry(entry)
        self.play_track_menu_item_callback(entry)
        print("CoverArtBrowser DEBUG - do_entry_activated()")
        return True
        
    def add_external_menu(self, *args):
        pass

    def do_show_popup(self, over_entry):
        if over_entry:
            print("CoverArtBrowser DEBUG - do_show_popup()")
            
            self.popup.popup(self.source,
                'entryview_popup_menu', 0, Gtk.get_current_event_time())

        return over_entry
        
    def play_similar_artist_menu_item_callback(self, *args):
        if not self.echonest_similar_playlist:
            self.echonest_similar_playlist = \
                EchoNestPlaylist(   self.shell,
                                    self.shell.props.queue_source)
                                    
        selected = self.get_selected_entries()
        entry = selected[0]
        self.echonest_similar_playlist.start(entry, reinitialise=True)
        
    def play_similar_genre_menu_item_callback(self, *args):
        if not self.echonest_similar_genre_playlist:
            self.echonest_similar_genre_playlist = \
                EchoNestGenrePlaylist(   self.shell,
                                    self.shell.props.queue_source)
                                    
        selected = self.get_selected_entries()
        entry = selected[0]
        self.echonest_similar_genre_playlist.start(entry, reinitialise=True)
                                    
    def play_similar_track_menu_item_callback(self, *args):
        if not self.lastfm_similar_playlist:
            self.lastfm_similar_playlist = \
                LastFMTrackPlaylist(    self.shell,
                                        self.shell.props.queue_source)
                                    
        selected = self.get_selected_entries()
        entry = selected[0]
        self.lastfm_similar_playlist.start(entry, reinitialise=True)
    

    def play_track_menu_item_callback(self, *args):
        print("CoverArtBrowser DEBUG - play_track_menu_item_callback()")
        
        query_model = RB.RhythmDBQueryModel.new_empty(self.shell.props.db)

        selected = self.get_selected_entries()
        entry = selected[0]
        
        if len(selected) == 1:
            query_model.copy_contents(self.qm)
        else:
            self.add_tracks_to_source(query_model)
            
        self.source.props.query_model = query_model

        # Start the music
        player = self.shell.props.shell_player
        player.play_entry(entry, self.source)

        print("CoverArtBrowser DEBUG - play_track_menu_item_callback()")

    def queue_track_menu_item_callback(self, *args):
        print("CoverArtBrowser DEBUG - queue_track_menu_item_callback()")

        self.add_tracks_to_source(self.shell.props.queue_source)

    def add_tracks_to_source(self, source):
        selected = self.get_selected_entries()
        selected.reverse()

        selected = sorted(selected,
            key=lambda song: song.get_ulong(RB.RhythmDBPropType.TRACK_NUMBER))

        for entry in selected:
            source.add_entry(entry, -1)

        print("CoverArtBrowser DEBUG - queue_track_menu_item_callback()")

    def love_track(self, rating):
        '''
        utility function to set the rating for selected tracks
        '''
        selected = self.get_selected_entries()

        for entry in selected:
            self.shell.props.db.entry_set(entry, RB.RhythmDBPropType.RATING,
                rating)

        self.shell.props.db.commit()

    def show_properties_menu_item_callback(self, *args):
        print("CoverArtBrowser DEBUG - show_properties_menu_item_callback()")

        info_dialog = RB.SongInfo(source=self.source, entry_view=self)
        info_dialog.show_all()
        
        print("CoverArtBrowser DEBUG - show_properties_menu_item_callback()")

    def playing_song_changed(self, shell_player, entry):
        print("CoverArtBrowser DEBUG - playing_song_changed()")

        if entry is not None and self.get_entry_contained(entry):
            self.set_state(RB.EntryViewState.PLAYING)
        else:
            self.set_state(RB.EntryViewState.NOT_PLAYING)

        print("CoverArtBrowser DEBUG - playing_song_changed()")

    def playing_changed(self, shell_player, playing):
        print("CoverArtBrowser DEBUG - playing_changed()")
        entry = shell_player.get_playing_entry()

        if entry is not None and self.get_entry_contained(entry):
            if playing:
                self.set_state(RB.EntryViewState.PLAYING)
            else:
                self.set_state(RB.EntryViewState.PAUSED)
        else:
            self.set_state(RB.EntryViewState.NOT_PLAYING)

        print("CoverArtBrowser DEBUG - playing_changed()")

    def add_playlist_menu_item_callback(self, *args):
        print("CoverArtBrowser DEBUG - add_playlist_menu_item_callback")
        playlist_manager = self.shell.props.playlist_manager
        playlist = playlist_manager.new_playlist(_('New Playlist'), False)

        self.add_tracks_to_source(playlist)

    def playlist_menu_item_callback(self, *args):
        pass

    def add_to_static_playlist_menu_item_callback(self, action, param, args):
        print("CoverArtBrowser DEBUG - " + \
            "add_to_static_playlist_menu_item_callback")
        
        playlist = args['playlist']
        self.add_tracks_to_source(playlist)

    def _on_library_sorting_changed(self, view, _):
        self._old_sort_order = self.props.sort_order

        self.set_sorting_type(view.props.sort_order)

    def _notify_sort_order(self, view, _, library_view):
        if self.props.sort_order != self._old_sort_order:
            self.resort_model()

            # update library source's view direction
            library_view.set_sorting_type(self.props.sort_order)
            
class CoverArtCompactEntryView(BaseView):
    __hash__ = GObject.__hash__
    
    def __init__(self, shell, source):
        '''
        Initializes the entryview.
        '''
        super(CoverArtCompactEntryView, self).__init__(shell, source)
    
    def display_columns(self):
        
        self.col_map = OrderedDict([
                        ('track-number', RB.EntryViewColumn.TRACK_NUMBER),
                        ('title', RB.EntryViewColumn.TITLE),
                        ('artist', RB.EntryViewColumn.ARTIST), 
                        ('rating', RB.EntryViewColumn.RATING),
                        ('duration', RB.EntryViewColumn.DURATION)
                        ])
        
        for entry in self.col_map:
            visible = False if entry == 'artist' else True
            self.append_column(self.col_map[entry], visible)
            
    def add_album(self, album):
        super(CoverArtCompactEntryView, self).add_album(album)
        
        if len(self.artists) > 1:
            self.get_column(RB.EntryViewColumn.ARTIST).set_visible(True)
        else:
            self.get_column(RB.EntryViewColumn.ARTIST).set_visible(False)
            
    def define_menu(self):
        popup = Menu(self.plugin, self.shell)
        popup.load_from_file('N/A',
                             'ui/coverart_entryview_compact_pop_rb3.ui')
        signals = {
            'ev_compact_play_track_menu_item': self.play_track_menu_item_callback,
            'ev_compact_queue_track_menu_item': self.queue_track_menu_item_callback,
            'ev_compact_new_playlist': self.add_playlist_menu_item_callback,
            'ev_compact_show_properties_menu_item': self.show_properties_menu_item_callback,
            'ev_compact_similar_track_menu_item': self.play_similar_track_menu_item_callback,
            'ev_compact_similar_artist_menu_item': self.play_similar_artist_menu_item_callback,
            'ev_compact_similar_genre_menu_item': self.play_similar_genre_menu_item_callback }
            
        popup.connect_signals(signals)
        popup.connect('pre-popup', self.add_external_menu)
        self.popup = popup
        
    def playlist_menu_item_callback(self, *args):
        print("CoverArtBrowser DEBUG - playlist_menu_item_callback")

        self.source.playlist_fillmenu(self.popup, 'ev_compact_playlist_sub_menu_item', 'ev_compact_playlist_section',
            self.actiongroup, self.add_to_static_playlist_menu_item_callback)

    def add_external_menu(self, *args):
        '''
        Callback when the popup menu is about to be displayed
        '''
        if not self.external_plugins:
            self.external_plugins = \
                    CreateExternalPluginMenu("ev_compact_entryview", 4, self.popup)
            self.external_plugins.create_menu('entryview_compact_popup_menu')
            
        self.playlist_menu_item_callback()
    
class CoverArtEntryView(BaseView):
    __hash__ = GObject.__hash__
    
    def __init__(self, shell, source):
        '''
        Initializes the entryview.
        '''
        super(CoverArtEntryView, self).__init__(shell, source)
    
    def display_columns(self):
        
        self.col_map = OrderedDict([
                        ('track-number', RB.EntryViewColumn.TRACK_NUMBER),
                        ('title', RB.EntryViewColumn.TITLE),
                        ('genre', RB.EntryViewColumn.GENRE),
                        ('artist', RB.EntryViewColumn.ARTIST),
                        ('album', RB.EntryViewColumn.ALBUM),
                        ('composer', RB.EntryViewColumn.COMPOSER),
                        ('date', RB.EntryViewColumn.YEAR),
                        ('duration', RB.EntryViewColumn.DURATION),
                        ('bitrate', RB.EntryViewColumn.QUALITY),
                        ('play-count', RB.EntryViewColumn.PLAY_COUNT),
                        ('beats-per-minute', RB.EntryViewColumn.BPM),
                        ('comment', RB.EntryViewColumn.COMMENT),
                        ('location', RB.EntryViewColumn.LOCATION),
                        ('rating', RB.EntryViewColumn.RATING),
                        ('last-played', RB.EntryViewColumn.LAST_PLAYED),
                        ('first-seen', RB.EntryViewColumn.FIRST_SEEN)
                        ])
                        
        for entry in self.col_map:
            visible = True if entry == 'title' else False
            self.append_column(self.col_map[entry], visible)
        
        # connect the visible-columns global setting to update our entryview
        gs = GSetting()
        rhythm_settings = gs.get_setting(gs.Path.RBSOURCE)
        rhythm_settings.connect('changed::visible-columns',
            self.on_visible_columns_changed)
        self.on_visible_columns_changed(rhythm_settings, 'visible-columns')
        
    def on_visible_columns_changed(self, settings, key):
        print("CoverArtBrowser DEBUG - on_visible_columns_changed()")
        # reset current columns
        print("CoverArtBrowser DEBUG - end on_visible_columns_changed()")
        for entry in self.col_map:
            col = self.get_column(self.col_map[entry])
            if entry in settings[key]:
                col.set_visible(True)
            else:
                if entry != 'title': 
                    col.set_visible(False)
            
        print ("CoverArtBrowser DEBUG - end on_visible_columns_changed()")
        
    def define_menu(self):
        popup = Menu(self.plugin, self.shell)
        popup.load_from_file('N/A',
                             'ui/coverart_entryview_full_pop_rb3.ui')
        signals = {
            'ev_full_play_track_menu_item': self.play_track_menu_item_callback,
            'ev_full_queue_track_menu_item': self.queue_track_menu_item_callback,
            'ev_full_new_playlist': self.add_playlist_menu_item_callback,
            'ev_full_show_properties_menu_item': self.show_properties_menu_item_callback,
            'ev_full_similar_track_menu_item': self.play_similar_track_menu_item_callback,
            'ev_full_similar_artist_menu_item': self.play_similar_artist_menu_item_callback,
            'ev_full_similar_genre_menu_item': self.play_similar_genre_menu_item_callback }
            
        popup.connect_signals(signals)
        popup.connect('pre-popup', self.add_external_menu)
        self.popup = popup
        
    def playlist_menu_item_callback(self, *args):
        print("CoverArtBrowser DEBUG - playlist_menu_item_callback")

        self.source.playlist_fillmenu(self.popup, 'ev_full_playlist_sub_menu_item', 'ev_full_playlist_section',
            self.actiongroup, self.add_to_static_playlist_menu_item_callback)
            
    def add_external_menu(self, *args):
        '''
        Callback when the popup menu is about to be displayed
        '''
        if not self.external_plugins:
            self.external_plugins = \
                    CreateExternalPluginMenu("ev_full_entryview", 4, self.popup)
            self.external_plugins.create_menu('entryview_full_popup_menu')
            
        self.playlist_menu_item_callback()

GObject.type_register(CoverArtEntryView)
GObject.type_register(CoverArtCompactEntryView)

