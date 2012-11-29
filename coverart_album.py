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


class Cover(object):
    ''' Cover of an Album. '''

    def __init__(self, size, file_path=None, pixbuf=None):
        '''
        Initialises a cover, creating it's pixbuf or adapting a given one.
        Either a file path or a pixbuf should be given to it's correct
        initialization.
        '''
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


class Album(object):
    '''
    An specific album defined by it's name and with the ability to obtain it's
    cover and set itself in a treemodel.
    '''
    # cover used for those albums without one
    UNKNOWN_COVER = 'img/rhythmbox-missing-artwork.svg'

    # text manager that haves all the info necesary to create markup text
    TEXT_MAN = None

    def __init__(self, name, album_artist=None):
        '''
        Initialises the album with it's name and artist.
        Initially, the album haves no cover, so the default Unknown cover is
        asigned.
        '''
        self.name = name
        self._album_artist = album_artist
        self._artist = set()
        self.entries = []
        self.cover = Album.UNKNOWN_COVER
        self.model = None
        self._year = -1
        self._rating = -1

    @property
    def album_name(self):
        '''
        Returns the name of the album.
        '''
        return self.name

    @property
    def artist(self):
        '''
        Returns a string representation of the conjuction of all the artist
        that have entries on this album.
        '''
        return ', '.join(self._artist)

    @property
    def track_title(self):
        '''
        Returns a string representation of the conjunction of all the track
        titles that have entries on this album.
        '''
        title = set()

        for e in self.entries:
            title.add(e.get_string(RB.RhythmDBPropType.TITLE))

        return ' '.join(title)

    @property
    def album_artist(self):
        '''
        Returns this album's artist.
        '''
        album_artist = self._album_artist

        if len(self._artist) > 1:
            # if the album haves multiple entries,
            #ignore the setted album artist
            album_artist = _('Various Artists')

        return album_artist

    @property
    def year(self):
        '''
        Returns this album's year.
        '''
        y = self._year

        if y == -1:
            for e in self.entries:
                track_year = e.get_ulong(RB.RhythmDBPropType.DATE)

                if track_year > 0:
                    if y == -1:
                        y = track_year
                    elif track_year < y:
                        y = track_year

        if y < 0:
            y = 0

        self._year = y

        return y

    @property
    def rating(self):
        '''
        Returns this album's rating.
        '''
        r = self._rating

        if r == -1:
            num = 0
            r = 0

            for e in self.entries:
                track_rating = e.get_double(RB.RhythmDBPropType.RATING)

                if track_rating > 0:
                    r += track_rating
                    num += 1

            if num > 0 and r > 0:
                r = r / num
            else:
                r = 0

            self._rating = r

        return r

    def has_genre(self, test_genre):
        '''
        Returns boolean value if any track is of test_genre
        '''
        for e in self.entries:
            if e.get_string(RB.RhythmDBPropType.GENRE) == test_genre:
                return True

        return False

    def favourite_entries(self, threshold):
        '''
        Returns the RBRhythmDBEntry's for the album
        the meet the rating threshold
        i.e. all the tracks >= Rating
        '''
        # first look for any songs with a rating
        # if none then we are not restricting what is queued
        rating = 0
        for entry in self.entries:
            rating = entry.get_double(RB.RhythmDBPropType.RATING)

            if rating != 0:
                break

        if rating == 0:
            return self.entries

        songs = []

        # Add the songs to the play queue
        for entry in self.entries:
            rating = entry.get_double(RB.RhythmDBPropType.RATING)

            if rating >= threshold:
                songs.append(entry)

        return songs

    def set_rating(self, rating):
        '''
        sets all the RBRhythmDBEntry's for the album
        to have the given rating
        '''

        for entry in self.entries:
            db = AlbumLoader.get_instance().db
            db.entry_set(entry, RB.RhythmDBPropType.RATING,
                rating)

        AlbumLoader.get_instance().emit('album-modified', self)

    def _remove_artist(self, artist):
        '''
        Allows to remove a orphaned artist. If the artist isn't orphaned (e.g.
        there still exist an entry with the artist), this request will be
        ignored.
        '''
        same_artist = False
        for e in self.entries:
            if e.get_string(RB.RhythmDBPropType.ARTIST) == artist:
                same_artist = True
                break

        if not same_artist:
            self._artist.discard(artist)

    def _create_tooltip(self):
        '''
        Utility function that creates the tooltip for this album to set into
        the model.
        '''
        return cgi.escape(_('%s by %s').encode('utf-8') % (self.name,
            self.artist))

    def _create_markup(self):
        '''
        Utility function that creates the markup text for this album to set
        into the model.
        '''
        # we use unicode to avoid problems with non ascii albums
        name = unicode(self.name, 'utf-8')
        artist = unicode(self.album_artist, 'utf-8')

        if self.TEXT_MAN.display_text_ellipsize_enabled:
            ellipsize = self.TEXT_MAN.display_text_ellipsize_length

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
        MARKUP_FORMAT = "<span font='%d'><b>%s</b>\n<i>%s</i></span>"
        return MARKUP_FORMAT % (self.TEXT_MAN.display_font_size, name, artist)

    def append_entry(self, entry):
        ''' Appends an entry to the album entries' list. '''
        self.entries.append(entry)

        # also, add the artist to the artist list
        artist = entry.get_string(RB.RhythmDBPropType.ARTIST)
        self._artist.add(artist)

        if self.model:
            # update the model's tooltip and markup for this album
            self.model.set_value(self.tree_iter, 0, self._create_tooltip())
            self.model.set_value(self.tree_iter, 3, self._create_markup())

    def remove_entry(self, entry):
        '''
        Removes an entry from the album entrie's list. If the removed entry
        was the last one on the Album, it automatically removes itself from
        it's tree model.
        '''
        # find and remove the entry
        for e in self.entries:
            if rb.entry_equal(e, entry):
                self.entries.remove(e)
                break

        # if there isn't any other entry with the same artist, remove it
        artist = entry.get_string(RB.RhythmDBPropType.ARTIST)

        self._remove_artist(artist)

        if self.model:
            # update the album on the model
            self.model.set_value(self.tree_iter, 0, self._create_tooltip())
            self.model.set_value(self.tree_iter, 2, self)
            self.model.set_value(self.tree_iter, 3, self._create_markup())

    def entry_artist_modified(self, entry, old_artist, new_artist):
        '''
        This method should be called when an entry belonging to this album got
        it's artist modified. It takes care of removing and adding the new
        artist if necesary.
        '''
        # if there isn't any other entry with the old artist, remove it
        self._remove_artist(old_artist)

        # add our new artist
        self._artist.add(new_artist)

        if self.model:
            # update the album on the model
            self.model.set_value(self.tree_iter, 0, self._create_tooltip())
            self.model.set_value(self.tree_iter, 2, self)
            self.model.set_value(self.tree_iter, 3, self._create_markup())

    def year_changed(self):
        '''
        This method should be called when an entry belonging to this album got
        it's year modified. It takes care of recalculating the album year
        '''
        old_year = self._year
        self._year = -1

        if old_year != self.year and self.model:
            self.model.set_value(self.tree_iter, 2, self)

    def rating_changed(self):
        '''
        This method should be called when an entry belonging to this album got
        it's rating modified. It takes care of recalculating the album rating
        '''
        old_rating = self._rating
        self._rating = -1

        if old_rating != self.rating and self.model:
            self.model.set_value(self.tree_iter, 2, self)

    def entry_album_artist_modified(self, entry, new_album_artist):
        '''
        This method should be called when an entry belonging to this album got
        it's album artist modified.
        '''
        # replace the album_artist
        if self._album_artist != new_album_artist:
            self._album_artist = new_album_artist

            if self.model:
                # inform the model of the change
                self.model.set_value(self.tree_iter, 2, self)

                # update the markup
                self.model.set_value(self.tree_iter, 3, self._create_markup())

    def has_cover(self):
        ''' Indicates if this album has his cover loaded. '''
        return not self.cover is Album.UNKNOWN_COVER

    def load_cover(self, cover_db, size):
        '''
        Tries to load the Album's cover from the provided cover_db. If no cover
        is found upon lookup, the Unknown cover is used.
        '''
        key = self.entries[0].create_ext_db_key(RB.RhythmDBPropType.ALBUM)
        art_location = cover_db.lookup(key)

        if art_location and os.path.exists(art_location):
            try:
                self.cover = Cover(size, art_location)
            except:
                self.cover = Album.UNKNOWN_COVER

    def cover_search(self, cover_db, callback, data):
        '''
        Activelly requests the Album's cover to the provided cover_db, calling
        the callback given once the process finishes (since it generally is
        asyncrhonous).
        '''
        key = self.entries[0].create_ext_db_key(RB.RhythmDBPropType.ALBUM)

        provides = cover_db.request(key, callback, data)

        if not provides:
            # in case there is no provider, call the callback inmediatly
            callback(data)

    def update_cover(self, size, pixbuf=None):
        ''' Updates this Album's cover using the given pixbuf. '''
        if pixbuf:
            self.cover = Cover(size, pixbuf=pixbuf)
            self.model.set_value(self.tree_iter, 1, self.cover.pixbuf)
        else:
            self.cover.resize(size)

    def add_to_model(self, model, position=-1):
        '''
        Add this model to the tree model. For default, the info is assigned
        in the next order:
            column 0 -> string containing the album name and artist
            column 1 -> pixbuf of the album's cover.
            column 2 -> instance of this same album.
            column 3 -> markup text showed under the cover.
        '''
        self.model = model
        tooltip = self._create_tooltip()
        markup = self._create_markup()

        self.tree_iter = model.insert(position,
            (tooltip, self.cover.pixbuf, self, markup))

        return self.tree_iter

    def remove_from_model(self):
        ''' Removes this album from it's model. '''
        self.model.remove(self.tree_iter)

        self.model = None
        del self.tree_iter

    def recreate_text(self):
        # update the markup
        self.model.set_value(self.tree_iter, 3, self._create_markup())

    def get_entries(self, model):
        ''' adds all entries to the model'''
        songs = sorted(self.entries, key=lambda song:
                song.get_ulong(RB.RhythmDBPropType.TRACK_NUMBER))

        for e in songs:
            model.add_entry(e, -1)

    def get_track_count(self):
        ''' Returns the quantity of tracks stored on this Album. '''
        return len(self.entries)

    def calculate_duration_in_secs(self):
        '''
        Returns the duration of this album (given by it's tracks) in seconds.
        '''
        duration = 0

        for entry in self.entries:
            duration += entry.get_ulong(RB.RhythmDBPropType.DURATION)

        return duration

    def calculate_duration_in_mins(self):
        '''
        Returns the duration of this album in minutes. The duration is
        truncated.
        '''
        return self.calculate_duration_in_secs() / 60

    @classmethod
    def create_unknown_cover(cls, cover_size, cover_path):
        '''
        Updates the unknown cover size or creates it if it isn't already
        created.
        '''
        cls.UNKNOWN_COVER = Cover(cover_size, cover_path)


