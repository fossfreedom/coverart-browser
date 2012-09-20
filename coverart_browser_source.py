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
import locale
import gettext


from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import RB
from gi.repository import Gdk
from gi.repository import GdkPixbuf

from coverart_album import AlbumLoader

class CoverArtBrowserSource(RB.Source):
    LOCALE_DOMAIN = 'coverart_browser'
 
    def __init__( self ):
        self.hasActivated = False
        RB.Source.__init__( self,name="CoverArtBrowserPlugin" )
        
        # create the source pop up
        self.source_menu = Gtk.Menu()
        
        self.source_menu_search_all_item = Gtk.MenuItem( 
            'Download all the covers' )
        self.source_menu_search_all_item.set_sensitive( False )
        self.source_menu.append( self.source_menu_search_all_item )
        
        self.source_menu.show_all()

        # status to show in the status bar
        self.status = ''

    def do_set_property( self, property, value ):
        if property.name == 'plugin':
            self.plugin = value

    def do_get_status( self, *args ):    
        try:
            progress = self.loader.progress
            progress_text = 'Loading...' if progress < 1 else ''
        except:
            progress = 1
            progress_text = ''
    
        return (self.status, progress_text, progress)

    def do_selected( self ):
        self.do_impl_activate()

    """ on source activation """
    def do_impl_activate( self ):
        print "do_impl_activate"
        # first time of activation -> add graphical stuff
        if self.hasActivated:
            return
        print "do_impl_activate again"
        
        # initialise some variables
        self.plugin = self.props.plugin
        self.shell = self.props.shell

        # setup translation support
        locale.setlocale(locale.LC_ALL, '')
        locale.bindtextdomain(self.LOCALE_DOMAIN, "/usr/share/locale")
        locale.textdomain(self.LOCALE_DOMAIN)
        gettext.bindtextdomain(self.LOCALE_DOMAIN, "/usr/share/locale")
        gettext.textdomain(self.LOCALE_DOMAIN)
        gettext.install(self.LOCALE_DOMAIN)

        #indicate that the source was activated before
        self.hasActivated = True
            
        # dialog has not been created so lets do so.
        ui = Gtk.Builder()
        ui.set_translation_domain(self.LOCALE_DOMAIN)
        ui.add_from_file(rb.find_plugin_file(self.plugin, "coverart_browser.ui"))
        ui.connect_signals( self )
        
        # load the page and put it in the source
        self.page = ui.get_object( 'main_box' )
        self.pack_start( self.page, True, True, 0 )               
        
        # get widgets
        self.status_label = ui.get_object( 'status_label' )
        self.covers_view = ui.get_object( 'covers_view' )
        self.search_entry = ui.get_object( 'search_entry' )
        self.request_status_box = ui.get_object( 'request_status_box' )
        self.request_spinner = ui.get_object( 'request_spinner' )
        self.request_statusbar = ui.get_object( 'request_statusbar' )
        self.request_cancel_button = ui.get_object( 'request_cancel_button' ) 
         
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
        self.loader.connect( 'load-finished', self.load_finished_callback)
        self.loader.load_albums()   
        
        print "CoverArtBrowser DEBUG - end show_browser_dialog"
    
    def load_finished_callback( self, _ ):
        print 'CoverArt Load Finished'
        self.source_menu_search_all_item.set_sensitive( True )
        self.source_menu_search_all_item.connect( 'activate', 
            self.search_all_covers_callback )
    
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
        # don't start another fetch if we are in middle of one right now
        if self.request_status_box.get_visible():
            return
             
        # fetch the album and hide the status_box once finished                     
        def hide_status_box( *args ):
            self.request_spinner.hide()    
        
            # all args except for args[0] are None if no cover was found
            if args[1]:
                self.request_statusbar.set_text( 'Cover found!' )
            else:
                self.request_statusbar.set_text( 'No cover found.' )

            # set a timeout to hide the box
            Gdk.threads_add_timeout( GLib.PRIORITY_DEFAULT, 1500, 
                lambda _: self.request_status_box.hide(), None )
                  
        self.loader.search_cover_for_album( album, hide_status_box )
                
        # show the status bar indicating we're fetching the cover
        self.request_statusbar.set_text( 
            'Requesting cover for %s - %s...' % (album.name, album.artist) )
        self.request_status_box.show_all()
        self.request_cancel_button.set_visible( False )
        
        print "CoverArtBrowser DEBUG - end cover_search_menu_callback()"
    
    def do_show_popup( source ):
        source.source_menu.popup( None, None, None, None, 0, 
            Gtk.get_current_event_time() )   
            
        return True
        
    def search_all_covers_callback( self, _ ):
        print "CoverArtBrowser DEBUG - search_all_covers_callback()"
        self.request_status_box.show_all()
        self.source_menu_search_all_item.set_sensitive( False )
        self.loader.search_all_covers( self.update_request_status_bar )
        
        print "CoverArtBrowser DEBUG - end search_all_covers_callback()"
        
    def update_request_status_bar( self, album ):
        if album:
            self.request_statusbar.set_text( 
                'Requesting cover for %s - %s...' % (album.name, album.artist) )
        else:
            self.request_status_box.hide()
            self.source_menu_search_all_item.set_sensitive( True )
            self.request_cancel_button.set_sensitive( True )
        
    def cancel_request_callback( self, _ ):
        self.request_cancel_button.set_sensitive( False )
        self.loader.cancel_cover_request()        
        
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
            self.status = ''
            return

        # now lets build up a status label containing some 'interesting stuff' 
        #about the album
        status = ('%s - %s' % ( album.name, album.artist )).decode('UTF-8')

    
        # Calculate duration and number of tracks from that album
        track_count = album.get_track_count()
        duration = album.calculate_duration_in_mins()
        
        if track_count == 1:
            status += (_(' has 1 track')).decode('UTF-8')
        else:
            status+= (_(' has %d tracks') % track_count).decode('UTF-8')

        if duration == 1:
            status += (_(' and a duration of 1 minute')).decode('UTF-8')
        else:
            status += (_(' and a duration of %d minutes') % duration).decode('UTF-8')

        self.status = status
        
        self.notify_status_changed()
        
GObject.type_register(CoverArtBrowserSource)

