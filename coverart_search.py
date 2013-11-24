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
from mako.template import Template
import coverart_rb3compat as rb3compat
from coverart_album import Album
from coverart_browser_prefs import webkit_support

class CoverSearchPane(Gtk.Box):
    '''
    This UI represents a pane where different covers can be presented
    given an album or artist to look for. It also allows to make custom image searchs,
    customize the default search and select covers from the pane and use them
    as the covers (either with a double click or dragging them).
    '''
    def __init__(self, plugin, selection_color):
        '''
        Initializes the pane, loading it's html templates and it's ui.
        '''
        super(CoverSearchPane, self).__init__()
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.selection_color = selection_color

        self.file = ""
        self.basepath = 'file://' + plugin.plugin_info.get_data_dir()

        self.load_templates(plugin)
        if webkit_support():
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
            encoding_errors='replace')
        path = rb.find_plugin_file(plugin,
            'tmpl/albumartsearchempty-tmpl.html')
        self.empty_template = Template(filename=path,
            default_filters=['decode.utf8'],
            module_directory='/tmp/',
            encoding_errors='replace')
        path = rb.find_plugin_file(plugin,
            'tmpl/artistartsearch-tmpl.html')
        self.artist_template = Template(filename=path,
            default_filters=['decode.utf8'],
            module_directory='/tmp/',
            encoding_errors='replace')
        self.styles = rb.find_plugin_file(plugin, 'tmpl/main.css')

    def init_gui(self):
        '''
        Initializes the pane ui.
        '''
        #---- set up webkit pane -----#
        from gi.repository import WebKit
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
        self.webview.connect('notify::title', self.set_cover)

    def do_search(self, coverobject, callback):
        '''
        When this method is called, the webview gets refreshed with the info
        of the album or artist passed.
        
        '''
        print ("coverart-search do_search")
        if coverobject is self.current_searchobject:
            return

        self.current_searchobject = coverobject
        self.callback = callback
        
        if isinstance(coverobject, Album):
            artist = coverobject.artist
            album_name = coverobject.name

            if album_name.upper() == "UNKNOWN":
                album_name = ""

            if artist.upper() == "UNKNOWN":
                artist = ""

            if not(album_name == "" and artist == ""):
                artist = rb3compat.unicodestr(artist.replace('&', '&amp;'),
                    'utf-8')
                album_name = rb3compat.unicodestr(album_name.replace('&', '&amp;'), 'utf-8')
                self.render_album_art_search(artist, album_name)
        else:
            artist_name = coverobject.name

            if artist_name.upper() == "UNKNOWN":
                artist_name = ""

            if not(artist_name == ""):
                artist = rb3compat.unicodestr(artist_name.replace('&', '&amp;'),
                    'utf-8')
                self.render_artist_art_search(artist)


    def render_album_art_search(self, artist, album_name):
        '''
        Renders the template on the webview.
        '''
        temp_file = self.template.render(artist=artist, album=album_name,
            stylesheet=self.styles, selection_color=self.selection_color)

        self.webview.load_string(temp_file, 'text/html', 'utf-8',
            self.basepath)

    def render_artist_art_search(self, artist):
        '''
        Renders the template on the webview.
        '''
        temp_file = self.artist_template.render(artist=artist,
            stylesheet=self.styles, selection_color=self.selection_color)

        self.webview.load_string(temp_file, 'text/html', 'utf-8',
            self.basepath)
            
    def clear(self):
        '''
        Clears the webview of any specific info/covers.
        '''
        self.current_searchobject = None
        temp_file = self.empty_template.render(stylesheet=self.styles)

        self.webview.load_string(temp_file, 'text/html', 'utf-8',
            self.basepath)

    def set_cover(self, webview, arg):
        '''
        Callback called when a image in the pane is double-clicked. It takes
        care of updating the searched object cover.
        Some titles have spurious characters beginning with % - remove these
        '''
        # update the cover
        title = webview.get_title()

        print(title)
        if title:
            #self.album_manager.cover_man.update_cover(self.current_searchobject,
            #    uri=title)
            self.callback(self.current_searchobject, uri=title)
