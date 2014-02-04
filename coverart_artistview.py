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

from coverart_external_plugins import CreateExternalPluginMenu
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import GdkPixbuf
from gi.repository import RB

from coverart_browser_prefs import GSetting
from coverart_album import Cover
from coverart_album import Album
from coverart_album import AlbumsModel
from coverart_album import CoverManager
from coverart_widgets import AbstractView
from coverart_utils import SortedCollection
from coverart_widgets import PanedCollapsible
from coverart_toolbar import ToolbarObject
from coverart_utils import idle_iterator
from coverart_utils import dumpstack
from coverart_utils import create_pixbuf_from_file_at_size
from coverart_external_plugins import CreateExternalPluginMenu
from coverart_extdb import CoverArtExtDB
import coverart_rb3compat as rb3compat 
from coverart_rb3compat import Menu

import rb
import os

from collections import namedtuple

import tempfile, shutil
def create_temporary_copy(path):
    temp_dir = tempfile.gettempdir()
    filename = tempfile.mktemp()
    temp_path = os.path.join(temp_dir, filename)
    shutil.copy2(path, temp_path)
    return temp_path

ARTIST_LOAD_CHUNK = 50

class Artist(GObject.Object):
    '''
    An album. It's conformed from one or more tracks, and many of it's
    information is deduced from them.

    :param name: `str` name of the artist.
    :param cover: `Cover` cover for this artist.
    '''
    # signals
    __gsignals__ = {
        'modified': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'emptied': (GObject.SIGNAL_RUN_LAST, None, ()),
        'cover-updated': (GObject.SIGNAL_RUN_LAST, None, ())
        }

    __hash__ = GObject.__hash__
    
    def __init__(self, name, cover):
        super(Artist, self).__init__()

        self.name = name
        self._cover = None
        self.cover = cover

        self._signals_id = {}

    @property
    def cover(self):
        return self._cover

    @cover.setter
    def cover(self, new_cover):
        #if self._cover:
        #    self._cover.disconnect(self._cover_resized_id)

        self._cover = new_cover
        #self._cover_resized_id = self._cover.connect('resized',
        #    lambda *args: self.emit('cover-updated'))

        self.emit('cover-updated')
    def create_ext_db_key(self):
        '''
        Returns an `RB.ExtDBKey` 
        '''
        key = RB.ExtDBKey.create_lookup('artist', self.name)
        return key


