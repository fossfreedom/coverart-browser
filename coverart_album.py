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

from datetime import datetime, date
import os
import cgi
import tempfile
import gc

from gi.repository import RB
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
import cairo

from coverart_browser_prefs import GSetting
from coverart_utils import create_pixbuf_from_file_at_size
from coverart_utils import SortedCollection
from coverart_utils import idle_iterator
from coverart_utils import NaturalString
import coverart_rb3compat as rb3compat
from coverart_utils import uniquify_and_sort
from coverart_utils import dumpstack
from coverart_utils import check_lastfm
import rb



# default chunk of entries to process when loading albums
ALBUM_LOAD_CHUNK = 50

# default chunk of albums to process when loading covers
COVER_LOAD_CHUNK = 5


class Cover(GObject.Object):
    '''
    Cover of an Album. It may be initialized either by a file path to the image
    to use or by a previously allocated pixbuf.

    :param size: `int` size in pixels of the side of the cover (asuming a
        square-shapped cover).
    :param image: `str` containing a path of an image from where to create
        the cover.
    '''
    # signals
    __gsignals__ = {
        'resized': (GObject.SIGNAL_RUN_LAST, None, ())
    }

    def __init__(self, size, image):
        super(Cover, self).__init__()

        assert isinstance(image, str), "image should be a string"

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
        self.pixbuf = create_pixbuf_from_file_at_size(
            self.original, size, size)

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

        surface = cairo.ImageSurface(
            cairo.FORMAT_ARGB32, pix.get_width(), pix.get_height())
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

    __hash__ = GObject.__hash__

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
    def composer(self):
        return self.entry.get_string(RB.RhythmDBPropType.COMPOSER)

    @property
    def track_number(self):
        return self.entry.get_ulong(RB.RhythmDBPropType.TRACK_NUMBER)

    @property
    def disc_number(self):
        return self.entry.get_ulong(RB.RhythmDBPropType.DISC_NUMBER)

    @property
    def album_artist_sort(self):
        sort = self.entry.get_string(
            RB.RhythmDBPropType.ALBUM_ARTIST_SORTNAME_FOLDED) or \
               self.entry.get_string(RB.RhythmDBPropType.ALBUM_ARTIST_FOLDED) or \
               self.entry.get_string(RB.RhythmDBPropType.ARTIST_FOLDED)

        return NaturalString(sort)

    @property
    def album_sort(self):
        sort = self.entry.get_string(
            RB.RhythmDBPropType.ALBUM_SORTNAME_FOLDED) or \
               self.entry.get_string(RB.RhythmDBPropType.ALBUM_FOLDED)

        return NaturalString(sort)

    @property
    def is_saveable(self):
        return self.entry.get_entry_type().props.save_to_disk

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
        'modified': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'emptied': (GObject.SIGNAL_RUN_LAST, None, ()),
        'cover-updated': (GObject.SIGNAL_RUN_LAST, None, ())
    }

    __hash__ = GObject.__hash__

    def __init__(self, name, artist, cover):
        super(Album, self).__init__()

        self.name = name
        self.artist = artist
        self._album_artist_sort = None
        self._album_sort = None
        self._artists = None
        self._titles = None
        self._composers = None
        self._genres = None
        self._tracks = []
        self._cover = None
        self.cover = cover
        self._year = None
        self._rating = None
        self._duration = None

        self._signals_id = {}

    @property
    def album_artist_sort(self):
        if not self._album_artist_sort:
            self._album_artist_sort = uniquify_and_sort(
                [track.album_artist_sort for track in self._tracks])

        return self._album_artist_sort

    @property
    def album_sort(self):
        if not self._album_sort:
            self._album_sort = uniquify_and_sort(
                [track.album_sort for track in self._tracks])

        return self._album_sort

    @property
    def artists(self):
        if not self._artists:
            self._artists = ', '.join(set(
                [track.artist for track in self._tracks]))

        return self._artists

    @property
    def track_titles(self):
        if not self._titles:
            self._titles = ' '.join(set(
                [track.title for track in self._tracks]))

        return self._titles

    @property
    def composers(self):
        if not self._composers:
            composers = [track.composer for track in self._tracks if track.composer]
            if composers:
                self._composers = ' '.join(set(composers))

        return self._composers

    @property
    def year(self):
        if not self._year:
            real_years = [track.year for track in self._tracks if track.year != 0]

            if len(real_years) > 0:
                self._year = min(real_years)
            else:
                self._year = 0

        return self._year

    @property
    def real_year(self):
        ''' 
        return the calculated year e.g. 1989
        '''
        calc_year = self.year

        if calc_year == 0:
            calc_year = date.today().year
        else:
            calc_year = datetime.fromordinal(calc_year).year

        return calc_year

    @property
    def calc_year_sort(self):
        ''' 
        returns a str combinationi of real_year + album name
        '''

        return str(self.real_year) + self.name

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
        self._rating = None
        self.emit('modified')

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
        if not rating_threshold:
            # if no threshold is set, return all
            tracks = self._tracks
        else:
            # otherwise, only return the entries over the threshold
            tracks = [track for track in self._tracks
                      if track.rating >= rating_threshold]

        return sorted(tracks, key=lambda track: (track.disc_number, track.track_number))

    def add_track(self, track):
        '''
        Adds a track to the album.

        :param track: `Track` track to be added.
        '''
        self._tracks.append(track)
        ids = (track.connect('modified', self._track_modified),
               track.connect('deleted', self._track_deleted))

        self._signals_id[track] = ids
        self.emit('modified')

    def _track_modified(self, track):
        print("_track_modified")
        if track.album != self.name:
            self._track_deleted(track)
        else:
            self.emit('modified')

    def _track_deleted(self, track):
        print("_track_deleted")
        self._tracks.remove(track)

        #list(map(track.disconnect, self._signals_id[track]))
        for signal_id in self._signals_id[track]:
            track.disconnect(signal_id)

        del self._signals_id[track]

        if len(self._tracks) == 0:
            self.emit('emptied')
        else:
            self.emit('modified')

    def create_ext_db_key(self):
        '''
        Creates a `RB.ExtDBKey` from this album's tracks.
        '''
        return self._tracks[0].create_ext_db_key()

    def do_modified(self):
        self._album_artist = None
        self._album_artist_sort = None
        self._album_sort = None
        self._artists = None
        self._titles = None
        self._genres = None
        self._year = None
        self._rating = None
        self._duration = None
        self._composers = None

    def __str__(self):
        return self.artist + self.name

    def __eq__(self, other):
        return other and self.name == other.name and \
               self.artist == other.artist

    def __ne__(self, other):
        return not other or \
               self.name + self.artist != other.name + other.artist


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

            words = RB.search_fold(searchtext).split()
            params = list(map(RB.search_fold, [album.name, album.artist,
                                               album.artists, album.track_titles, album.composers]))
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

            return RB.search_fold(searchtext) in RB.search_fold(album.artist)

        return filt

    @classmethod
    def artist_filter(cls, searchtext=None):
        def filt(album):
            if not searchtext:
                return True

            return RB.search_fold(searchtext) in RB.search_fold(album.artists)

        return filt

    @classmethod
    def similar_artist_filter(cls, searchtext=None):
        def filt(album):
            # this filter is more complicated: for each word in the search
            # text, it tries to find at least one match on the params of
            # the album. If no match is given, then the album doesn't match
            if not searchtext:
                return True

            words = RB.search_fold(searchtext).split()
            params = list(map(RB.search_fold, [album.artist,
                                               album.artists]))
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
    def album_name_filter(cls, searchtext=None):
        def filt(album):
            if not searchtext:
                return True

            return RB.search_fold(searchtext) in RB.search_fold(album.name)

        return filt

    @classmethod
    def track_title_filter(cls, searchtext=None):
        def filt(album):
            if not searchtext:
                return True

            return RB.search_fold(searchtext) in RB.search_fold(
                album.track_titles)

        return filt

    @classmethod
    def composer_filter(cls, searchtext=None):
        def filt(album):
            if not searchtext:
                return True

            return RB.search_fold(searchtext) in RB.search_fold(
                album.composers)

        return filt

    @classmethod
    def genre_filter(cls, searchtext=None):
        def filt(album):
            if not searchtext:
                return True

            genres = RB.search_fold(' '.join(album.genres))
            return RB.search_fold(searchtext) in genres

        return filt

    @classmethod
    def model_filter(cls, model=None):
        if not model or not len(model):
            return lambda x: False

        albums = set()

        for row in model:
            entry = model[row.path][0]
            albums.add(Track(entry).album)

        def filt(album):
            return album.name in albums

        return filt

    @classmethod
    def decade_filter(cls, searchdecade=None):
        '''
        The year is in RATA DIE format so need to extract the year

        The searchdecade param can be None meaning all results
        or -1 for all albums older than our standard range which is 1930
        or an actual decade for 1930 to 2020
        '''

        def filt(album):
            if not searchdecade:
                return True

            if album.year == 0:
                year = date.today().year
            else:
                year = datetime.fromordinal(album.year).year

            year = int(round(year - 5, -1))

            if searchdecade > 0:
                return searchdecade == year
            else:
                return year < 1930

        return filt


