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

'''
Structures and managers to work with albums on Rhythmbox. This module provides
the base model for the plugin to work on top of.
'''

from gi.repository import RB
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
import cairo

from coverart_browser_prefs import GSetting
from coverart_utils import SortedCollection
from urlparse import urlparse

import urllib
import os
import cgi
import tempfile
import rb
import gc


# default chunk of entries to procces when loading albums
ALBUM_LOAD_CHUNK = 50

# default chunk of albums to procces when loading covers
COVER_LOAD_CHUNK = 5


class Cover(GObject.Object):
    '''
    Cover of an Album. It may be initialized either by a file path to the image
    to use or by a previously allocated pixbuf.

    :param size: `int` size in pixels of the side of the cover (asuming a
        square-shapped cover).
    :param image: `str` containing a path of an image from where to create
        the cover or `GdkPixbuf.Pixbuf` containing the cover.
    '''
    # signals
    __gsignals__ = {
        'resized': (GObject.SIGNAL_RUN_LAST, None, ())
        }

    def __init__(self, size, image):
        super(Cover, self).__init__()

        self.original = image

        self._create_pixbuf(size)

    def resize(self, size):
        '''
        Resizes the cover's pixbuf.
        '''
        if self.size != size:
            self._create_pixbuf(size)
            self.emit('resized')

    def _create_pixbuf(self, size):
        try:
            self.pixbuf = self.original.scale_simple(size, size,
                 GdkPixbuf.InterpType.BILINEAR)
        except:
            self.pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(self.original,
                size, size)

        self.size = size


class Shadow(Cover):
    SIZE = 120.
    WIDTH = 11

    def __init__(self, size, image):
        super(Shadow, self).__init__(size, image)

        self._calculate_sizes(size)

    def resize(self, size):
        super(Shadow, self).resize(size)

        self._calculate_sizes(size)

    def _calculate_sizes(self, size):
        self.width = int(size / self.SIZE * self.WIDTH)
        self.cover_size = self.size - self.width * 2


class ShadowedCover(Cover):

    def __init__(self, shadow, image):
        super(ShadowedCover, self).__init__(shadow.cover_size, image)

        self._shadow = shadow

        self._add_shadow()

    def resize(self, size):
        if self.size != self._shadow.cover_size:
            self._create_pixbuf(self._shadow.cover_size)
            self._add_shadow()

            self.emit('resized')

    def _add_shadow(self):
        pix = self._shadow.pixbuf

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, pix.get_width(),
            pix.get_height())
        context = cairo.Context(surface)

        # draw shadow
        Gdk.cairo_set_source_pixbuf(context, pix, 0, 0)
        context.paint()

        # draw cover
        Gdk.cairo_set_source_pixbuf(context, self.pixbuf, self._shadow.width,
            self._shadow.width)
        context.paint()

        self.pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0,
            self._shadow.size, self._shadow.size)


class Track(GObject.Object):
    '''
    A music track. Provides methods to access to most of the tracks data from
    Rhythmbox's database.

    :param entry: `RB.RhythmbDBEntry` rhythmbox's database entry for the track.
    :param db: `RB.RhythmbDB` instance. It's needed to update the track's
        values.
    '''
    # signals
    __gsignals__ = {
        'modified': (GObject.SIGNAL_RUN_LAST, None, ()),
        'deleted': (GObject.SIGNAL_RUN_LAST, None, ())
        }

    def __init__(self, entry, db=None):
        super(Track, self).__init__()

        self.entry = entry
        self._db = db

    def __eq__(self, other):
        return rb.entry_equal(self.entry, other.entry)

    @property
    def title(self):
        return self.entry.get_string(RB.RhythmDBPropType.TITLE)

    @property
    def artist(self):
        return self.entry.get_string(RB.RhythmDBPropType.ARTIST)

    @property
    def album(self):
        return self.entry.get_string(RB.RhythmDBPropType.ALBUM)

    @property
    def album_artist(self):
        return self.entry.get_string(RB.RhythmDBPropType.ALBUM_ARTIST)

    @property
    def genre(self):
        return self.entry.get_string(RB.RhythmDBPropType.GENRE)

    @property
    def year(self):
        return self.entry.get_ulong(RB.RhythmDBPropType.DATE)

    @property
    def rating(self):
        return self.entry.get_double(RB.RhythmDBPropType.RATING)

    @rating.setter
    def rating(self, new_rating):
        self._db.entry_set(self.entry, RB.RhythmDBPropType.RATING, new_rating)

    @property
    def duration(self):
        return self.entry.get_ulong(RB.RhythmDBPropType.DURATION)

    @property
    def location(self):
        return self.entry.get_string(RB.RhythmDBPropType.LOCATION)

    @property
    def track_number(self):
        return self.entry.get_ulong(RB.RhythmDBPropType.TRACK_NUMBER)

    def create_ext_db_key(self):
        '''
        Returns an `RB.ExtDBKey` that can be used to acces/write some other
        track specific data on an `RB.ExtDB`.
        '''
        return self.entry.create_ext_db_key(RB.RhythmDBPropType.ALBUM)