class ArtistsModel(GObject.Object):
    '''
    Model that contains artists, keeps them sorted, filtered and provides an
    external `Gtk.TreeModel` interface to use as part of a Gtk interface.

    The `Gtk.TreeModel` haves the following structure:
    column 0 -> string containing the artist name
    column 1 -> pixbuf of the artist's cover.
    column 2 -> instance of the artist or album itself.
    column 3 -> boolean that indicates if the row should be shown
    column 4 -> blank text column to pad the view correctly
    column 5 -> markup containing formatted text
    column 6 -> blank text for the expander column
    '''
    # signals
    __gsignals__ = {
        'update-path': (GObject.SIGNAL_RUN_LAST, None, (object,)),
        'visual-updated': ((GObject.SIGNAL_RUN_LAST, None, (object, object)))
        }

    # list of columns names and positions on the TreeModel
    columns = {'tooltip': 0, 'pixbuf': 1, 
        'artist_album': 2, 'show': 3, 
        'empty': 4, 'markup': 5, 'expander': 6}
        
    force_lastfm_check = True
    
    def __init__(self, album_manager):
        super(ArtistsModel, self).__init__()

        self.album_manager = album_manager
        self._iters = {}
        self._albumiters = {}
        self._artists = SortedCollection(
            key=lambda artist: getattr(artist, 'name'))

        self._tree_store = Gtk.TreeStore(str, GdkPixbuf.Pixbuf, object, 
            bool,  str, str, str)
            
        # sorting idle call
        self._sort_process = None

        # create the filtered store that's used with the view
        self._filtered_store = self._tree_store.filter_new()
        self._filtered_store.set_visible_column(ArtistsModel.columns['show'])
        
        self._tree_sort = Gtk.TreeModelSort(model=self._filtered_store)     
        #self._tree_sort.set_default_sort_func(lambda *unused: 0)       
        self._tree_sort.set_sort_func(0, self._compare, None)
        
        self._connect_signals()
        
    def _connect_signals(self):
        self.connect('update-path', self._on_update_path)
        self.album_manager.model.connect('filter-changed', self._on_album_filter_changed)
        
    def _on_album_filter_changed(self, *args):
        if len(self._iters) == 0:
            return
            
        artists = list(set(row[AlbumsModel.columns['album']].artist for row in self.album_manager.model.store))

        for artist in self._iters:
            self.show(artist, artist in artists)
        
    def _compare(self, model, row1, row2, user_data):
        
        if not model.iter_has_child(row1) or \
            not model.iter_has_child(row2):
                return 0
                
        sort_column = 0
        value1 = RB.search_fold(model.get_value(row1, sort_column))
        value2 = RB.search_fold(model.get_value(row2, sort_column))
        if value1 < value2:
            return -1
        elif value1 == value2:
            return 0
        else:
            return 1
 
    @property
    def store(self):
        #return self._filtered_store
        return self._tree_sort

    def add(self, artist):
        '''
        Add an artist to the model.

        :param artist: `Artist` to be added to the model.
        '''
        # generate necessary values
        values = self._generate_artist_values(artist)
        # insert the values
        pos = self._artists.insert(artist)
        tree_iter = self._tree_store.insert(None,pos, values)
        child_iter = self._tree_store.insert(tree_iter, pos, values) # dummy child row so that the expand is available
        # connect signals
        ids = (artist.connect('modified', self._artist_modified),
            artist.connect('cover-updated', self._cover_updated),
            artist.connect('emptied', self.remove))
        
        if not artist.name in self._iters:
            self._iters[artist.name] = {}
        self._iters[artist.name] = {'artist_album': artist,
            'iter': tree_iter, 'dummy_iter': child_iter, 'ids': ids}
        return tree_iter
    
    def _emit_signal(self, tree_iter, signal):
        # we get the filtered path and iter since that's what the outside world
        # interacts with
        tree_path = self._filtered_store.convert_child_path_to_path(
            self._tree_store.get_path(tree_iter))

        if tree_path:
            # if there's no path, the album doesn't show on the filtered model
            # so no one needs to know
            tree_iter = self._filtered_store.get_iter(tree_path)

            self.emit(signal, tree_path, tree_iter)
            
    def remove(self, *args):
        print ("artist remove")
        
    def _cover_updated(self, artist):
        tree_iter = self._iters[artist.name]['iter']

        if self._tree_store.iter_is_valid(tree_iter):
            # only update if the iter is valid
            pixbuf = artist.cover.pixbuf

            self._tree_store.set_value(tree_iter, self.columns['pixbuf'],
                pixbuf)

            self._emit_signal(tree_iter, 'visual-updated')
            
    def _artist_modified(self, *args):
        print ("artist modified")

    def _on_update_path(self, widget, treepath):
        '''
           called when update-path signal is called
        '''
        artist = self.get_from_path(treepath)
        albums = self.album_manager.model.get_all()
        self.add_album_to_artist(artist, albums)
        
    def add_album_to_artist(self, artist, albums):
        '''
        Add an album to the artist in the model.

        :param artist: `Artist` for the album to be added to (i.e. the parent)
        :param album: array of `Album` which are the children of the Artist
        
        '''
        # get the artist iter
        artist_iter = self._iters[artist.name]['iter']
        
        # now remove the dummy_iter - if this fails, we've removed this 
        # before and have no need to add albums

        if 'dummy_iter' in self._iters[artist.name]:
            self._iters[artist.name]['album'] = []
                    
        for album in albums:
            if artist.name == album.artist and not (album in self._albumiters):
                # now for all matching albums that were found lets add to the model

                # generate necessary values
                values = self._generate_album_values(album)
                # insert the values
                tree_iter = self._tree_store.append(artist_iter, values)
                self._albumiters[album] = {}
                self._albumiters[album]['iter'] = tree_iter
                self._iters[artist.name]['album'].append(tree_iter)
                    
                # connect signals
                ids = (album.connect('modified', self._album_modified),
                    album.connect('cover-updated', self._album_coverupdate),
                    album.connect('emptied', self._album_emptied))
                    
                self._albumiters[album]['ids'] = ids 

        if 'dummy_iter' in self._iters[artist.name]:
            self._tree_store.remove(self._iters[artist.name]['dummy_iter'])
            del self._iters[artist.name]['dummy_iter']
            
        self.sort() # ensure the added albums are sorted correctly

    def _album_modified(self, album):
        print ("album modified")
        print (album)
        if not (album in self._albumiters):
            print ("not found in albumiters")
            return
            
        tree_iter = self._albumiters[album]['iter']

        if self._tree_store.iter_is_valid(tree_iter):
            # only update if the iter is valid
            # generate and update values
            tooltip, pixbuf, album, show, blank, markup, empty = \
                self._generate_album_values(album)

            self._tree_store.set(tree_iter, self.columns['tooltip'], tooltip,
                self.columns['markup'], markup, self.columns['show'], show)
                
            self.sort() # ensure the added albums are sorted correctly
       
    def _album_emptied(self, album):
        '''
        Removes this album from the model.

        :param album: `Album` to be removed from the model.
        '''
        print ('album emptied')
        print (album)
        print (album.artist)
        if not (album in self._albumiters):
            print ("not found in albumiters")
            return

        artist = self.get(album.artist)
        album_iter = self._albumiters[album]['iter']

        self._iters[album.artist]['album'].remove(album_iter)
        self._tree_store.remove(album_iter)

        # disconnect signals
        for sig_id in self._albumiters[album]['ids']:
            album.disconnect(sig_id)

        del self._albumiters[album]

        # test if there are any more albums for this artist otherwise just cleanup
        if len(self._iters[album.artist]['album']) == 0:
            self.remove(artist)
            self._on_album_filter_changed(_)
            
    def _album_coverupdate(self, album):
        tooltip, pixbuf, album, show, blank, markup, empty = self._generate_album_values(album)
        self._tree_store.set_value(self._albumiters[album]['iter'], 
            self.columns['pixbuf'], pixbuf)
            
    def _generate_artist_values(self, artist):
        tooltip = artist.name
        pixbuf = artist.cover.pixbuf
        show = True

        return tooltip, pixbuf, artist, show, '', \
            GLib.markup_escape_text(tooltip), ''
    
    def _generate_album_values(self, album):
        tooltip = album.name
        pixbuf = album.cover.pixbuf.scale_simple(48,48,GdkPixbuf.InterpType.BILINEAR)
        show = True
        
        rating = album.rating
        if int(rating) > 0:
            rating = u'\u2605' * int(rating)
        else:
            rating = ''
        
        year = ' (' + str(album.real_year) +')'
            
        track_count = album.track_count
        if track_count == 1:
            detail = rb3compat.unicodedecode(_(' with 1 track'), 'UTF-8')
        else:
            detail = rb3compat.unicodedecode(_(' with %d tracks') % 
                        track_count, 'UTF-8')
                        
        duration = album.duration / 60
        
        if duration == 1:
            detail += rb3compat.unicodedecode(_(' and a duration of 1 minute'), 'UTF-8')
        else:
            detail += rb3compat.unicodedecode(_(' and a duration of %d minutes') % 
                        duration, 'UTF-8')
            
        tooltip = rb3compat.unicodestr(tooltip, 'utf-8')
        tooltip = rb3compat.unicodeencode(tooltip, 'utf-8')
        import cgi
        
        formatted = '<b><i>' + \
            cgi.escape(rb3compat.unicodedecode(tooltip, 'utf-8')) + \
            '</i></b>' + \
            year + \
            ' ' + rating + \
            '\n<small>' + \
            GLib.markup_escape_text(detail) + \
            '</small>'

        return tooltip, pixbuf, album, show, '', formatted, ''

    def remove(self, artist):
        '''
        Removes this artist from the model.

        :param artist: `Artist` to be removed from the model.
        '''
        self._artists.remove(artist)
        self._tree_store.remove(self._iters[artist.name]['iter'])

        del self._iters[artist.name]

    def contains(self, artist_name):
        '''
        Indicates if the model contains a specific artist.

        :param artist_name: `str` name of the artist.
        '''
        return artist_name in self._iters

    def get(self, artist_name):
        '''
        Returns the requested Artist.

        :param artist_name: `str` name of the artist.
        '''
        return self._iters[artist_name]['artist_album']
        
    def get_albums(self, artist_name):
        '''
        Returns the displayed albums for the requested artist

        :param artist_name: `str` name of the artist.
        '''
        
        albums = []
        
        artist_iter = self._iters[artist_name]['iter']
        next_iter = self._tree_store.iter_children(artist_iter)
        
        while next_iter != None:
            albums.append(self._tree_store[next_iter][self.columns['artist_album']])
            next_iter = self._tree_store.iter_next(next_iter)
        #if 'album' in self._iters[artist_name]:
        #    for album_iter in self._iters[artist_name]['album']:
        #        path = self._tree_store.get_path(album_iter)
        #        if path:
        #        tree_path = self._filtered_store.convert_child_path_to_path(
        #            )
        #        albums.append(self.get_from_path(tree_path))
            
        return albums

    def get_all(self):
        '''
        Returns a collection of all the artists in this model.
        '''
        return self._artists
        
    def get_from_path(self, path):
        '''
        Returns the Artist or Album referenced by a `Gtk.TreeModelSort` path.

        :param path: `Gtk.TreePath` referencing the artist.
        '''
        return self.store[path][self.columns['artist_album']]

    def get_path(self, artist):
        print (artist.name)
        print (self._iters[artist.name]['iter'])
        return self._tree_store.get_path(
                self._iters[artist.name]['iter'])
                
    def get_from_ext_db_key(self, key):
        '''
        Returns the requested artist.

        :param key: ext_db_key
        '''
        # get the album name and artist
        name = key.get_field('artist')
        
        # first check if there's a direct match
        artist = self.get(name) if self.contains(name) else None
        return artist

    def show(self, artist_name, show):
        '''
        filters/unfilters an artist, making it visible to the publicly available model's
        `Gtk.TreeModel`

        :param artist: str containing the name of the artist to show or hide.
        :param show: `bool` indcating whether to show(True) or hide(False) the
            artist.
        '''
        artist_iter = self._iters[artist_name]['iter']

        if self._tree_store.iter_is_valid(artist_iter):
            self._tree_store.set_value(artist_iter, self.columns['show'], show)
            
            
    def sort(self):
        
        albums = SortedCollection(key=lambda album: getattr(album, 'name'))
        
        gs = GSetting()
        source_settings = gs.get_setting(gs.Path.PLUGIN)
        key = source_settings[gs.PluginKey.SORT_BY_ARTIST]
        order = source_settings[gs.PluginKey.SORT_ORDER_ARTIST]
        
        sort_keys = {
            'name_artist': ('album_sort', 'album_sort'),
            'year_artist': ('real_year', 'calc_year_sort'),
            'rating_artist': ('rating', 'album_sort')
            }

        props = sort_keys[key]
        
        def key_function(album):
            keys = [getattr(album, prop) for prop in props]
            return keys
            
        # remember the current sort then remove the sort order
        # because sorting will only work in unsorted lists
        sortSettings = self.store.get_sort_column_id()

        self.store.set_sort_column_id(-1, Gtk.SortType.ASCENDING)
        
        for artist in self._iters:
            albums.clear()
            albums.key = key_function
            
            if 'album' in self._iters[artist] and len(self._iters[artist]['album']) > 1:
                # we only need to sort an artists albums if there is more than one album
                
                # sort all the artists albums
                for album_iter in self._iters[artist]['album']:
                    albums.insert(self._tree_store[album_iter][self.columns['artist_album']])

                if not order:
                    albums = reversed(albums)
        
                # now we iterate through the sorted artist albums.  Look and swap iters
                # according to where they are in the tree store
            
                artist_iter = self._iters[artist]['iter']
                next_iter = self._tree_store.iter_children(artist_iter)
                
                for album in albums:
                    if self._tree_store[next_iter][self.columns['artist_album']] != album:
                        self._tree_store.swap(next_iter, self._albumiters[album]['iter'])
                        next_iter = self._albumiters[album]['iter']
                    next_iter = self._tree_store.iter_next(next_iter)
        
        # now we have finished sorting, reapply the sort
        self.store.set_sort_column_id(*sortSettings)
        
