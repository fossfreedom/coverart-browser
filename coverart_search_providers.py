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

# define plugin
import rb
import locale
import gettext


from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import RB
from gi.repository import GdkPixbuf
from gi.repository import Peas

from coverart_browser_prefs import GSetting
from coverart_album_search import CoverAlbumSearch
from coverart_album_search import DiscogsSearch
from coverart_album_search import CoverSearch

class CoverArtAlbumSearchPlugin(GObject.Object, Peas.Activatable):
    '''
    Main class of the plugin. Manages the activation and deactivation of the
    plugin.
    '''
    __gtype_name = 'CoverArtAlbumSearchPlugin'
    object = GObject.property(type=GObject.Object)
    
    def __init__(self):
        '''
        Initialises the plugin object.
        '''
        GObject.Object.__init__(self)
        GObject.threads_init()

    def do_activate(self):
        '''
        Called by Rhythmbox when the plugin is activated. It creates the
        plugin's source and connects signals to manage the plugin's
        preferences.
        '''

        #define .plugin text strings used for translation
        #plugin = _('CoverArt Browser')
        #desc = _('Browse and play your albums through their covers')

        print "CoverArtBrowser DEBUG - do_activate"
        self.shell = self.object
        self.db = self.shell.props.db

        self.art_store = RB.ExtDB(name="album-art")
        self.req_id = self.art_store.connect("request", self.album_art_requested)

        print "CoverArtBrowser DEBUG - end do_activate"

    def do_deactivate(self):
        '''
        Called by Rhythmbox when the plugin is deactivated. It makes sure to
        free all the resources used by the plugin.
        '''
        print "CoverArtBrowser DEBUG - do_deactivate"
        
        del self.shell
        del self.db
        self.art_store.disconnect(self.req_id)
        self.req_id = 0
        self.art_store = None
        
        print "CoverArtBrowser DEBUG - end do_deactivate"

    def album_art_requested(self, store, key, last_time):
        searches = []
        
        gs = GSetting()
        setting = gs.get_setting(gs.Path.PLUGIN)
        
        if setting[gs.PluginKey.EMBEDDED_SEARCH]:
            searches.append(CoverAlbumSearch())
        if setting[gs.PluginKey.DISCOGS_SEARCH]:
            searches.append(DiscogsSearch())

        print "about to search"
        s = CoverSearch(store, key, last_time, searches)
        print "finished about to return"
        return s.next_search()
