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
from gi.repository import GLib
from gi.repository import Gdk
from gi.repository import GdkPixbuf

import os
import cgi
import rb

class AlbumLoader( object ):
    DEFAULT_LOAD_CHUNK = 10

    def __init__( self, plugin, cover_model ):
        self.albums = {}
        self.db = plugin.shell.props.db
        self.cover_model = cover_model
        self.cover_db = RB.ExtDB( name='album-art' )

        # connect the signal to update cover arts when added
        self.req_id = self.cover_db.connect( 'added',
                                             self._albumart_added_callback )
        
        # connect signals for updating the albums        
        self.entry_changed_id = self.db.connect( 'entry-changed', 
                                                  self._entry_changed_callback )
        
        # initialise unkown cover for albums without cover
        Album.init_unknown_cover( plugin )
    
    def _albumart_added_callback( self, ext_db, obj, p0, p1 ):
        # called when new album art added
        # parameters: ext_db - this is the album-art database
        # obj = RB.ExtDBKey
        # p0 = full path to cached album art file
        # p1 = pixbuf of the album art file
        print "CoverArtBrowser DEBUG - albumart_added_callback"
        
        album_name = obj.get_field("album")

        # use the name to get the album and update the cover
        self.albums[album_name].update_cover( p1 )

        print "CoverArtBrowser DEBUG - end albumart_added_callback"
        
    def _entry_changed_callback( self, db, entry, changes ):
        print "CoverArtBrowser DEBUG - entry_changed_callback"
        # look at all the changes and update the albums acordingly
        try:
            while True:
                change = changes.values
                            
                if change.prop is RB.RhythmDBPropType.ALBUM:
                    self._entry_album_modified( entry, change.old, change.new )

                    
                changes.remove( 0 )
        except:
            pass          
        
        print "CoverArtBrowser DEBUG - end entry_changed_callback"
           
    def _entry_album_modified( self, entry, old_name, new_name ):
        print "CoverArtBrowser DEBUG - album_modified_callback"
        # find the old album and remove the entry        
        if old_name in self.albums:
            album = self.albums[old_name]
            album.remove_entry( entry )
            
            # if the album is empty, remove it's reference
            if album.get_track_count() == 0:
                del self.albums[old_name]
                
        # add the entry to the album it belongs now
        if new_name in self.albums:
            album = self.albums[new_name]
            album.append_entry( entry )
        else:
            artist = entry.get_string( RB.RhythmDBPropType.ARTIST ) 
            album = Album( new_name, artist )
            self.albums[new_name] = album
         
            album.append_entry( entry )
            album.load_cover( self.cover_db )
            album.add_to_model( self.cover_model )              
        
        print "CoverArtBrowser DEBUG - end album_modified_callback"
               
    def load_albums( self ):    
        #build the query
        q = GLib.PtrArray()
        self.db.query_append_params( q,
              RB.RhythmDBQueryType.EQUALS, 
              RB.RhythmDBPropType.TYPE, 
              self.db.entry_type_get_by_name( 'song' ) )
              
        #create the model and connect to the completed signal
        qm = RB.RhythmDBQueryModel.new_empty( self.db )
        
        qm.connect( 'complete', self._query_complete_callback )
        
        self.db.do_full_query_async_parsed( qm, q )
        
    def _query_complete_callback( self, qm ):     
        qm.foreach( self._process_entry, None )
    
        self._fill_model()
        
    def _process_entry( self, model, tree_path, tree_iter, _ ):
        (entry,) = model.get( tree_iter, 0 )
    
        album_name = entry.get_string( RB.RhythmDBPropType.ALBUM )
        artist = entry.get_string( RB.RhythmDBPropType.ARTIST ) 
               
        if album_name in self.albums.keys():
            album = self.albums[album_name]
        else:
            album = Album( album_name, artist )
            self.albums[album_name] = album
            
        album.append_entry( entry )
        
    def _fill_model( self ):
        Gdk.threads_add_idle( GLib.PRIORITY_DEFAULT_IDLE, 
                              self._idle_load_callback, 
                              self.albums.values() )

    def _idle_load_callback( self, albums ):     
        for i in range( AlbumLoader.DEFAULT_LOAD_CHUNK ):
            try:
                album = albums.pop()
                album.load_cover( self.cover_db  )
                album.add_to_model( self.cover_model )
            except:
                return False
        
        return True

class Album( object ):
    UNKNOWN_COVER = 'rhythmbox-missing-artwork.svg'

    def __init__( self, name, artist ):
        # name is the album name
        # artist is the artist name
        
        self.name = name
        self.artist = artist
        self.entries = []
        self.cover = Album.UNKNOWN_COVER
        
    def append_entry( self, entry ):        
        self.entries.append( entry )
        
    def remove_entry( self, entry ):
        # remove the entry from the entries list
        for e in self.entries:
            if rb.entry_equal( e, entry ):
                self.entries.remove( e )
                break
                
        # if there aren't entries left, remove the album from the model
        if self.get_track_count() == 0:
            self.remove_from_model()        
        
    def load_cover( self, cover_db ):
        key = self.entries[0].create_ext_db_key( RB.RhythmDBPropType.ALBUM )
        art_location = cover_db.lookup( key )
        
        if art_location and os.path.exists( art_location ):
            try:
                self.cover = Cover( art_location )
            except:
                self.cover = Album.UNKNOWN_COVER
        
    def add_to_model( self, model ):   
        self.model = model
        self.tree_iter = model.append( 
            (cgi.escape( '%s - %s' % (self.artist, self.name) ),
            self.cover.pixbuf, 
            self) )
    
    def remove_from_model( self ):
        self.model.remove( self.tree_iter )

    def update_cover( self, pixbuf ):
        if pixbuf:
            self.cover = Cover( pixbuf=pixbuf )
            self.model.set_value( self.tree_iter, 1, self.cover.pixbuf )

    def get_track_count( self ):
        return len( self.entries )
        
    def calculate_duration_in_secs( self ):
        duration = 0
        
        for entry in self.entries:
            duration += entry.get_ulong( RB.RhythmDBPropType.DURATION )
        
        return duration
    
    def calculate_duration_in_mins( self ):
        return self.calculate_duration_in_secs() / 60        
                    
    @classmethod
    def init_unknown_cover( cls, plugin ):
        if type( cls.UNKNOWN_COVER ) is str:
            cls.UNKNOWN_COVER = Cover( rb.find_plugin_file( plugin, 
                                                           cls.UNKNOWN_COVER ) )

    def contains( self, searchtext ):
        if searchtext == "":
            return True

        if searchtext.lower() in self.name.lower():
            return True

        return searchtext.lower() in self.artist.lower()
        
class Cover( object ):
    COVER_SIZE = 92
    
    def __init__( self, file_path=None, pixbuf=None, width=COVER_SIZE, 
                                                     height=COVER_SIZE ):
        '''
        Either a file path or a pixbuf should be given to the cover to 
        initialize it's own pixbuf.
        '''
        self.width = width
        self.height = height
        
        if pixbuf:
            self.pixbuf = pixbuf.scale_simple( self.width, 
                                               self.height,
                                               GdkPixbuf.InterpType.BILINEAR )
        else:              
            self.pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size( file_path, 
                                                                  self.width, 
                                                                  self.height )
        