AlbumFilters.keys = {
    'nay': AlbumFilters.nay_filter,
    'all': AlbumFilters.global_filter,
    'album_artist': AlbumFilters.album_artist_filter,
    'artist': AlbumFilters.artist_filter,
    'quick_artist': AlbumFilters.artist_filter,
    'composers': AlbumFilters.composer_filter,
    'similar_artist': AlbumFilters.similar_artist_filter,
    'album_name': AlbumFilters.album_name_filter,
    'track': AlbumFilters.track_title_filter,
    'genre': AlbumFilters.genre_filter,
    'model': AlbumFilters.model_filter,
    'decade': AlbumFilters.decade_filter
}

sort_keys = {
    'name': ('album_sort', 'album_sort'),
    'artist': ('album_artist_sort', 'album_artist_sort'),
    'year': ('year', 'album_sort'),
    'rating': ('rating', 'album_sort'),
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
        'filter-changed': ((GObject.SIGNAL_RUN_FIRST, None, ())),
        'album-added': ((GObject.SIGNAL_RUN_LAST, None, (object,)))
    }

    # list of columns names and positions on the TreeModel
    columns = {'tooltip': 0, 'pixbuf': 1, 'album': 2, 'markup': 3, 'show': 4}

    def __init__(self):
        super(AlbumsModel, self).__init__()

        self._iters = {}
        self._albums = SortedCollection(
            key=lambda album: getattr(album, 'name'))
        self._sortkey = {'type': 'name', 'order': True}

        self._tree_store = Gtk.ListStore(str, GdkPixbuf.Pixbuf, object, str,
                                         bool)

        # filters
        self._filters = {}

        # sorting idle call
        self._sort_process = None

        # create the filtered store that's used with the view
        self._filtered_store = self._tree_store.filter_new()
        self._filtered_store.set_visible_column(AlbumsModel.columns['show'])

    @property
    def store(self):
        return self._filtered_store

    @idle_iterator
    def _recreate_text(self):
        def process(album, data):
            tree_iter = self._iters[album.name][album.artist]['iter']
            markup = self.emit('generate-markup', album)

            self._tree_store.set(tree_iter, self.columns['markup'],
                                 markup)
            self._emit_signal(tree_iter, 'visual-updated')

        def error(exception):
            print('Error while recreating text: ' + str(exception))

        return ALBUM_LOAD_CHUNK, process, None, error, None

    def _album_modified(self, album):
        print("_album_modified")
        tree_iter = self._iters[album.name][album.artist]['iter']

        if self._tree_store.iter_is_valid(tree_iter):
            # only update if the iter is valid
            # generate and update values
            tooltip, pixbuf, album, markup, hidden = \
                self._generate_values(album)

            self._tree_store.set(tree_iter, self.columns['tooltip'], tooltip,
                                 self.columns['markup'], markup, self.columns['show'], hidden)

            # reorder the album
            new_pos = self._albums.reorder(album)

            if new_pos != -1:
                if (new_pos + 1) >= len(self._albums):
                    old_album = self._albums[new_pos - 1]
                    old_iter = \
                        self._iters[old_album.name][old_album.artist]['iter']
                    self._tree_store.move_after(tree_iter, old_iter)
                else:
                    old_album = self._albums[new_pos + 1]
                    old_iter = \
                        self._iters[old_album.name][old_album.artist]['iter']
                    self._tree_store.move_before(tree_iter, old_iter)

            # inform that the album is updated
            print("album modified")
            print(album)
            self._emit_signal(tree_iter, 'album-updated')

    def _cover_updated(self, album):
        tree_iter = self._iters[album.name][album.artist]['iter']

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

        # generate necessary values
        values = self._generate_values(album)
        # insert the values
        tree_iter = self._tree_store.insert(self._albums.insert(album), values)
        # connect signals
        ids = (album.connect('modified', self._album_modified),
               album.connect('cover-updated', self._cover_updated),
               album.connect('emptied', self.remove))
        if not album.name in self._iters:
            self._iters[album.name] = {}
        self._iters[album.name][album.artist] = {'album': album,
                                                 'iter': tree_iter, 'ids': ids}
        self.emit('album-added', album)
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
        print("album model remove")
        print(album)
        self._albums.remove(album)
        self._tree_store.remove(self._iters[album.name][album.artist]['iter'])

        # disconnect signals
        for sig_id in self._iters[album.name][album.artist]['ids']:
            album.disconnect(sig_id)

        del self._iters[album.name][album.artist]

    def contains(self, album_name, album_artist):
        '''
        Indicates if the model contains a specific album.

        :param album_name: `str` name of the album.
        '''
        return album_name in self._iters \
            and album_artist in self._iters[album_name]

    def get(self, album_name, album_artist):
        '''
        Returns the requested album.

        :param album_name: `str` name of the album.
        '''
        return self._iters[album_name][album_artist]['album']

    def get_from_dbentry(self, entry):
        '''
        Returns the album containing the track corresponding to rhythmdbentry
        
        :param entry: `RhythmDBEntry`
        '''

        album_artist = entry.get_string(RB.RhythmDBPropType.ALBUM_ARTIST)
        album_artist = album_artist if album_artist else entry.get_string(RB.RhythmDBPropType.ARTIST)
        album_name = entry.get_string(RB.RhythmDBPropType.ALBUM)

        return self._iters[album_name][album_artist]['album']

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

    def get_from_ext_db_key(self, key):
        '''
        Returns the requested album.

        :param key: ext_db_key
        '''
        # get the album name and artist
        name = key.get_field('album')
        artist = key.get_field('artist')

        # first check if there's a direct match
        album = self.get(name, artist) if self.contains(name, artist) else None

        if not album:
            # get all the albums with the given name and look for a match
            albums = [artist['album'] for artist in list(self._iters[name].values())]

            for curr_album in albums:
                if key.matches(curr_album.create_ext_db_key()):
                    album = curr_album
                    break

        return album

    def get_path(self, album):
        return self._filtered_store.convert_child_path_to_path(
            self._tree_store.get_path(
                self._iters[album.name][album.artist]['iter']))

    def find_first_visible(self, filter_key, filter_arg, start=None,
                           backwards=False):
        album_filter = AlbumFilters.keys[filter_key](filter_arg)

        albums = reversed(self._albums) if backwards else self._albums
        ini = albums.index(start) + 1 if start else 0

        for i in range(ini, len(albums)):
            album = albums[i]

            if album_filter(album) and self._album_filter(album):
                return album

        return None

    def show(self, album, show):
        '''
        Unfilters an album, making it visible to the publicly available model's
        `Gtk.TreeModel`

        :param album: `Album` to show or hide.
        :param show: `bool` indcating whether to show(True) or hide(False) the
            album.
        '''
        album_iter = self._iters[album.name][album.artist]['iter']

        if self._tree_store.iter_is_valid(album_iter):
            self._tree_store.set_value(album_iter, self.columns['show'], show)

    @idle_iterator
    def _sort(self):
        def process(album, data):
            values = self._generate_values(album)

            tree_iter = self._tree_store.append(values)
            self._iters[album.name][album.artist]['iter'] = tree_iter

        def error(exception):
            print('Error(1) while adding albums to the model: ' + str(exception))

        def finish(data):
            self._sort_process = None
            self.remove_filter('nay')

        return ALBUM_LOAD_CHUNK, process, None, error, finish

    def sort(self):
        '''
        Changes the sorting strategy for the model.
        '''

        gs = GSetting()
        source_settings = gs.get_setting(gs.Path.PLUGIN)
        key = source_settings[gs.PluginKey.SORT_BY]
        order = source_settings[gs.PluginKey.SORT_ORDER]

        print("current")
        print(self._sortkey)

        print("registry")
        print(key)
        print(order)

        if key == self._sortkey['type']:
            key = None
        else:
            self._sortkey['type'] = key

        if order != self._sortkey['order']:
            reverse = True
            self._sortkey['order'] = order
        else:
            reverse = False

        def key_function(album):
            keys = [getattr(album, prop) for prop in props]
            return keys

        if not key and not reverse:
            print("nothing to sort")
            return

        print(key)
        print(reverse)
        if key:
            props = sort_keys[key]
            self._albums.key = key_function

        if reverse:
            self._albums = reversed(self._albums)

        self._tree_store.clear()

        # add the nay filter
        self.replace_filter('nay', refilter=False)

        if self._sort_process:
            # stop the previous sort process if there's one
            self._sort_process.stop()

        # load the albums back to the model
        self._sort_process = self._sort(iter(self._albums))

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
        pos = 0
        for show_result in list(map(self._album_filter, self._albums)):
            self.show(self._albums[pos], show_result)
            pos = pos + 1

    def _album_filter(self, album):
        for f in list(self._filters.values()):
            if not f(album):
                return False

        return True

    def recreate_text(self):
        '''
        Forces the recreation and update of the markup text for each album.
        '''
        self._recreate_text(iter(self._albums))


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

    @idle_iterator
    def _load_albums(self):
        def process(row, data):
            entry = data['model'][row.path][0]

            # allocate the track
            track = Track(entry, self._album_manager.db)
            self._tracks[track.location] = track

            album_name = track.album
            album_artist = track.album_artist
            album_artist = album_artist if album_artist else track.artist

            if album_name not in data['albums']:
                data['albums'][album_name] = {}

            if album_artist in data['albums'][album_name]:
                album = data['albums'][album_name][album_artist]
            else:
                album = Album(album_name, album_artist,
                              self._album_manager.cover_man.unknown_cover)
                data['albums'][album_name][album_artist] = album

            album.add_track(track)

        def after(data):
            # update the progress
            data['progress'] += ALBUM_LOAD_CHUNK

            self._album_manager.progress = data['progress'] / data['total']

        def error(exception):
            print('Error processing entries: ' + str(exception))

        def finish(data):
            self._album_manager.progress = 1
            self.emit('albums-load-finished', data['albums'])

        return ALBUM_LOAD_CHUNK, process, after, error, finish

    @idle_iterator
    def _load_model(self):
        def process(albums, data):
            # add  the album to the model
            for album in list(albums.values()):
                self._album_manager.model.add(album)

        def after(data):
            data['progress'] += ALBUM_LOAD_CHUNK

            # update the progress
            self._album_manager.progress = 1 - data['progress'] / data['total']

        def error(exception):
            dumpstack("Something awful happened!")
            print('Error(2) while adding albums to the model: ' + str(exception))

        def finish(data):
            self._album_manager.progress = 0
            self.emit('model-load-finished')
            return False

        return ALBUM_LOAD_CHUNK, process, after, error, finish

    def _entry_changed_callback(self, db, entry, changes):
        print("CoverArtBrowser DEBUG - entry_changed_callback")
        # NOTE: changes are packed in array of rhythmdbentrychange

        def analyse_change(change):
            print(change.prop)
            if change.prop is RB.RhythmDBPropType.ALBUM \
                    or change.prop is RB.RhythmDBPropType.ALBUM_ARTIST \
                    or change.prop is RB.RhythmDBPropType.ARTIST \
                    or change.prop is RB.RhythmDBPropType.ALBUM_SORTNAME \
                    or change.prop is RB.RhythmDBPropType.ALBUM_ARTIST_SORTNAME:
                # called when the album of a entry is modified
                track.emit('deleted')
                track.emit('modified')
                print("change prop album or artist")
                self._allocate_track(track)

            elif change.prop is RB.RhythmDBPropType.HIDDEN:
                # called when an entry gets hidden (e.g.:the sound file is
                # removed.
                if changes.new:
                    print("change prop new")
                    track.emit('deleted')
                else:
                    print("change prop dunno")
                    self._allocate_track(track)

        # look at all the changes and update the albums accordingly
        track = self._tracks[Track(entry).location]

        #RB3 has a simple rhythmdbentrychange array to deal with so we
        #just need to loop each element of the array

        for change in changes:
            analyse_change(change)

        print("CoverArtBrowser DEBUG - end entry_changed_callback")

    def _entry_added_callback(self, db, entry):
        print("CoverArtBrowser DEBUG - entry_added_callback")
        self._allocate_track(Track(entry, db))

        print("CoverArtBrowser DEBUG - end entry_added_callback")

    def _entry_deleted_callback(self, db, entry):
        print("CoverArtBrowser DEBUG - entry_deleted_callback")
        prototype = Track(entry).location

        if prototype in self._tracks:
            # gotta check if the track is loaded first
            track = self._tracks[prototype]
            del self._tracks[track.location]

            track.emit('deleted')

        print("CoverArtBrowser DEBUG - end entry_deleted_callback")

    def _allocate_track(self, track):
        if track.duration > 0 and track.is_saveable:
            # only allocate the track if it's a valid track
            self._tracks[track.location] = track

            album_name = track.album
            album_artist = track.album_artist
            album_artist = album_artist if album_artist else track.artist

            if self._album_manager.model.contains(album_name, album_artist):
                print("allocate track - contains")
                album = self._album_manager.model.get(album_name, album_artist)
                print(album)
                album.add_track(track)
            else:
                print("allocate track - does not contain")
                album = Album(album_name, album_artist,
                              self._album_manager.cover_man.unknown_cover)
                print(album)
                album.add_track(track)
                self._album_manager.cover_man.load_cover(album)
                self._album_manager.model.add(album)

    def load_albums(self, query_model):
        '''
        Loads and creates `Track` instances for all entries on query_model,
        assigning them into their correspondant `Album`.
        '''
        print("CoverArtBrowser DEBUG - load_albums")

        self._load_albums(iter(query_model), albums={}, model=query_model,
                          total=len(query_model), progress=0.)

        print("CoverArtBrowser DEBUG - load_albums finished")

    def do_albums_load_finished(self, albums):
        # load the albums to the model
        self._album_manager.model.replace_filter('nay')
        self._load_model(iter(list(albums.values())), total=len(albums), progress=0.)

    def do_model_load_finished(self):
        self._album_manager.model.remove_filter('nay')