class Album(GObject.Object):
    '''
    An album. It's conformed from one or more tracks, and many of it's
    information is deduced from them.

    :param name: `str` name of the album.
    :param cover: `Cover` cover for this album.
    '''
    # signals
    __gsignals__ = {
        'pre-modified': (GObject.SIGNAL_RUN_LAST, None, ()),
        'modified': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'emptied': (GObject.SIGNAL_RUN_LAST, None, ()),
        'cover-updated': (GObject.SIGNAL_RUN_LAST, None, ())
        }

    def __init__(self, name, cover):
        super(Album, self).__init__()

        self.name = name
        self._album_artist = None
        self._artists = None
        self._titles = None
        self._genres = None
        self._tracks = []
        self._cover = None
        self.cover = cover
        self._year = None
        self._rating = None
        self._duration = None

        self._signals_id = {}

    @property
    def album_artist(self):
        if not self._album_artist:
            multiple_artist = False

            for track in self._tracks:
                if not self._album_artist:
                    self._album_artist = track.album_artist
                elif track.album_artist != self._album_artist:
                    multiple_artist = True
                    break

            if not self._album_artist and not multiple_artist:
                for track in self._tracks:
                    if not self._album_artist:
                        self._album_artist = track.artist
                    elif track.artist != self._album_artist:
                        multiple_artist = True
                        break

            if multiple_artist:
                self._album_artist = _('Various Artist')

        return self._album_artist

    @property
    def artists(self):
        if not self._artists:
            self._artists = ', '.join(
                set([track.artist for track in self._tracks]))

        return self._artists

    @property
    def track_titles(self):
        if not self._titles:
            self._titles = ' '.join(
                set([track.title for track in self._tracks]))

        return self._titles

    @property
    def year(self):
        if not self._year:
            self._year = min([track.year for track in self._tracks])

        return self._year

    @property
    def genres(self):
        if not self._genres:
            self._genres = set([track.genre for track in self._tracks])

        return self._genres

    @property
    def rating(self):
        if not self._rating:
            ratings = [track.rating for track in self._tracks
                if track.rating and track.rating != 0]

            if len(ratings) > 0:
                self._rating = sum(ratings) / len(self._tracks)
            else:
                self._rating = 0

        return self._rating

    @rating.setter
    def rating(self, new_rating):
        for track in self._tracks:
            track.rating = new_rating

    @property
    def track_count(self):
        return len(self._tracks)

    @property
    def duration(self):
        if not self._duration:
            self._duration = sum([track.duration for track in self._tracks])

        return self._duration

    @property
    def cover(self):
        return self._cover

    @cover.setter
    def cover(self, new_cover):
        if self._cover:
            self._cover.disconnect(self._cover_resized_id)

        self._cover = new_cover
        self._cover_resized_id = self._cover.connect('resized',
            lambda *args: self.emit('cover-updated'))

        self.emit('cover-updated')

    def get_tracks(self, rating_threshold=0):
        '''
        Returns the tracks on this album. If rating_threshold is provided,
        only those tracks over the threshold will be returned. The track list
        returned is ordered by track number.

        :param rating_threshold: `float` threshold over which the rating of the
            track should be to be returned.
        '''
        if not rating_threshold or not self.rating:
            # if no song has rating, or no threshold is set, return all
            tracks = self._tracks

        else:
            # otherwise, only return the entries over the threshold
            tracks = [track for track in self._tracks
                if track.rating >= rating_threshold]

        return sorted(tracks, key=lambda track: track.track_number)

    def add_track(self, track):
        '''
        Adds a track to the album.

        :param track: `Track` track to be added.
        '''
        self._tracks.append(track)

        ids = (track.connect('modified', self._track_modified),
            track.connect('deleted', self._track_deleted))

        self._signals_id[track] = ids

        self.emit('pre-modified')

    def _track_modified(self, track):
        if track.album != self.name:
            self._track_deleted(track)
        else:
            self.emit('pre-modified')

    def _track_deleted(self, track):
        self._tracks.remove(track)

        map(track.disconnect, self._signals_id[track])
        del self._signals_id[track]

        if len(self._tracks) == 0:
            self.emit('emptied')
        else:
            self.emit('pre-modified')

    def create_ext_db_key(self):
        '''
        Creates a `RB.ExtDBKey` from this album's tracks.
        '''
        return self._tracks[0].create_ext_db_key()

    def do_pre_modified(self):
        self.emit('modified')

    def do_modified(self):
        self._album_artist = None
        self._artists = None
        self._titles = None
        self._genres = None
        self._year = None
        self._rating = None
        self._duration = None


