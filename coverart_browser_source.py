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
from coverart_album import Album

class CoverArtBrowserSource(RB.Source):
    LOCALE_DOMAIN = 'coverart_browser'
    filter_type = Album.FILTER_ALL
    search_text = ''
 
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
        
        # get widgets for main icon-view
        self.status_label = ui.get_object( 'status_label' )
        self.covers_view = ui.get_object( 'covers_view' )
        self.popup_menu = ui.get_object( 'popup_menu' )
        self.cover_search_menu_item = ui.get_object( 'cover_search_menu_item' )
        self.request_status_box = ui.get_object( 'request_status_box' )
        self.request_spinner = ui.get_object( 'request_spinner' )
        self.request_statusbar = ui.get_object( 'request_statusbar' )
        self.request_cancel_button = ui.get_object( 'request_cancel_button' )

        # workaround for some RBSearchEntry's problems
        search_entry = ui.get_object( 'search_entry' )
        search_entry.set_placeholder(_('Search album'))
        search_entry.show_all()

        # get widgets for source popup
        self.source_menu = ui.get_object( 'source_menu' )
        self.source_menu_search_all_item = ui.get_object( 'source_search_menu_item' )


        # get widgets for filter popup
        self.filter_menu = ui.get_object( 'filter_menu' )
        self.filter_menu_all_item = ui.get_object( 'filter_all_menu_item' )
        self.filter_menu_artist_item = ui.get_object( 'filter_artist_menu_item' )
        self.filter_menu_album_artist_item = ui.get_object( 'filter_album_artist_menu_item' )
        self.filter_menu_album_item = ui.get_object( 'filter_album_menu_item' )
         
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
        self.loader.connect( 'load-finished', self.load_finished_callback )
        self.loader.connect( 'album-modified', self.album_modified_callback )
        self.loader.load_albums()   
        
        print "CoverArtBrowser DEBUG - end show_browser_dialog"
    
    def load_finished_callback( self, _ ):
        print 'CoverArt Load Finished'
        self.source_menu_search_all_item.set_sensitive( True )
        self.source_menu_search_all_item.connect( 'activate', 
            self.search_all_covers_callback )
            
    def album_modified_callback( self, _, modified_album ):
        print "CoverArtBrowser DEBUG - album_modified_callback"
        try:
            album = \
                self.covers_model[self.covers_view.get_selected_items()[0]][2]
        except:
            return
            
        if album is modified_album:
            self.selectionchanged_callback( self.covers_view )
    
        print "CoverArtBrowser DEBUG - end album_modified_callback"
    def visible_covers_callback( self, model, iter, data ):
