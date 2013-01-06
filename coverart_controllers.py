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
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import RB

import rb
from datetime import date

from coverart_browser_prefs import CoverLocale
from coverart_browser_prefs import GSetting
from coverart_utils import ConfiguredSpriteSheet
from coverart_utils import GenreConfiguredSpriteSheet
from coverart_utils import get_stock_size
from coverart_utils import resize_to_stock

from collections import OrderedDict


class PopupController(GObject.Object):

    # properties
    options = GObject.property(type=object, default=None)
    current_key = GObject.property(type=str, default=None)

    def __init__(self):
        super(PopupController, self).__init__()

        # connect the variations on the current key to the controllers action
        self.connect('notify::current-key', self._do_action)

    def get_current_key_index(self):
        return self.options.index(self.current_key)

    def item_selected(self, key):
        if key != self.current_key:
            # update the current value
            self.current_key = key

    def _do_action(self, *args):
        self.do_action()

    def do_action(self):
        pass

    def get_current_image(self):
        return None

    def get_current_tooltip(self):
        return self.current_key


class PlaylistPopupController(PopupController):

    def __init__(self, plugin, album_model):
        super(PlaylistPopupController, self).__init__()

        self._album_model = album_model

        shell = plugin.shell

        # get the library name and initialize the superclass with it
        self._library_name = shell.props.library_source.props.name

        # get the queue name
        self._queue_name = shell.props.queue_source.props.name

        if " (" in self._queue_name:
            self._queue_name = self._queue_name[0:self._queue_name.find(" (")]

        # configure the sprite sheet
        self._spritesheet = ConfiguredSpriteSheet(plugin, 'playlist',
            get_stock_size())

        # get the playlist manager and it's model
        playlist_manager = shell.props.playlist_manager
        playlist_model = playlist_manager.props.display_page_model

        # connect signals to update playlists
        playlist_model.connect('row-inserted', self._update_options, shell)
        playlist_model.connect('row-deleted', self._update_options, shell)
        playlist_model.connect('row-changed', self._update_options, shell)

        # generate initial options
        self._update_options(shell)

    def _update_options(self, *args):
        shell = args[-1]
        playlist_manager = shell.props.playlist_manager
        still_exists = self.current_key == self._library_name or\
            self.current_key == self._queue_name

        # retrieve the options
        values = OrderedDict()

        # library and play queue sources
        values[self._library_name] = None
        values[self._queue_name] = shell.props.queue_source

        # playlists
        playlists_entries = playlist_manager.get_playlists()

        for playlist in playlists_entries:
            if playlist.props.is_local:
                name = playlist.props.name
                values[name] = playlist

                still_exists = still_exists or name == self.current_key

        self.values = values
        self.options = values.keys()

        self.current_key = self.current_key if still_exists else\
            self._library_name

    def do_action(self):
        playlist = self.values[self.current_key]

        if not playlist:
            self._album_model.remove_filter('model')
        else:
            self._album_model.replace_filter('model',
                playlist.get_query_model())

    def get_current_image(self):
        playlist = self.values[self.current_key]

        if self.current_key == self._library_name:
            image = self._spritesheet['music']
        elif self._queue_name in self.current_key:
            image = self._spritesheet['queue']
        elif isinstance(playlist, RB.StaticPlaylistSource):
            image = self._spritesheet['playlist']
        else:
            image = self._spritesheet['smart']

        return image