class AlbumFilters(object):

    @classmethod
    def nay_filter(cls, *args):
        def filt(*args):
            return False

        return filt

    @classmethod
    def global_filter(cls, searchtext=None):
        def filt(album):
            # this filter is more complicated: for each word in the search
            # text, it tries to find at least one match on the params of
            # the album. If no match is given, then the album doesn't match
            if not searchtext:
                return True

            words = searchtext.lower().split()
            params = [album.name.lower(), album.album_artist.lower(),
                album.artists.lower(), album.track_titles.lower()]
            matches = []

            for word in words:
                match = False

                for param in params:
                    if word in param:
                        match = True
                        break

                matches.append(match)

            return False not in matches

        return filt

    @classmethod
    def album_artist_filter(cls, searchtext=None):
        def filt(album):
            if not searchtext:
                return True

            return searchtext.lower() in album.album_artist.lower()

        return filt

    @classmethod
    def artist_filter(cls, searchtext=None):
        def filt(album):
            if not searchtext:
                return True

            return searchtext.lower() in album.artists.lower()

        return filt

    @classmethod
    def album_name_filter(cls, searchtext=None):
        def filt(album):
            if not searchtext:
                return True

            return searchtext.lower() in album.name.lower()

        return filt

    @classmethod
    def track_title_filter(cls, searchtext=None):
        def filt(album):
            if not searchtext:
                return True

            return searchtext.lower() in album.track_titles.lower()

        return filt

    @classmethod
    def genre_filter(cls, searchtext=None):
        def filt(album):
            if not searchtext:
                return True

            return searchtext in album.genres

        return filt

    @classmethod
    def model_filter(cls, model=None):
        if not model or not len(model):
            return lambda x: True

        albums = set()

        for row in model:
            entry = model[row.path][0]
            albums.add(Track(entry).album)

        def filt(album):
            return album.name in albums

        return filt

AlbumFilters.keys = {'nay': AlbumFilters.nay_filter,
        'all': AlbumFilters.global_filter,
        'album_artist': AlbumFilters.album_artist_filter,
        'artist': AlbumFilters.artist_filter,
        'album_name': AlbumFilters.album_name_filter,
        'track': AlbumFilters.track_title_filter,
        'genre': AlbumFilters.genre_filter,
        'model': AlbumFilters.model_filter
        }


