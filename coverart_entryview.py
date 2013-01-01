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

import rb

from coverart_browser_prefs import GSetting
from coverart_browser_prefs import CoverLocale


class CoverArtEntryView(RB.EntryView):

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

        self.append_column(RB.EntryViewColumn.TRACK_NUMBER, False)
        self.append_column(RB.EntryViewColumn.TITLE, True)  # always shown
        self.append_column(RB.EntryViewColumn.GENRE, False)
        self.append_column(RB.EntryViewColumn.ARTIST, False)
        self.append_column(RB.EntryViewColumn.ALBUM, False)
        self.append_column(RB.EntryViewColumn.DURATION, False)
        self.append_column(RB.EntryViewColumn.COMMENT, False)
        self.append_column(RB.EntryViewColumn.RATING, False)
        self.append_column(RB.EntryViewColumn.QUALITY, False)
        self.append_column(RB.EntryViewColumn.PLAY_COUNT, False)
        self.append_column(RB.EntryViewColumn.LAST_PLAYED, False)
        self.append_column(RB.EntryViewColumn.YEAR, False)
        self.append_column(RB.EntryViewColumn.FIRST_SEEN, False)
        self.append_column(RB.EntryViewColumn.LOCATION, False)
        self.append_column(RB.EntryViewColumn.BPM, False)

        cl.switch_locale(cl.Locale.LOCALE_DOMAIN)

        # UI elements need to be imported.
        ui = Gtk.Builder()
        ui.set_translation_domain(cl.Locale.LOCALE_DOMAIN)
        ui.add_from_file(rb.find_plugin_file(self.plugin,
            'ui/coverart_entryview.ui'))
        ui.connect_signals(self)

        self.popup_menu = ui.get_object('entryview_popup_menu')

        # connect signals to the shell to know when the playing state changes
        self.shell.props.shell_player.connect('playing-song-changed',
            self.playing_song_changed)
        self.shell.props.shell_player.connect('playing-changed',
            self.playing_changed)

        self.playlist_sub_menu_item = ui.get_object('playlist_sub_menu_item')
        self.actiongroup = Gtk.ActionGroup('coverentryplaylist_submenu')
        uim = self.shell.props.ui_manager
        uim.insert_action_group(self.actiongroup)

        # connect the visible-columns global setting to update our entryview
        gs = GSetting()
        rhythm_settings = gs.get_setting(gs.Path.RBSOURCE)
        rhythm_settings.connect('changed::visible-columns',
            self.on_visible_columns_changed)
        self.on_visible_columns_changed(rhythm_settings, 'visible-columns')

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

    def __del__(self):
        uim = self.shell.props.ui_manager

        uim.remove_action_group(self.action_group)
        uim.remove_ui(self.ui_id)
        uim.ensure_update()

        del self.action_group
        del self.play_action
        del self.queue_action

    def on_visible_columns_changed(self, settings, key):
        print "CoverArtBrowser DEBUG - on_visible_columns_changed()"
        #reset current columns
        self.props.visible_columns = settings[key]
        print "CoverArtBrowser DEBUG - end on_visible_columns_changed()"

    def add_album(self, album):
        print "CoverArtBrowser DEBUG - add_album()"
        tracks = album.get_tracks()

        for track in tracks:
            self.qm.add_entry(track.entry, -1)

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
        self.select_entry(entry)
        self.play_track_menu_item_callback(entry)
        print "CoverArtBrowser DEBUG - do_entry_activated()"
        return True

    def do_show_popup(self, over_entry):
        if over_entry:
            print "CoverArtBrowser DEBUG - do_show_popup()"

            self.popup_menu.popup(None, None, None, None, 0,
                Gtk.get_current_event_time())

        return over_entry

    def play_track_menu_item_callback(self, entry):
        print "CoverArtBrowser DEBUG - play_track_menu_item_callback()"

        # clear the queue
        play_queue = self.shell.props.queue_source
        for row in play_queue.props.query_model:
            play_queue.remove_entry(row[0])

        self.add_tracks_to_source(self.shell.props.queue_source)
        # Start the music
        player = self.shell.props.shell_player
        player.stop()
        player.set_playing_source(self.shell.props.queue_source)

        player.playpause(True)
        print "CoverArtBrowser DEBUG - play_track_menu_item_callback()"

    def queue_track_menu_item_callback(self, entry):
        print "CoverArtBrowser DEBUG - queue_track_menu_item_callback()"

        self.add_tracks_to_source(self.shell.props.queue_source)

    def add_tracks_to_source(self, source):
        selected = self.get_selected_entries()
        selected.reverse()

        selected = sorted(selected,
            key=lambda song: song.get_ulong(RB.RhythmDBPropType.TRACK_NUMBER))

        for entry in selected:
            source.add_entry(entry, -1)

        print "CoverArtBrowser DEBUG - queue_track_menu_item_callback()"

    def love_track(self, rating):
        '''
        utility function to set the rating for selected tracks
        '''
        selected = self.get_selected_entries()

        for entry in selected:
            self.shell.props.db.entry_set(entry, RB.RhythmDBPropType.RATING,
                rating)

        self.shell.props.db.commit()

    def show_properties_menu_item_callback(self, entry):
        print "CoverArtBrowser DEBUG - show_properties_menu_item_callback()"

        info_dialog = RB.SongInfo(source=self.source, entry_view=self)

        info_dialog.show_all()

        print "CoverArtBrowser DEBUG - show_properties_menu_item_callback()"

    def playing_song_changed(self, shell_player, entry):
        print "CoverArtBrowser DEBUG - playing_song_changed()"

        if entry is not None and self.get_entry_contained(entry):
            self.set_state(RB.EntryViewState.PLAYING)
        else:
            self.set_state(RB.EntryViewState.NOT_PLAYING)

        print "CoverArtBrowser DEBUG - playing_song_changed()"

    def playing_changed(self, shell_player, playing):
        print "CoverArtBrowser DEBUG - playing_changed()"
        entry = shell_player.get_playing_entry()

        if entry is not None and self.get_entry_contained(entry):
            if playing:
                self.set_state(RB.EntryViewState.PLAYING)
            else:
                self.set_state(RB.EntryViewState.PAUSED)
        else:
            self.set_state(RB.EntryViewState.NOT_PLAYING)

        print "CoverArtBrowser DEBUG - playing_changed()"

    def add_playlist_menu_item_callback(self, menu_item):
        print "CoverArtBrowser DEBUG - add_playlist_menu_item_callback"
        playlist_manager = self.shell.props.playlist_manager
        playlist = playlist_manager.new_playlist('', False)

        self.add_tracks_to_source(playlist)

    def playlist_menu_item_callback(self, menu_item):
        print "CoverArtBrowser DEBUG - playlist_menu_item_callback"

        self.source.playlist_fillmenu(self.playlist_sub_menu_item,
            self.actiongroup, self.add_to_static_playlist_menu_item_callback)

    def add_to_static_playlist_menu_item_callback(self, action, playlist,
        favourite):
        print "CoverArtBrowser DEBUG - " + \
            "add_to_static_playlist_menu_item_callback"
        self.add_tracks_to_source(playlist)

    def _on_library_sorting_changed(self, view, _):
        self._old_sort_order = self.props.sort_order

        self.set_sorting_type(view.props.sort_order)

    def _notify_sort_order(self, view, _, library_view):
        if self.props.sort_order != self._old_sort_order:
            self.resort_model()

            # update library source's view direction
            library_view.set_sorting_type(self.props.sort_order)

GObject.type_register(CoverArtEntryView)