class GenrePopupController(PopupController):

    def __init__(self, plugin, album_model):
        super(GenrePopupController, self).__init__()

        self._album_model = album_model

        shell = plugin.shell

        # create a new property model for the genres
        genres_model = RB.RhythmDBPropertyModel.new(shell.props.db,
            RB.RhythmDBPropType.GENRE)

        query = shell.props.library_source.props.base_query_model
        genres_model.props.query_model = query

        # initial genre
        self._initial_genre = genres_model[0][0]

        # initialise the button spritesheet and other images
        self._spritesheet = GenreConfiguredSpriteSheet(plugin, 'genre',
            get_stock_size())
        self._default_image = resize_to_stock(
            GdkPixbuf.Pixbuf.new_from_file(rb.find_plugin_file(plugin,
                'img/default_genre.png')))
        self._unrecognised_image = resize_to_stock(
            GdkPixbuf.Pixbuf.new_from_file(rb.find_plugin_file(plugin,
                'img/unrecognised_genre.png')))

        # connect signals to update genres
        query.connect('row-inserted', self._update_options, genres_model)
        query.connect('row-deleted', self._update_options, genres_model)
        query.connect('row-changed', self._update_options, genres_model)

        # generate initial popup
        self._update_options(genres_model)

    def _update_options(self, *args):
        genres_model = args[-1]
        still_exists = False

        # retrieve the options
        options = []

        for row in genres_model:
            genre = row[0]
            options.append(genre)

            still_exists = still_exists or genre == self.current_key

        self.options = options

        self.current_key = self.current_key if still_exists else\
            self._initial_genre

    def do_action(self):
        '''
        called when genre popup menu item chosen
        return None if the first entry in popup returned
        '''
        if self.current_key == self._initial_genre:
            self._album_model.remove_filter('genre')
        else:
            self._album_model.replace_filter('genre', self.current_key)

    def get_current_image(self):
        test_genre = self.current_key.lower()

        if test_genre == self._initial_genre.lower():
            image = self._default_image
        elif test_genre in self._spritesheet:
            image = self._spritesheet[test_genre]
        else:
            image = self._find_alternates(test_genre)

        return image

    def _find_alternates(self, test_genre):
        # first check if any of the default genres are a substring
        # of test_genre - check in reverse order so that we
        # test largest strings first (prevents spurious matches with
        # short strings)
        for genre in sorted(self._spritesheet.names,
            key=lambda b: (-len(b), b)):
            if genre in test_genre:
                return self._spritesheet[genre]

        # next check alternates
        if test_genre in self._spritesheet.alternate:
            return self._spritesheet[self._spritesheet.alternate[test_genre]]

        # if no matches then default to unrecognised image
        return self._unrecognised_image

    def get_current_tooltip(self):
        if self.current_key == self._initial_genre:
            return _('All Genres')
        else:
            return self.current_key


class SortPopupController(PopupController):

    def __init__(self, plugin, album_model):
        super(SortPopupController, self).__init__()

        self._album_model = album_model

        # initialise spritesheet
        self._spritesheet = ConfiguredSpriteSheet(plugin, 'sort',
            get_stock_size())

        # sorts dictionary
        cl = CoverLocale()
        cl.switch_locale(cl.Locale.LOCALE_DOMAIN)

        self.values = OrderedDict([(_('Sort by album name'), 'name'),
            (_('Sort by album artist'), 'artist'),
            (_('Sort by year'), 'year'),
            (_('Sort by rating'), 'rating')])

        self.options = self.values.keys()

        # get the current sort key and initialise the superclass
        gs = GSetting()
        source_settings = gs.get_setting(gs.Path.PLUGIN)
        value = source_settings[gs.PluginKey.SORT_BY]

        self.current_key = self.values.keys()[
            self.values.values().index(value)]

    def do_action(self):
        sort = self.values[self.current_key]

        gs = GSetting()
        settings = gs.get_setting(gs.Path.PLUGIN)
        settings[gs.PluginKey.SORT_BY] = sort

        self._album_model.sort(sort)

    def get_current_image(self):
        sort = self.values[self.current_key]

        return self._spritesheet[sort]


class DecadePopupController(PopupController):

    def __init__(self, plugin, album_model):
        super(DecadePopupController, self).__init__()

        self._album_model = album_model

        # initialize spritesheet
        self._spritesheet = ConfiguredSpriteSheet(plugin, 'decade',
            get_stock_size())

        # decade options
        cl = CoverLocale()
        cl.switch_locale(cl.Locale.LOCALE_DOMAIN)

        self.values = OrderedDict([(_('All'), -1), ('20s', 2020),
            ('10s', 2010), ('00s', 2000), ('90s', 1990), ('80s', 1980),
            ('70s', 1970), ('60s', 1960), ('50s', 1950), ('40s', 1940),
            ('30s', 1930), (_('Old'), -1)])

        self.options = self.values.keys()

        # if we aren't on the 20s yet, remove it
        if date.today().year < 2020:
            self.options.remove('20s')

        # define a initial decade an set the initial key
        self._initial_decade = self.options[0]
        self.current_key = self._initial_decade

    def do_action(self):
        if self.current_key == self._initial_decade:
            self._album_model.remove_filter('decade')
        else:
            self._album_model.replace_filter('decade',
                self.values[self.current_key])

    def get_current_image(self):
        return self._spritesheet[self.current_key]

    def get_current_tooltip(self):
        if self.current_key == self._initial_decade:
            return _('All Decades')
        else:
            return self.current_key
