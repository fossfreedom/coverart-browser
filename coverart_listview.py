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
from gi.repository import GLib

from coverart_widgets import AbstractView


class ListShowingPolicy(GObject.Object):
    """
    Policy that mostly takes care of how and when things should be showed on
    the view that makes use of the `AlbumsModel`.
    """

    def __init__(self, list_view):
        super(ListShowingPolicy, self).__init__()

        self.counter = 0
        self._has_initialised = False

    def initialise(self, album_manager):
        if self._has_initialised:
            return

        self._has_initialised = True


class ListView(AbstractView):
    __gtype_name__ = "ListView"

    name = 'listview'
    use_plugin_window = False

    def __init__(self):
        super(ListView, self).__init__()
        self.view = self
        self._has_initialised = False
        self.show_policy = ListShowingPolicy(self)

    def initialise(self, source):
        if self._has_initialised:
            return

        self._has_initialised = True

        self.view_name = "list_view"
        super(ListView, self).initialise(source)
        # self.album_manager = source.album_manager
        self.shell = source.shell

    def switch_to_view(self, source, album):
        self.initialise(source)

        GLib.idle_add(self.shell.props.display_page_tree.select,
                      self.shell.props.library_source)

    def get_selected_objects(self):
        """
        finds what has been selected

        returns an array of `Album`
        """
        return []