class AlbumLoader(GObject.Object):
    '''
    Utility class that manages the albums created for the coverart browser's
    source.
    '''
    # signals
    __gsignals__ = {
        'load-finished': (GObject.SIGNAL_RUN_LAST, None, ())
        }

    def __init__(self, album_manager):
        '''
        Initialises the loader, getting the needed objects from the plugin and
        saving the model that will be used to assign the loaded albums.
        '''
        super(AlbumLoader, self).__init__()

        self._album_manager = album_manager

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

    def _get_album_artist(self, entry):
        '''
        Looks and retrieves an entry's album artist.
        '''
        album_artist = entry.get_string(RB.RhythmDBPropType.ALBUM_ARTIST)

        if not album_artist:
            album_artist = entry.get_string(RB.RhythmDBPropType.ARTIST)

        return album_artist

    def _get_album_name(self, entry):
        '''
        Looks and retrieves an entry's album name.
        '''
        return entry.get_string(RB.RhythmDBPropType.ALBUM)

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
            while True:
                change = changes.values

                if change.prop is RB.RhythmDBPropType.ALBUM:
                    # called when the album of a entry is modified
                    self._entry_album_modified(entry, change.old, change.new)

                elif change.prop is RB.RhythmDBPropType.HIDDEN:
                    # called when an entry gets hidden (e.g.:the sound file is
                    # removed.
                    self._entry_hidden(db, entry, change.new)

                # removes the last change from the GValueArray
                changes.remove(0)
        except:
            # we finished reading the GValueArray
            pass

        print "CoverArtBrowser DEBUG - end entry_changed_callback"

    def _entry_album_modified(self, entry, old_name, new_name):
        '''
        Called by entry_changed_callback when the modified prop is the album.
        Reallocates the entry into the album defined by new_name, removing
        it from the old_name album previously.
        '''
        print "CoverArtBrowser DEBUG - entry_album_modified"
        # find the old album and remove the entry
        self._remove_entry(entry, old_name)

        # add the entry to the album it belongs now
        self._allocate_entry(entry, new_name)

        print "CoverArtBrowser DEBUG - end entry_album_modified"

    def _entry_hidden(self, db, entry, hidden):
        '''
        Called by entry_changed_callback when the modified prop is the hidden
        prop.
        It removes/adds the entry to the albums acordingly.
        '''
        print "CoverArtBrowser DEBUG - entry_hidden"
        if hidden:
            self._entry_deleted_callback(db, entry)
        else:
            self._entry_added_callback(db, entry)

        print "CoverArtBrowser DEBUG - end entry_hidden"

    def _entry_added_callback(self, db, entry):
        '''
        Callback called when a new entry is added to the Rhythmbox's db.
        '''
        print "CoverArtBrowser DEBUG - entry_added_callback"
        # before trying to allocate the entry, found out if this entry is
        # really a song, querying it's duration
        if entry.get_ulong(RB.RhythmDBPropType.DURATION):
            self._allocate_entry(entry)

        print "CoverArtBrowser DEBUG - end entry_added_callback"

    def _entry_deleted_callback(self, db, entry):
        '''
        Callback called when a entry is deleted from the Rhythmbox's db.
        '''
        print "CoverArtBrowser DEBUG - entry_deleted_callback"
        self._remove_entry(entry)

        print "CoverArtBrowser DEBUG - end entry_deleted_callback"

    def _allocate_entry(self, entry, new_album_name=None):
        '''
        Allocates a given entry in to an album. If not album name is given,
        it's inferred from the entry metadata.
        '''
        album_name = self._get_album_name(entry)
        album_artist = self._get_album_artist(entry)

        if new_album_name:
            album_name = new_album_name

        if self._album_manager.has(album_name):
            album = self._album_manager.get(album_name)
        else:
            album = Album(album_name, album_artist)
            self._album_manager.add(album_name, album)

        album.append_entry(entry)

        self._album_manager.emit('album-modified', album)

    def _remove_entry(self, entry, album_name=None):
        '''
        Removes an entry from the an album. If the album name is not provided,
        it's inferred from the entry metatada.
        '''
        if not album_name:
            album_name = self._get_album_name(entry)

        if self._album_manager.has(album_name):
            album = self._album_manager.get(album_name)
            album.remove_entry(entry)

            if album.get_track_count() == 0:
                # if the album is empty, remove it from the model remove it's
                #reference
                album.remove_from_model()
                self._album_manager.remove(album_name)
            else:
                self._album_manager.emit('album-modified', album)

    def load_albums(self, query_model):
        '''
        Initiates the process of recover, create and load all the albums from
        the Rhythmbox's db and their covers provided by artsearch plugin.
        Specifically, it throws the query against the RhythmDB.
        '''
        print "CoverArtBrowser DEBUG - load_albums"
        query_model.foreach(self._process_entry, None)

        self.emit('load-finished')
        print "CoverArtBrowser DEBUG - load finished"

    def _process_entry(self, model, tree_path, tree_iter, _):
        '''
        Process a single entry, allocating it to it's correspondent album or
        creating a new one if necesary.
        '''
        (entry,) = model.get(tree_iter, 0)

        # retrieve album metadata
        album_name = self._get_album_name(entry)
        album_artist = self._get_album_artist(entry)

        # look for the album or create it
        if self._album_manager.has(album_name):
            album = self._album_manager.get(album_name)
        else:
            album = Album(album_name, album_artist)
            self._album_manager.add(album_name, album)

        album.append_entry(entry)


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
        self.autoload = False

        self._connect_signals()
        self._connect_properties()

        # create the unknown cover
        Album.create_unknown_cover(self.cover_size,
            rb.find_plugin_file(plugin, Album.UNKNOWN_COVER))

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
        for album in self._album_manager.get_showing_albums():
            album.update_cover(self.cover_size)

    def _albumart_added_callback(self, ext_db, key, path, pixbuf):
        '''
        Callback called when new album art added. It updates the pixbuf to the
        album defined by key.
        '''
        print "CoverArtBrowser DEBUG - albumart_added_callback"

        album_name = key.get_field('album')

        # use the name to get the album and update the cover
        if self.album_manager.has(album_name):
            self._album_manager.get(album_name).update_cover(pixbuf,
                self.cover_size)

        print "CoverArtBrowser DEBUG - end albumart_added_callback"

    def load_cover(self, album):
        if self.autoload:
            album.load_cover(album, self._cover_db, self.cover_size)

    def load_covers(self):
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE,
            self._idle_load_callback,
             self._album_manager._albums.values())

    def _idle_load_callback(self, albums):
        '''
        Idle callback that loads the albums by chunks, to avoid blocking the
        ui while doing it.
        '''
        for i in range(DEFAULT_LOAD_CHUNK):
            try:
                album = albums.pop()
                album.load_cover(self._cover_db, self.cover_size)

            except:
                # we finished loading
                self._album_manager.progress = 1
                self.emit('load-finished')
                return False

        # update the progress
        self._album_manager.progress = 1 - len(albums) / float(
            len(self._album_manager._albums))

        # the list still got albums, keep going
        return True

    def search_cover_for_album(self, album, callback=lambda *_: None,
        data=None):
        '''
        Request to a given album to find it's cover. This call is generally
        made asynchronously, so a callback can be given to be called upon
        the finishing of the process.
        '''
        album.cover_search(self.cover_db, callback, data)

    def search_covers(self, albums=None, callback=lambda *_: None):
        '''
        Request all the albums' covers, one by one, periodically calling a
        callback to inform the status of the process.
        The callback should accept one argument: the album which cover is
        being requested. When the argument passed is None, it means the
        process has finished.
        '''
        if albums is None:
            albums = self.album_manager.albums.values()

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

                    if album.model and not album.has_cover():
                        break
            except:
                # inform we finished
                callback(None)
                return

            # inform we are starting a new search
            callback(album)

            # request the cover for the next album
            self.search_cover_for_album(album, search_next_cover,
                (iterator, callback))

        self._cancel_cover_request = False
        search_next_cover((albums.__iter__(), callback))

    def cancel_cover_request(self):
        '''
        Cancel the current cover request, if there is one running.
        '''
        try:
            self._cancel_cover_request = True
        except:
            pass

    def update_cover(self, album, pixbuf=None, uri=None):
        '''
        Updates the cover database, inserting the pixbuf as the cover art for
        all the entries on the album.
        '''
        if pixbuf:
            # if it's a pixbuf, asign it to all the artist for the album
            for artist in album._artist:
                key = RB.ExtDBKey.create_storage('album', album.name)
                key.add_field('artist', artist)

                self.cover_db.store(key, RB.ExtDBSourceType.USER_EXPLICIT,
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

    def __init__(self, album_manager):
        super(GenresManager, self).__init__()

        self._album_manager = album_manager
        self._genres = set()

    def _get_genre(self, entry):
        '''
        Looks and retrieves an entry's genre.
        '''
        return entry.get_string(RB.RhythmDBPropType.GENRE)

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
                    self._genres.add(change.new)

                # removes the last change from the GValueArray
                changes.remove(0)
        except:
            # we finished reading the GValueArray
            pass

        print "CoverArtBrowser DEBUG - end entry_changed_callback"

    def get_genres(self):
        return list(self._genres)


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
        for album in self._album_manager.get_showing_albums():
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
            item_width = self._album_manager.covers_man.cover_size + 20
        else:
            column = item_width = -1

        self._album_manager.cover_view.set_markup_column(column)
        self._album_manager.cover_view.set_item_width(item_width)

        print "CoverArtBrowser DEBUG - end activate_markup"


class AlbumFilters(object):

    @classmethod
    def global_filter(searchtext=''):
        def filt(album):
            # this filter is more complicated: for each word in the search
            # text, it tries to find at least one match on the params of
            # the album. If no match is given, then the album doesn't match
            if searchtext == "":
                return True

            words = searchtext.split()
            params = [album.name.lower(), album.album_artist.lower(),
                album.artist.lower(), album.track_title.lower()]
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
    def album_artist_filter(searchtext=''):
        def filt(album):
            if searchtext == "":
                return True

            return searchtext.lower() in album.album_artist.lower()

        return filt

    @classmethod
    def artist_filter(searchtext=''):
        def filt(album):
            if searchtext == "":
                return True

            return searchtext.lower() in album.artist.lower()

        return filt

    @classmethod
    def album_name_filter(searchtext=''):
        def filt(album):
            if searchtext == "":
                return True

            return searchtext.lower() in album.name.lower()

        return filt

    @classmethod
    def track_title_filter(searchtext=''):
        def filt(album):
            if searchtext == "":
                return True

            return searchtext.lower() in album.track_title.lower()

        return filt

    @classmethod
    def genre_filter(searchtext=''):
        def filt(album):
            if searchtext == "":
                return True

            return album.has_genre(searchtext)

        return filt

    keys = {'all': global_filter,
            'album_artist': album_artist_filter,
            'artist': artist_filter,
            'album_name': album_name_filter,
            'track': track_title_filter,
            'genre': genre_filter
            }


class AlbumShowingPolicy(GObject.Object):

    def __init__(self, cover_model, cover_view, album_manager):
        super(AlbumShowingPolicy, self).__init__()

        self._cover_model = cover_model
        self._cover_view = cover_view
        self._album_manager = album_manager
        self._filters = {}
        self._filtered = SortedCollection(self._album_manager._albums.values())
        self.showing = []
        self.autoshow = False

    def album_added(self, album):
        if self._album_filter(album):
            self._filtered.insert(album)

            if self.autoshow:
                self.show_one(album)

    def album_removed(self, album):
        if self._album_filter(album):
            self._filtered.remove(album)

            if album in self.showing:
                self.hide_one(album)

    def resort(self, key_attr='name'):
        self._filtered.key = lambda album: getattr(album, key_attr)

        self.clear()
        self.show()

    def replace_filter(self, filter_key, filter_text):
        self._filter[filter_key] = AlbumFilters.keys['filter_key'](filter_text)

        self.refilter()

    def remove_filter(self, filter_key):
        try:
            del self._filter[filter_key]

            self.refilter()
        except:
            pass

    def _album_filter(self, album):
        for f in self._filters.values():
            if not f(album):
                return False

        return True

    def _refilter(self):
        filtered = filter(self._album_filter, self._album_manager._albums)

        del self._filtered[:]

        self._filtered.insert_all(filtered)

        self.show()

    def clear(self):
        for album in self.showing:
            album.remove_from_model()

        del self.showing[:]

    def show(self):
        raise Exception('show not overrided')

    def show_one(self, album):
        raise Exception('show_one not overrided')

    def hide_one(self):
        raise Exception('hide_one not overrided')


class ShowAllPolicy(AlbumShowingPolicy):

    def __init__(self, cover_model, cover_view, album_manager):
        super(ShowAllPolicy, self).__init__(cover_model, cover_view,
            album_manager)

    def show(self):
        '''
        Fills the model defined for this loader with the info a covers from
        all the albums loaded.
        '''
        add = [album for album in self._filtered if album not in self.showing]
        remove = [album for album in self._filtered if album in self.showing]

        for album in add:
            self.showing.append(album)
            self.show_one(album)

        for album in remove:
            self.showing.remove(album)
            self.hide_one(album)

    def show_one(self, album):
        self.showing.append(album)
        album.add_to_model(self._cover_model, self._filtered.index(album))

    def hide_one(self, album):
        self.showing.remove(album)
        album.remove_from_model()


class ShowProgessivePolicy(AlbumShowingPolicy):

    def __init__(self, cover_model, cover_view, album_manager):
        super(ShowProgessivePolicy, self).__init__(cover_model, cover_view,
            album_manager)


class AlbumManager(GObject.Object):

    # singleton instance
    instance = None

    # signals
    __gsignals__ = {
        'album-modified': (GObject.SIGNAL_RUN_LAST, object, (object,))
        }

    # properties
    progress = GObject.property(type=float, default=0)

    def __init__(self, plugin, cover_model, cover_view):
        super(AlbumManager, self).__init__()

        self.cover_model = cover_model
        self.cover_view = cover_view
        self._albums = {}
        self.db = plugin.shell.props.db

        # initialize showing policy
        policy = ShowAllPolicy(cover_model, cover_view, self)

        self._show_policy = policy

        # initialize managers
        self.loader = AlbumLoader(self)
        self.covers_man = CoverManager(plugin, self)
        self.genres_man = GenresManager(self)

        # set the text manager for the albums
        Album.TEXT_MAN = TextManager(self)

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
        self.album_load_finished_id = self.loader.connect('load-finished',
            self._album_load_finished_callback)
        self.cover_load_finished_id = self.covers_man.connect('load-finished',
            self._cover_load_finished_callback)

    def _entry_changed_callback(self, db, entry, changes):
        '''
        Callback called when a RhythDB entry is modified. Updates the albums
        accordingly to the changes made on the db.

        :param changes: GValueArray with the RhythmDBEntryChange made on the
        entry.
        '''
        print "CoverArtBrowser DEBUG - entry_changed_callback"

        # look at all the changes and update the albums acordingly
        try:
            while True:
                change = changes.values

                if change.prop is RB.RhythmDBPropType.ARTIST:
                    # called when the artist of an entry gets modified
                    self._entry_artist_modified(entry, change.old, change.new)

                elif change.prop is RB.RhythmDBPropType.ALBUM_ARTIST:
                    # called when the album artist of an entry gets modified
                    self._entry_album_artist_modified(entry, change.new)

                elif change.prop is RB.RhythmDBPropType.RATING:
                    # called when the rating of an entry gets modified
                    self._entry_album_rating_modified(entry)

                elif change.prop is RB.RhythmDBPropType.DATE:
                    # called when the year of an entry gets modified
                    self._entry_album_year_modified(entry)

                # removes the last change from the GValueArray
                changes.remove(0)
        except:
            # we finished reading the GValueArray
            pass

        print "CoverArtBrowser DEBUG - end entry_changed_callback"

    def _entry_artist_modified(self, entry, old_artist, new_artist):
        '''
        Called by entry_changed_callback when the modified prop is the artist
        of the entry.
        It informs the album of the change on the artist name.
        '''
        print "CoverArtBrowser DEBUG - entry_artist_modified"
        # find the album and inform of the change
        album_name = self._get_album_name(entry)

        if album_name in self._albums:
            self._albums[album_name].entry_artist_modified(entry,
                old_artist, new_artist)

            # emit a signal indicating the album has changed
            self.emit('album-modified', self._albums[album_name])

        print "CoverArtBrowser DEBUG - end entry_artist_modified"

    def _entry_album_year_modified(self, entry):
        '''
        Called by entry_changed_callback when an year value is changed
        which should cause the associated album information to be
        recalculated.
        '''
        print "CoverArtBrowser DEBUG - _entry_album_year_modified"
        # find the album and inform of the change
        album_name = self._get_album_name(entry)

        if album_name in self._albums:
            album = self._albums[album_name]
            if album.has_year_changed():
                self.emit('album-modified', self._albums[album_name])

        print "CoverArtBrowser DEBUG - end _entry_album_year_modified"

    def _entry_album_rating_modified(self, entry):
        '''
        Called by entry_changed_callback when an rating value is changed
        which should cause the associated album information to be
        recalculated.
        '''
        print "CoverArtBrowser DEBUG - entry_rating_modified"
        # find the album and inform of the change
        album_name = self._get_album_name(entry)

        if album_name in self._albums:
            album = self._albums[album_name]
            if album.has_rating_changed():
                self.emit('album-modified', self._albums[album_name])

        print "CoverArtBrowser DEBUG - end entry_rating_modified"

    def _entry_album_artist_modified(self, entry, new_album_artist):
        '''
        Called by entry_changed_callback when the modified prop is the album
        artist of the entry.
        It informs the album of the change on the album artist name.
        '''
        print "CoverArtBrowser DEBUG - entry_album_artist_modified"
        # find the album and inform of the change
        album_name = self._get_album_name(entry)

        if album_name in self._albums:
            self._albums[album_name].entry_album_artist_modified(entry,
                new_album_artist)

            # emit a signal indicating the album has changed
            self.emit('album-modified', self._albums[album_name])

        print "CoverArtBrowser DEBUG - end entry_album_artist_modified"

    def _album_load_finished_callback(self, *args):
        self.covers_man.autoload = True
        self.covers_man.load_covers()

    def _cover_load_finished_callback(self, *args):
        self._show_policy.autoshow = True
        self.show()

    def add(self, album_name, album):
        self._albums[album_name] = album
        self.covers_man.load_cover(album)
        self._show_policy.album_added(album)

    def get(self, album_name):
        return self._albums[album_name]

    def remove(self, album_name):
        self._show_policy.album_removed(self._albums[album_name])

        del self._albums[album_name]

    def has(self, album_name):
        return album_name in self._albums

    def get_showing_albums(self):
        return self._show_policy.showing

    def show(self):
        self._show_policy.show()

    def replace_filter(self, filter_key, filter_text):
        self._show_policy.replace_filter(filter_key, filter_text)

    def remove_filter(self, filter_key):
        self._show_policy.remove_filter(filter_key)

    @classmethod
    def get_instance(cls, plugin, cover_model, cover_view, query_model):
        if not cls.instance:
            cls.instance = AlbumManager(plugin, cover_model, cover_view)

            cls.instance.loader.load_albums(query_model)

        return cls.instance
