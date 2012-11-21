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
from urlparse import urlparse

import urllib
import os
import cgi
import tempfile
import rb

class AlbumLoader(GObject.Object):
    '''
    Utility class that manages the albums created for the coverart browser's
    source.
    '''
    # singleton instance
    instance = None

    # signals
    __gsignals__ = {
        'load-finished': (GObject.SIGNAL_RUN_LAST, None, ()),
        'reload-finished': (GObject.SIGNAL_RUN_LAST, None, ()),
        'album-modified': (GObject.SIGNAL_RUN_LAST, object, (object,)),
        'album-post-view-modified': (GObject.SIGNAL_RUN_LAST, object, (object,))
        }

    # properties
    progress = GObject.property(type=float, default=0)
    display_text_ellipsize_enabled = GObject.property(type=bool, default=False)
    display_text_ellipsize_length = GObject.property(type=int, default=0)
    cover_size = GObject.property(type=int, default=0)
    display_font_size = GObject.property(type=int, default=0)

    # default chunk of albums to load at a time while filling the model
    DEFAULT_LOAD_CHUNK = 15

    def __init__(self, plugin, cover_model):
        '''
        Initialises the loader, getting the needed objects from the plugin and
        saving the model that will be used to assign the loaded albums.
        '''
        super(AlbumLoader, self).__init__()

        self.albums = {}
        self.db = plugin.shell.props.db
        self.cover_model = cover_model
        self.cover_db = RB.ExtDB(name='album-art')
        self.reloading = None
        self.reload_covers = False
        self.cover_genres = {}

        # set the unknown cover path
        Album.UNKNOWN_COVER = rb.find_plugin_file(plugin, Album.UNKNOWN_COVER)

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
        self.connect('notify::cover-size', self._on_notify_cover_size)
        self.connect('notify::display-font-size', self._on_notify_cover_size)


        # connect the signal to update cover arts when added
        self.req_id = self.cover_db.connect('added',
            self._albumart_added_callback)

        # connect signals for updating the albums
        self.entry_changed_id = self.db.connect('entry-changed',
            self._entry_changed_callback)
        self.entry_added_id = self.db.connect('entry-added',
            self._entry_added_callback)
        self.entry_deleted_id = self.db.connect('entry-deleted',
            self._entry_deleted_callback)

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
        setting.bind(gs.PluginKey.COVER_SIZE, self, 'cover_size',
            Gio.SettingsBindFlags.GET)
        setting.bind(gs.PluginKey.DISPLAY_FONT_SIZE, self, 'display_font_size',
            Gio.SettingsBindFlags.GET)

    @classmethod
    def get_instance(cls, plugin=None, model=None, query_model=None):
        '''
        Singleton method to allow to access the unique loader instance.
        '''
        if not cls.instance:
            cls.instance = AlbumLoader(plugin, model)
            cls.instance.load_albums(query_model)

        return cls.instance

    def _on_notify_cover_size(self, *args):
        '''
        Updates the loader's albums' cover size and forces a model reload.
        '''
        # update album variables
        Album.FONT_SIZE =  self.display_font_size
        Album.update_unknown_cover(self.cover_size)

        self.reload_model(True)

    def _on_notify_display_text_ellipsize(self, *args):
        '''
        Callback called when one of the properties related with the ellipsize
        option is changed.
        '''
        if self.display_text_ellipsize_enabled:
            Album.set_ellipsize_length(self.display_text_ellipsize_length)
        else:
            Album.set_ellipsize_length(0)

        self.reload_model()

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

    def _get_genre(self, entry):
        '''
        Looks and retrieves an entry's genre.
        '''
        return entry.get_string(RB.RhythmDBPropType.GENRE)

    def _albumart_added_callback(self, ext_db, key, path, pixbuf):
        '''
        Callback called when new album art added. It updates the pixbuf to the
        album defined by key.
        '''
        print "CoverArtBrowser DEBUG - albumart_added_callback"

        album_name = key.get_field('album')

        # use the name to get the album and update the cover
        if album_name in self.albums:
            self.albums[album_name].update_cover(pixbuf, self.cover_size)

        print "CoverArtBrowser DEBUG - end albumart_added_callback"

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

                #print change.prop

                if change.prop is RB.RhythmDBPropType.ALBUM:
                    # called when the album of a entry is modified
                    self._entry_album_modified(entry, change.old, change.new)

                elif change.prop is RB.RhythmDBPropType.HIDDEN:
                    # called when an entry gets hidden (e.g.:the sound file is
                    # removed.
                    self._entry_hidden(db, entry, change.new)

                elif change.prop is RB.RhythmDBPropType.ARTIST:
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

                elif change.prop is RB.RhythmDBPropType.GENRE:
                    # called when the genre of an entry gets modified
                    self._entry_album_genre_modified(change.new)


                # removes the last change from the GValueArray
                changes.remove(0)
        except:
            # we finished reading the GValueArray
            pass

        print "CoverArtBrowser DEBUG - end entry_changed_callback"

    def _entry_album_genre_modified(self, new_genre):
        '''
        Called by entry_changed_callback when the modified prop is the genre.
        If this is a new genre, it is added to the overall genre list
        '''
        print "CoverArtBrowser DEBUG - entry_album_genre_modified"

        if new_genre not in self.cover_genres.keys():
            self.cover_genres[new_genre] = new_genre

        print "CoverArtBrowser DEBUG - end entry_album_genre_modified"

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

    def _entry_artist_modified(self, entry, old_artist, new_artist):
        '''
        Called by entry_changed_callback when the modified prop is the artist
        of the entry.
        It informs the album of the change on the artist name.
        '''
        print "CoverArtBrowser DEBUG - entry_artist_modified"
        # find the album and inform of the change
        album_name = self._get_album_name(entry)

        if album_name in self.albums:
            self.albums[album_name].entry_artist_modified(entry,
                old_artist, new_artist)

            # emit a signal indicating the album has changed
            self.emit('album-modified', self.albums[album_name])

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

        if album_name in self.albums:
            album = self.albums[album_name]
            if album.has_year_changed():
                album_artist=album.album_artist
                qm = RB.RhythmDBQueryModel.new_empty(self.db)
                album.get_entries(qm)
                album.remove_from_model()
                del self.albums[album_name]
                album = Album(album_name, album_artist)
                for row in qm:
                    album.append_entry(row[0])

                album.load_cover(self.cover_db, self.cover_size)
                treeiter = album.add_to_model(self.cover_model)
                self.albums[album_name] = album

                path = self.cover_model.get_path(treeiter)
                self.emit('album-post-view-modified', path)
                self.emit('album-modified', self.albums[album_name])

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

        if album_name in self.albums:
            album = self.albums[album_name]
            if album.has_rating_changed():
                album_artist=album.album_artist
                qm = RB.RhythmDBQueryModel.new_empty(self.db)
                album.get_entries(qm)
                album.remove_from_model()
                del self.albums[album_name]
                album = Album(album_name, album_artist)
                for row in qm:
                    album.append_entry(row[0])

                album.load_cover(self.cover_db, self.cover_size)
                treeiter = album.add_to_model(self.cover_model)
                self.albums[album_name] = album

                path = self.cover_model.get_path(treeiter)

                self.emit('album-post-view-modified', path)
                self.emit('album-modified', self.albums[album_name])

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

        if album_name in self.albums:
            self.albums[album_name].entry_album_artist_modified(entry,
                new_album_artist)

            # emit a signal indicating the album has changed
            self.emit('album-modified', self.albums[album_name])

        print "CoverArtBrowser DEBUG - end entry_album_artist_modified"

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

        if album_name in self.albums:
            self.albums[album_name].append_entry(entry)

            # emit a signal indicating the album has changed
            self.emit('album-modified', self.albums[album_name])
        else:
            album = Album(album_name, album_artist)
            self.albums[album_name] = album

            album.append_entry(entry)
            album.load_cover(self.cover_db, self.cover_size)
            album.add_to_model(self.cover_model)

    def _remove_entry(self, entry, album_name=None):
        '''
        Removes an entry from the an album. If the album name is not provided,
        it's inferred from the entry metatada.
        '''
        if not album_name:
            album_name = self._get_album_name(entry)

        if album_name in self.albums:
            album = self.albums[album_name]
            album.remove_entry(entry)

            if album.get_track_count() == 0:
                # if the album is empty, remove it from the model remove it's
                #reference
                album.remove_from_model()
                del self.albums[album_name]
            else:
                # emit a signal indicating the album has changed
                self.emit('album-modified', album)

    def get_genres(self):
        '''
        return a set of genres
        '''
        return self.cover_genres

    def reload_albums(self, query_model):
        '''
        This clears old albums before loading new albums from query_model
        '''
        print "CoverArtBrowser DEBUG - reload_albums"

        for album in self.albums.values():
            album_name = album.album_name
            album.remove_from_model()
            del self.albums[album_name]

        self.load_albums(query_model)
        print "CoverArtBrowser DEBUG - reload_albums"

    def load_albums(self, query_model):
        '''
        Initiates the process of recover, create and load all the albums from
        the Rhythmbox's db and their covers provided by artsearch plugin.
        Specifically, it throws the query against the RhythmDB.
        '''
        print "CoverArtBrowser DEBUG - load_albums"
        # process the entries and load albums asynchronously
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE,
            self._process_query_model, query_model)

        print "CoverArtBrowser DEBUG - end load_albums"

    def _process_query_model(self, qm):
        '''
        Callback called when the asynchronous query made by load_albums
        finishes.
        Processes all the entries from the db and fills the model.
        '''
        qm.foreach(self._process_entry, None)

        self._fill_model()

    def _process_entry(self, model, tree_path, tree_iter, _):
        '''
        Process a single entry, allocating it to it's correspondent album or
        creating a new one if necesary.
        '''
        (entry,) = model.get(tree_iter, 0)

        # retrieve album metadata
        album_name = self._get_album_name(entry)
        album_artist = self._get_album_artist(entry)

        genre = self._get_genre(entry)
        if genre not in self.cover_genres.keys():
            self.cover_genres[genre] = genre

        # look for the album or create it
        if album_name in self.albums.keys():
            album = self.albums[album_name]
        else:
            album = Album(album_name, album_artist)
            self.albums[album_name] = album

        album.append_entry(entry)

    def _fill_model(self):
        '''
        Fills the model defined for this loader with the info a covers from
        all the albums loaded.
        '''
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE,
            self._idle_load_callback,
            self.albums.values())

    def _idle_load_callback(self, albums):
        '''
        Idle callback that loads the albums by chunks, to avoid blocking the
        ui while doing it.
        '''
        for i in range(AlbumLoader.DEFAULT_LOAD_CHUNK):
            try:
                album = albums.pop()
                album.load_cover(self.cover_db, self.cover_size)
                album.add_to_model(self.cover_model)
            except:
                # we finished loading
                self.progress = 1
                self.emit('load-finished')
                return False

        # update the progress
        self.progress = 1 - len(albums) / float(len(self.albums))

        # the list still got albums, keep going
        return True

    def do_load_finished(self):
        '''
        Updates progress to indicate we finished loading.
        '''
        self.progress = 1

    def reload_model(self, reload_covers=False):
        '''
        This method allows to remove and readd all the albums that are
        currently in this loader model.
        '''
        # set the reload_covers flag
        self.reload_covers = self.reload_covers or reload_covers

        # get those albums in te model and remove them
        albums = [album for album in self.albums.values() if album.model]

        for album in albums:
            album.remove_from_model()

        if self.reloading:
            # if there is already a reloading process going on, just add the
            # albums to the list
            self.reloading.extend(albums)
        else:
            # generate the reloading list
            self.reloading = albums

            # initiate the idle process
            Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE,
                self._readd_albums_to_model, None)

    def _readd_albums_to_model(self, *args):
        '''
        Idle callback that readds the albums removed from the modle by
        'reload_model' in chunks to improve ui resposiveness.
        '''
        for i in range(AlbumLoader.DEFAULT_LOAD_CHUNK):
            try:
                album = self.reloading.pop()

                if self.reload_covers and \
                    album.cover is not Album.UNKNOWN_COVER:
                    album.cover.resize(self.cover_size)

                album.add_to_model(self.cover_model)
            except:
                # clean the reloading list and emit the signal
                self.reload_covers = False
                self.reloading = None
                self.emit('reload_finished')

                return False

        return True

    def search_cover_for_album(self, album, callback=lambda *_: None,
        data=None):
        '''
        Request to a given album to find it's cover. This call is generally
        made asynchronously, so a callback can be given to be called upon
        the finishing of the process.
        '''
        print "search_cover_for_album"
        album.cover_search(self.cover_db, callback, data)
        print "end search_cover_for_album"

    def search_covers(self, albums=None, callback=lambda *_: None):
        '''
        Request all the albums' covers, one by one, periodically calling a
        callback to inform the status of the process.
        The callback should accept one argument: the album which cover is
        being requested. When the argument passed is None, it means the
        process has finished.
        '''
        print "search_covers"
        
        if albums is None:
            albums = self.albums.values()

        def search_next_cover(*args):
            print "search_next_cover"
            # unpack the data
            iterator, callback = args[-1]

            # if the operation was canceled, break the recursion
            if self._cancel_cover_request:
                del self._cancel_cover_request
                callback(None)
                print "a"
                return

            #try to obtain the next album
            try:
                while True:
                    print "in loop"
                    album = iterator.next()

                    if album.model and not album.has_cover():
                        print "about to break"
                        break
            except:
                # inform we finished
                print "callback"
                callback(None)
                print "end callback"
                return

            # inform we are starting a new search
            callback(album)
            print "second callback"

            # request the cover for the next album
            self.search_cover_for_album(album, search_next_cover,
                (iterator, callback))
            print "b"

        self._cancel_cover_request = False
        print "about to test if go around again"
        search_next_cover((albums.__iter__(), callback))
        print "end search_covers"

    def cancel_cover_request(self):
        '''
        Cancel the current cover request, if there is one running.
        '''
        print "cancel_cover"
        try:
            self._cancel_cover_request = True
        except:
            pass

    def update_cover(self, album, pixbuf=None, uri=None):
        '''
        Updates the cover database, inserting the pixbuf as the cover art for
        all the entries on the album.
        '''
        print "update_cover"
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

    def resize(self, size):
        '''
        Resizes the cover's pixbuf.
        '''
        del self.pixbuf

        try:
            self.pixbuf = self.original.scale_simple(size, size,
                 GdkPixbuf.InterpType.BILINEAR)
        except:
            self.pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(self.original,
                size, size)


