# -*- Mode: python; coding: utf-8; tab-width: 8; indent-tabs-mode: t; -*-
#
# Copyright (C) 2010 - Manu Wagner
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
from gi.repository import GObject, Gtk, RB, GdkPixbuf, Peas, Gdk, GLib
#import gobject
#import Gtk, Gtk.glade, Gtk.gdk
import rb
#import rhythmdb

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
	print "CoverArtBrowser DEBUG - activate()"
        self.shell = self.object
        self.db = self.shell.props.db
        self.running = False
        self.cover_db = None
        self.local_search = None
        self.dialog = None

        data = dict()
        manager = self.shell.props.shell_player
	uim = self.shell.props.ui_manager

	icon_file_name = rb.find_plugin_file(self, "coverbrowser.png")
        #iconsource = Gtk.IconSource()
        #iconsource.set_filename(icon_file_name)
        #iconset = Gtk.IconSet()
        #iconset.add_source(iconsource)
        #iconfactory = Gtk.IconFactory()
        #iconfactory.add("covermgr_icon", iconset)
        #iconfactory.add_default()
        #data['action_group'] = Gtk.ActionGroup('CoverArtBrowserPluginActions')

        #action = Gtk.Action('CoverArtBrowser', _('Cover Art _Browser'),
        #                    _("Show a cover art browser"),
        #                    "covermgr_icon")
        #action.connect('activate', self.show_browser_dialog, shell)
        #data['action_group'].add_action(action)

	icon_factory = Gtk.IconFactory()
	pxbf = GdkPixbuf.Pixbuf.new_from_file(icon_file_name)
	icon_factory.add(STOCK_IMAGE, Gtk.IconSet.new_from_pixbuf(pxbf))
	icon_factory.add_default()
	self.action_group = Gtk.ActionGroup('CoverArtBrowserPluginActions')
	action = Gtk.Action('CoverArtBrowser',
				_('Cover Art _Browser'),
				_("Show a cover art browser"),
				STOCK_IMAGE)
	action.connect('activate', self.show_browser_dialog)
	self.action_group.add_action(action)
	uim.insert_action_group(self.action_group, -1)

        #manager.insert_action_group(data['action_group'], 0)
        #data['ui_id'] = manager.add_ui_from_string(ui_str)
        #manager.ensure_update()
	
	self.ui_tb = uim.add_ui_from_string(ui_str)
	uim.ensure_update()

        #self.shell.set_data('CoverArtBrowserPluginInfo', data)

    def do_deactivate(self):
	print "CoverArtBrowser DEBUG - deactivate()"
	
        data = self.shell.get_data('CoverArtBrowserPlugin')

        manager = self.shell.props.ui_manager
        manager.remove_ui(self.ui_tb)
        manager.remove_action_group(self.action_group)
        manager.ensure_update()

        #shell.set_data('CoverArtBrowserPlugin', None)

        self.shell = None
        self.db = None
        self.dialog = None
        self.running = False

    def create_configure_dialog(self, dialog=None):
        if not dialog:
            dialog = self.create_dialog()
        return dialog

    def show_browser_dialog(self, action):
        self.create_dialog()

    def create_dialog(self):
	print "CoverArtBrowser DEBUG - create_dialog()"
        if self.dialog is not None:
	    self.close_callback(None)
            return
        #Only load it after all plugins are loaded
        #import CoverArtDatabase
        #import LocalCoverArtSearch

	self.cover_db = RB.ExtDB(name="album-art")

        #CoverArtDatabase.ART_SEARCHES_LOCAL = []
        #if not self.cover_db:
        #    self.cover_db = CoverArtDatabase.CoverArtDatabase()
        #if not self.local_search:
        #    self.loader = rb.Loader()
            #self.local_search = LocalCoverArtSearch.LocalCoverArtSearch(self.loader)
	#self.local_search = LocalCoverArtSearch.LocalCoverArtSearch()
        #glade_file = self.find_file("coverart_browser.glade")
        #self.gladexml = Gtk.glade.XML(glade_file)
        self.ui = Gtk.Builder()
	print "ui"
	self.ui.add_from_file(rb.find_plugin_file(self,"coverart_browser.ui"))
	print "next ui"	
	self.dialog = Gtk.VBox()
        self.status_label = self.ui.get_object("status_label")
        self.covers_view = self.ui.get_object("covers_view")
#	self.start_button = self.ui.get_object("start_button")
#       self.close_button = self.ui.get_object("close_button")