class AlbumsModel(GObject.Object):
    '''
    Model that contains albums, keeps them sorted, filtered and provides an
    external `Gtk.TreeModel` interface to use as part of a Gtk interface.

    The `Gtk.TreeModel` haves the following structure:
    column 0 -> string containing the album name and artist
    column 1 -> pixbuf of the album's cover.
    column 2 -> instance of the album itself.
    column 3 -> markup text showed under the cover.
    column 4 -> boolean that indicates if the row should be shown
    '''
    # signals
    __gsignals__ = {
        'generate-tooltip': (GObject.SIGNAL_RUN_LAST, str, (object,)),
        'generate-markup': (GObject.SIGNAL_RUN_LAST, str, (object,)),
        'album-updated': ((GObject.SIGNAL_RUN_LAST, None, (object, object))),
        'visual-updated': ((GObject.SIGNAL_RUN_LAST, None, (object, object))),
        'filter-changed': ((GObject.SIGNAL_RUN_FIRST, None, ()))
        }

    # list of columns names and positions on the TreeModel
    columns = {'tooltip': 0, 'pixbuf': 1, 'album': 2, 'markup': 3, 'show': 4}

    def __init__(self):
        super(AlbumsModel, self).__init__()

        self._iters = {}
        self._albums = SortedCollection(
            key=lambda album: getattr(album, 'name'))

        self._tree_store = Gtk.ListStore(str, GdkPixbuf.Pixbuf, object, str,
            bool)
        self._tree_store

        # filters
        self._filters = {}

        # sorting direction
        self._asc = True

        # create the filtered store that's used with the view
        self._filtered_store = self._tree_store.filter_new()
        self._filtered_store.set_visible_column(4)

    @property
    def store(self):
        return self._filtered_store

    def _album_pre_modified(self, album):
        # remove the album before it get's changed and we loose it on the limbo
        self._albums.remove(album)

    def _album_modified(self, album):
        tree_iter = self._iters[album.name]['iter']

        if self._tree_store.iter_is_valid(tree_iter):
            # only update if the iter is valid
            # generate and update values
            tooltip, pixbuf, album, markup, hidden =\
                self._generate_values(album)

            self._tree_store.set(tree_iter, self.columns['tooltip'], tooltip,
                self.columns['markup'], markup, self.columns['show'], hidden)

            # reorder the album
            new_pos = self._albums.insert(album)
            old_iter = self._iters[self._albums[new_pos + 1].name]['iter']

            self._tree_store.move_before(tree_iter, old_iter)

            # inform that the album is updated
            self._emit_signal(tree_iter, 'album_updated')

    def _cover_updated(self, album):
        tree_iter = self._iters[album.name]['iter']

        if self._tree_store.iter_is_valid(tree_iter):
            # only update if the iter is valid
            pixbuf = album.cover.pixbuf

            self._tree_store.set_value(tree_iter, self.columns['pixbuf'],
                pixbuf)

            self._emit_signal(tree_iter, 'visual-updated')

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

    def add(self, album):
        '''
        Add an album to the model.

        :param album: `Album` to be added to the model.
        '''
        # generate necesary values
        values = self._generate_values(album)

        # insert the values
        tree_iter = self._tree_store.insert(self._albums.insert(album), values)

        # connect signals
        ids = (album.connect('pre-modified', self._album_pre_modified),
            album.connect('modified', self._album_modified),
            album.connect('cover-updated', self._cover_updated),
            album.connect('emptied', self.remove))

        self._iters[album.name] = {'album': album, 'iter': tree_iter,
            'ids': ids}

        return tree_iter

    def _generate_values(self, album):
        tooltip = self.emit('generate-tooltip', album)
        markup = self.emit('generate-markup', album)
        pixbuf = album.cover.pixbuf
        hidden = self._album_filter(album)

        return tooltip, pixbuf, album, markup, hidden

    def remove(self, album):
        '''
        Removes this album from the model.

        :param album: `Album` to be removed from the model.
        '''
        self._albums.remove(album)
        self._tree_store.remove(self._iters[album.name]['iter'])

        # disconnect signals
        for sig_id in self._iters[album.name]['ids']:
            album.disconnect(sig_id)

        del self._iters[album.name]

    def contains(self, album_name):
        '''
        Indicates if the model contains an especific album.

        :param album_name: `str` name of the album.
        '''
        return album_name in self._iters

    def get(self, album_name):
        '''
        Returns the requested album.

        :param album_name: `str` name of the album.
        '''
        return self._iters[album_name]['album']

    def get_all(self):
        '''
        Returns a collection of all the albums in this model.
        '''
        return self._albums

    def get_from_path(self, path):
        '''
        Returns an album referenced by a `Gtk.TreeModel` path.

        :param path: `Gtk.TreePath` referencing the album.
        '''
        return self._filtered_store[path][self.columns['album']]

    def show(self, album, show):
        '''
        Unfilters an album, making it visible to the publicly available model's
        `Gtk.TreeModel`

        :param album: `Album` to show or hide.
        :param show: `bool` indcating whether to show(True) or hide(False) the
            album.
        '''
        self._tree_store.set_value(self._iters[album.name]['iter'],
                self.columns['show'], show)

    def sort(self, key, asc):
        '''
        Changes the sorting strategy for the model.

        :param key: `str`attribute of the `Album` class by witch the sort
            should be performed.
        :param asc: `bool` indicating whether it should be sortered in
            ascendent(True) or descendent(False) direction.
        '''
        self._albums.key = lambda album: getattr(album, key)

        if asc != self._asc:
            self._albums = reversed(self._albums)

        self._asc = asc

        self._tree_store.clear()

        def idle_add_albums(albums_iter):
            for i in range(ALBUM_LOAD_CHUNK):
                try:
                    album = albums_iter.next()
                    values = self._generate_values(album)

                    tree_iter = self._tree_store.append(values)
                    self._iters[album.name]['iter'] = tree_iter

                except StopIteration:
                    # remove the nay filter
                    self.remove_filter('nay')

                    return False

                except Exception as e:
                    print 'Error while adding albums to the model: ' + str(e)

            # the list still got albums, keep going
            return True

        # add the nay filter
        self.replace_filter('nay', refilter=False)

        # load the albums back to the model
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, idle_add_albums,
            iter(self._albums))

    def replace_filter(self, filter_key, filter_arg=None, refilter=True):
        '''
        Adds or replaces a filter by it's filter_key.

        :param filter_key: `str` key of the filter method to use. This should
            be one of the available keys on the `AlbumFilters` class.
        :param filter_arg: `object` any object that the correspondant filter
            method may need to perform the filtering process.
        :param refilter: `bool` indicating whether to force a refilter and
        emit the 'filter-changed' signal(True) or not(False).
        '''
        self._filters[filter_key] = AlbumFilters.keys[filter_key](filter_arg)

        if refilter:
            self.emit('filter-changed')

    def remove_filter(self, filter_key, refilter=True):
        '''
        Removes a filter by it's filter_key

        :param filter_key: `str` key of the filter method to use. This should
            be one of the available keys on the `AlbumFilters` class.
        :param refilter: `bool` indicating whether to force a refilter and
        emit the 'filter-changed' signal(True) or not(False).
        '''
        if filter_key in self._filters:
            del self._filters[filter_key]

            if refilter:
                self.emit('filter-changed')

    def clear_filters(self):
        '''
        Clears all filters on the model.
        '''
        if self._filters:
            self._filters.clear()

            self.emit('filter-changed')

    def do_filter_changed(self):
        map(self.show, self._albums, map(self._album_filter, self._albums))

    def _album_filter(self, album):
            for f in self._filters.values():
                if not f(album):
                    return False

            return True

    def recreate_text(self):
        '''
        Forces the recreation and update of the markup text for each album.
        '''
        def idle_add_albums(albums_iter):
            for i in range(ALBUM_LOAD_CHUNK):
                try:
                    album = albums_iter.next()
                    tree_iter = self._iters[album.name]['iter']
                    markup = self.emit('generate-markup', album)

                    self._tree_store.set(tree_iter, self.columns['markup'],
                        markup)
                    self._emit_signal(tree_iter, 'visual-updated')

                except StopIteration:
                    return False

                except Exception as e:
                    print 'Error while recreating text: ' + str(e)

            # the list still got albums, keep going
            return True

        # load the albums back to the model
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, idle_add_albums,
            iter(self._albums))


