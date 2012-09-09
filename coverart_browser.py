# -*- Mode: python; coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
#
# Copyright (C) 2012 - fossfreedom
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

CoverSize = 92

class CoverArtBrowserPlugin(GObject.Object, Peas.Activatable):
    __gtype_name = 'CoverArtBrowserPlugin'
    object = GObject.property(type=GObject.Object)
    
    def __init__(self):
        GObject.Object.__init__(self)
        

    def do_activate(self):
        print "CoverArtBrowser DEBUG - do_activate"
        shell = self.object       
        
        icon_file_name = rb.find_plugin_file(self, "coverbrowser.png")
        size = Gtk.icon_size_lookup( Gtk.IconSize.LARGE_TOOLBAR )
        pxbf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon_file_name, size[1], size[2] )
        
        self.dialog = GObject.new ( CoverArtDisplay, plugin=self, 
        			    name=_("Cover Art Browser"), pixbuf=pxbf )
        group = RB.DisplayPageGroup.get_by_id( "library" )
        shell.append_display_page( self.dialog, group )
        
        print "CoverArtBrowser DEBUG - end do_activate"
        
    def do_deactivate(self):
        print "CoverArtBrowser DEBUG - do_deactivate"
        self.dialog.delete_thyself()
        print "CoverArtBrowser DEBUG - end do_deactivate"
            
