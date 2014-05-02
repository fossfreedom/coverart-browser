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
        
        self.pixbuf = None #GdkPixbuf.Pixbuf().new_from_file('empire.jpg')
        
        self.image = Gtk.Image()
        self.image.props.hexpand = True
        self.image.props.vexpand = True
        self.image.connect('draw', self.draw_cover_event)
        self.frame=Gtk.AspectFrame.new("", 0.5, 0.5, 1, False)
        self.update_cover(None, None, None)
        self.frame.add(self.image)
        
        #self.pack_end(self.frame, False, True, 1)
        self.attach(self.frame,3,0,1,1)
        self.connect('update-cover', self.update_cover)
        
    def update_cover(self, widget, source, entry):
        
        if entry:
            album = source.album_manager.model.get_from_dbentry(entry)
            self.pixbuf = album.cover.pixbuf
            self.frame.set_shadow_type(Gtk.ShadowType.NONE)
        else:
            self.pixbuf = None
            self.frame.set_shadow_type(Gtk.ShadowType.ETCHED_OUT)
            
        self.image.queue_draw()
        
    def window_resize(self, widget):
        alloc = self.get_allocation()
        if alloc.height < 10:
            return
        print (alloc.height)
        print (alloc.width)
        
        
        if (alloc.width / 3) < (MIN_IMAGE_SIZE+30) or \
           (alloc.height) < (MIN_IMAGE_SIZE+30):
            self.frame.props.visible = False
        else:
            self.frame.props.visible = True
            
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
        print (entry_view)
        
    def draw_rounded(self, cr, area, radius):
        """ draws rectangles with rounded (circular arc) corners """
        a,b,c,d=area
        cr.arc(a + radius, c + radius, radius, 2*(pi/2), 3*(pi/2))
        cr.arc(b - radius, c + radius, radius, 3*(pi/2), 4*(pi/2))
        cr.arc(b - radius, d - radius, radius, 0*(pi/2), 1*(pi/2))
        cr.arc(a + radius, d - radius, radius, 1*(pi/2), 2*(pi/2))
        cr.close_path()
        
    def draw_cover_event(self, widget, ctx):
        
        if not self.pixbuf:
            return
            
        alloc = self.image.get_allocation()
        
        p = self.pixbuf.scale_simple(alloc.width, alloc.height, GdkPixbuf.InterpType.BILINEAR) 
        offset = 15
        inside_area = (offset, alloc.width-offset, offset, alloc.height-offset)
        
        #Gdk.cairo_set_source_pixbuf(ctx, p, 15,15)
        Gdk.cairo_set_source_pixbuf(ctx, p, 0,0)
        #self.draw_rounded(ctx, inside_area, 10)
        #ctx.clip()
        ctx.paint()
        return True

        
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

        popup = Menu(self.plugin, self.shell)
        popup.load_from_file('ui/coverart_entryview_pop_rb2.ui',
                             'ui/coverart_entryview_pop_rb3.ui')
        signals = {
            'ev_play_track_menu_item': self.play_track_menu_item_callback,
            'ev_queue_track_menu_item': self.queue_track_menu_item_callback,
            'ev_new_playlist': self.add_playlist_menu_item_callback,
            'ev_show_properties_menu_item': self.show_properties_menu_item_callback,
            'ev_similar_track_menu_item': self.play_similar_track_menu_item_callback,
            'ev_similar_artist_menu_item': self.play_similar_artist_menu_item_callback }
            
        popup.connect_signals(signals)
        popup.connect('pre-popup', self.add_external_menu)
        self.popup = popup

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
        self.lastfm_similar_playlist = None
        
        self.set_columns_clickable(False)
        
        self.connect('selection-changed', self.selection_changed)

    def __del__(self):
        del self.action_group
        del self.play_action
        del self.queue_action
        
    def display_columns(self):
        pass
        
    def selection_changed(self, entry_view):
        print ("XXXXXXXXXXXXXXXX")
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
        print("CoverArtBrowser DEBUG - add_album()")

    def clear(self):
        print("CoverArtBrowser DEBUG - clear()")
        # self.set_model(RB.RhythmDBQueryModel.new_empty(self.shell.props.db))
        for row in self.qm:
            self.qm.remove_entry(row[0])

        print("CoverArtBrowser DEBUG - clear()")

    def do_entry_activated(self, entry):
        print("CoverArtBrowser DEBUG - do_entry_activated()")
        self.select_entry(entry)
        self.play_track_menu_item_callback(entry)
        print("CoverArtBrowser DEBUG - do_entry_activated()")
        return True
        
    def add_external_menu(self, *args):
        '''
        Callback when the popup menu is about to be displayed
        '''
        if not self.external_plugins:
            self.external_plugins = \
                    CreateExternalPluginMenu("ev_entryview", 4, self.popup)
            self.external_plugins.create_menu('entryview_popup_menu')
            
        self.playlist_menu_item_callback()

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
        print("CoverArtBrowser DEBUG - playlist_menu_item_callback")

        self.source.playlist_fillmenu(self.popup, 'ev_playlist_sub_menu_item', 'ev_playlist_section',
            self.actiongroup, self.add_to_static_playlist_menu_item_callback)

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
    def __init__(self, shell, source):
        '''
        Initializes the entryview.
        '''
        BaseView.__init__(self, shell, source)
    
    def display_columns(self):
        
        self.col_map = OrderedDict([
                        ('track-number', RB.EntryViewColumn.TRACK_NUMBER),
                        ('title', RB.EntryViewColumn.TITLE),
                        ('artist', RB.EntryViewColumn.ARTIST),
                        ('duration', RB.EntryViewColumn.DURATION),
                        ])
                        
        for entry in self.col_map:
            self.append_column(self.col_map[entry], True)
    
            
class CoverArtEntryView(BaseView):
    
    def __init__(self, shell, source):
        '''
        Initializes the entryview.
        '''
        BaseView.__init__(self, shell, source)
    
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

GObject.type_register(CoverArtEntryView)