#        searchtext = self.search_entry.get_text()
        
        if self.search_text == "":
            return True
            
        return model[iter][2].contains( self.search_text, self.filter_type )

    def search_show_popup_callback( self, entry ):
        self.filter_menu.popup( None, None, None, None, 0, 
                                Gtk.get_current_event_time() )
    
    def searchchanged_callback( self, entry, text ):
        print "CoverArtBrowser DEBUG - searchchanged_callback"

        self.search_text = text
        self.covers_model.refilter()
        
        print "CoverArtBrowser DEBUG - end searchchanged_callback"
        
    def update_iconview_callback( self, *args ):
        self.covers_view.set_columns( 0 )
        self.covers_view.set_columns( -1 )                  
            
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
            self.selected_album = model[pthinfo][2]               
                        
            self.popup_menu.popup( None, None, None, None, event.button, time )

        print "CoverArtBrowser DEBUG - end mouseclick_callback()"
        return
        
    def play_album_menu_item_callback(self, _):
        # callback when play an album  
        print "CoverArtBrowser DEBUG - play_menu_callback"
 
        # clear the queue
        play_queue = self.shell.props.queue_source
        for row in play_queue.props.query_model:
            play_queue.remove_entry(row[0])
 
        self.queue_selected_album()        
    
        # Start the music
        player = self.shell.props.shell_player
        player.stop()
        player.set_playing_source( self.shell.props.queue_source )
        player.playpause( True )
        print "CoverArtBrowser DEBUG - end play_menu_callback"
        
    def queue_album_menu_item_callback( self, _):
        print "CoverArtBrowser DEBUG - queue_menu_callback()"
        
        self.queue_selected_album()
        
        print "CoverArtBrowser DEBUG - queue_menu_callback()"

    def queue_selected_album( self):
        # Retrieve and sort the entries of the album
        songs = sorted( self.selected_album.entries, 
                        key=lambda song: song.get_ulong( 
                            RB.RhythmDBPropType.TRACK_NUMBER) )
        
        # Add the songs to the play queue
        for song in songs:
            self.shell.props.queue_source.add_entry( song, -1 )
        
    def cover_search_menu_item_callback( self, _ ):
        print "CoverArtBrowser DEBUG - cover_search_menu_item_callback()"
        # don't start another fetch if we are in middle of one right now
        if self.request_status_box.get_visible():
            return
             
        print 'hello'
        # fetch the album and hide the status_box once finished                     
        def cover_search_callback( *args ):
            self.request_spinner.hide()    
        
            # all args except for args[0] are None if no cover was found
            if args[1]:
                self.request_statusbar.set_text( _('Cover found!') )
            else:
                self.request_statusbar.set_text( _('No cover found.') )

            def restore( _ ):
                self.request_status_box.hide()
                self.cover_search_menu_item.set_sensitive( True )
                self.source_menu_search_all_item.set_sensitive( True )

            # set a timeout to hide the box and enable items
            Gdk.threads_add_timeout( GLib.PRIORITY_DEFAULT, 1500, restore, 
                None )
                  
        self.loader.search_cover_for_album( self.selected_album, 
            cover_search_callback )
                
        # show the status bar indicating we're fetching the cover
        self.request_statusbar.set_text( 
            (_('Requesting cover for %s - %s...') % 
            (self.selected_album.name, self.selected_album.artist)).decode('UTF-8') )
        self.request_status_box.show_all()
        self.request_cancel_button.set_visible( False )
        
        # disable full cover search and cover search items
        self.cover_search_menu_item.set_sensitive( False )
        self.source_menu_search_all_item.set_sensitive( False )
        
        print "CoverArtBrowser DEBUG - end cover_search_menu_item_callback()"
    
    def do_show_popup( self ):
        self.source_menu.popup( None, None, None, None, 0, 
            Gtk.get_current_event_time() )   
            
        return True
        
    def search_all_covers_callback( self, _ ):
        print "CoverArtBrowser DEBUG - search_all_covers_callback()"
        self.request_status_box.show_all()
        self.source_menu_search_all_item.set_sensitive( False )
        self.cover_search_menu_item.set_sensitive( False )
        self.loader.search_all_covers( self.update_request_status_bar )
        
        print "CoverArtBrowser DEBUG - end search_all_covers_callback()"
        
    def update_request_status_bar( self, album ):
        if album:
            self.request_statusbar.set_text( 
                (_('Requesting cover for %s - %s...') % (album.name, album.artist)).decode('UTF-8') )
        else:
            self.request_status_box.hide()
            self.source_menu_search_all_item.set_sensitive( True )
            self.cover_search_menu_item.set_sensitive( True )
            self.request_cancel_button.set_sensitive( True )
        
    def cancel_request_callback( self, _ ):
        self.request_cancel_button.set_sensitive( False )
        self.loader.cancel_cover_request()        
                        
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
        label = ('%s - %s' % ( album.name, album.album_artist )).decode('UTF-8')
    
        # Calculate duration and number of tracks from that album
        track_count = album.get_track_count()
        duration = album.calculate_duration_in_mins()
        
        if track_count == 1:
            label += (_(' has 1 track')).decode('UTF-8')
        else:
            label+= (_(' has %d tracks') % track_count).decode('UTF-8')

        if duration == 1:
            label += (_(' and a duration of 1 minute')).decode('UTF-8')
        else:
            label += (_(' and a duration of %d minutes') % duration).decode('UTF-8')

        self.status_label.set_label( label )

    def filter_menu_callback( self, radiomenu ):
        # radiomenu is of type GtkRadioMenuItem

        if radiomenu == self.filter_menu_all_item:
            self.filter_type = Album.FILTER_ALL
        elif radiomenu == self.filter_menu_album_item:
            self.filter_type = Album.FILTER_ALBUM
        elif radiomenu == self.filter_menu_artist_item:
            self.filter_type = Album.FILTER_ARTIST
        elif radiomenu == self.filter_menu_album_artist_item:
            self.filter_type = Album.FILTER_ALBUM_ARTIST
        else:
            assert "unknown radiomenu"
            
        self.searchchanged_callback( _, self.search_text )
            
GObject.type_register(CoverArtBrowserSource)

