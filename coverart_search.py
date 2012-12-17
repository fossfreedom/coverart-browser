# -*- Mode: python; coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
#
# Copyright (C) 2012 - fossfreedom
# Copyright (C) 2012 - Agustin Carrasco
# Based on Rupesh Kumar's and Luqman Aden'a AlbumArtSearch plugin
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

import rb

from gi.repository import Gtk
from gi.repository import WebKit
from mako.template import Template

from coverart_album import AlbumManager


class CoverSearchPane(Gtk.VBox):
    '''
    This UI represents a pane where different album's covers can be presented
    given an album to look for. It also allows to make custom image searchs,
    customize the default search and select covers from the pane and use them
    as the album covers (either with a double click or draging them).
    '''
    def __init__(self, plugin, album_manager, selection_color):
        '''
        Initializes the pane, loading it's html templates and it's ui.
        '''
        super(CoverSearchPane, self).__init__()

        self.album_manager = album_manager
        self.selection_color = selection_color

        self.file = ""
        self.basepath = 'file://' + plugin.plugin_info.get_data_dir()

        self.load_templates(plugin)
        self.init_gui()

        # init the pane with the empty template
        self.clear()

    def load_templates(self, plugin):
        '''
        Loads the templates and stylesheets to be used by the pane.
        '''
#            input_encoding='utf-8',

        path = rb.find_plugin_file(plugin,
            'tmpl/albumartsearch-tmpl.html')
        self.template = Template(filename=path,
            default_filters=['decode.utf8'],
            module_directory='/tmp/',
            output_encoding='utf-8',
            encoding_errors='replace')
        path = rb.find_plugin_file(plugin,
            'tmpl/albumartsearchempty-tmpl.html')
        self.empty_template = Template(filename=path,
            default_filters=['decode.utf8'],
            module_directory='/tmp/',
            output_encoding='utf-8',
            encoding_errors='replace')
        self.styles = rb.find_plugin_file(plugin, 'tmpl/main.css')

    def init_gui(self):
        '''
        Initializes the pane ui.
        '''
        #---- set up webkit pane -----#
        self.webview = WebKit.WebView()
        settings = self.webview.get_settings()
        settings.set_property('enable-default-context-menu', False)
        self.webview.set_settings(settings)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.webview)

        self.pack_start(scroll, expand=True, fill=True, padding=0)
        self.show_all()

        # connect the title changed signal
        self.webview.connect('title-changed', self.set_cover)

    def do_search(self, album):
        '''
        When this method is called, the webview gets refreshed with the info
        of the album passed.
        '''
        if album is self.current_album:
            return

        self.current_album = album

        artist = album.artist
        album_name = album.name

        if album_name.upper() == "UNKNOWN":
            album_name = ""

        if artist.upper() == "UNKNOWN":
            artist = ""

        if not(album_name == "" and artist == ""):
            artist = unicode(artist.replace('&', '&amp;'),
                'utf-8')
            album_name = unicode(album_name.replace('&', '&amp;'), 'utf-8')
            self.render_album_art_search(artist, album_name)

    def render_album_art_search(self, artist, album_name):
        '''
        Renders the template on the webview.
        '''
        temp_file = self.template.render(artist=artist, album=album_name,
            stylesheet=self.styles, selection_color=self.selection_color)

        self.webview.load_string(temp_file, 'text/html', 'utf-8',
            self.basepath)

    def clear(self):
        '''
        Clears the webview of any album's specific info/covers.
        '''
        self.current_album = None
        temp_file = self.empty_template.render(stylesheet=self.styles)

        self.webview.load_string(temp_file, 'text/html', 'utf-8',
            self.basepath)

    def set_cover(self, webview, frame, title):
        '''
        Callback called when a image in the pane is double-clicked. It takes
        care of asking the AlbumLoader to update the album's cover.
        '''
        # update the cover
        self.album_manager.cover_man.update_cover(self.current_album,
            uri=title)
