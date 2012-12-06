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
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf

from coverart_browser_prefs import GSetting
from coverart_utils import SortedCollection
from urlparse import urlparse

import urllib
import os
import cgi
import tempfile
import rb


# default chunk of albums to process
DEFAULT_LOAD_CHUNK = 15


class Cover(GObject.Object):
    ''' Cover of an Album. '''

    __gsignals__ = {
        'resized': (GObject.SIGNAL_RUN_LAST, None, ())
        }

    def __init__(self, size, file_path=None, pixbuf=None):
        '''
        Initialises a cover, creating it's pixbuf or adapting a given one.
        Either a file path or a pixbuf should be given to it's correct
        initialization.
        '''
        super(Cover, self).__init__()

        if pixbuf:
            self.original = pixbuf
            self.pixbuf = pixbuf.scale_simple(size, size,
                 GdkPixbuf.InterpType.BILINEAR)
        else:
            self.original = file_path
            self.pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(file_path,
                size, size)

        self.size = size

    def resize(self, size):
        '''
        Resizes the cover's pixbuf.
        '''
        if self.size == size:
            return

        del self.pixbuf

        try:
            self.pixbuf = self.original.scale_simple(size, size,
                 GdkPixbuf.InterpType.BILINEAR)
        except:
            self.pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(self.original,
                size, size)

        self.size = size

        self.emit('resized')


class Track(GObject.Object):

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
        return self.entry.create_ext_db_key(RB.RhythmDBPropType.ALBUM)


class Album(GObject.Object):
    '''
    An specific album defined by it's name and with the ability to obtain it's
    cover and set itself in a treemodel.
    '''
    # signals
    __gsignals__ = {
        'modified': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'emptied': (GObject.SIGNAL_RUN_LAST, None, ()),
        'cover-updated': (GObject.SIGNAL_RUN_LAST, None, ())
        }

    def __init__(self, name, cover):
        '''
        Initialises the album with it's name and artist.
        Initially, the album haves no cover, so the default Unknown cover is
        asigned.
        '''
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
        '''
        Returns this album's artist.
        '''
        if not self._album_artist:
            multiple_artist = False

            for track in self._tracks:
                if not self._album_artist:
                    self._album_artist = track.album_artist
                elif track.album_artist != self._album_artist:
                    multiple_artist = True
                    break

            if not self._album_artist or multiple_artist:
                self._album_artist = _('Various Artist')

        return self._album_artist

    @property
    def artists(self):
        '''
        Returns a string representation of the conjuction of all the artist
        that have entries on this album.
        '''
        if not self._artists:
            self._artists = ', '.join(
                set([track.artist for track in self._tracks]))

        return self._artists

    @property
    def track_titles(self):
        '''
        Returns a string representation of the conjunction of all the track
        titles that have entries on this album.
        '''
        if not self._titles:
            self._titles = ' '.join(
                set([track.title for track in self._tracks]))

        return self._titles

    @property
    def year(self):
        '''
        Returns this album's year.
        '''
        if not self._year:
            self._year = min([track.year for track in self._tracks])

        return self._year

    @property
    def genres(self):
        if not self._genres:
            self._genres = ' '.join(
                set([track.genre for track in self._tracks]))

        return self._genres

    @property
    def rating(self):
        '''
        Returns this album's rating.
        '''
        if not self._rating:
            ratings = [track.rating for track in self._tracks
                if track.rating != 0]

            if len(ratings) > 0:
                self._rating = float(sum(ratings)) / len(ratings)
            else:
                self._rating = 0

        return self._rating

    @rating.setter
    def rating(self, new_rating):
        '''
        sets all the RBRhythmDBEntry's for the album
        to have the given rating
        '''
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
        only those tracks over the threshold will be returned.
        '''
        if not rating_threshold or not self.rating:
            # if no song has rating, or no threshold is set, return all
            tracks = self._tracks

        else:
            # otherwise, only return the entries over the threshold
            tracks = []

            for track in self._tracks:
                if track.rating > rating_threshold:
                    tracks.append(track)

        return sorted(tracks, key=lambda track: track.track_number)

    def add_track(self, track):
        ''' Appends an track to the album's tracks list. '''
        self._tracks.append(track)

        ids = (track.connect('modified', self._track_modified),
            track.connect('deleted', self._track_deleted))

        self._signals_id[track] = ids

        self.emit('modified')

    def _track_modified(self, track):
        if track.album != self.name:
            self._track_deleted(track)

        self.emit('modified')

    def _track_deleted(self, track):
        self._tracks.remove(track)

        mod_id, del_id = self._signals_id[track]
        del self._signals_id[track]

        track.disconnect(mod_id)
        track.disconnect(del_id)

        if len(self._tracks) == 0:
            self.emit('emptied')
        else:
            self.emit('modified')

    def create_ext_db_key(self):
        return self._tracks[0].create_ext_db_key()

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
    def global_filter(cls, searchtext=''):
        def filt(album):
            # this filter is more complicated: for each word in the search
            # text, it tries to find at least one match on the params of
            # the album. If no match is given, then the album doesn't match
            if searchtext == "":
                return True

            words = searchtext.split()
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
    def album_artist_filter(cls, searchtext=''):
        def filt(album):
            if searchtext == "":
                return True

            return searchtext.lower() in album.album_artist.lower()

        return filt

    @classmethod
    def artist_filter(cls, searchtext=''):
        def filt(album):
            if searchtext == "":
                return True

            return searchtext.lower() in album.artists.lower()

        return filt

    @classmethod
    def album_name_filter(cls, searchtext=''):
        def filt(album):
            if searchtext == "":
                return True

            return searchtext.lower() in album.name.lower()

        return filt

    @classmethod
    def track_title_filter(cls, searchtext=''):
        def filt(album):
            if searchtext == "":
                return True

            return searchtext.lower() in album.track_titles

        return filt

    @classmethod
    def genre_filter(cls, searchtext=''):
        def filt(album):
            if searchtext == "":
                return True

            return searchtext in album.genres

        return filt