class AlbumLoader(GObject.Object):
    '''
    Loads and updates Rhythmbox's tracks and albums, updating the model
    accordingly.

    :param album_manager: `AlbumManager` responsible for this loader.
    '''
    # signals
    __gsignals__ = {
        'albums-load-finished': (GObject.SIGNAL_RUN_LAST, None, (object,)),
        'model-load-finished': (GObject.SIGNAL_RUN_LAST, None, ())
        }

    def __init__(self, album_manager):
        super(AlbumLoader, self).__init__()

        self._album_manager = album_manager
        self._tracks = {}

        self._connect_signals()

    def _connect_signals(self):
        # connect signals for updating the albums
        self.entry_changed_id = self._album_manager.db.connect('entry-changed',
            self._entry_changed_callback)
        self.entry_added_id = self._album_manager.db.connect('entry-added',
            self._entry_added_callback)
        self.entry_deleted_id = self._album_manager.db.connect('entry-deleted',
            self._entry_deleted_callback)

    def _entry_changed_callback(self, db, entry, changes):
        print "CoverArtBrowser DEBUG - entry_changed_callback"
        # NOTE: changes are packed on a GValueArray

        # look at all the changes and update the albums acordingly
        try:
            track = self._tracks[Track(entry).location]

            while True:
                change = changes.values

                if change.prop is RB.RhythmDBPropType.ALBUM:
                    # called when the album of a entry is modified
                    track.emit('deleted')
                    self._allocate_track(track)

                elif change.prop is RB.RhythmDBPropType.HIDDEN:
                    # called when an entry gets hidden (e.g.:the sound file is
                    # removed.
                    if changes.new:
                        track.emit('deleted')
                    else:
                        self._allocate_track(track)

                # removes the last change from the GValueArray
                changes.remove(0)
        except:
            # we finished reading the GValueArray
            pass

        print "CoverArtBrowser DEBUG - end entry_changed_callback"

    def _entry_added_callback(self, db, entry):
        print "CoverArtBrowser DEBUG - entry_added_callback"
        self._allocate_track(Track(entry, db))

        print "CoverArtBrowser DEBUG - end entry_added_callback"

    def _entry_deleted_callback(self, db, entry):
        print "CoverArtBrowser DEBUG - entry_deleted_callback"
        track = self._tracks[Track(entry).location]
        del self._tracks[track.location]

        track.emit('deleted')

        print "CoverArtBrowser DEBUG - end entry_deleted_callback"

    def _allocate_track(self, track):
        if track.duration > 0:
            # only allocate the track if it's a valid track
            self._tracks[track.location] = track

            album_name = track.album

            if self._album_manager.model.contains(album_name):
                album = self._album_manager.model.get(album_name)
                album.add_track(track)
            else:
                album = Album(album_name,
                    self._album_manager.cover_man.unknown_cover)
                album.add_track(track)
                self._album_manager.cover_man.load_cover(album)
                self._album_manager.model.add(album)

    def load_albums(self, query_model):
        '''
        Loads and creates `Track` instances for all entries on query_model,
        asigning them into their correspondant `Album`.
        '''
        print "CoverArtBrowser DEBUG - load_albums"

        # function to proccess entries
        def idle_process_entry(args):
            # unpack args
            albums, model, total, count, row_iter = args

            for i in range(ALBUM_LOAD_CHUNK):
                try:
                    # get next entry
                    row = row_iter.next()

                    entry = model[row.path][0]

                    # allocate the track
                    track = Track(entry, self._album_manager.db)

                    self._tracks[track.location] = track

                    album_name = track.album

                    if album_name in albums:
                        album = albums[album_name]
                    else:
                        album = Album(album_name,
                            self._album_manager.cover_man.unknown_cover)
                        albums[album_name] = album

                    album.add_track(track)

                except StopIteration:
                    self._album_manager.progress = 1
                    self.emit('albums-load-finished', albums)
                    return False
                except Exception as e:
                    print 'Error processing entries: ' + str(e)

            # update the progress
            count += ALBUM_LOAD_CHUNK
            args[3] = count

            self._album_manager.progress = count / total

            return True

        # load the albums from the query_model
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, idle_process_entry,
            [{}, query_model, len(query_model), 0., iter(query_model)])

        print "CoverArtBrowser DEBUG - load_albums finished"

    def do_albums_load_finished(self, albums):
        # function to add the albums to the model
        def idle_add_albums(args):
            # unpack args
            albums_iter, loaded, total = args

            for i in range(ALBUM_LOAD_CHUNK):
                try:
                    # get next album and add it to the model
                    album = albums_iter.next()

                    self._album_manager.model.add(album)

                except StopIteration:
                    # we finished loading
                    self._album_manager.progress = 1
                    self.emit('model-load-finished')
                    return False

                except Exception as e:
                    print 'Error while adding albums to the model: ' + str(e)

            # update loaded
            loaded += ALBUM_LOAD_CHUNK
            args[1] = loaded

            # update the progress
            self._album_manager.progress = 1 - loaded / total

            # the list still got albums, keep going
            return True

        # load the albums to the model
        self._album_manager.model.replace_filter('nay')
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, idle_add_albums,
            [iter(albums.values()), 0, float(len(albums))])

    def do_model_load_finished(self):
        self._album_manager.model.remove_filter('nay')