class ArtistCellRenderer(Gtk.CellRendererPixbuf):
    
    def __init__(self):
        super(ArtistCellRenderer, self).__init__()
        
    def do_render(self, cr, widget,  
                background_area,
                cell_area,
                flags):
        
        newpix = self.props.pixbuf #.copy()
        #newpix = newpix.scale_simple(48,48,GdkPixbuf.InterpType.BILINEAR)
        
        Gdk.cairo_set_source_pixbuf(cr, newpix, 0, 0)
        cr.paint()
    
class ArtistLoader(GObject.Object):
    '''
    Loads Artists - updating the model accordingly.

    :param artist_manager: `artist_manager` responsible for this loader.
    '''
    # signals
    __gsignals__ = {
        'artists-load-finished': (GObject.SIGNAL_RUN_LAST, None, (object,)),
        'model-load-finished': (GObject.SIGNAL_RUN_LAST, None, ())
        }

    def __init__(self, artist_manager, album_manager):
        super(ArtistLoader, self).__init__()

        self.shell = artist_manager.shell
        self._connect_signals()
        self._album_manager = album_manager
        self._artist_manager = artist_manager
        
        self.model = artist_manager.model
    
    def load_artists(self):
        albums = self._album_manager.model.get_all()
        model = list(set(album.artist for album in albums))
        
        self._load_artists(iter(model), artists={}, model=model, 
            total=len(model), progress=0.)
            
    @idle_iterator
    def _load_artists(self):
        def process(row, data):
            # allocate the artist
            artist = Artist(row, self._artist_manager.cover_man.unknown_cover)
                
            data['artists'][row] = artist
            
        def after(data):
            # update the progress
            data['progress'] += ARTIST_LOAD_CHUNK

            self._album_manager.progress = data['progress'] / data['total']

        def error(exception):
            print('Error processing entries: ' + str(exception))

        def finish(data):
            self._album_manager.progress = 1
            self.emit('artists-load-finished', data['artists'])

        return ARTIST_LOAD_CHUNK, process, after, error, finish

    @idle_iterator
    def _load_model(self):
        def process(artist, data):
            # add  the artists to the model
            self._artist_manager.model.add(artist)
            
        def after(data):
            data['progress'] += ARTIST_LOAD_CHUNK

            # update the progress
            self._album_manager.progress = 1 - data['progress'] / data['total']
            
        def error(exception):
            dumpstack("Something awful happened!")
            print('Error(2) while adding artists to the model: ' + str(exception))

        def finish(data):
            self._album_manager.progress = 1
            self.emit('model-load-finished')
            #return False

        return ARTIST_LOAD_CHUNK, process, after, error, finish
        
    def _connect_signals(self):
        # connect signals for updating the albums
        #self.entry_changed_id = self._album_manager.db.connect('entry-changed',
        #    self._entry_changed_callback)
        pass
        
    def do_artists_load_finished(self, artists):
        self._load_model(iter(list(artists.values())), total=len(artists), progress=0.)
        self._album_manager.model.connect('album-added', self._on_album_added)
        
    def _on_album_added(self, album_model, album):
        '''
          called when album-manager album-added signal is invoked
        '''
        print (album.artist)
        if self._artist_manager.model.contains(album.artist):
            print ("contains artist")
            artist = self._artist_manager.model.get(album.artist)
            self._artist_manager.model.add_album_to_artist(artist, [album])
        else:
            print ("new artist")
            artist = Artist(album.artist, self._artist_manager.cover_man.unknown_cover)
            self._artist_manager.model.add(artist)