AlbumFilters.keys = {'nay': AlbumFilters.nay_filter,
        'all': AlbumFilters.global_filter,
        'album_artist': AlbumFilters.album_artist_filter,
        'artist': AlbumFilters.artist_filter,
        'album_name': AlbumFilters.album_name_filter,
        'track': AlbumFilters.track_title_filter,
        'genre': AlbumFilters.genre_filter
        }


class AlbumsModel(GObject.Object):

    # signals
    __gsignals__ = {
        'generate-tooltip': (GObject.SIGNAL_RUN_LAST, str, (object,)),
        'generate-markup': (GObject.SIGNAL_RUN_LAST, str, (object,)),
        'album-updated': ((GObject.SIGNAL_RUN_LAST, None, (object, object))),
        'filter-changed': ((GObject.SIGNAL_RUN_FIRST, None, ()))
        }

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
        self._asc = False

        # create the filtered store that's used with the view
        self._filtered_store = self._tree_store.filter_new()
        self._filtered_store.set_visible_column(4)

    @property
    def store(self):
        return self._filtered_store

    def _album_modified(self, album):
        tree_iter = self._iters[album.name][1]

        if self._tree_store.iter_is_valid(tree_iter):
            # only update if the iter is valid
            tooltip = self.emit('generate-tooltip', album)
            markup = self.emit('generate-markup', album)
            show = self._album_filter(album)

            self._tree_store.set(tree_iter, self.columns['tooltip'], tooltip,
                self.columns['markup'], markup, self.columns['show'], show)

            self._album_updated(tree_iter)

    def _cover_updated(self, album):
        tree_iter = self._iters[album.name][1]

        if self._tree_store.iter_is_valid(tree_iter):
            # only update if the iter is valid
            pixbuf = album.cover.pixbuf

            self._tree_store.set_value(tree_iter, self.columns['pixbuf'],
                pixbuf)

            self._album_updated(tree_iter)

    def _album_updated(self, tree_iter):
        # we get the filtered path and iter since that's what the outside world
        # interacts with
        tree_path = self._filtered_store.convert_child_path_to_path(
            self._tree_store.get_path(tree_iter))
        tree_iter = self._filtered_store.get_iter(tree_path)

        self.emit('album-updated', tree_path, tree_iter)

    def add(self, album):
        '''
        Add album to the tree model. For default, the info is assigned
        in the next order:
            column 0 -> string containing the album name and artist
            column 1 -> pixbuf of the album's cover.
            column 2 -> instance of the album itself.
            column 3 -> markup text showed under the cover.
            column 4 -> boolean that indicates if the row should be shown
        '''
        # generate necesary values
        values = self._generate_values(album)

        # insert the values
        tree_iter = self._tree_store.insert(self._albums.insert(album), values)

        # connect signals
        ids = (album.connect('modified', self._album_modified),
            album.connect('cover-updated', self._cover_updated),
            album.connect('emptied', self.remove))

        self._iters[album.name] = [album, tree_iter, ids]

        return tree_iter

    def _generate_values(self, album):
        tooltip = self.emit('generate-tooltip', album)
        markup = self.emit('generate-markup', album)
        pixbuf = album.cover.pixbuf
        hidden = self._album_filter(album)

        return tooltip, pixbuf, album, markup, hidden

    def remove(self, album):
        ''' Removes this album from it's model. '''
        self._albums.remove(album)
        self._tree_store.remove(self._iters[album.name][1])

        # disconnect signals
        for sig_id in self._iters[album.name][2]:
            album.disconnect(sig_id)

        del self._iters[album.name]

    def contains(self, album_name):
        return album_name in self._iters

    def get(self, album_name):
        return self._iters[album_name][0]

    def get_all(self):
        return self._albums

    def get_from_path(self, path):
        return self._filtered_store[path][2]

    def show(self, album, show):
        self._tree_store.set_value(self._iters[album.name][1],
                self.columns['show'], show)

    def sort(self, key, asc=False):
        self._albums.key = lambda album: getattr(album, key)

        if asc != self._asc:
            self._albums = reversed(self._albums)

        self._asc = asc

        self._tree_store.clear()

        def idle_add_albums(albums_iter):
            for i in range(DEFAULT_LOAD_CHUNK):
                try:
                    album = albums_iter.next()
                    values = self._generate_values(album)

                    tree_iter = self._tree_store.append(values)
                    self._iters[album.name][1] = tree_iter

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

    def replace_filter(self, filter_key, filter_text='', refilter=True):
        self._filters[filter_key] = AlbumFilters.keys[filter_key](filter_text)

        if refilter:
            self.emit('filter-changed')

    def remove_filter(self, filter_key, refilter=True):
        if filter_key in self._filters:
            del self._filters[filter_key]

            if refilter:
                self.emit('filter-changed')

    def clear_filters(self):
        if self._filters:
            self._filters.clear()

            self.emit('filter-changed')

    def do_filter_changed(self):
        for album in self._albums:
            self.show(album, self._album_filter(album))

    def _album_filter(self, album):
            for f in self._filters.values():
                if not f(album):
                    return False

            return True


