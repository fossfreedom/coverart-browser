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

ui_context_menu = """
<ui>
    <popup name="EntryViewPopup">
        <menuitem name="EntryViewPlay" action="EntryViewPlay"/>
        <menuitem name="EntryViewQueue" action="EntryViewQueue"/>
        <separator/>
        <placeholder name="PluginPlaceholder"/>
    </popup>
</ui>
"""

class CoverArtEntryView(RB.EntryView):
    def __init__(self, shell):
        '''
        Initializes the source.
        '''
        self.shell = shell

        super(RB.EntryView, self).__init__(db=shell.props.db,
            shell_player=shell.props.shell_player, is_drag_source=True)

        self.append_column(RB.EntryViewColumn.TRACK_NUMBER, True)
        self.append_column(RB.EntryViewColumn.GENRE, True)
        self.append_column(RB.EntryViewColumn.TITLE, True)
        self.append_column(RB.EntryViewColumn.ARTIST, True)
        self.append_column(RB.EntryViewColumn.ALBUM, True)
        self.append_column(RB.EntryViewColumn.DURATION, True)
        self.set_columns_clickable(False)

        uim = self.shell.props.ui_manager

        self.play_action = Gtk.Action('EntryViewPlay',
            _('Play'), _('Add selected tracks to play queue and play'),
            _)

        self.play_action.connect('activate', self.play_tracks)

        self.queue_action = Gtk.Action('EntryViewQueue', _('Queue'),
            _('Queue selected tracks'), _)

        self.queue_action.connect('activate', self.queue_tracks)

        self.action_group = Gtk.ActionGroup('CoverArtEntryViewActionGroup')
        self.action_group.add_action(self.play_action)
        self.action_group.add_action(self.queue_action)
        uim.insert_action_group(self.action_group, -1)

        self.ui_id = uim.add_ui_from_string(ui_context_menu)
        self.popup_menu = uim.get_widget('/EntryViewPopup')
        uim.ensure_update()

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

    def add_album(self, album):
        print "CoverArtBrowser DEBUG - add_album()"
        album.get_entries(self.qm)

        (_, playing) = self.shell.props.shell_player.get_playing()
        self.playing_changed(self.shell.props.shell_player, playing)
        print "CoverArtBrowser DEBUG - add_album()"

    def clear(self):
        print "CoverArtBrowser DEBUG - clear()"
        #self.set_model(RB.RhythmDBQueryModel.new_empty(self.shell.props.db))
        for row in self.qm:
            self.qm.remove_entry(row[0])
        print "CoverArtBrowser DEBUG - clear()"

    def do_entry_activated(self, entry):
        print "CoverArtBrowser DEBUG - do_entry_activated()"
        print entry
        self.select_entry(entry)
        self.play_tracks(entry)
        print "CoverArtBrowser DEBUG - do_entry_activated()"
        return True

    def do_show_popup(self, over_entry):
        print "CoverArtBrowser DEBUG - do_show_popup()"
        self.popup_menu.popup(None, None, None, None, 0,
            Gtk.get_current_event_time())

        print "CoverArtBrowser DEBUG - do_show_popup()"
        return True

    def play_tracks(self, entry):
        print "CoverArtBrowser DEBUG - play_tracks()"

        # clear the queue
        play_queue = self.shell.props.queue_source
        for row in play_queue.props.query_model:
            play_queue.remove_entry(row[0])

        self.queue_tracks(entry)
        # Start the music
        player = self.shell.props.shell_player
        player.stop()
        player.set_playing_source(self.shell.props.queue_source)

        player.playpause(True)
        print "CoverArtBrowser DEBUG - play_tracks()"

    def queue_tracks(self, entry):
        print "CoverArtBrowser DEBUG - queue_tracks()"
        selected = self.get_selected_entries()
        selected.reverse()

        selected = sorted(selected,
            key=lambda song: song.get_ulong(RB.RhythmDBPropType.TRACK_NUMBER))

        for entry in selected:
            self.shell.props.queue_source.add_entry(entry, -1)

        print "CoverArtBrowser DEBUG - queue_tracks()"

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