class Album(object):
    '''
    An specific album defined by it's name and with the ability to obtain it's
    cover and set itself in a treemodel.
    '''
    # cover used for those albums without one
    UNKNOWN_COVER = 'img/rhythmbox-missing-artwork.svg'

    # filter types
    FILTER_ALL = 1
    FILTER_ARTIST = 2
    FILTER_ALBUM = 3
    FILTER_ALBUM_ARTIST = 4
    FILTER_TRACK_TITLE = 5
    FILTER_GENRE = 6

    # font size for the markup text
    FONT_SIZE = 0

    # ellipsize length
    ELLIPSIZE = 0

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
            y=0

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

        if self.ELLIPSIZE and len(name) > self.ELLIPSIZE:
            name = name[:self.ELLIPSIZE] + '...'

        if self.ELLIPSIZE and len(artist) > self.ELLIPSIZE:
            artist = artist[:self.ELLIPSIZE] + '...'

        name = name.encode('utf-8')
        artist = artist.encode('utf-8')

        # escape odd chars
        artist = GLib.markup_escape_text(artist)
        name = GLib.markup_escape_text(name)

        # markup format
        MARKUP_FORMAT = "<span font='%d'><b>%s</b>\n<i>%s</i></span>"
        return MARKUP_FORMAT % (self.FONT_SIZE, name, artist)

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
            # update the model's tooltip and markup for this album
            self.model.set_value(self.tree_iter, 0, self._create_tooltip())
            self.model.set_value(self.tree_iter, 3, self._create_markup())

    def entry_artist_modified(self, entry, old_artist, new_artist):
        '''
        This method should be called when an entry belonging to this album got
        it's artist modified. It takes care of removing and adding the new
        artist if necesary.
        '''
        # find and replace the entry
        for e in self.entries:
            if rb.entry_equal(e, entry):
                self.entries.remove(e)
                self.entries.append(entry)
                break

        # if there isn't any other entry with the old artist, remove it
        self._remove_artist(old_artist)

        # add our new artist
        self._artist.add(new_artist)

        if self.model:
            # update the model's tooltip and markup for this album
            self.model.set_value(self.tree_iter, 0, self._create_tooltip())
            self.model.set_value(self.tree_iter, 3, self._create_markup())

    def has_year_changed(self):
        '''
        This method should be called when an entry belonging to this album got
        it's year modified. It takes care of recalculating the album year
        '''
        old_year = self._year
        print old_year
        self._year = -1
        y = self.year #force a recalculation
        print y
        return not old_year == self._year

    def has_rating_changed(self):
        '''
        This method should be called when an entry belonging to this album got
        it's rating modified. It takes care of recalculating the album rating
        '''
        old_rating = self._rating
        #print old_rating
        self._rating = -1
        r = self.rating #force a recalculation
        #print r
        return not old_rating == self._rating

    def entry_album_artist_modified(self, entry, new_album_artist):
        '''
        This method should be called when an entry belonging to this album got
        it's album artist modified.
        '''
        # find and replace the entry
        for e in self.entries:
            if rb.entry_equal(e, entry):
                self.entries.remove(e)
                self.entries.append(entry)
                break

        # replace the album_artist
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
        print "cover_search"
        key = self.entries[0].create_ext_db_key(RB.RhythmDBPropType.ALBUM)

        provides = cover_db.request(key, callback, data)

        if not provides:
            print "not provides"
            # in case there is no provider, call the callback inmediatly
            callback(data)
            print "callback"
        print "end cover_search"

    def add_to_model(self, model):
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

        self.tree_iter = model.append((tooltip, self.cover.pixbuf, self,
            markup))

        return self.tree_iter

    def get_entries(self, model):
        ''' adds all entries to the model'''

        for e in self.entries:
            model.add_entry(e, -1)

    def remove_from_model(self):
        ''' Removes this album from it's model. '''
        self.model.remove(self.tree_iter)

        self.model = None
        del self.tree_iter

    def update_cover(self, pixbuf, size):
        ''' Updates this Album's cover using the given pixbuf. '''
        if pixbuf:
            self.cover = Cover(size, pixbuf=pixbuf)
            self.model.set_value(self.tree_iter, 1, self.cover.pixbuf)

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

    def contains(self, searchtext, filter_type):
        '''
        Indicates if the text provided coincides with the property defined
        by the indicated filter type.
        '''

        if searchtext == "":
            return True

        if filter_type == Album.FILTER_ALL:
            # this filter is more complicated: for each word in the search
            # text, it tries to find at least one match on the params of
            # the album. If no match is given, then the album doesn't match
            words = searchtext.split()
            params = [self.name.lower(), self.album_artist.lower(),
                self.artist.lower(), self.track_title.lower()]
            matches = []

            for word in words:
                match = False

                for param in params:
                    if word in param:
                        match = True
                        break

                matches.append(match)

            return False not in matches

        if filter_type == Album.FILTER_ALBUM_ARTIST:
            return searchtext.lower() in self.album_artist.lower()

        if filter_type == Album.FILTER_ARTIST:
            return searchtext.lower() in self.artist.lower()

        if filter_type == Album.FILTER_ALBUM:
            return searchtext.lower() in self.name.lower()

        if filter_type == Album.FILTER_TRACK_TITLE:
            return searchtext.lower() in self.track_title.lower()

        if filter_type == Album.FILTER_GENRE:
            return self.has_genre(searchtext)

        return False

    @classmethod
    def update_unknown_cover(cls, cover_size):
        '''
        Updates the unknown cover size or creates it if it isn't already
        created.
        '''
        if type(cls.UNKNOWN_COVER) is str:
            cls.UNKNOWN_COVER = Cover(cover_size, cls.UNKNOWN_COVER)
        else:
            cls.UNKNOWN_COVER.resize(cover_size)

    @classmethod
    def compare_albums_by_name(cls, album1, album2):
        '''
        Classmethod that compares two albums by their names.
        Returns -1 if album1 goes before album2, 0 if their are considered
        equal and 1 if album1 goes after album2.
        '''
        if album1.name < album2.name:
            return 1
        if album1.name > album2.name:
            return -1
        else:
            return 0

    @classmethod
    def compare_albums_by_album_artist(cls, album1, album2):
        '''
        Classmethod that compares two albums by their album artist names.
        Returns -1 if album1 goes before album2, 0 if their are considered
        equal and 1 if album1 goes after album2.
        '''
        if album1.album_artist < album2.album_artist:
            return 1
        if album1.album_artist > album2.album_artist:
            return -1
        else:
            return 0

    @classmethod
    def compare_albums_by_year(cls, album1, album2):
        '''
        Classmethod that compares two albums by their year.
        Returns -1 if album1 goes before album2, 0 if their are considered
        equal and 1 if album1 goes after album2.
        '''
        if album1.year < album2.year:
            return 1
        if album1.year > album2.year:
            return -1
        else:
            return 0

    @classmethod
    def compare_albums_by_rating(cls, album1, album2):
        '''
        Classmethod that compares two albums by their rating.
        Returns -1 if album1 goes before album2, 0 if their are considered
        equal and 1 if album1 goes after album2.
        '''
        if album1.rating < album2.rating:
            return 1
        if album1.rating > album2.rating:
            return -1
        else:
            return 0

    @classmethod
    def set_ellipsize_length(cls, length):
        '''
        Utility method to set the ELLIPSIZE length for the albums markup.
        '''
        cls.ELLIPSIZE = length

        if cls.ELLIPSIZE < 0:
            cls.ELLIPSIZE = 0