class CoverArtDisplay( RB.DisplayPage ):
	def __init__(self):
        super( CoverArtDisplay, self ).__init__()     
        self.has_activated = False   
        self.cover_db = RB.ExtDB( name="album-art" )           
         	                	
    def do_selected(self):
        print "CoverArtBrowser DEBUG - initialise_source"
        
        if self.has_activated:
            return
        else:
            self.has_activated = True
        
        plugin = self.props.plugin
        self.ui_file = rb.find_plugin_file(plugin,"coverart_browser.ui")
		self.shell = plugin.object
		self.db = self.shell.props.db         
        
        # dialog has not been created so lets do so.
        self.ui = Gtk.Builder()
        self.ui.add_from_file( self.ui_file )
        
        self.status_label = self.ui.get_object("status_label")
        self.covers_view = self.ui.get_object("covers_view")
    
        self.vbox=self.ui.get_object("dialog-vbox1")
        self.vbox.reparent(self)
        self.vbox.show_all()
        self.show_all()
        #self.shell.add_widget(self.dialog, RB.ShellUILocation.MAIN_TOP,True,True)

        self.covers_model = Gtk.ListStore(GObject.TYPE_STRING, GdkPixbuf.Pixbuf, object)
        self.covers_view.set_model(self.covers_model)
        self.unknown_cover = GdkPixbuf.Pixbuf.new_from_file_at_size(\
                    rb.find_plugin_file(plugin, 'rhythmbox-missing-artwork.svg'), \
                    CoverSize, \
                    CoverSize)
        self.error_cover = GdkPixbuf.Pixbuf.new_from_file_at_size(\
                    rb.find_plugin_file(plugin, 'rhythmbox-error-artwork.svg'), \
                    CoverSize, \
                    CoverSize)
        self.iter = None

        # for performance - the actual loading of album pictures is done in another thread
        self.album_loader = Thread(target = self.album_load)

        self.album_loader.start()

        # ok - lets query for all the albums names
        self.album_queue = Queue()
        self.albums = Set()
        self.album_count = 0
        self.cover_count = 0

        q = GLib.PtrArray()
        self.db.query_append_params(q, \
                RB.RhythmDBQueryType.EQUALS, \
                RB.RhythmDBPropType.TYPE, \
        self.db.entry_type_get_by_name("song"))
        qm = RB.RhythmDBQueryModel.new_empty(self.db)
        self.db.do_full_query_parsed(qm,q)
        

        def process_entry(model, path, iter, data):
            (entry,) = model.get(iter, 0)       
            album = entry.get_string( RB.RhythmDBPropType.ALBUM )

            if album not in self.albums:
                pixbuf = self.unknown_cover
                artist = entry.get_string( RB.RhythmDBPropType.ARTIST ) 

                self.album_count += 1
                self.albums.add(album)
                tree_iter = self.covers_model.append((cgi.escape('%s - %s' % (artist, album)),pixbuf,entry))
                self.iter = self.iter or tree_iter
                self.album_queue.put([artist, album, entry, tree_iter])

        # temporarily disconnect the covers_view from the model to stop the flickering
        # whilst updating
        self.covers_view.freeze_child_notify()
        self.covers_view.set_model(None)
        qm.foreach(process_entry, None)
        self.covers_view.set_model(self.covers_model)
        self.covers_view.thaw_child_notify()

        print "CoverArtBrowser DEBUG - end show_browser_dialog"       
            
    def coverdoubleclicked_callback(self, widget,item):
        # callback when double clicking on an album 
        print "CoverArtBrowser DEBUG - coverdoubleclicked_callback"
        model=widget.get_model()
        entry = model[item][2]

        # clear the queue
        play_queue = self.shell.props.queue_source
        for row in play_queue.props.query_model:
            play_queue.remove_entry(row[0])

        st_album = entry.get_string( RB.RhythmDBPropType.ALBUM ) or _("Unknown")
        self.queue_album(st_album)  
    
        # Start the music
        player = self.shell.props.shell_player
        player.stop()
        player.set_playing_source(self.shell.props.queue_source)
        player.playpause(True)
        print "CoverArtBrowser DEBUG - end coverdoubleclicked_callback"


    def queue_album(self, st_album):
        print "CoverArtBrowser DEBUG - queue_album"
        # ok, query for all the tracks for the album and add them to the queue
        
        query = GLib.PtrArray()
        self.db.query_append_params(query, \
                        RB.RhythmDBQueryType.EQUALS, \
                        RB.RhythmDBPropType.ALBUM, st_album)
        query_model = RB.RhythmDBQueryModel.new_empty(self.db)
        self.db.do_full_query_parsed(query_model, query)
    
        # Find all the songs from that album
        songs = []
        for row in query_model:
            songs.append(row[0])
  
        # Sort the songs
        songs = sorted(songs, key=lambda song: song.get_ulong(RB.RhythmDBPropType.TRACK_NUMBER))
        
        # Add the songs to the play queue
        for song in songs:
            self.shell.props.queue_source.add_entry(song, -1)
        print "CoverArtBrowser DEBUG - end queue_album"
        
    def mouseclick_callback(self, iconview, event):     
        print "CoverArtBrowser DEBUG - mouseclick_callback()"

        x = int(event.x)
        y = int(event.y)
        time = event.time
        pthinfo = iconview.get_path_at_pos(x, y)

        if pthinfo is None:
            return

        iconview.grab_focus()
                            
        model=iconview.get_model()
        entry = model[pthinfo][2]               
     
        if event.button == 3:
            # when right-click then...
            st_album = entry.get_string( RB.RhythmDBPropType.ALBUM )
            
            self.popup_menu = Gtk.Menu()
            main_menu = Gtk.MenuItem("Queue Album")
            main_menu.connect("activate", self.queue_menu_callback, st_album)
            self.popup_menu.append(main_menu)
            self.popup_menu.show_all()
            
            self.popup_menu.popup( None, None, None, None, event.button, time)

        print "CoverArtBrowser DEBUG - end mouseclick_callback()"
        return
        
    def queue_menu_callback(self, menu, item):
        print "CoverArtBrowser DEBUG - queue_menu_callback()"
        
        self.queue_album( item )
        
        print "CoverArtBrowser DEBUG - queue_menu_callback()"
        
    def album_load(self):
        print "CoverArtBrowser DEBUG - album_load"
        
        while True:
            artist, album, entry, tree_iter = self.album_queue.get()

            key = entry.create_ext_db_key(RB.RhythmDBPropType.ALBUM)
            art_location = self.cover_db.lookup(key)
            if art_location is not None and os.path.exists (art_location):
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(art_location, CoverSize, CoverSize)
                except:
                    pixbuf = self.error_cover
                    
                self.cover_count += 1
                Gdk.threads_enter()
                self.covers_model.set(tree_iter, 1, pixbuf)
                albumleft = self.album_count-self.cover_count
                self.status_label.set_label("%d covers left to download" % albumleft)
                Gdk.threads_leave()
                
            if self.album_queue.empty():
                Gdk.threads_enter()
                
                self.covers_view.connect("item-activated", self.coverdoubleclicked_callback)
                self.covers_view.connect('button-press-event', self.mouseclick_callback)
                self.covers_view.connect('selection_changed', self.selectionchanged_callback)
                Gdk.threads_leave()
        print "CoverArtBrowser DEBUG - end album_load"
        
    def selectionchanged_callback(self, widget):
        print "CoverArtBrowser DEBUG - selectionchanged_callback"
        # callback when focus had changed on an album
        model=widget.get_model()
        entry = model[widget.get_selected_items()[0]][2]

        # now lets build up a status label containing some 'interesting stuff' about the album
        st_album = entry.get_string( RB.RhythmDBPropType.ALBUM )

        label = "%s - %s" % (st_album, \
                            entry.get_string( RB.RhythmDBPropType.ARTIST ) )


        query = GLib.PtrArray()
        self.db.query_append_params(query, \
                        RB.RhythmDBQueryType.EQUALS, \
                        RB.RhythmDBPropType.ALBUM, st_album)
        query_model = RB.RhythmDBQueryModel.new_empty(self.db)
        self.db.do_full_query_parsed(query_model, query)
    
        # Find duration and number of tracks from that album
        track_count = 0
        album_duration = 0
        for row in query_model:
            track_count = track_count + 1
            album_duration = album_duration + \
                             row[0].get_ulong(RB.RhythmDBPropType.DURATION )

        if track_count == 1:
            label = label + ", 1 track"
        else:
            label = label + ", %d tracks" % track_count

        minutes = int(album_duration / 60)

        if minutes == 1:
            label = label + ", duration of 1 minute"
        else:
            label = label + ", duration of %d minutes" % minutes

        label = label + ", genre is %s" % query_model[0][0].get_string(RB.RhythmDBPropType.GENRE )

        self.status_label.set_label( label )
        	
GObject.type_register( CoverArtDisplay )
	