#	self.start_button.set_sensitive(False)
#	self.close_button.set_sensitive(False)
	# pour mettre le fond en noir
    	#style = self.covers_view.get_style().copy()
    	#for state in (Gtk.StateFlags.NORMAL, Gtk.StateFlags.PRELIGHT,Gtk.StateFlags.ACTIVE):
	#	style.base[state] = Gdk.Color(0,0,0)
    	#self.covers_view.set_style(style)
	
	self.vbox=self.ui.get_object("dialog-vbox1")
	self.vbox.reparent(self.dialog)
	self.vbox.show_all()
	self.dialog.show_all()
	self.shell.add_widget(self.dialog, RB.ShellUILocation.MAIN_TOP,True,True)
	#self.shell.notebook_set_page(self.dialog)

        self.covers_model = Gtk.ListStore(GObject.TYPE_STRING, GdkPixbuf.Pixbuf, object)
        self.covers_view.set_model(self.covers_model)
	self.unknown_cover = GdkPixbuf.Pixbuf.new_from_file_at_size(\
                rb.find_plugin_file(self, 'rhythmbox-missing-artwork.svg'), CoverSize, CoverSize)
	self.error_cover = GdkPixbuf.Pixbuf.new_from_file_at_size(\
                rb.find_plugin_file(self, 'rhythmbox-error-artwork.svg'), CoverSize, CoverSize)
	#self.shell.connect("visibility-changed",self.close_callback)
        self.iter = None
	self.current_drop = None
        print "Loading albums"
        self.load_albums()
        return self.dialog
        
    def enable_controls_and_cb(self):
	print "CoverArtBrowser DEBUG - enable_controls_and_cb"
#	self.start_button.set_sensitive(True)
#	self.close_button.set_sensitive(True)
#	self.start_button.connect("clicked", self.startstop_callback)
#       self.close_button.connect("clicked", self.close_callback)
	#targets = None	
	#targets = Gtk.target_list_add_image_targets (targets, writable=True)
	#targets = Gtk.target_list_add_image_targets (targets)
	#targets = Gtk.target_list_add_uri_targets (targets)
	##self.covers_view.enable_model_drag_dest(targets,Gtk.gdk.ACTION_DEFAULT | Gtk.gdk.ACTION_MOVE)
	##self.covers_view.drag_source_set (Gtk.gdk.BUTTON1_MASK, targets, Gtk.gdk.ACTION_COPY)
	#self.covers_view.drag_dest_set (Gtk.DEST_DEFAULT_ALL, targets, Gtk.gdk.ACTION_COPY)

	##self.covers_view.drag_source_set (Gtk.gdk.BUTTON1_MASK,[('application/x-rhythmbox-entry',0,0)], Gtk.gdk.ACTION_DEFAULT)
	#targets2 = None
	##targets2 = Gtk.target_list_add_image_targets (targets2, writable=True)
	#targets2 = Gtk.target_list_add_uri_targets (targets2)
	#self.covers_view.drag_source_set (Gtk.gdk.BUTTON1_MASK,targets2, Gtk.gdk.ACTION_COPY)
	#self.covers_view.connect("drag-end", self.drop_callback)
	
	self.covers_view.connect("item-activated", self.coverdoubleclicked_callback)
	##self.covers_view.connect("activate-cursor-item",self.coverclicked_callback)
	#self.covers_view.connect("drag-data-received", self.dragimage_callback)

	#self.covers_view.connect('button-press-event',self.rightclick_callback)
	

    def close_callback(self, widget):
	print "CoverArtBrowser DEBUG - close_callback()"
	self.dialog.hide()
	self.dialog.destroy()
	self.dialog=None
	
    def coverclicked_callback(self, widget,item):
	print "CoverArtBrowser DEBUG - coverclicked_callback()"
	model=widget.get_model()
	entry = model[item][2]
	self.get_pixbuf(self.db, entry, self.load_entry)
	    
    def coverdoubleclicked_callback(self, widget,item):
	print "CoverArtBrowser DEBUG - coverdoubleclicked_callback()"
	model=widget.get_model()
	entry = model[item][2]

	# clear the queue
	play_queue = self.shell.props.queue_source
    	for row in play_queue.props.query_model:
      		#entry = row[0]
      		play_queue.remove_entry(row[0])

	# ok, query for all the tracks for the album and add them to the queue
	st_album = entry.get_string( RB.RhythmDBPropType.ALBUM ) or _("Unknown")
	
	query = GLib.PtrArray()
        self.db.query_append_params(query, RB.RhythmDBQueryType.EQUALS, RB.RhythmDBPropType.ALBUM, st_album)
        query_model = RB.RhythmDBQueryModel.new_empty(self.db)
        self.db.do_full_query_parsed(query_model, query)
	
