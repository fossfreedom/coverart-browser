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
from gi.repository import Gio
from gi.repository import GLib

from coverart_browser_prefs import Preferences
from coverart_browser_prefs import GSetting
from coverart_browser_prefs import CoverLocale
from coverart_browser_source import CoverArtBrowserSource
from coverart_utils import Theme
from coverart_listview import ListView
from coverart_queueview import QueueView
from coverart_toolbar import TopToolbar

import coverart_rb3compat as rb3compat

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
        if not rb3compat.compare_pygobject_version('3.9'):
            GObject.threads_init()

    def do_activate(self):
        '''
        Called by Rhythmbox when the plugin is activated. It creates the
        plugin's source and connects signals to manage the plugin's
        preferences.
        '''

        print("CoverArtBrowser DEBUG - do_activate")
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
        
        group = RB.DisplayPageGroup.get_by_id('library')
        # load plugin icon
        theme = Gtk.IconTheme.get_default()
        rb.append_plugin_source_path(theme, '/icons')

        # lets assume that python3 versions of RB only has the new icon attribute in the source
        if rb3compat.PYVER >=3:
                iconfile = Gio.File.new_for_path(
                    rb.find_plugin_file(self, 'img/covermgr_rb3.png'))
                    
                self.source = CoverArtBrowserSource(
                        shell=self.shell,
                        name=_("CoverArt"), 
                        entry_type=entry_type,
                        plugin=self,
                        icon=Gio.FileIcon.new(iconfile), 
                        query_model=self.shell.props.library_source.props.base_query_model)
        else:
                what, width, height = Gtk.icon_size_lookup(Gtk.IconSize.LARGE_TOOLBAR)
                pxbf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                    rb.find_plugin_file(self, 'img/covermgr.png'), width, height)

                self.source = CoverArtBrowserSource(
                        shell=self.shell,
                        name=_("CoverArt"), entry_type=entry_type,
                        plugin=self, pixbuf=pxbf,
                        query_model=self.shell.props.library_source.props.base_query_model)
                    
        self.shell.register_entry_type_for_source(self.source, entry_type)
        self.shell.append_display_page(self.source, group)

        self.source.props.query_model.connect('complete', self.load_complete)
        if rb3compat.PYVER >=3:
            self._externalmenu = ExternalPluginMenu(self)
        else:
            self._externalmenu = None
                
        cl.switch_locale(cl.Locale.RB)
        print("CoverArtBrowser DEBUG - end do_activate")

    def do_deactivate(self):
        '''
        Called by Rhythmbox when the plugin is deactivated. It makes sure to
        free all the resources used by the plugin.
        '''
        print("CoverArtBrowser DEBUG - do_deactivate")
        self.source.delete_thyself()
        if self._externalmenu:
            self._externalmenu.cleanup()
        del self.shell
        del self.db
        del self.source

        print("CoverArtBrowser DEBUG - end do_deactivate")
        
    def load_complete(self, *args, **kwargs):
        '''
        Called by Rhythmbox when it has completed loading all data
        Used to automatically switch to the browser if the user
        has set in the preferences
        '''
        gs = GSetting()
        setting = gs.get_setting(gs.Path.PLUGIN)

        if setting[gs.PluginKey.AUTOSTART]:
            GLib.idle_add(self.shell.props.display_page_tree.select,
                self.source)
                
    def _translation_helper(self):
        '''
        a method just to help out with translation strings
        it is not meant to be called by itself
        '''
        
        # define .plugin text strings used for translation
        plugin = _('CoverArt Browser')
        desc = _('Browse and play your albums through their covers')
        
        #. TRANSLATORS: This is the icon-grid view that the user sees
        tile = _('Tiles')
        
        #. TRANSLATORS: This is the cover-flow view the user sees - they can swipe album covers from side-to-side
        artist = _('Flow')
        
        #. TRANSLATORS: percentage size that the image will be expanded
        scale = _('Scale by %:')

class ExternalPluginMenu(GObject.Object):

    toolbar_pos = GObject.property(type=str, default=TopToolbar.name)
    
    def __init__(self, plugin):
        super(ExternalPluginMenu, self).__init__()
        
        self.plugin = plugin
        self.shell = plugin.shell
        self.source = plugin.source
        self.app_id = None
        from coverart_browser_source import Views
        self._views = Views(self.shell)
        
        self._connect_properties()
        self._connect_signals()
        
        self._create_menu()

    def _connect_signals(self):
        self.connect('notify::toolbar-pos', self._on_notify_toolbar_pos)
        self.shell.props.display_page_tree.connect(
            "selected", self.on_page_change
            )
        
    def _connect_properties(self):
        gs = GSetting()
        setting = gs.get_setting(gs.Path.PLUGIN)
        setting.bind(gs.PluginKey.TOOLBAR_POS, self, 'toolbar_pos',
            Gio.SettingsBindFlags.GET)
            
    def _on_notify_toolbar_pos(self, *args):
        if self.toolbar_pos == TopToolbar.name:
            self._create_menu()
        else:
            self.cleanup()
        
    def cleanup(self):
        if self.app_id:
            app = Gio.Application.get_default()
            for location in self.locations:
                app.remove_plugin_menu_item(location, self.app_id)
            self.app_id = None

    def _create_menu(self):
        app = Gio.Application.get_default()
        self.app_id = 'coverart-browser'
        
        self.locations = ['library-toolbar', 'queue-toolbar']
        action_name = 'coverart-browser-views'
        self.action = Gio.SimpleAction.new_stateful(
            action_name, GLib.VariantType.new('s'),
            self._views.get_action_name(ListView.name)
            )
        self.action.connect("activate", self.view_change_cb)
        app.add_action(self.action)
        
        menu_item = Gio.MenuItem()
        section = Gio.Menu()
        menu = Gio.Menu()
        toolbar_item = Gio.MenuItem()
        
        for view_name in self._views.get_view_names():
            menu_item.set_label(self._views.get_menu_name(view_name))
            menu_item.set_action_and_target_value(
                'app.' + action_name, self._views.get_action_name(view_name)
                )
            section.append_item(menu_item)
        
        menu.append_section(None, section)

        cl = CoverLocale()
        cl.switch_locale(cl.Locale.LOCALE_DOMAIN)        
        toolbar_item.set_label(_('Views'))
        cl.switch_locale(cl.Locale.RB)

        toolbar_item.set_submenu(menu)
        for location in self.locations:
            app.add_plugin_menu_item(location, self.app_id, toolbar_item)
            
        
    def on_page_change(self, display_page_tree, page):
        '''
        Called when the display page changes. Grabs query models and sets the 
        active view.
        '''
        
        if page == self.shell.props.library_source:
            self.action.set_state(self._views.get_action_name(ListView.name))
        elif page == self.shell.props.queue_source:
            self.action.set_state(self._views.get_action_name(QueueView.name))

    def view_change_cb(self, action, current):
        '''
        Called when the view state on a page is changed. Sets the new 
        state.
        '''
        action.set_state(current)
        view_name = self._views.get_view_name_for_action(current)
        if view_name != ListView.name and view_name != QueueView.name:
            gs = GSetting()
            setting = gs.get_setting(gs.Path.PLUGIN)
            setting[gs.PluginKey.VIEW_NAME] = view_name
            GLib.idle_add(self.shell.props.display_page_tree.select,
                    self.source)
        elif view_name == ListView.name:
            GLib.idle_add(self.shell.props.display_page_tree.select,
                    self.shell.props.library_source)
        elif view_name == QueueView.name:
            GLib.idle_add(self.shell.props.display_page_tree.select,
                    self.shell.props.queue_source)
    
