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

import os
import cgi
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
        'album-modified': (GObject.SIGNAL_RUN_LAST, object, (object,))
        }

    # properties
    progress = GObject.property(type=float, default=0)
    display_text_ellipsize_enabled = GObject.property(type=bool, default=False)
    display_text_ellipsize_length = GObject.property(type=int, default=0)
    cover_size = GObject.property(type=int, default=0)

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
        Album.FONT_SIZE = self.cover_size / 10
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

    def _get_album_name_and_artist(self, entry):
        '''
        Looks and retrieves an entry's album name and artist
        '''
        album_name = entry.get_string(RB.RhythmDBPropType.ALBUM)
        album_artist = entry.get_string(RB.RhythmDBPropType.ALBUM_ARTIST)

        if not album_artist:
            album_artist = entry.get_string(RB.RhythmDBPropType.ARTIST)

        return album_name, album_artist

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

    def _entry_artist_modified(self, entry, old_artist, new_artist):
        '''
        Called by entry_changed_callback when the modified prop is the artist
        of the entry.
        It informs the album of the change on the artist name.
        '''
        print "CoverArtBrowser DEBUG - entry_artist_modified"
        # find the album and inform of the change
        album_name = entry.get_string(RB.RhythmDBPropType.ALBUM)

        if album_name in self.albums:
            self.albums[album_name].entry_artist_modified(entry,
                old_artist, new_artist)

            # emit a signal indicating the album has changed
            self.emit('album-modified', self.albums[album_name])

        print "CoverArtBrowser DEBUG - end entry_artist_modified"

    def _entry_album_artist_modified(self, entry, new_album_artist):
        '''
        Called by entry_changed_callback when the modified prop is the album
        artist of the entry.
        It informs the album of the change on the album artist name.
        '''
        print "CoverArtBrowser DEBUG - entry_album_artist_modified"
        # find the album and inform of the change
        album_name = entry.get_string(RB.RhythmDBPropType.ALBUM)

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
        album_name, album_artist = self._get_album_name_and_artist(entry)

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
            album.load_cover(self.cover_db)
            album.add_to_model(self.cover_model)

    def _remove_entry(self, entry, album_name=None):
        '''
        Removes an entry from the an album. If the album name is not provided,
        it's inferred from the entry metatada.
        '''
        if not album_name:
            album_name = entry.get_string(RB.RhythmDBPropType.ALBUM)

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

    def load_albums(self, query_model):
        '''
        Initiates the process of recover, create and load all the albums from
        the Rhythmbox's db and their covers provided by artsearch plugin.
        Specifically, it throws the query against the RhythmDB.
        '''
        print "CoverArtBrowser DEBUG - load_albums"
        # process the entries and load albums asynchronously
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE,
            self._proccess_query_model, query_model)

        print "CoverArtBrowser DEBUG - end load_albums"

    def _proccess_query_model(self, qm):
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
        album_name, album_artist = self._get_album_name_and_artist(entry)

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
                self._readd_albums_to_model, (reload_covers,
                    AlbumLoader.DEFAULT_LOAD_CHUNK))

    def _readd_albums_to_model(self, data):
        '''
        Idle callback that readds the albums removed from the modle by
        'reload_model' in chunks to improve ui resposiveness.
        '''
        reload_covers, chunk = data

        for i in range(chunk):
            try:
                album = self.reloading.pop()

                if reload_covers and album.cover is not Album.UNKNOWN_COVER:
                    album.cover.resize(self.cover_size)

                album.add_to_model(self.cover_model)
            except:
                # clean the reloading list and emit the signal
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
            albums = self.albums.values()

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
        Either a pixbuf or a uri must be passed to make the update.
        '''
        for artist in album._artist:
            key = RB.ExtDBKey.create_storage('album', album.name)
            key.add_field('artist', artist)

            if pixbuf:
                self.cover_db.store(key, RB.ExtDBSourceType.USER_EXPLICIT,
                    pixbuf)
            else:
                self.cover_db.store_uri(key, RB.ExtDBSourceType.USER_EXPLICIT,
                    uri)


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

    # markup format
    MARKUP_FORMAT = '''<span font='%d'><b>%s</b>\n<i>by %s</i></span>'''

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
        Returns a string representation of the conjuction of all the track
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

    def _create_tooltip(self):
        '''
        Utility function that creates the tooltip for this album to set into
        the model.
        '''
        return cgi.escape('%s by %s' % (self.name, self.artist))

    def _create_markup(self):
        '''
        Utility function that creates the markup text for this album to set
        into the model.
        '''
        # we use unicode to avoid problems with non ascii albums
        name = unicode(self.name, 'utf-8')

        if self.ELLIPSIZE and len(name) > self.ELLIPSIZE:
            name = name[:self.ELLIPSIZE] + '...'

        name = name.encode('utf-8')

        # scape odd chars
        artist = GLib.markup_escape_text(self.album_artist)
        name = GLib.markup_escape_text(name)

        return self.MARKUP_FORMAT % (self.FONT_SIZE, name, artist)

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
        key = self.entries[0].create_ext_db_key(RB.RhythmDBPropType.ALBUM)

        cover_db.request(key, callback, data)

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
    def set_ellipsize_length(cls, length):
        '''
        Utility method to set the ELLIPSIZE length for the albums markup.
        '''
        cls.ELLIPSIZE = length

        if cls.ELLIPSIZE < 0:
            cls.ELLIPSIZE = 0