#	def process_entry(model, path, iter, data):
#	    (parsed_entry,) = model.get(iter, 0)
#	    st_track_found = parsed_entry.get_ulong( RB.RhythmDBPropType.TRACK_NUMBER) or _("Unknown")
#	    #print st_track_found
#
#	    if st_track_found==1:
#		self.shell.props.shell_player.play_entry(parsed_entry, \
#							 self.shell.props.library_source)

#	    	key = parsed_entry.create_ext_db_key(RB.RhythmDBPropType.ALBUM)
#	    	art_location = self.cover_db.lookup(key)
#            	#art_location = self.cover_db.build_art_cache_filename (self.db, parsed_entry, 'jpg')
#            	if art_location is not None and os.path.exists (art_location):
#                	pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(art_location, CoverSize, CoverSize)
#	    		self.covers_model.set(self.covers_model.get_iter(item), 1, pixbuf)

#	query_model.foreach(process_entry, None)


    	# Find all the songs from that album
    	songs = []
	library = self.shell.props.library_source
    	#for row in library.props.query_model:
	for row in query_model:
      		entry = row[0]
#      album = entry.get_string(RB.RhythmDBPropType.ALBUM)
#      if (album == selected_album):
	        songs.append(entry)
  
    	# Sort the songs
    	songs = sorted(songs, key=lambda song: song.get_ulong(RB.RhythmDBPropType.TRACK_NUMBER))
        
    	# Add the songs to the play queue
    	for song in songs:
      		self.shell.props.queue_source.add_entry(song, -1)


    	# Start the music!(well, first stop it, but it'll start up again.)
    	print 'Playing Album'
    	player = self.shell.props.shell_player
    	player.stop()
    	player.set_playing_source(self.shell.props.queue_source)
    	player.playpause(True)

