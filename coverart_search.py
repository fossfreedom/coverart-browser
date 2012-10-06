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
import re
import os
import gettext

from gi.repository import Gtk
from gi.repository import RB
from gi.repository import WebKit
from mako.template import Template

gettext.install('rhythmbox', RB.locale_dir(), unicode=True)

class CoverSearchPane(Gtk.VBox):
    def __init__(self, plugin):
        super(CoverSearchPane, self).__init__()

        self.file = ""
        self.basepath = 'file://' + plugin.plugin_info.get_data_dir()

        self.load_templates(plugin)
        self.init_gui()

    def load_templates(self, plugin):
        path = rb.find_plugin_file(plugin,
            'tmpl/albumartsearch-tmpl.html')
        self.template = Template(filename=path, module_directory='/tmp/')
        path = rb.find_plugin_file(plugin,
            'tmpl/albumartsearchempty-tmpl.html')
        self.empty_template = Template(filename=path, module_directory='/tmp/')
        self.styles = rb.find_plugin_file(plugin, 'tmpl/main.css')

    def init_gui(self) :
        #---- set up webkit pane -----#
        self.webview = WebKit.WebView()
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.webview)

        self.pack_start(scroll, expand=True, fill=True, padding=0)
        self.show_all()

    def do_search (self, album) :
        artist = album.album_artist
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

    def clear(self):
        temp_file = self.empty_template.render(stylesheet=self.styles)

        self.webview.load_string(temp_file, 'text/html', 'utf-8',
            self.basepath)

    def render_album_art_search(self, artist, album_name):
        temp_file = self.template.render(artist=artist, album=album_name,
            stylesheet=self.styles)

        self.webview.load_string(temp_file, 'text/html', 'utf-8',
            self.basepath)