class CoverRequester(GObject.Object):
    def __init__(self, cover_db):
        super(CoverRequester, self).__init__()

        self._cover_db = cover_db
        self.unknown_cover = None
        self._callback = None
        self._queue = []
        self._queue_id = 0
        self._running = False
        self._stop = False

    def add_to_queue(self, coverobjects, callback):
        ''' Adds coverobjects to the queue if they're not already there. '''
        self._queue.extend(
            [coverobject for coverobject in coverobjects if coverobject not in self._queue])

        self._start_process(callback)

    def replace_queue(self, coverobjects, callback):
        ''' Completely replace the current queue. '''
        self._queue = coverobjects

        self._start_process(callback)

    def _start_process(self, callback):
        ''' Starts the queue processing if it isn't running already '''
        if not self._running:
            self._callback = callback
            self._running = True
            self._process_queue()

    def _process_queue(self):
        '''
        Main method that process the queue.
        First, it tries to adquire a lock on the queue, and if it can, pops
        the next element of the queue and process it.
        The lock makes sure that only one request is done at a time, and
        successfully ignores false timeouts or strand callbacks.
        '''
        # process the next element in the queue
        while self._queue:
            coverobject = self._queue.pop(0)

            if coverobject.cover is self.unknown_cover:
                break
        else:
            coverobject = None

        if coverobject:
            # inform the current coverobject being searched
            self._callback(coverobject)

            # start the request
            self._queue_id += 1
            self._search_for_cover(coverobject, self._queue_id)

            # add a timeout to the request
            Gdk.threads_add_timeout_seconds(GLib.PRIORITY_DEFAULT_IDLE, 40,
                                            self._next, self._queue_id)
        else:
            # if there're no more elements, clean the state of the requester
            self._running = False
            self._callback(None)

    def _search_for_cover(self, coverobject, search_id):
        '''
        Activelly requests a cover to the cover_db, calling
        the callback given once the process finishes (since it generally is
        asynchronous).
        For more information on the callback arguments, check
        `RB.ExtDB.request` documentation.

        :param coverobject: covertype for which search the cover.
        '''
        # create a key and request the cover
        key = coverobject.create_ext_db_key()
        provides = self._cover_db.request(key, self._next, search_id)

        if not provides:
            # in case there is no provider, call the callback immediately
            self._next(search_id)

    def _next(self, *args):
        ''' Advances to the next coverobject to process. '''
        # get the id of the search
        search_id = args[-1]
        if search_id == self._queue_id:
            # only process the next element if the search_id is the same as
            # the current id. Otherwise, this is a invalid call
            self._process_queue()

    def stop(self):
        ''' Clears the queue, forcing the requester to stop. '''
        del self._queue[:]


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
    has_finished_loading = False
    force_lastfm_check = False
    cover_size = GObject.property(type=int, default=0)

    def __init__(self, plugin, manager):
        super(CoverManager, self).__init__()
        #self.cover_db = None to be defined by inherited class
        self._manager = manager
        self._requester = CoverRequester(self.cover_db)

        self.unknown_cover = None  #to be defined by inherited class
        self.album_manager = None  #to be defined by inherited class

        # connect the signal to update cover arts when added
        self.req_id = self.cover_db.connect('added',
                                            self.coverart_added_callback)
        self.connect('load-finished', self._on_load_finished)

    def _on_load_finished(self, *args):
        self.has_finished_loading = True

    @idle_iterator
    def _load_covers(self):
        def process(coverobject, data):
            self.load_cover(coverobject)

        def finish(data):
            self.album_manager.progress = 1
            gc.collect()
            self.emit('load-finished')

        def error(exception):
            print('Error while loading covers: ' + str(exception))

        def after(data):
            data['progress'] += COVER_LOAD_CHUNK

            # update the progress
            self.album_manager.progress = data['progress'] / data['total']

        return COVER_LOAD_CHUNK, process, after, error, finish

    def create_unknown_cover(self, plugin):
        # set the unknown cover to the requester to make comparisons
        self._requester.unknown_cover = self.unknown_cover

    def create_cover(self, image):
        return Cover(self.cover_size, image)

    def coverart_added_callback(self, ext_db, key, path, pixbuf):
        # use the name to get the album and update it's cover
        if pixbuf:
            coverobject = self._manager.model.get_from_ext_db_key(key)

            if coverobject:
                coverobject.cover = self.create_cover(path)

    def load_cover(self, coverobject):
        '''
        Tries to load an Album's cover. If no cover is found upon lookup,
        the unknown cover is used.
        This method doesn't actively tries to find a cover, for that you should
        use the search_cover method.

        :param album: `Album` for which load the cover.
        '''
        # create a key and look for the art location
        key = coverobject.create_ext_db_key()
        art_location = self.cover_db.lookup(key)

        # try to create a cover
        if art_location:
            coverobject.cover = self.create_cover(art_location)
        else:
            coverobject.cover = self.unknown_cover

    def load_covers(self):
        '''
        Loads all the covers for the model's albums.
        '''
        # get all the coverobjects
        coverobjects = self._manager.model.get_all()

        self._load_covers(iter(coverobjects), total=len(coverobjects), progress=0.)

    def search_covers(self, coverobjects=None, callback=lambda *_: None):
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
        if not check_lastfm(self.force_lastfm_check):
            # display error message and quit
            dialog = Gtk.MessageDialog(None,
                                       Gtk.DialogFlags.MODAL,
                                       Gtk.MessageType.INFO,
                                       Gtk.ButtonsType.OK,
                                       _("Enable LastFM plugin and log in first"))

            dialog.run()
            dialog.destroy()

            return

        if coverobjects is None:
            self._requester.replace_queue(
                list(self._manager.model.get_all()), callback)
        else:
            self._requester.add_to_queue(coverobjects, callback)

    def cancel_cover_request(self):
        '''
        Cancel the current cover request, if there is one running.
        '''
        self._requester.stop()

    def update_pixbuf_cover(self, coverobject, pixbuf):
        pass

    def update_cover(self, coverobject, pixbuf=None, uri=None):
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
            self.update_pixbuf_cover(coverobject, pixbuf)
        elif uri:
            parsed = rb3compat.urlparse(uri)

            if parsed.scheme == 'file':
                # local file, load it on a pixbuf and assign it
                path = rb3compat.url2pathname(uri.strip()).replace('file://', '')

                if os.path.exists(path):
                    cover = GdkPixbuf.Pixbuf.new_from_file(path)
                    self.update_cover(coverobject, cover)
            else:
                # assume is a remote uri and we have to retrieve the data
                def cover_update(data, coverobject):
                    # save the cover on a temp file and open it as a pixbuf
                    with tempfile.NamedTemporaryFile(mode='wb') as tmp:
                        try:
                            tmp.write(data)
                            tmp.flush()
                            cover = GdkPixbuf.Pixbuf.new_from_file(tmp.name)

                            # set the new cover
                            self.update_cover(coverobject, cover)
                        except:
                            print("The URI doesn't point to an image or " + \
                                  "the image couldn't be opened.")

                async = rb.Loader()
                async.get_url(uri, cover_update, coverobject)


