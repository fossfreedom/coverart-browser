# -*- Mode: python; coding: utf-8; tab-width: 8; indent-tabs-mode: t; -*-
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

ui_str = """
<ui>
    <toolbar name="ToolBar">
        <placeholder name="ToolBarPluginPlaceholder">
            <toolitem name="CoverArtBrowser" action="CoverArtBrowser"/>
        </placeholder>
    </toolbar>
</ui>
"""

CoverSize = 92
STOCK_IMAGE = "stock-coverart-button"

class CoverArtBrowserPlugin(GObject.Object, Peas.Activatable):
    __gtype_name = 'CoverArtBrowserPlugin'
    object = GObject.property(type=GObject.Object)

    def __init__(self):
        GObject.Object.__init__(self)

    def do_activate(self):
        print "CoverArtBrowser DEBUG - do_activate"
        self.shell = self.object
        self.db = self.shell.props.db
        self.uim = self.shell.props.ui_manager
        self.cover_db = None
        self.dialog = None
        
        icon_file_name = rb.find_plugin_file(self, "coverbrowser.png")
        icon_factory = Gtk.IconFactory()
        pxbf = GdkPixbuf.Pixbuf.new_from_file(icon_file_name)
        icon_factory.add(STOCK_IMAGE, Gtk.IconSet.new_from_pixbuf(pxbf))
        icon_factory.add_default()
    
        action = ('CoverArtBrowser', STOCK_IMAGE, _('Browse Covers'), None, _('Show a coverart browser'), self.show_browser_dialog, False)

        self.action_group = Gtk.ActionGroup('CoverArtBrowserPluginActions')
        self.action_group.add_toggle_actions([action])

        self.uim.insert_action_group(self.action_group, -1)
        self.ui_tb = self.uim.add_ui_from_string(ui_str)
        self.uim.ensure_update()
        print "CoverArtBrowser DEBUG - end do_activate"
        
    def do_deactivate(self):
        print "CoverArtBrowser DEBUG - do_deactivate"
        manager = self.shell.props.ui_manager
        manager.remove_ui(self.ui_tb)
        manager.remove_action_group(self.action_group)
        manager.ensure_update()

        self.shell = None
        self.db = None
        self.dialog = None
        self.running = False
        print "CoverArtBrowser DEBUG - end do_deactivate"

    def show_browser_dialog(self, action):
        print "CoverArtBrowser DEBUG - show_browser_dialog"
        # first decide if this is a toggle to display or turn-off
        if self.dialog is not None:
            # dialog has been created so we need to toggle-off
            self.dialog.hide()
            self.dialog.destroy()
            self.dialog=None
            return

        # dialog has not been created so lets do so.
        self.cover_db = RB.ExtDB(name="album-art")
        self.ui = Gtk.Builder()
        self.ui.add_from_file(rb.find_plugin_file(self,"coverart_browser.ui"))
        self.dialog = Gtk.VBox()
        self.status_label = self.ui.get_object("status_label")
        self.covers_view = self.ui.get_object("covers_view")
    
        self.vbox=self.ui.get_object("dialog-vbox1")
        self.vbox.reparent(self.dialog)
        self.vbox.show_all()
        self.dialog.show_all()
        self.shell.add_widget(self.dialog, RB.ShellUILocation.MAIN_TOP,True,True)

        self.covers_model = Gtk.ListStore(GObject.TYPE_STRING, GdkPixbuf.Pixbuf, object)
        self.covers_view.set_model(self.covers_model)
        self.unknown_cover = GdkPixbuf.Pixbuf.new_from_file_at_size(\
                    rb.find_plugin_file(self, 'rhythmbox-missing-artwork.svg'), \
                    CoverSize, \
                    CoverSize)
        self.error_cover = GdkPixbuf.Pixbuf.new_from_file_at_size(\
                    rb.find_plugin_file(self, 'rhythmbox-error-artwork.svg'), \
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
        return self.dialog
            
    def coverclicked_callback(self, widget,item):
        # stub
        return
        
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
        
    def dragimage_callback(self, widget, drag_context, x, y, selection_data, info, timestamp):
        #stub
        return
        
    def rightclick_callback(self, iconview, event):     
        print "CoverArtBrowser DEBUG - rightclick_callback()"
        
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = iconview.get_path_at_pos(x, y)
            if pthinfo is not None:
                iconview.grab_focus()
                            
                model=iconview.get_model()
                entry = model[pthinfo][2]               
                st_album = entry.get_string( RB.RhythmDBPropType.ALBUM )
            
                self.popup_menu = Gtk.Menu()
                main_menu = Gtk.MenuItem("Queue Album")
                main_menu.connect("activate", self.queue_menu_callback, st_album)
                self.popup_menu.append(main_menu)
                self.popup_menu.show_all()
            
                self.popup_menu.popup( None, None, None, None, event.button, time)
        print "CoverArtBrowser DEBUG - end rightclick_callback()"
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
                #self.covers_view.connect("activate-cursor-item",self.coverclicked_callback)
                #self.covers_view.connect("drag-data-received", self.dragimage_callback)
                self.covers_view.connect('button-press-event',self.rightclick_callback)
                Gdk.threads_leave()
        print "CoverArtBrowser DEBUG - end album_load"