class AlbumLoader(GObject.Object):
    '''
    Utility class that manages the albums created for the coverart browser's
    source.
    '''
    # signals
    __gsignals__ = {
        'albums-load-finished': (GObject.SIGNAL_RUN_LAST, None, (object,)),
        'model-load-finished': (GObject.SIGNAL_RUN_LAST, None, ())
        }

    def __init__(self, album_manager):
        '''
        Initialises the loader, getting the needed objects from the plugin and
        saving the model that will be used to assign the loaded albums.
        '''
        super(AlbumLoader, self).__init__()

        self._album_manager = album_manager
        self._tracks = {}

        self._connect_signals()

    def _connect_signals(self):
        '''
        Connects the loader to all the needed signals for it to work.
        '''
        # connect signals for updating the albums
        self.entry_changed_id = self._album_manager.db.connect('entry-changed',
            self._entry_changed_callback)
        self.entry_added_id = self._album_manager.db.connect('entry-added',
            self._entry_added_callback)
        self.entry_deleted_id = self._album_manager.db.connect('entry-deleted',
            self._entry_deleted_callback)

    def _entry_changed_callback(self, db, entry, changes):
        '''
        Callback called when a RhythDB entry is modified. Loads/Unloads albums
        if necesary

        :param changes: GValueArray with the RhythmDBEntryChange made on the
        entry.
        '''
        print "CoverArtBrowser DEBUG - entry_changed_callback"

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
        '''
        Callback called when a new entry is added to the Rhythmbox's db.
        '''
        print "CoverArtBrowser DEBUG - entry_added_callback"
        # before trying to allocate the entry, found out if this entry is
        # really a song, querying it's duration
        self._allocate_track(Track(entry, db))

        print "CoverArtBrowser DEBUG - end entry_added_callback"

    def _entry_deleted_callback(self, db, entry):
        '''
        Callback called when a entry is deleted from the Rhythmbox's db.
        '''
        print "CoverArtBrowser DEBUG - entry_deleted_callback"
        track = self._tracks[Track(entry).location]

        track.emit('deleted')

        print "CoverArtBrowser DEBUG - end entry_deleted_callback"

    def _allocate_track(self, track):
        '''
        Allocates a given entry in to an album. If not album name is given,
        it's inferred from the entry metadata.
        '''
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
        Initiates the process of recover, create and load all the albums from
        the Rhythmbox's db and their covers provided by artsearch plugin.
        Specifically, it throws the query against the RhythmDB.
        '''
        print "CoverArtBrowser DEBUG - load_albums"

        # function to proccess entries
        def idle_process_entry(args):
            albums, model, total, count, tree_iter = args

            for i in range(DEFAULT_LOAD_CHUNK):
                if tree_iter is None:
                    self._album_manager.progress = 1
                    self.emit('albums-load-finished', albums)
                    return False

                (entry,) = model.get(tree_iter, 0)

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

                tree_iter = model.iter_next(tree_iter)

            # update the iter
            args[4] = tree_iter

            # update the progress
            count += DEFAULT_LOAD_CHUNK
            args[3] = count

            self._album_manager.progress = count / total

            return True

        # load the albums from the query_model
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, idle_process_entry,
            [{}, query_model, len(query_model), 0.,
                query_model.get_iter_first()])

        print "CoverArtBrowser DEBUG - load_albums finished"

    def do_albums_load_finished(self, albums):
        # function to add the albums to the model
        def idle_add_albums(args):
            albums_iter, loaded, total = args

            for i in range(DEFAULT_LOAD_CHUNK):
                try:
                    album = albums_iter.next()

                    self._album_manager.model.add(album)

                    loaded += 1

                except StopIteration:
                    # we finished loading
                    self._album_manager.progress = 1
                    self.emit('model-load-finished')
                    return False

                except Exception as e:
                    print 'Error while adding albums to the model: ' + str(e)

            # update loaded
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

    # signals
    __gsignals__ = {
        'load-finished': (GObject.SIGNAL_RUN_LAST, None, ())
        }

    # properties
    cover_size = GObject.property(type=int, default=0)

    def __init__(self, plugin, album_manager):
        super(CoverManager, self).__init__()

        self._cover_db = RB.ExtDB(name='album-art')
        self._album_manager = album_manager

        self._connect_signals()
        self._connect_properties()

        # create the unknown cover
        self.unknown_cover = Cover(self.cover_size,
            rb.find_plugin_file(plugin, 'img/rhythmbox-missing-artwork.svg'))

    def _connect_signals(self):
        self.connect('notify::cover-size', self._on_notify_cover_size)

        # connect the signal to update cover arts when added
        self.req_id = self._cover_db.connect('added',
            self._albumart_added_callback)

    def _connect_properties(self):
        gs = GSetting()
        setting = gs.get_setting(gs.Path.PLUGIN)

        setting.bind(gs.PluginKey.COVER_SIZE, self, 'cover_size',
            Gio.SettingsBindFlags.GET)

    def _on_notify_cover_size(self, *args):
        '''
        Updates the showing albums cover size.
        '''
        # update the album's covers
        albums = self._album_manager.model.get_all()

        if albums:
            # function to resize the covers
            def idle_resize_callback(args):
                albums_iter, loaded, total = args

                for i in range(DEFAULT_LOAD_CHUNK):
                    try:
                        album = albums_iter.next()

                        album.cover.resize(self.cover_size)

                        loaded += 1

                    except StopIteration:
                        # we finished loading
                        self._album_manager.progress = 1
                        self.emit('load-finished')
                        return False
                    except Exception as e:
                        print "Error while resizing covers: " + str(e)

                # update loaded
                args[1] = loaded

                # update the progress
                self._album_manager.progress = loaded / total

                # the list still got albums, keep going
                return True

            Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE,
                idle_resize_callback, [iter(albums), 0, float(len(albums))])

    def _albumart_added_callback(self, ext_db, key, path, pixbuf):
        '''
        Callback called when new album art added. It updates the pixbuf to the
        album defined by key.
        '''
        print "CoverArtBrowser DEBUG - albumart_added_callback"

        album_name = key.get_field('album')

        # use the name to get the album and update the cover
        if pixbuf and self._album_manager.model.contains(album_name):
            album = self._album_manager.model.get(album_name)

            album.cover = Cover(self.cover_size, pixbuf=pixbuf)

        print "CoverArtBrowser DEBUG - end albumart_added_callback"

    def load_cover(self, album):
        '''
        Tries to load an Album's cover . If no cover is found upon lookup,
        the Unknown cover is used.
        '''
        key = album.create_ext_db_key()
        art_location = self._cover_db.lookup(key)

        if art_location and os.path.exists(art_location):
            try:
                album.cover = Cover(self.cover_size, art_location)
            except:
                pass  # ignore

    def load_covers(self):
        albums = self._album_manager.model.get_all()

        # function to load the covers
        def idle_load_callback(args):
            albums_iter, loaded, total = args

            for i in range(DEFAULT_LOAD_CHUNK):
                try:
                    album = albums_iter.next()

                    if album.cover == self.unknown_cover:
                        self.load_cover(album)

                    loaded += 1

                except StopIteration:
                    # we finished loading
                    self._album_manager.progress = 1
                    self.emit('load-finished')
                    return False

                except Exception as e:
                    print 'Error while loading covers: ' + str(e)

            # update loaded
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
        '''
        key = album.create_ext_db_key()

        provides = self._cover_db.request(key, callback, data)

        if not provides:
            # in case there is no provider, call the callback inmediatly
            callback(data)

    def update_cover(self, album, pixbuf=None, uri=None):
        '''
        Updates the cover database, inserting the pixbuf as the cover art for
        all the entries on the album.
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
                            print "The URI doesn't point to an image."

                async = rb.Loader()
                async.get_url(uri, cover_update, album)


class GenresManager(GObject.Object):

    # signals
    __gsignals__ = {
        'genres-changed': (GObject.SIGNAL_RUN_LAST, None, ())
        }

    def __init__(self, album_manager):
        super(GenresManager, self).__init__()

        self._album_manager = album_manager

        self._connect_signals()

    def _connect_signals(self):
        self.entry_changed_id = self._album_manager.db.connect('entry-changed',
            self._entry_changed_callback)

    def _entry_changed_callback(self, db, entry, changes):
        '''
        Callback called when a RhythDB entry is modified. Updates the genres
        list if necesary

        :param changes: GValueArray with the RhythmDBEntryChange made on the
            entry.
        '''
        print "CoverArtBrowser DEBUG - entry_changed_callback"

        # look at all the changes and update the albums acordingly
        try:
            while True:
                change = changes.values

                if change.prop is RB.RhythmDBPropType.GENRE:
                    # called when the genre of an entry gets modified
                    self.emit('genres-changed')

                # removes the last change from the GValueArray
                changes.remove(0)
        except:
            # we finished reading the GValueArray
            pass

        print "CoverArtBrowser DEBUG - end entry_changed_callback"


class TextManager(GObject.Object):

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
        for album in self._album_manager.model.get_all():
            album.recreate_text(self)

    def _activate_markup(self, *args):
        '''
        Utility method to activate/deactivate the markup text on the
        cover view.
        '''
        print "CoverArtBrowser DEBUG - activate_markup"

        activate = self.display_text_enabled

        if activate:
            column = 3
            item_width = self._album_manager.cover_man.cover_size + 20
        else:
            column = item_width = -1

        self._album_manager.cover_view.set_markup_column(column)
        self._album_manager.cover_view.set_item_width(item_width)

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
        self.genre_man = GenresManager(self)
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

    @classmethod
    def get_instance(cls, plugin=None, cover_view=None):
        if not cls.instance:
            cls.instance = AlbumManager(plugin, cover_view)

        return cls.instance