class AlbumCoverManager(CoverManager):
    # properties
    add_shadow = GObject.property(type=bool, default=False)
    shadow_image = GObject.property(type=str, default="above")

    def __init__(self, plugin, album_manager):
        self.cover_db = RB.ExtDB(name='album-art')
        super(AlbumCoverManager, self).__init__(plugin, album_manager)

        self.album_manager = album_manager
        self._connect_properties()
        self._connect_signals(plugin)

        # create unknown cover and shadow for covers
        self.create_unknown_cover(plugin)

    def _connect_signals(self, plugin):
        self.connect('notify::cover-size', self._on_cover_size_changed)
        self.connect('notify::add-shadow', self._on_add_shadow_changed, plugin)
        self.connect('notify::shadow-image', self._on_add_shadow_changed,
                     plugin)

    def _connect_properties(self):
        gs = GSetting()
        setting = gs.get_setting(gs.Path.PLUGIN)

        setting.bind(gs.PluginKey.COVER_SIZE, self, 'cover_size',
                     Gio.SettingsBindFlags.GET)
        setting.bind(gs.PluginKey.ADD_SHADOW, self, 'add_shadow',
                     Gio.SettingsBindFlags.GET)
        setting.bind(gs.PluginKey.SHADOW_IMAGE, self, 'shadow_image',
                     Gio.SettingsBindFlags.GET)

    def create_unknown_cover(self, plugin):
        # create the unknown cover
        self._shadow = Shadow(self.cover_size,
                              rb.find_plugin_file(plugin, 'img/album-shadow-%s.png' %
                                                          self.shadow_image))
        self.unknown_cover = self.create_cover(
            rb.find_plugin_file(plugin, 'img/rhythmbox-missing-artwork.svg'))

        super(AlbumCoverManager, self).create_unknown_cover(plugin)

    def create_cover(self, image):
        if self.add_shadow:
            cover = ShadowedCover(self._shadow, image)
        else:
            cover = Cover(self.cover_size, image)

        return cover

    def _on_add_shadow_changed(self, obj, prop, plugin):
        # update the unknown_cover
        self.create_unknown_cover(plugin)

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
        albums = self.album_manager.model.get_all()

        self._resize_covers(iter(albums), total=len(albums), progress=0.)

    def update_item_width(self):
        self.album_manager.current_view.resize_icon(self.cover_size)

    def update_pixbuf_cover(self, coverobject, pixbuf):
        # if it's a pixbuf, assign it to all the artist for the album
        key = RB.ExtDBKey.create_storage('album', coverobject.name)
        key.add_field('artist', coverobject.artist)

        self.cover_db.store(key, RB.ExtDBSourceType.USER_EXPLICIT,
                            pixbuf)

        for artist in coverobject.artists.split(', '):
            key = RB.ExtDBKey.create_storage('album', coverobject.name)
            key.add_field('artist', artist)

            self.cover_db.store(key, RB.ExtDBSourceType.USER_EXPLICIT,
                                pixbuf)

    @idle_iterator
    def _resize_covers(self):
        def process(coverobject, data):
            coverobject.cover.resize(self.cover_size)

        def finish(data):
            self.album_manager.progress = 1
            self.emit('load-finished')

        def error(exception):
            print("Error while resizing covers: " + str(exception))

        def after(data):
            data['progress'] += COVER_LOAD_CHUNK

            # update the progress
            self.album_manager.progress = data['progress'] / data['total']

        return COVER_LOAD_CHUNK, process, after, error, finish


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

    def __init__(self, album_manager):
        super(TextManager, self).__init__()

        self._album_manager = album_manager
        self._current_view = self._album_manager.current_view

        # connect properties and signals
        self._connect_signals()
        self._connect_properties()

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

    def _on_notify_display_text_ellipsize(self, *args):
        '''
        Callback called when one of the properties related with the ellipsize
        option is changed.
        '''
        self._album_manager.model.recreate_text()

    def _generate_tooltip(self, model, album):
        '''
        Utility function that creates the tooltip for this album to set into
        the model.
        '''
        return cgi.escape(rb3compat.unicodeencode(_('%s by %s'), 'utf-8') % (album.name,
                                                                             album.artists))

    def _generate_markup_text(self, model, album):
        '''
        Utility function that creates the markup text for this album to set
        into the model.
        '''
        # we use unicode to avoid problems with non ascii albums
        name = rb3compat.unicodestr(album.name, 'utf-8')
        artist = rb3compat.unicodestr(album.artist, 'utf-8')

        if self.display_text_ellipsize_enabled:
            ellipsize = self.display_text_ellipsize_length

            if len(name) > ellipsize:
                name = name[:ellipsize] + '...'

            if len(artist) > ellipsize:
                artist = artist[:ellipsize] + '...'

        name = rb3compat.unicodeencode(name, 'utf-8')
        artist = rb3compat.unicodeencode(artist, 'utf-8')

        # escape odd chars
        artist = GLib.markup_escape_text(artist)
        name = GLib.markup_escape_text(name)

        # markup format
        markup = "<span font='%d'><b>%s</b>\n<i>%s</i></span>"
        return markup % (self.display_font_size, name, artist)


