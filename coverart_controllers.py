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
from gi.repository import GObject
from gi.repository import RB

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

        # get the library name and initialize the superclass with it
        self._library_name = plugin.shell.props.library_source.props.name

        # get the queue name
        self._queue_name = plugin.shell.props.queue_source.props.name

        if " (" in self._queue_name:
            self._queue_name = self._queue_name[0:self._queue_name.find(" (")]

        # configure the sprite sheet
        self._spritesheet = ConfiguredSpriteSheet(plugin, 'playlist',
            get_stock_size())

        # get the playlist manager and it's model
        playlist_manager = plugin.shell.props.playlist_manager
        playlist_model = playlist_manager.props.display_page_model

        # connect signals to update playlists
        playlist_model.connect('row-inserted', self._update_options,
            plugin.shell)
        playlist_model.connect('row-deleted', self._update_options,
            plugin.shell)
        playlist_model.connect('row-changed', self._update_options,
            plugin.shell)

        # generate initial options
        self._update_options(plugin.shell)

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