class ArtistCoverManager(CoverManager):
    
    def __init__(self, plugin, artist_manager):
        self.cover_db = CoverArtExtDB(name='artist-art')
        
        super(ArtistCoverManager, self).__init__(plugin, artist_manager)

        self.cover_size = 72

        # create unknown cover and shadow for covers
        self.create_unknown_cover(plugin)
            
    def create_unknown_cover(self, plugin):
        # create the unknown cover
        self.unknown_cover = self.create_cover(
            rb.find_plugin_file(plugin, 'img/microphone.png'))

        super(ArtistCoverManager,self).create_unknown_cover(plugin)
        
    def update_pixbuf_cover(self, coverobject, pixbuf):
        # if it's a pixbuf, assign it to all the artist for the artist
        key = RB.ExtDBKey.create_storage('artist', coverobject.name)
        
        self.cover_db.store(key, RB.ExtDBSourceType.USER_EXPLICIT,
            pixbuf)

class ArtistManager(GObject.Object):
    '''
    Main construction that glues together the different managers, the loader
    and the model. It takes care of initializing all the system.

    :param plugin: `Peas.PluginInfo` instance.
    :param current_view: `ArtistView` where the Artists are shown.
    '''
    # singleton instance
    instance = None

    # properties
    progress = GObject.property(type=float, default=0)
    
    # signals
    __gsignals__ = {
        'sort': (GObject.SIGNAL_RUN_LAST, None, (object,))
        }
    
    def __init__(self, plugin, album_manager, shell):
        super(ArtistManager, self).__init__()

        self.db = plugin.shell.props.db
        self.shell = shell
        self.plugin = plugin

        self.cover_man = ArtistCoverManager(plugin, self)
        self.cover_man.album_manager = album_manager

        self.model = ArtistsModel(album_manager)
        self.loader = ArtistLoader(self, album_manager)
 
        # connect signals
        self._connect_signals()

    def _connect_signals(self):
        '''
        Connects the manager to all the needed signals for it to work.
        '''
        self.loader.connect('model-load-finished', self._load_finished_callback)
        self.connect('sort', self._sort_artist)
        
    def _sort_artist(self, widget, param):
        
        toolbar_type = param

        if not toolbar_type or toolbar_type == "artist":
            self.model.sort()
    
    def _load_finished_callback(self, *args):
        self.cover_man.load_covers()
        