class AlbumManager(GObject.Object):
    '''
    Main construction that glues together the different managers, the loader
    and the model. It takes care of initializing all the system.

    :param plugin: `Peas.PluginInfo` instance.
    :param current_view: `AlbumView` where the album's cover are shown.
    '''
    # singleton instance
    instance = None

    # properties
    progress = GObject.property(type=float, default=0)

    # signals
    __gsignals__ = {
        'sort': (GObject.SIGNAL_RUN_LAST, None, (object,))
    }


    def __init__(self, plugin, current_view):
        super(AlbumManager, self).__init__()

        self.current_view = current_view
        self.db = plugin.shell.props.db

        self.model = AlbumsModel()

        # initialize managers
        self.loader = AlbumLoader(self)
        self.cover_man = AlbumCoverManager(plugin, self)
        from coverart_artistview import ArtistManager

        self.artist_man = ArtistManager(plugin, self, plugin.shell)
        self.text_man = TextManager(self)
        self._show_policy = current_view.show_policy.initialise(self)

        # connect signals
        self._connect_signals()

    def _connect_signals(self):
        '''
        Connects the manager to all the needed signals for it to work.
        '''
        # connect signal to the loader so it shows the albums when it finishes
        self._load_finished_id = self.loader.connect('model-load-finished',
                                                     self._load_finished_callback)
        self.connect('sort', self._sort_album)

    def _sort_album(self, widget, param):
        toolbar_type = param

        if not toolbar_type or toolbar_type == "album":
            self.model.sort()

    def _load_finished_callback(self, *args):
        self.artist_man.loader.load_artists()
        self.cover_man.load_covers()