#    library = shell.props.library_source
  
    def display_cover(self,db,pixbuf,uris):
	if self.current_drop:
		pixbuf = pixbuf.scale_simple(CoverSize, CoverSize, Gtk.gdk.INTERP_BILINEAR)
		self.covers_model.set(self.current_drop, 1, pixbuf)
		self.cover_count += 1
		self.set_status()
	return
    def dragimage_callback(self, widget, drag_context, x, y, selection_data, info, timestamp):
	print "CoverArtBrowser DEBUG - dragimage_callback()"
	model = widget.get_model()
	print `model`
	item = self.covers_view.get_dest_item_at_pos(x,y)[0]
	print `item`
	entry = None
	if item:
		entry = model[item][2]
		print `entry`
		uris = selection_data.get_uris ()
		if uris:
			print "this is an url"
			print `uris`
			self.current_drop = self.covers_model.get_iter(item)
			self.cover_db.set_pixbuf_from_uri (self.db, entry, uris[0], self.display_cover)
		pixbuf = selection_data.get_pixbuf()
		if pixbuf:
			print "this is an pixbuf"
	    		pixbuf = pixbuf.scale_simple(CoverSize, CoverSize, Gdk.INTERP_BILINEAR)
			#self.covers_model.set(item, 1, pixbuf)
    def drop_callback(self, widget, drag_context):
	print "CoverArtBrowser DEBUG - drop_callback()"
	print `widget`
	model = widget.get_model()
	iter_first = model.get_iter_first()
	val =  model.get_value(iter_first,0)
	print `val`
	print `drag_context`
	print `drag_context.dest_window`
	print `drag_context.dest_window.get_window_type()`
	return
    def device_copy(self, widget, data=None):
       print "CoverArtBrowser DEBUG - Copy album to device"
       return False
    def build_contextual_menu(self):
	self.popup_menu = Gtk.Menu()
	main_menu = Gtk.MenuItem("Transfer Album to ")
        self.popup_menu.append(main_menu)
	
        submenu = Gtk.Menu()
	main_menu.set_submenu(submenu)
	for group in self.shell.props.sourcelist_model:
		group_type = group[7]
		if  str(group_type)=='<enum RB_SOURCE_GROUP_CATEGORY_REMOVABLE of type RBSourcelistGroupType>':
			for source in group.iterchildren():
				help(source)
				name = source[2]
				device = source[3]
				print `device`		
				#print source[2],source[4]
				media_menu = Gtk.MenuItem(name)
				media_menu.connect("activate", self.device_copy)
				submenu.append(media_menu)
					
        self.popup_menu.show_all()
    def rightclick_callback(self, treeview, event):
 	if event.button == 3:
        	x = int(event.x)
        	y = int(event.y)
        	time = event.time
        	pthinfo = treeview.get_path_at_pos(x, y)
        	if pthinfo is not None:
            		#path, col, cellx, celly = pthinfo
            		treeview.grab_focus()
            		#treeview.set_cursor( path, col, 0)
			self.build_contextual_menu()
            		self.popup_menu.popup( None, None, None, event.button, time)
			print "CoverArtBrowser DEBUG - rightclick_callback()"
    def startstop_callback(self, widget):
	print "CoverArtBrowser DEBUG - startstop_callback()"
        self.set_running(not self.running)
    def load_finished(self,entry):
	print "CoverArtBrowser DEBUG - load_finished()"
    def load_albums(self):
	print "CoverArtBrowser DEBUG - load_albums()"
        self.album_queue = Queue()
        self.album_loader = Thread(target = self.album_load)
        self.album_loader.start()
        self.albums = Set()
        self.album_count = 0
        self.cover_count = 0
        #self.db.entry_foreach_by_type(RB.RhythmDB.get_song_entry_type(), \
        #                              self.load_entry_callback, None)
	#self.db.entry_foreach( self.load_entry_callback, True )

	q = GLib.PtrArray()
	self.db.query_append_params(	q, \
					RB.RhythmDBQueryType.EQUALS, \
					RB.RhythmDBPropType.TYPE, \
					self.db.entry_type_get_by_name("song"))
	qm = RB.RhythmDBQueryModel.new_empty(self.db)
	self.db.do_full_query_parsed(qm,q)

	def process_entry(model, path, iter, data):
		(entry,) = model.get(iter, 0)		
		self.load_entry_callback(entry)

	qm.foreach(process_entry, None)

	print "CoverArtBrowser DEBUG - load_albums() FINISHED"
        #for album, artist_info in self.albums.iteritems():
        #    for artist, info in artist_info:
        #        entry = info[0]

    def load_entry_callback(self, entry):
	#print "CoverArtBrowser DEBUG - load_entry_callback()"
	#self.db.entry_get(entry, RB.RhythmDBPropType.ALBUM, album)
        #self.db.entry_get(entry, RB.RhythmDBPropType.ARTIST, artist)
	
	album = entry.get_string( RB.RhythmDBPropType.ALBUM )
	artist = entry.get_string( RB.RhythmDBPropType.ARTIST )	

	#track = self.db.entry_get(entry, rhythmdb.PROP_TRACK_NUMBER)
	# we only deal with the first track of album
	#if track==1:
	pixbuf = self.unknown_cover
	add = False
	if album not in self.albums:
	    self.album_count += 1
	    self.albums.add(album)
	    #self.album_queue.put([artist, album, entry])
	    tree_iter = self.covers_model.append((cgi.escape('%s - %s' % (artist, album)),pixbuf,entry))
	    #print album
	    #print artist

	    #print "CoverArtBrowser DEBUG - load_entry_callback"
	    self.iter = self.iter or tree_iter
	    self.album_queue.put([artist, album, entry, tree_iter])

    def album_load(self):

        while True:
	    #print "CoverArtBrowser DEBUG - album_load()"
            artist, album, entry, tree_iter = self.album_queue.get()

	    key = entry.create_ext_db_key(RB.RhythmDBPropType.ALBUM)
	    #print key.get_field_values('album')
	    #print key.get_field_values('artist')
	    #art_location = self.cover_db.build_art_cache_filename (self.db, entry, 'jpg')
	    #print self.cover_db
	    #print self.cover_db.lookup(key)
	    #print "CoverArtBrowser DEBUG - album_load, art_location = "
	    art_location = self.cover_db.lookup(key)
            if art_location is not None and os.path.exists (art_location):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(art_location, CoverSize, CoverSize)
		#print "CoverArtBrowser DEBUG - album_load OK"
                self.cover_count += 1
                Gdk.threads_enter()
                self.covers_model.set(tree_iter, 1, pixbuf)
		self.set_status()
                Gdk.threads_leave()
	    if self.album_queue.empty():
		Gdk.threads_enter()
		print "CoverArtBrowser DEBUG - album_load() FINISHED"
		self.enable_controls_and_cb()
		Gdk.threads_leave()

    def set_running(self, value):
        self.running = value
        if self.running:
	    print "CoverArtBrowser DEBUG - set_running() = TRUE"
            self.start_button.set_label("Cancel")
            self.load_iter()
        else:
	    print "CoverArtBrowser DEBUG - set_running() = FALSE"
            self.start_button.set_label("Fetch covers")

    def load_iter(self):
	print "CoverArtBrowser DEBUG - load_iter()"
        if (not self.running) or (not self.iter):
            self.set_running(False)
            return
        entry = self.covers_model.get(self.iter, 2)[0]
        self.get_pixbuf(self.db, entry, self.load_entry)


    def get_pixbuf (self, db, entry, callback):
	print "CoverArtBrowser DEBUG - get_pixbuf()"
        if entry is None:
            callback (entry, None, None)
            return

        st_artist = db.entry_get (entry, RB.RhythmDBPropType.ARTIST) or _("Unknown")
        st_album = db.entry_get (entry, RB.RhythmDBPropType.ALBUM) or _("Unknown")

        # replace quote characters
        # don't replace single quote: could be important punctuation
        for char in ["\""]:
            st_artist = st_artist.replace (char, '')
            st_album = st_album.replace (char, '')

        Coroutine (self.next, self.cover_db.image_search, db, st_album, st_artist,entry, False, callback).begin()

    def load_entry(self, entry, pixbuf, location):
	print "CoverArtBrowser DEBUG - load_entry()"
        if self.dialog:
            pixbuf = pixbuf.scale_simple(CoverSize, CoverSize, Gtk.gdk.INTERP_BILINEAR)
            self.covers_model.set(self.iter, 1, pixbuf)
            self.next()

    def next(self):
	print "CoverArtBrowser DEBUG - next()"
	if self.iter is None:
	    self.set_running(False)
	    return
        else:
            if (self.covers_model.get(self.iter, 1)[0] == self.unknown_cover):
                self.covers_model.set(self.iter, 1, self.error_cover)
            self.iter = self.covers_model.iter_next(self.iter)
            current_cover=None
	    if self.iter:
            	current_cover = (self.covers_model.get(self.iter, 1)[0])
            	while self.iter and (current_cover != self.unknown_cover):
                	self.iter = self.covers_model.iter_next(self.iter)
                	if self.iter:
				current_cover = (self.covers_model.get(self.iter, 1)[0])
            self.load_iter()

    def set_status(self):
	albumleft = self.album_count-self.cover_count
        self.status_label.set_label("%d covers left to download" % albumleft)

    def reset(self):
	albumleft = self.album_count-self.cover_count
        self.status_label.set_label("%d covers left to download" % albumleft)
