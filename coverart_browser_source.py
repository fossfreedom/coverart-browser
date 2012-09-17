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

import rb

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import RB
from gi.repository import GdkPixbuf

from coverart_album import AlbumLoader
from coverart_album import Album

class CoverArtBrowserSource(RB.Source):
    def __init__( self ):
        self.hasActivated = False
        RB.Source.__init__( self,name="CoverArtBrowserPlugin" )

    def do_set_property( self, property, value ):
        if property.name == 'plugin':
            self.plugin = value

    def do_selected( self ):
        self.do_impl_activate()

    """ on source activation """
    def do_impl_activate( self ):
        # first time of activation -> add graphical stuff
        if self.hasActivated:
            return
        
        # initialise some variables
        self.plugin = self.props.plugin
        self.shell = self.props.shell
        
        #indicate that the source was activated before
        self.hasActivated = True
            
        # dialog has not been created so lets do so.
        ui = Gtk.Builder()
        ui.add_from_file(rb.find_plugin_file(self.plugin, "coverart_browser.ui"))
        ui.connect_signals( self )
        
        # load the page and put it in the source
        self.page = ui.get_object( 'main_box' )
        self.pack_start( self.page, True, True, 0 )               
        
        # get widgets
        self.status_label = ui.get_object( 'status_label' )
        self.covers_view = ui.get_object( 'covers_view' )
        self.search_entry = ui.get_object( 'search_entry' )
         
        # set the model for the icon view              
        self.covers_model_store = Gtk.ListStore( GObject.TYPE_STRING, 
                                                 GdkPixbuf.Pixbuf, 
                                                 object )
                                           
        self.covers_model = self.covers_model_store.filter_new()
        self.covers_model.set_visible_func( self.visible_covers_callback )
        
        self.covers_view.set_model( self.covers_model )
                
        # size pixbuf updated workaround
        self.covers_model_store.connect( 'row-changed', 
                                         self.update_iconview_callback )
                                          
        # load the albums
        self.loader = AlbumLoader( self.plugin, self.covers_model_store )
        self.loader.load_albums()   
        
        print "CoverArtBrowser DEBUG - end show_browser_dialog"
    
    def visible_covers_callback( self, model, iter, data ):
        searchtext = self.search_entry.get_text()
        
        if searchtext == "":
            return True
            
        return model[iter][2].contains( searchtext )
    
    def icon_press_callback( self, entry, pos, event ):
        if pos is Gtk.EntryIconPosition.SECONDARY:
            entry.set_text( '' )
        
        self.searchchanged_callback( entry )
    
    def searchchanged_callback( self, gtk_entry ):
        print "CoverArtBrowser DEBUG - searchchanged_callback"

        self.covers_model.refilter()
        
        print "CoverArtBrowser DEBUG - end searchchanged_callback"
        
    def update_iconview_callback( self, *args ):
        self.covers_view.set_columns( 0 )
        self.covers_view.set_columns( -1 )
                       
    def play_menu_callback(self, _, album):
        # callback when play an album  
        print "CoverArtBrowser DEBUG - play_menu_callback"
 
        # clear the queue
        play_queue = self.shell.props.queue_source
        for row in play_queue.props.query_model:
            play_queue.remove_entry(row[0])
 
        self.queue_album( album )        
    
        # Start the music
        player = self.shell.props.shell_player
        player.stop()
        player.set_playing_source( self.shell.props.queue_source )
        player.playpause( True )
        print "CoverArtBrowser DEBUG - end play_menu_callback"

    def queue_album( self, album ):
        # Retrieve and sort the entries of the album
        songs = sorted( album.entries, 
                        key=lambda song: song.get_ulong( 
                            RB.RhythmDBPropType.TRACK_NUMBER) )
        
        # Add the songs to the play queue
        for song in songs:
            self.shell.props.queue_source.add_entry( song, -1 )
        
    def mouseclick_callback(self, iconview, event):     
        print "CoverArtBrowser DEBUG - mouseclick_callback()"
        if event.button == 3:
            x = int( event.x )
            y = int( event.y )
            time = event.time
            pthinfo = iconview.get_path_at_pos( x, y )

            if pthinfo is None:
                return

            iconview.grab_focus()
                                
            model = iconview.get_model()
            album = model[pthinfo][2]               
                 
            self.popup_menu = Gtk.Menu()
            play_album_menu = Gtk.MenuItem( _("Play Album") )
            play_album_menu.connect( "activate", self.play_menu_callback, album )
            self.popup_menu.append( play_album_menu )
            
            queue_album_menu = Gtk.MenuItem( _("Queue Album") )
            queue_album_menu.connect( "activate", self.queue_menu_callback, album )
            self.popup_menu.append( queue_album_menu )
            
            cover_search_menu = Gtk.MenuItem( _("Search for covers") )
            cover_search_menu.connect( "activate", self.cover_search_menu_callback, album )
            self.popup_menu.append( cover_search_menu )
            
            self.popup_menu.show_all()
            
            self.popup_menu.popup( None, None, None, None, event.button, time )

        print "CoverArtBrowser DEBUG - end mouseclick_callback()"
        return
        
    def cover_search_menu_callback( self, _, album ):
        print "CoverArtBrowser DEBUG - cover_search_menu_callback()"

        self.loader.search_cover_for_album( album )     
        
        print "CoverArtBrowser DEBUG - cover_search_menu_callback()"
        
    def queue_menu_callback( self, _, album ):
        print "CoverArtBrowser DEBUG - queue_menu_callback()"
        
        self.queue_album( album )
        
        print "CoverArtBrowser DEBUG - queue_menu_callback()"
                
    def selectionchanged_callback( self, widget ):
        print "CoverArtBrowser DEBUG - selectionchanged_callback"
        # callback when focus had changed on an album
        model = widget.get_model()
        try:
            album = model[widget.get_selected_items()[0]][2]
        except:
            self.status_label.set_label( '' )
            return

        # now lets build up a status label containing some 'interesting stuff' about the album
        label = '%s - %s' % ( album.name, album.artist )
    
        # Calculate duration and number of tracks from that album
        track_count = album.get_track_count()
        duration = album.calculate_duration_in_mins()
        
        if track_count == 1:
            label += _(' has 1 track')
        else:
            label += ' has %d tracks' % track_count

        if duration == 1:
            label += _(' and a duration of 1 minute')
        else:
            label += ' and a duration of %d minutes' % duration

        self.status_label.set_label( label )
        
GObject.type_register(CoverArtBrowserSource)

