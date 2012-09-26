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
from coverart_album import Album

ui_context_menu = """
<ui>
    <popup name="EntryViewPopup">
        <placeholder name="PluginPlaceholder">
            <menuitem name="EntryViewPlay" action="EntryViewPlay"/>
            <menuitem name="EntryViewQueue" action="EntryViewQueue"/>
        </placeholder>
    </popup>
</ui>
"""

class CoverArtEntryView(RB.EntryView):
    def __init__(self, shell):
        '''
        Initializes the source.
        '''
        self.shell = shell
    
        super(RB.EntryView, self).__init__(db=shell.props.db, shell_player=shell.props.shell_player, is_drag_source=True)
            
        self.append_column(RB.EntryViewColumn.TRACK_NUMBER, True)
        self.append_column(RB.EntryViewColumn.GENRE, True)
        self.append_column(RB.EntryViewColumn.TITLE, True)
        self.append_column(RB.EntryViewColumn.ARTIST, True)
        self.append_column(RB.EntryViewColumn.ALBUM, True)
        self.append_column(RB.EntryViewColumn.DURATION, True)
        self.set_columns_clickable(False)
        
        uim = self.shell.props.ui_manager	
        self.play_action = Gtk.Action( 'EntryViewPlay',
                                       _('Play'),
                                       _('Add selected tracks to play queue and play'),
                                       _ )
                                   
        self.play_action.connect ( 'activate', self.play_tracks )
        
        self.queue_action = Gtk.Action( 'EntryViewQueue',
                                       _('Queue'),
                                       _('Queue selected tracks'),
                                       _ )
                                   
        self.queue_action.connect ( 'activate', self.queue_tracks )
        
        self.action_group = Gtk.ActionGroup( 'CoverArtEntryViewActionGroup' )
        self.action_group.add_action( self.play_action )
        self.action_group.add_action( self.queue_action )
        uim.insert_action_group( self.action_group, -1 )
        
        self.ui_id = uim.add_ui_from_string( ui_context_menu )
        self.popup_menu = uim.get_widget( "/EntryViewPopup" )
        uim.ensure_update()  
        
    def __del__(self):
        uim = self.shell.props.ui_manager

        uim.remove_action_group(self.action_group)
        uim.remove_ui(self.ui_id)
        uim.ensure_update()

        del self.action_group
        del self.play_action
        del self.queue_action
        
    def add_album(self, album):
        qm = RB.RhythmDBQueryModel.new_empty(self.shell.props.db)
        album.get_entries(qm)
        self.set_model(qm)
        
    def do_show_popup(self, over_entry):
        self.popup_menu.popup(None, None, None, None, 0,
            Gtk.get_current_event_time())

        return True
        
    def play_tracks(self, entry):
        self.queue_tracks( entry )
        # Start the music
        player = self.shell.props.shell_player
        player.stop()
        player.set_playing_source(self.shell.props.queue_source)
        player.playpause(True)
    
    def queue_tracks(self, entry):
        selected = self.get_selected_entries()
        selected.reverse()
        
        for entry in selected:
            self.shell.props.queue_source.add_entry( entry, 0 ) 

GObject.type_register(CoverArtEntryView)
