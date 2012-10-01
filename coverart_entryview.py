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
from gi.repository import Gio

import rb
import locale
import gettext

class CoverArtEntryView(RB.EntryView):
    LOCALE_DOMAIN = 'coverart_browser'
    
    def __init__(self, shell, source):
        '''
        Initializes the source.
        '''
        self.shell = shell
        self.source = source
        self.plugin = self.source.props.plugin
        self.albums = []

        super(RB.EntryView, self).__init__(db=shell.props.db,
            shell_player=shell.props.shell_player, is_drag_source=True)

        self.visible_cols = None
        self.new_visible_column()
        
        ordered_cols = ['track-number', 'genre', 'title', 'artist', 'album', 'duration']

        for val in ordered_cols:
            if val in self.visible_cols or val=='title':
                print val
                self._add_column(val)

        itercols = iter(self.visible_cols)

        for col in itercols:
            if col not in ordered_cols:
                print col
                self._add_column(col)

        self.set_columns_clickable(False)

        # UI elements need to be imported.
        ui = Gtk.Builder()
        ui.set_translation_domain(self.LOCALE_DOMAIN)
        ui.add_from_file(rb.find_plugin_file(self.plugin,
            'coverart_entryview.ui'))
        ui.connect_signals(self)

        self.popup_menu = ui.get_object('entryview_popup_menu')
        
        self.shell.props.shell_player.connect('playing-song-changed',
            self.playing_song_changed)
        self.shell.props.shell_player.connect('playing-changed',
            self.playing_changed)

        self.qm = RB.RhythmDBQueryModel.new_empty(self.shell.props.db)
        self.set_model(self.qm)

    def __del__(self):
        uim = self.shell.props.ui_manager

        uim.remove_action_group(self.action_group)
        uim.remove_ui(self.ui_id)
        uim.ensure_update()

        del self.action_group
        del self.play_action
        del self.queue_action

    def new_visible_column(self):
        setting = Gio.Settings('org.gnome.rhythmbox.sources')
        current_visible_cols = setting.get_value('visible-columns')
        #print self.visible_cols
        #print current_visible_cols
        
        if self.visible_cols == None:
            self.visible_cols = current_visible_cols
            print "new column from empty"
            return True

        itercol = iter(self.visible_cols)
        itercompare = iter(current_visible_cols)

        same=True

        try:
            for i in self.visible_cols:
                print self.visible_cols[i]
                print current_visible_cols[i]
                
                if self.visible_cols[1] != current_visible_cols[i]:
                    print "not the same"
                    same=False
        except:
            pass

        return same

    def _add_column(self, visible_column):
        # org.gnome.rhythmbox.sources visible-columns
        # default ['track-number', 'artist', 'album', 'genre', 'post-time']
        # with all columns visible ['post-time',

        if visible_column == 'track-number':
            self.append_column(RB.EntryViewColumn.TRACK_NUMBER, True)
            return

        if visible_column == 'title': # not a user defined column i.e. will always exist
            self.append_column(RB.EntryViewColumn.TITLE, True)
            return

        if visible_column == 'artist': 
            self.append_column(RB.EntryViewColumn.ARTIST, True)
            return

        if visible_column == 'album': 
            self.append_column(RB.EntryViewColumn.ALBUM, True)
            return

        if visible_column == 'genre': 
            self.append_column(RB.EntryViewColumn.GENRE, True)
            return

        if visible_column == 'comment': 
            self.append_column(RB.EntryViewColumn.COMMENT, True)
            return

        if visible_column == 'duration': 
            self.append_column(RB.EntryViewColumn.DURATION, True)
            return

        if visible_column == 'rating': 
            self.append_column(RB.EntryViewColumn.RATING, True)
            return

        if visible_column == 'bitrate': 
            self.append_column(RB.EntryViewColumn.QUALITY, True)
            return

        if visible_column == 'play-count': 
            self.append_column(RB.EntryViewColumn.PLAY_COUNT, True)
            return

        if visible_column == 'last-played': 
            self.append_column(RB.EntryViewColumn.LAST_PLAYED, True)
            return

        if visible_column == 'date': 
            self.append_column(RB.EntryViewColumn.YEAR, True)
            return

        if visible_column == 'first-seen': 
            self.append_column(RB.EntryViewColumn.FIRST_SEEN, True)
            return

        if visible_column == 'location': 
            self.append_column(RB.EntryViewColumn.LOCATION, True)
            return

        if visible_column == 'beats-per-minute': 
            self.append_column(RB.EntryViewColumn.BPM, True)
            return

        if visible_column == 'post-time':
            return

        # no mapping
        #EntryViewColumn.ERROR :
        #EntryViewColumn.LAST_SEEN :
        assert False, 'unknown column %s' % visible_column

    def get_album_list(self):
        return albums

    def add_album(self, album):
        print "CoverArtBrowser DEBUG - add_album()"
        album.get_entries(self.qm)
        self.albums.append(album)
        
        (_, playing) = self.shell.props.shell_player.get_playing()
        self.playing_changed(self.shell.props.shell_player, playing)
        print "CoverArtBrowser DEBUG - add_album()"

    def clear(self):
        print "CoverArtBrowser DEBUG - clear()"
        #self.set_model(RB.RhythmDBQueryModel.new_empty(self.shell.props.db))
        for row in self.qm:
            self.qm.remove_entry(row[0])

        del self.albums[:]
        print "CoverArtBrowser DEBUG - clear()"

    def do_entry_activated(self, entry):
        print "CoverArtBrowser DEBUG - do_entry_activated()"
        print entry
        self.select_entry(entry)
        self.play_track_menu_item_callback(entry)
        print "CoverArtBrowser DEBUG - do_entry_activated()"
        return True

    def do_show_popup(self, over_entry):
        print "CoverArtBrowser DEBUG - do_show_popup()"
        self.popup_menu.popup(None, None, None, None, 0,
            Gtk.get_current_event_time())

        print "CoverArtBrowser DEBUG - do_show_popup()"
        return True

    def play_track_menu_item_callback(self, entry):
        print "CoverArtBrowser DEBUG - play_track_menu_item_callback()"

        # clear the queue
        play_queue = self.shell.props.queue_source
        for row in play_queue.props.query_model:
            play_queue.remove_entry(row[0])

        self.queue_track_menu_item_callback(entry)
        # Start the music
        player = self.shell.props.shell_player
        player.stop()
        player.set_playing_source(self.shell.props.queue_source)

        player.playpause(True)
        print "CoverArtBrowser DEBUG - play_track_menu_item_callback()"

    def queue_track_menu_item_callback(self, entry):
        print "CoverArtBrowser DEBUG - queue_track_menu_item_callback()"
        selected = self.get_selected_entries()
        selected.reverse()

        selected = sorted(selected,
            key=lambda song: song.get_ulong(RB.RhythmDBPropType.TRACK_NUMBER))

        for entry in selected:
            self.shell.props.queue_source.add_entry(entry, -1)

        print "CoverArtBrowser DEBUG - queue_track_menu_item_callback()"


    def show_properties_menu_item_callback(self, entry):
        print "CoverArtBrowser DEBUG - show_properties_menu_item_callback()"

        info_dialog = RB.SongInfo(source=self.source, entry_view=self)

        info_dialog.show_all()
        
        print "CoverArtBrowser DEBUG - show_properties_menu_item_callback()"

    def playing_song_changed(self, shell_player, entry):
        print "CoverArtBrowser DEBUG - playing_song_changed()"
        print shell_player
        print entry

        if entry is not None and self.get_entry_contained(entry):
            self.set_state(RB.EntryViewState.PLAYING)
        else:
            self.set_state(RB.EntryViewState.NOT_PLAYING)

        print "CoverArtBrowser DEBUG - playing_song_changed()"

    def playing_changed(self, shell_player, playing):
        print "CoverArtBrowser DEBUG - playing_changed()"
        print shell_player
        print playing
        entry = shell_player.get_playing_entry()

        if entry is not None and self.get_entry_contained(entry):
            if playing:
                self.set_state(RB.EntryViewState.PLAYING)
            else:
                self.set_state(RB.EntryViewState.PAUSED)
        else:
            self.set_state(RB.EntryViewState.NOT_PLAYING)

        print "CoverArtBrowser DEBUG - playing_changed()"

GObject.type_register(CoverArtEntryView)