class CoverManager(GObject.Object):
    '''
    Manager that takes care of cover loading and updating.

    :param plugin: `Peas.PluginInfo` instance used to have access to the
        predefined unknown cover.
    :param album_manager: `AlbumManager` responsible for this manager.
    '''

    # signals
    __gsignals__ = {
        'load-finished': (GObject.SIGNAL_RUN_LAST, None, ())
        }

    # properties
    cover_size = GObject.property(type=int, default=0)
    add_shadow = GObject.property(type=bool, default=False)

    def __init__(self, plugin, album_manager):
        super(CoverManager, self).__init__()

        self._cover_db = RB.ExtDB(name='album-art')
        self._album_manager = album_manager

        self._connect_properties()
        self._connect_signals()

        # create the unknown cover
        self._shadow = Shadow(self.cover_size,
            rb.find_plugin_file(plugin, 'img/album-shadow.png'))
        self.unknown_cover = self._create_cover(
            rb.find_plugin_file(plugin, 'img/rhythmbox-missing-artwork.svg'))

    def _connect_signals(self):
        self.connect('notify::cover-size', self._on_cover_size_changed)
        self.connect('notify::add-shadow', self._on_add_shadow_changed)

        # connect the signal to update cover arts when added
        self.req_id = self._cover_db.connect('added',
            self._albumart_added_callback)

    def _connect_properties(self):
        gs = GSetting()
        setting = gs.get_setting(gs.Path.PLUGIN)

        setting.bind(gs.PluginKey.COVER_SIZE, self, 'cover_size',
            Gio.SettingsBindFlags.GET)
        setting.bind(gs.PluginKey.ADD_SHADOW, self, 'add_shadow',
            Gio.SettingsBindFlags.GET)

    def _create_cover(self, image):
        if self.add_shadow:
            cover = ShadowedCover(self._shadow, image)
        else:
            cover = Cover(self.cover_size, image)

        return cover

    def _on_add_shadow_changed(self, *args):
        # update the unknown_cover
        self.unknown_cover = self._create_cover(self.unknown_cover.original)

        # recreate all the covers
        self.load_covers()

    def _on_cover_size_changed(self, *args):
        '''
        Updates the showing albums cover size.
        '''
        # update the shadow
        self._shadow.resize(self.cover_size)

        # update coverview item width
        self.update_item_width()

        # update the album's covers
        albums = self._album_manager.model.get_all()

        # function to resize the covers
        def idle_resize_callback(args):
            # unpack the args
            albums_iter, loaded, total = args

            for i in range(COVER_LOAD_CHUNK):
                try:
                    # get the next album and resize it's cover
                    album = albums_iter.next()

                    album.cover.resize(self.cover_size)

                except StopIteration:
                    # we finished loading
                    self._album_manager.progress = 1
                    self.emit('load-finished')
                    return False
                except Exception as e:
                    print "Error while resizing covers: " + str(e)

            # update loaded
            loaded += COVER_LOAD_CHUNK
            args[1] = loaded

            # update the progress
            self._album_manager.progress = loaded / total

            # the list still got albums, keep going
            return True

        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE,
            idle_resize_callback, [iter(albums), 0, float(len(albums))])

    def _albumart_added_callback(self, ext_db, key, path, pixbuf):
        print "CoverArtBrowser DEBUG - albumart_added_callback"
        # get the album name
        album_name = key.get_field('album')

        # use the name to get the album and update it's cover
        if pixbuf and self._album_manager.model.contains(album_name):
            album = self._album_manager.model.get(album_name)

            album.cover = self._create_cover(pixbuf)

        print "CoverArtBrowser DEBUG - end albumart_added_callback"

    def update_item_width(self):
        self._album_manager.cover_view.set_item_width(self.cover_size)

    def load_cover(self, album):
        '''
        Tries to load an Album's cover. If no cover is found upon lookup,
        the unknown cover is used.
        This method doesn't actively tries to find a cover, for that you should
        use the search_cover method.

        :param album: `Album` for which load the cover.
        '''
        # create a key and look for the art location
        key = album.create_ext_db_key()
        art_location = self._cover_db.lookup(key)

        # try to create a cover
        if art_location and os.path.exists(art_location):
            try:
                album.cover = self._create_cover(art_location)
            except:
                album.cover = self.unknown_cover

    def load_covers(self):
        '''
        Loads all the covers for the model's albums.
        '''
        # get all the albums
        albums = self._album_manager.model.get_all()

        # function to load the covers
        def idle_load_callback(args):
            # unpack the args
            albums_iter, loaded, total = args

            for i in range(COVER_LOAD_CHUNK):
                try:
                    # get the next album and try to load it's cover
                    album = albums_iter.next()

                    self.load_cover(album)

                except StopIteration:
                    # we finished loading
                    self._album_manager.progress = 1
                    gc.collect()
                    self.emit('load-finished')
                    return False

                except Exception as e:
                    print 'Error while loading covers: ' + str(e)

            # update loaded
            loaded += COVER_LOAD_CHUNK
            args[1] = loaded

            # update the progress
            self._album_manager.progress = loaded / total

            # the list still got albums, keep going
            return True

        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, idle_load_callback,
            [iter(albums), 0, float(len(albums))])

    def search_covers(self, albums=None, callback=lambda *_: None):
        '''
        Request all the albums' covers, one by one, periodically calling a
        callback to inform the status of the process.
        The callback should accept one argument: the album which cover is
        being requested. When the argument passed is None, it means the
        process has finished.

        :param albums: `list` of `Album` for which look for covers.
        :param callback: `callable` to periodically inform when an album's
            cover is being searched.
        '''
        if albums is None:
            albums = self._album_manager.model.get_all()

        def search_next_cover(*args):
            # unpack the data
            iterator, callback = args[-1]

            # if the operation was canceled, break the recursion
            if self._cancel_cover_request:
                del self._cancel_cover_request
                callback(None)
                return

            #try to obtain the next album
            try:
                while True:
                    album = iterator.next()

                    if album.cover is self.unknown_cover:
                        break

                # inform we are starting a new search
                callback(album)

                # request the cover for the next album
                self.search_cover_for_album(album, search_next_cover,
                    (iterator, callback))
            except StopIteration:
                # inform we finished
                callback(None)
            except Exception as e:
                print "Error while searching covers: " + str(e)

        self._cancel_cover_request = False
        search_next_cover((iter(albums), callback))

    def cancel_cover_request(self):
        '''
        Cancel the current cover request, if there is one running.
        '''
        try:
            self._cancel_cover_request = True
        except:
            pass

    def search_cover_for_album(self, album, callback=lambda *_: None,
        data=None):
        '''
        Activelly requests an Album's cover to the cover_db, calling
        the callback given once the process finishes (since it generally is
        asyncrhonous).
        For more information on the callback arguments, check
        `RB.ExtDB.request` documentation.

        :param album: `Album` for which search the cover.
        :param callback: `callable` to call when the process finishes.
        :param data: `object` to call the callable with.
        '''
        # create a key and request the cover
        key = album.create_ext_db_key()

        provides = self._cover_db.request(key, callback, data)

        if not provides:
            # in case there is no provider, call the callback inmediatly
            callback(data)

    def update_cover(self, album, pixbuf=None, uri=None):
        '''
        Updates the cover database, inserting the pixbuf as the cover art for
        all the entries on the album.
        In the case a uri is given instead of the pixbuf, it will first try to
        retrieve an image from the uri, then recall this method with the
        obtained pixbuf.

        :param album: `Album` for which the cover is.
        :param pixbuf: `GkdPixbuf.Pixbuf` to use as a cover.
        :param uri: `str` from where we should try to retrieve an image.
        '''
        if pixbuf:
            # if it's a pixbuf, asign it to all the artist for the album
            for artist in album.artists.split(', '):
                key = RB.ExtDBKey.create_storage('album', album.name)
                key.add_field('artist', artist)

                self._cover_db.store(key, RB.ExtDBSourceType.USER_EXPLICIT,
                    pixbuf)

        elif uri:
            parsed = urlparse(uri)

            if parsed.scheme == 'file':
                # local file, load it on a pixbuf and asign it
                path = urllib.url2pathname(uri.strip()).replace('file://', '')

                if os.path.exists(path):
                    cover = GdkPixbuf.Pixbuf.new_from_file(path)

                    self.update_cover(album, cover)

            else:
                # assume is a remote uri and we have to retrieve the data
                def cover_update(data, album):
                    # save the cover on a temp file and open it as a pixbuf
                    with tempfile.NamedTemporaryFile(mode='w') as tmp:
                        tmp.write(data)

                        try:
                            cover = GdkPixbuf.Pixbuf.new_from_file(tmp.name)

                            # set the new cover
                            self.update_cover(album, cover)
                        except:
                            print "The URI doesn't point to an image or " +\
                                "the image couldn't be opened."

                async = rb.Loader()
                async.get_url(uri, cover_update, album)