class ArtistShowingPolicy(GObject.Object):
    '''
    Policy that mostly takes care of how and when things should be showed on
    the view that makes use of the `AlbumsModel`.
    '''

    def __init__(self, flow_view):
        super(ArtistShowingPolicy, self).__init__()

        self._flow_view = flow_view
        self.counter = 0
        self._has_initialised = False

    def initialise(self, album_manager):
        if self._has_initialised:
            return

        self._has_initialised = True
        self._album_manager = album_manager
        self._model = album_manager.model
        
class ArtistView(Gtk.TreeView, AbstractView):
    __gtype_name__ = "ArtistView"

    name = 'artistview'
    icon_automatic = GObject.property(type=bool, default=True)
    panedposition = PanedCollapsible.Paned.COLLAPSE
    
    __gsignals__ = {
        'update-toolbar': (GObject.SIGNAL_RUN_LAST, None, ())
        }
    

    def __init__(self, *args, **kwargs):
        super(ArtistView, self).__init__(*args, **kwargs)
        
        self.ext_menu_pos = 0
        self._external_plugins = None
        self.gs = GSetting()
        self.show_policy = ArtistShowingPolicy(self)
        self.view = self
        self._has_initialised = False        
        self._last_row_was_artist = False
            
    def initialise(self, source):
        if self._has_initialised:
            return
            
        self._has_initialised = True

        self.view_name = "artist_view"
        super(ArtistView, self).initialise(source)
        self.album_manager = source.album_manager
        self.shell = source.shell
        self.ext_menu_pos = 6
        self.props.has_tooltip = True
        
        self.set_enable_tree_lines(True)
        
        col = Gtk.TreeViewColumn('     ', Gtk.CellRendererText(), text=6)
        self.append_column(col)
        
        pixbuf = Gtk.CellRendererPixbuf()
        col = Gtk.TreeViewColumn(_('Covers'), pixbuf, pixbuf=1)
        
        self.append_column(col)
        
        col = Gtk.TreeViewColumn(_('Track Artist'), Gtk.CellRendererText(), markup=5)
        self._artist_col = col
        col.set_clickable(True)
        col.set_sort_column_id(0)
        col.set_sort_indicator(True)
        col.connect('clicked', self._artist_sort_clicked)
        self.append_column(col)
        col = Gtk.TreeViewColumn('', Gtk.CellRendererText(), text=4)
        self.append_column(col) # dummy column to expand horizontally
        
        self.artist_manager = self.album_manager.artist_man
        self.artist_manager.model.store.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.set_model(self.artist_manager.model.store)
        
        # setup iconview drag&drop support
        # first drag and drop on the coverart view to receive coverart
        self.enable_model_drag_dest([], Gdk.DragAction.COPY)
        self.drag_dest_add_image_targets()
        self.drag_dest_add_text_targets()
        self.connect('drag-drop', self.on_drag_drop)
        self.connect('drag-data-received',
            self.on_drag_data_received)
            
        # lastly support drag-drop from coverart to devices/nautilus etc
        # n.b. enabling of drag-source is controlled by the selection-changed to ensure
        # we dont allow drag from artists
        self.connect('drag-begin', self.on_drag_begin)
        self._targets = Gtk.TargetList.new([Gtk.TargetEntry.new("text/uri-list", 0, 0) ])
    
        # N.B. values taken from rhythmbox v2.97 widgets/rb_entry_view.c
        self._targets.add_uri_targets(1)
        self.connect("drag-data-get", self.on_drag_data_get)
        
        # define artist specific popup menu
        self.artist_popup_menu = Menu(self.plugin, self.shell)
        self.artist_popup_menu.load_from_file('ui/coverart_artist_pop_rb2.ui',
            'ui/coverart_artist_pop_rb3.ui')
        signals = \
            { 'play_album_menu_item': self.source.play_album_menu_item_callback,
              'queue_album_menu_item': self.source.queue_album_menu_item_callback,
              'playlist_menu_item': self.source.playlist_menu_item_callback,
              'new_playlist': self.source.add_playlist_menu_item_callback,
              'artist_cover_search_menu_item': self.cover_search_menu_item_callback
            }
              
        self.artist_popup_menu.connect_signals(signals)
            
        # connect properties and signals
        self._connect_properties()
        self._connect_signals()
        
    def _connect_properties(self):
        setting = self.gs.get_setting(self.gs.Path.PLUGIN)
        setting.bind(self.gs.PluginKey.ICON_AUTOMATIC, self,
            'icon_automatic', Gio.SettingsBindFlags.GET)
        
    def _connect_signals(self):
        self.connect('row-activated', self._row_activated)
        self.connect('row-expanded', self._row_expanded)
        self.connect('button-press-event', self._row_click)
        self.get_selection().connect('changed', self._selection_changed)
        self.connect('query-tooltip', self._query_tooltip)
    
    def _artist_sort_clicked(self, *args):
        # in the absence of an apparent way to remove the unsorted default_sort_func
        # find out if we are now in an unsorted state - if we are
        # throw another clicked event so that we remain sorted.
        value, order = self.artist_manager.model.store.get_sort_column_id()
        
        if order == None:
            self._artist_col.emit('clicked')
        
    def cover_search_menu_item_callback(self, *args):
        self.artist_manager.cover_man.search_covers(self.get_selected_objects(just_artist=True),
            callback=self.source.update_request_status_bar)
        
    def _query_tooltip( self, widget, x, y, key, tooltip ):
        
        try:
            winx, winy = self.convert_widget_to_bin_window_coords(x, y)
            treepath, treecolumn, cellx, celly = self.get_path_at_pos(winx, winy)
            active_object = self.artist_manager.model.get_from_path(treepath)
            
            #active_object=self.artist_manager.model.store[treepath][self.artist_manager.model.columns['artist_album']]
            
            if isinstance(active_object, Artist) and \
                treecolumn.get_title() == _('Covers') and \
                active_object.cover.original != self.artist_manager.cover_man.unknown_cover.original:
                # we display the tooltip if the row is an artist and the column
                # is actually the artist cover itself
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(active_object.cover.original)
                    
                src_width = pixbuf.get_width()
                src_height = pixbuf.get_height()
                
                factor = min(float(256)  / float(src_width), float(256) / float(src_height))
                new_width  = int(src_width * factor + 0.5)
                new_height = int(src_height * factor + 0.5)
    
                pixbuf = create_pixbuf_from_file_at_size(
                    active_object.cover.original, new_width, new_height)
                
                tooltip.set_icon( pixbuf )
                return True
            else:
                return False

        except:
                pass
            
    def _row_expanded(self, treeview, treeiter, treepath):
        '''
        event called when clicking the expand icon on the treeview
        '''
        self._row_activated(treeview, treepath, _)
        
    def _row_activated(self, treeview, treepath, treeviewcolumn):
        '''
        event called when double clicking on the tree-view or by keyboard ENTER
        '''
        active_object = self.artist_manager.model.get_from_path(treepath)
        if isinstance(active_object, Artist):
            self.artist_manager.model.emit('update-path', treepath)
        else:
            #we need to play this album
            self.source.play_selected_album(self.source.favourites)
            
    def _row_click(self, widget, event):
        '''
        event called when clicking on a row
        '''
        
        try:
            treepath, treecolumn, cellx, celly = self.get_path_at_pos(event.x, event.y)
        except:
            return
            
        active_object = self.artist_manager.model.get_from_path(treepath)
        
        if not isinstance(active_object, Album):
            self.source.artist_info.emit('selected', active_object.name, None)
            if self.icon_automatic:
                # reset counter so that we get correct double click action for albums
                self.source.click_count = 0 
                
            if treecolumn != self.get_expander_column():
                if self.row_expanded(treepath) and event.button == 1 and self._last_row_was_artist:
                    self.collapse_row(treepath)
                else:
                    self.expand_row(treepath, False)
        
                self._last_row_was_artist = True
                
                if event.button ==3:
                    # on right click
                    # display popup
                    
                    self.artist_popup_menu.get_gtkmenu(self.source, 'popup_menu').popup(None,
                                    None, 
                                    None,
                                    None,
                                    3,
                                    Gtk.get_current_event_time())
            return
            
        if event.button == 1:
            # on click
            # to expand the entry view
            ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
            shift = event.state & Gdk.ModifierType.SHIFT_MASK

            if self.icon_automatic and not self._last_row_was_artist:
                self.source.click_count += 1 if not ctrl and not shift else 0

            if self.source.click_count == 1:
                Gdk.threads_add_timeout(GLib.PRIORITY_DEFAULT_IDLE, 250,
                    self.source.show_hide_pane, active_object)
                    
        elif event.button ==3:
            # on right click
            # display popup
            
            if not self._external_plugins:
                # initialise external plugin menu support
                self._external_plugins = \
                CreateExternalPluginMenu("ca_covers_view",
                    self.ext_menu_pos, self.popup)
                self._external_plugins.create_menu('popup_menu', True)
            
            self.popup.get_gtkmenu(self.source, 'popup_menu').popup(None,
                            None, 
                            None,
                            None,
                            3,
                            Gtk.get_current_event_time())
                            
        self._last_row_was_artist = False
            
    def get_view_icon_name(self):
        return "artistview.png"
        
    def _selection_changed(self, *args):
        selected = self.get_selected_objects(just_artist=True)

        print (selected)
        if len(selected) == 0:
            self.source.entry_view.clear()
            return
            
        if isinstance(selected[0], Artist):
            print ("selected artist")
            self.unset_rows_drag_source() # turn off drag-drop for artists
                
            # clear the entry view
            self.source.entry_view.clear()

            cover_search_pane_visible = self.source.notebook.get_current_page() == \
                self.source.notebook.page_num(self.source.cover_search_pane)
                            
            # update the cover search pane with the first selected artist
            if cover_search_pane_visible:
                print ("update coversearch for artist")
                print (selected[0])
                self.source.cover_search_pane.do_search(selected[0],
                    self.artist_manager.cover_man.update_cover)
            
        else:
            print ("selected album")
            self.source.update_with_selection()
            # now turnon drag-drop for album.
            self.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK,
                [], Gdk.DragAction.COPY)
            self.drag_source_set_target_list(self._targets)
    
    def switch_to_coverpane(self, cover_search_pane):
        '''
        called from the source to update the coverpane when
        it is switched from the track pane
        This overrides the base method
        '''
        
        selected = self.get_selected_objects(just_artist=True)

        if selected:
            manager = self.get_default_manager()
            cover_search_pane.do_search(selected[0],
                manager.cover_man.update_cover)

    def get_selected_objects(self, just_artist=False):
        '''
        finds what has been selected

        returns an array of `Album`
        '''
        selection = self.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter:
            active_object = model.get_value(treeiter,ArtistsModel.columns['artist_album'])
            if isinstance(active_object, Album):
                # have chosen an album then just return that album
                return [active_object]
            else:
                # must have chosen an artist - return all albums for the artist by default
                # or just the artist itself
                if not just_artist:
                    return self.artist_manager.model.get_albums(active_object.name)
                else:
                    return [active_object]
        return []
        
    def switch_to_view(self, source, album):
        self.initialise(source)
        self.show_policy.initialise(source.album_manager)
        
        if album:
            print ("switch to artist view")
            print (album)
            artist = self.artist_manager.model.get(album.artist)
            path = self.artist_manager.model.get_path(artist)
            print (artist)
            print (path)
            path = self.artist_manager.model.store.convert_child_path_to_path(path)
            print (path)
            if path:
                self.scroll_to_cell(path, self._artist_col)
                self.expand_row(path, False)
                self.set_cursor(path)
            
    def do_update_toolbar(self, *args):
        self.source.toolbar_manager.set_enabled(False, ToolbarObject.SORT_BY)
        self.source.toolbar_manager.set_enabled(False, ToolbarObject.SORT_ORDER)
        self.source.toolbar_manager.set_enabled(True, ToolbarObject.SORT_BY_ARTIST)
        self.source.toolbar_manager.set_enabled(True, ToolbarObject.SORT_ORDER_ARTIST)
        
    def on_drag_drop(self, widget, context, x, y, time):
        '''
        Callback called when a drag operation finishes over the view
        of the source. It decides if the dropped item can be processed as
        an image to use as a cover.
        '''

        # stop the propagation of the signal (deactivates superclass callback)
        if rb3compat.is_rb3(self.shell):
            widget.stop_emission_by_name('drag-drop')
        else:
            widget.stop_emission('drag-drop')

        # obtain the path of the icon over which the drag operation finished
        drop_info = self.get_dest_row_at_pos(x, y)
        path = None
        if drop_info:
            path, position = drop_info
            
        result = path is not None

        if result:
            target = self.drag_dest_find_target(context, None)
            widget.drag_get_data(context, target, time)

        return result

    def on_drag_data_received(self, widget, drag_context, x, y, data, info,
        time):
        '''
        Callback called when the drag source has prepared the data (pixbuf)
        for us to use.
        '''

        # stop the propagation of the signal (deactivates superclass callback)
        if rb3compat.is_rb3(self.shell):
            widget.stop_emission_by_name('drag-data-received')
        else:
            widget.stop_emission('drag-data-received')

        # get the artist and the info and ask the loader to update the cover
        path, position = self.get_dest_row_at_pos(x, y)
        artist_album = widget.get_model()[path][2]

        pixbuf = data.get_pixbuf()  

        if isinstance(artist_album, Album):
            manager = self.album_manager
        else:
            manager = self.artist_manager
            
        if pixbuf:
            manager.cover_man.update_cover(artist_album, pixbuf)
        else:
            uri = data.get_text()
            manager.cover_man.update_cover(artist_album, uri=uri)

        # call the context drag_finished to inform the source about it
        drag_context.finish(True, False, time)
        
    def on_drag_data_get(self, widget, drag_context, data, info, time):
        '''
        Callback called when the drag destination (playlist) has
        requested what album (icon) has been dragged
        '''

        uris = []
        for album in widget.get_selected_objects():
            for track in album.get_tracks():
                uris.append(track.location)

        data.set_uris(uris)
        # stop the propagation of the signal (deactivates superclass callback)
        if rb3compat.is_rb3(self.shell):
            widget.stop_emission_by_name('drag-data-get')
        else:
            widget.stop_emission('drag-data-get')

    def on_drag_begin(self, widget, context):
        '''
        Callback called when the drag-drop from coverview has started
        Changes the drag icon as appropriate
        '''
        album_number = len(widget.get_selected_objects())

        if album_number == 1:
            item = Gtk.STOCK_DND
        else:
            item = Gtk.STOCK_DND_MULTIPLE

        widget.drag_source_set_icon_stock(item)
        if rb3compat.is_rb3(self.shell):
            widget.stop_emission_by_name('drag-begin')
        else:
            widget.stop_emission('drag-begin')
    
        
    def get_default_manager(self):
        '''
        the default manager for this view is the artist_manager
        '''
        return self.artist_manager
