import string
import sys
import re
import os, threading
from threading import Thread
from sets import Set
from Queue import Queue
import cgi
import traceback
import rb

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import RB
from gi.repository import GdkPixbuf
from gi.repository import Peas
from gi.repository import Gdk
from gi.repository import GLib

from coverart_album import AlbumLoader, Album

class CoverArtBrowserSource(RB.Source):
    def __init__( self ):
        self.hasActivated = False
        RB.Source.__init__( self,name="CoverArtBrowserPlugin" )

    def do_set_property( self, property, value ):
        if property.name == 'plugin':
            self.plugin = value

    def do_selected( self ):
        self.do_impl_activate()

    """ on source actiavation, e.g. double click on source or playing something in this source """
    def do_impl_activate( self ):
        # first time of activation -> add graphical stuff
        if not self.hasActivated:
            self.plugin = self.props.plugin
            self.shell = self.props.shell
            self.db = self.shell.props.db;
            self.entry_type = self.props.entry_type
            self.hasActivated = True
            
            self.loader = AlbumLoader( self.plugin )
        else:
            return
            
        # dialog has not been created so lets do so.
        ui = Gtk.Builder()
        ui.add_from_file(rb.find_plugin_file(self.plugin, "coverart_browser.ui"))
        
        # load the page and put it in the source
        self.page = ui.get_object( 'main_box' )
        self.pack_start( self.page, True, True, 0 )               
        
        # get widgets
        self.status_label = ui.get_object( 'status_label' )
        self.covers_view = ui.get_object( 'covers_view' )
         
        # set the model for the icon view              
        self.covers_model = Gtk.ListStore( GObject.TYPE_STRING, 
                                           GdkPixbuf.Pixbuf, 
                                           object )
        self.covers_view.set_model( self.covers_model )
        
        # connect signals
        self.covers_view.connect( 'item-activated', 
                                  self.coverdoubleclicked_callback)
        self.covers_view.connect( 'button-press-event', 
                                  self.mouseclick_callback)
        self.covers_view.connect( 'selection_changed',
                                  self.selectionchanged_callback) 
                                          
        # size change workaround
        scrolled_window = ui.get_object( 'scrolled_window' )
        scrolled_window.connect( 'size-allocate', self.size_allocate_callback )
                                          
        # load the albums
        self.loader.load_albums( self.db, self.covers_model )   
        
        print "CoverArtBrowser DEBUG - end show_browser_dialog"       
         
    def size_allocate_callback( self, allocation, _ ):
        self.covers_view.set_columns( 0 )
        self.covers_view.set_columns( -1 )
                       
    def coverdoubleclicked_callback(self, widget,item):
        # callback when double clicking on an album 
        print "CoverArtBrowser DEBUG - coverdoubleclicked_callback"
        model = widget.get_model()
        album = model[item][2]

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
        print "CoverArtBrowser DEBUG - end coverdoubleclicked_callback"

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
            main_menu = Gtk.MenuItem("Queue Album")
            main_menu.connect( "activate", self.queue_menu_callback, album )
            self.popup_menu.append( main_menu )
            self.popup_menu.show_all()
            
            self.popup_menu.popup( None, None, None, None, event.button, time )

        print "CoverArtBrowser DEBUG - end mouseclick_callback()"
        return
        
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
            print "nothing to do"
            return

        # now lets build up a status label containing some 'interesting stuff' about the album
        label = '%s - %s' % ( album.name, album.artist )
    
        # Calculate duration and number of tracks from that album
        track_count = album.get_track_count()
        duration = album.calculate_duration_in_mins()
        
        if track_count == 1:
            label += ' haves 1 track'
        else:
            label += ' haves %d tracks' % track_count

        if duration == 1:
            label += ' and a duration of 1 minute'
        else:
            label += ' and a duration of %d minutes' % duration

        self.status_label.set_label( label )
        
GObject.type_register(CoverArtBrowserSource)