class TextManager(GObject.Object):
    '''
    Manager that keeps control of the text options for the model's markup text.
    It takes care of creating the text for the model when requested to do it.

    :param album_manager: `AlbumManager` responsible for this manager.
    '''
    # properties
    display_text_ellipsize_enabled = GObject.property(type=bool, default=False)
    display_text_ellipsize_length = GObject.property(type=int, default=0)
    display_font_size = GObject.property(type=int, default=0)
    display_text_enabled = GObject.property(type=bool, default=False)

    def __init__(self, album_manager):
        super(TextManager, self).__init__()

        self._album_manager = album_manager

        # connect properties and signals
        self._connect_signals()
        self._connect_properties()

        # activate markup if necesary
        self._activate_markup()

    def _connect_signals(self):
        '''
        Connects the loader to all the needed signals for it to work.
        '''
        # connect signals for the loader properties
        self.connect('notify::display-text-ellipsize-enabled',
            self._on_notify_display_text_ellipsize)
        self.connect('notify::display-text-ellipsize-length',
            self._on_notify_display_text_ellipsize)
        self.connect('notify::display-font-size',
            self._on_notify_display_text_ellipsize)
        self.connect('notify::display-text-enabled',
            self._activate_markup)

        self._album_manager.model.connect('generate-tooltip',
            self._generate_tooltip)
        self._album_manager.model.connect('generate-markup',
            self._generate_markup_text)

    def _connect_properties(self):
        '''
        Connects the loader properties to the saved preferences.
        '''
        gs = GSetting()
        setting = gs.get_setting(gs.Path.PLUGIN)

        setting.bind(gs.PluginKey.DISPLAY_TEXT_ELLIPSIZE, self,
            'display_text_ellipsize_enabled', Gio.SettingsBindFlags.GET)
        setting.bind(gs.PluginKey.DISPLAY_TEXT_ELLIPSIZE_LENGTH, self,
            'display_text_ellipsize_length',
            Gio.SettingsBindFlags.GET)
        setting.bind(gs.PluginKey.DISPLAY_FONT_SIZE, self, 'display_font_size',
            Gio.SettingsBindFlags.GET)
        setting.bind(gs.PluginKey.DISPLAY_TEXT, self,
            'display_text_enabled', Gio.SettingsBindFlags.GET)

    def _on_notify_display_text_ellipsize(self, *args):
        '''
        Callback called when one of the properties related with the ellipsize
        option is changed.
        '''
        self._album_manager.model.recreate_text()

    def _activate_markup(self, *args):
        '''
        Utility method to activate/deactivate the markup text on the
        cover view.
        '''
        print "CoverArtBrowser DEBUG - activate_markup"

        activate = self.display_text_enabled

        column = 3 if activate else -1

        self._album_manager.cover_man.update_item_width()
        self._album_manager.cover_view.set_markup_column(column)

        print "CoverArtBrowser DEBUG - end activate_markup"

    def _generate_tooltip(self, model, album):
        '''
        Utility function that creates the tooltip for this album to set into
        the model.
        '''
        return cgi.escape(_('%s by %s').encode('utf-8') % (album.name,
            album.artists))

    def _generate_markup_text(self, model, album):
        '''
        Utility function that creates the markup text for this album to set
        into the model.
        '''
        # we use unicode to avoid problems with non ascii albums
        name = unicode(album.name, 'utf-8')
        artist = unicode(album.album_artist, 'utf-8')

        if self.display_text_ellipsize_enabled:
            ellipsize = self.display_text_ellipsize_length

            if len(name) > ellipsize:
                name = name[:ellipsize] + '...'

            if len(artist) > ellipsize:
                artist = artist[:ellipsize] + '...'

        name = name.encode('utf-8')
        artist = artist.encode('utf-8')

        # escape odd chars
        artist = GLib.markup_escape_text(artist)
        name = GLib.markup_escape_text(name)

        # markup format
        markup = "<span font='%d'><b>%s</b>\n<i>%s</i></span>"
        return markup % (self.display_font_size, name, artist)


