# -*- Mode: python; coding: utf-8; tab-width: 8; indent-tabs-mode: t; -*-
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

import locale, os, gettext, sys

# setup translation support
(lang_code, encoding) = locale.getlocale()

LOCALE_DOMAIN = 'coverart_browser'
#LOCALE_DIR = os.path.join(sys.prefix, 'local', 'share', 'locale')

#print LOCALE_DIR
 
#locale.setlocale(locale.LC_ALL, '')
locale.bindtextdomain(LOCALE_DOMAIN, '') #LOCALE_DIR)
locale.textdomain(LOCALE_DOMAIN)
#locale.install(LOCALE_DOMAIN)
gettext.bindtextdomain(LOCALE_DOMAIN, '') #LOCALE_DIR)
gettext.textdomain(LOCALE_DOMAIN)
gettext.install(LOCALE_DOMAIN)

# define plugin
import rb

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import RB
from gi.repository import GdkPixbuf
from gi.repository import Peas

from coverart_browser_source import CoverArtBrowserSource

class CoverArtBrowserEntryType(RB.RhythmDBEntryType):
    def __init__(self):
        RB.RhythmDBEntryType.__init__(self, name='CoverArtBrowserEntryType')

class CoverArtBrowserPlugin(GObject.Object, Peas.Activatable):
    __gtype_name = 'CoverArtBrowserPlugin'
    object = GObject.property(type=GObject.Object)
    
    def __init__(self):
        GObject.Object.__init__(self)

    def do_activate(self):
        print "CoverArtBrowser DEBUG - do_activate"
        self.shell = self.object
        self.db = self.shell.props.db
        
        try:
            entry_type = CoverArtBrowserEntryType()
            self.db.register_entry_type(entry_type)
        except NotImplementedError:
            entry_type = db.entry_register_type("CoverArtBrowserEntryType")

        entry_type.category = RB.RhythmDBEntryCategory.NORMAL

        # load plugin icon
        theme = Gtk.IconTheme.get_default()
        rb.append_plugin_source_path(theme, "/icons")

        what, width, height = Gtk.icon_size_lookup(Gtk.IconSize.LARGE_TOOLBAR)
        pxbf = GdkPixbuf.Pixbuf.new_from_file_at_size(rb.find_plugin_file(self, "covermgr.png"), width, height)

        group = RB.DisplayPageGroup.get_by_id ("library")

        self.source = GObject.new ( CoverArtBrowserSource,
                                    shell=self.shell,
                                    name=_("CoverArt"),
                                    entry_type=entry_type,
                                    plugin=self,
                                    pixbuf=pxbf)

        self.shell.register_entry_type_for_source(self.source, entry_type)
        self.shell.append_display_page(self.source, group)
        
        print "CoverArtBrowser DEBUG - end do_activate"
        
    def do_deactivate(self):
        print "CoverArtBrowser DEBUG - do_deactivate"
        manager = self.shell.props.ui_manager
        manager.ensure_update()
        self.source.delete_thyself()
        self.shell = None
        self.source = None
        print "CoverArtBrowser DEBUG - end do_deactivate"

 
