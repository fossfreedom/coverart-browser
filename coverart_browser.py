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

from coverart_browser_prefs import Preferences
from coverart_browser_prefs import GSetting
from coverart_browser_prefs import CoverLocale

from coverart_browser_source import CoverArtBrowserSource

class CoverArtBrowserEntryType(RB.RhythmDBEntryType):
    '''
    Entry type for our source.
    '''
    def __init__(self):
        '''
        Initializes the entry type.
        '''
        RB.RhythmDBEntryType.__init__(self, name='CoverArtBrowserEntryType')


class CoverArtBrowserPlugin(GObject.Object, Peas.Activatable):
    '''
    Main class of the plugin. Manages the activation and deactivation of the
    plugin.
    '''
    __gtype_name = 'CoverArtBrowserPlugin'
    object = GObject.property(type=GObject.Object)
    
    def __init__(self):
        '''
        Initialises the plugin object.
        '''
        GObject.Object.__init__(self)

    def do_activate(self):
        '''
        Called by Rhythmbox when the plugin is activated. It creates the
        plugin's source and connects signals to manage the plugin's
        preferences.
        '''

        #define .plugin text strings used for translation
        plugin = _('CoverArt Browser')
        desc = _('Browse and play your albums through their covers')

        print "CoverArtBrowser DEBUG - do_activate"
        self.shell = self.object
        self.db = self.shell.props.db

        try:
            entry_type = CoverArtBrowserEntryType()
            self.db.register_entry_type(entry_type)
        except NotImplementedError:
            entry_type = self.db.entry_register_type(
                'CoverArtBrowserEntryType')

        cl = CoverLocale()
        cl.switch_locale(cl.Locale.LOCALE_DOMAIN)

        entry_type.category = RB.RhythmDBEntryCategory.NORMAL

        # load plugin icon
        theme = Gtk.IconTheme.get_default()
        rb.append_plugin_source_path(theme, '/icons')

        what, width, height = Gtk.icon_size_lookup(Gtk.IconSize.LARGE_TOOLBAR)
        pxbf = GdkPixbuf.Pixbuf.new_from_file_at_size(
            rb.find_plugin_file(self, 'img/covermgr.png'), width, height)

        group = RB.DisplayPageGroup.get_by_id('library')

        self.source = CoverArtBrowserSource(shell=self.shell,
            name=_("CoverArt"), entry_type=entry_type,
            plugin=self, pixbuf=pxbf,
            query_model=self.shell.props.library_source.props.base_query_model)

        self.shell.register_entry_type_for_source(self.source, entry_type)
        self.shell.append_display_page(self.source, group)

        self.shell.props.db.connect('load-complete', self.load_complete)

        uim = self.shell.props.ui_manager
        uim.add_ui_from_file(rb.find_plugin_file(self,
            'ui/coverart_plugin.ui'))
        
        action = Gtk.Action(name="PlaylistCover", label=_("CoverArt"),
                            tooltip=_("Display Covers for Playlist"),
                            stock_id='gnome-mime-text-x-python')
        action.connect('activate', self.display_covers_for_source)
        self.action_group = Gtk.ActionGroup(name="PlayListCoverActions")
        self.action_group.add_action(action)
        uim.insert_action_group(self.action_group, 0)
        uim.ensure_update()

        print "CoverArtBrowser DEBUG - end do_activate"

    def display_covers_for_source(self, action):
        '''
        Called by Rhythmbox when the user select coverart from popup
        menu from a playlist, music or queue source.
        This resets the coverart query model to what was chosen before
        switching to the coverart browser
        '''
        print "CoverArtBrowser DEBUG - display_covers_for_source"
        page = self.shell.props.selected_page

        try:
            model = page.get_query_model()
        except:
            model = self.shell.props.library_source.props.base_query_model
            
        self.source.reset_coverview(model)
        self.shell.props.display_page_tree.select(self.source)

        print "CoverArtBrowser DEBUG - display_covers_for_source"

    def do_deactivate(self):
        '''
        Called by Rhythmbox when the plugin is deactivated. It makes sure to
        free all the resources used by the plugin.
        '''
        print "CoverArtBrowser DEBUG - do_deactivate"
        self.source.delete_thyself()

        del self.shell
        del self.db
        del self.source
        del self.action_group
        
        print "CoverArtBrowser DEBUG - end do_deactivate"

    def load_complete(self, *args, **kwargs):
        '''
        Called by Rhythmbox when it has completed loading all data
        Used to automatically switch to the browser if the user
        has set in the preferences
        '''
        gs = GSetting()
        setting = gs.get_setting(gs.Path.PLUGIN)
        if setting[gs.PluginKey.AUTOSTART]:
            self.shell.props.display_page_tree.select(self.source)