class AlbumShowingPolicy(GObject.Object):
    '''
    Policy that mostly takes care of how and when things should be showed on
    the view that makes use of the `AlbumsModel`.
    '''

    def __init__(self, cover_view, album_manager):
        super(AlbumShowingPolicy, self).__init__()

        self._cover_view = cover_view
        self._album_manager = album_manager
        self._model = album_manager.model
        self._visible_paths = None

        self._connect_signals()

    def _connect_signals(self):
        self._cover_view.props.vadjustment.connect('value-changed',
            self._viewport_changed)
        self._model.connect('album-updated', self._album_updated)
        self._model.connect('visual-updated', self._album_updated)

    def _viewport_changed(self, *args):
        visible_range = self._cover_view.get_visible_range()

        if visible_range:
            init, end = visible_range

            # i have to use the tree iter instead of the path to iterate since
            # for some reason path.next doesn't work whit the filtermodel
            tree_iter = self._model.store.get_iter(init)

            self._visible_paths = []

            while init and init != end:
                self._visible_paths.append(init)

                tree_iter = self._model.store.iter_next(tree_iter)
                init = self._model.store.get_path(tree_iter)

            self._visible_paths.append(end)

    def _album_updated(self, model, album_path, album_iter):
        # get the currently showing paths
        if not self._visible_paths:
            self._viewport_changed()

        if album_path and album_path in self._visible_paths:
            # if our path is on the viewport, emit the signal to update it
            self._model.store.row_changed(album_path, album_iter)


class AlbumManager(GObject.Object):
    '''
    Main construction that glues together the different managers, the loader
    and the model. It takes care of initializing all the system.

    :param plugin: `Peas.PluginInfo` instance.
    :param cover_view: `Gtk.IconView` where the album's cover are shown.
    '''
    # singleton instance
    instance = None

    # properties
    progress = GObject.property(type=float, default=0)

    def __init__(self, plugin, cover_view):
        super(AlbumManager, self).__init__()

        self.cover_view = cover_view
        self.db = plugin.shell.props.db

        self.model = AlbumsModel()

        # initialize managers
        self.loader = AlbumLoader(self)
        self.cover_man = CoverManager(plugin, self)
        self.text_man = TextManager(self)
        self._show_policy = AlbumShowingPolicy(cover_view, self)

        # connect signals
        self._connect_signals()

    def _connect_signals(self):
        '''
        Connects the manager to all the needed signals for it to work.
        '''
        # connect signals for updating the albums
        self.entry_changed_id = self.db.connect('entry-changed',
            self._entry_changed_callback)

        # connect signal to the loader so it shows the albums when it finishes
        self._load_finished_id = self.loader.connect('model-load-finished',
            self._load_finished_callback)

    def _entry_changed_callback(self, db, entry, changes):
        '''
        Callback called when a RhythDB entry is modified. Updates the albums
        accordingly to the changes made on the db.

        :param changes: GValueArray with the RhythmDBEntryChange made on the
        entry.
        '''
        print "CoverArtBrowser DEBUG - entry_changed_callback"

        track = self.loader._tracks[Track(entry).location]
        track.emit('modified')

        print "CoverArtBrowser DEBUG - end entry_changed_callback"

    def _load_finished_callback(self, *args):
        self.cover_man.load_covers()