class Coroutine:
    """A simple message-passing coroutine implementation.
    Not thread- or signal-safe.
    Usage:
            def my_iter (plexer, args):
                    some_async_task (..., callback=plexer.send (tokens))
                    yield None
                    tokens, (data, ) = plexer.receive ()
                    ...
            Coroutine (my_iter, args).begin ()
    """
    def __init__ (self, error_callback, iter, *args):
	print "CoverArtBrowser DEBUG - Coroutine::__init__()"
        self._continuation = iter (self, *args)
        self.error_callback = error_callback
        self._executing = False
    def _resume (self):
	print "CoverArtBrowser DEBUG - Coroutine::_resume()"
        if not self._executing:
            self._executing = True
            try:
                try:
                    self._continuation.next ()
                    while self._data:
		        print "CoverArtBrowser DEBUG - Coroutine::_resume, OK()"
                        self._continuation.next ()
                except StopIteration:
                    print "CoverArtBrowser DEBUG - Coroutine::_resume, STOPITERATION()"
		    pass
                # Catch all exceptions for faulty art plugins
                except Exception:
		    print "CoverArtBrowser DEBUG - Coroutine::_resume, EXCEPTION()"
                    self.error_callback()
            finally:
                self._executing = False
    def clear (self):
	print "CoverArtBrowser DEBUG - Coroutine::clear()"
        self._data = []
    def begin (self):
	print "CoverArtBrowser DEBUG - Coroutine::begin()"
        self.clear ()
        self._resume ()
    def send (self, *tokens):
	print "CoverArtBrowser DEBUG - Coroutine::send()"
        def callback (*args):
            self._data.append ((tokens, args))
            self._resume ()
        return callback
    def receive (self):
	print "CoverArtBrowser DEBUG - Coroutine::receive()"
        return self._data.pop (0)
