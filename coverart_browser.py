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
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import RB
from gi.repository import Peas
from gi.repository import Gio
from gi.repository import GLib

import rb
from coverart_browser_prefs import GSetting
from coverart_browser_prefs import CoverLocale
from coverart_browser_prefs import Preferences
from coverart_browser_source import CoverArtBrowserSource
from coverart_listview import ListView
from coverart_queueview import QueueView
from coverart_toolbar import TopToolbar
from coverart_utils import get_stock_size
from coverart_utils import create_button_image_symbolic
        

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

        print("CoverArtBrowser DEBUG - do_activate")
        self.shell = self.object
        self.db = self.shell.props.db

        self.entry_type = CoverArtBrowserEntryType()
        self.db.register_entry_type(self.entry_type)

        cl = CoverLocale()
        cl.switch_locale(cl.Locale.LOCALE_DOMAIN)

        self.entry_type.category = RB.RhythmDBEntryCategory.NORMAL

        group = RB.DisplayPageGroup.get_by_id('library')

        # load plugin icon
        #try:
        #    theme = Gtk.IconTheme.get_default()
        #    rb.append_plugin_source_path(theme, '/icons') # prior to rb3.2
        #except:
        #    rb.append_plugin_source_path(self, '/icons') # rb3.2
         
        theme = Gtk.IconTheme.get_default()
        theme.append_search_path(rb.find_plugin_file(self, 'img'))
        
        iconfile = Gio.File.new_for_path(
            rb.find_plugin_file(self, 'img/coverart-icon-symbolic.svg'))

        self.source = CoverArtBrowserSource(
            shell=self.shell,
            name=_("CoverArt"),
            entry_type=self.entry_type,
            plugin=self,
            icon=Gio.FileIcon.new(iconfile),
            query_model=self.shell.props.library_source.props.base_query_model)

        self.shell.register_entry_type_for_source(self.source, self.entry_type)
        self.shell.append_display_page(self.source, group)

        self.source.props.query_model.connect('complete', self.load_complete)
        self._externalmenu = ExternalPluginMenu(self)

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

        # . TRANSLATORS: This is the icon-grid view that the user sees
        tile = _('Tiles')

        #. TRANSLATORS: This is the cover-flow view the user sees - they can swipe album covers from side-to-side
        artist = _('Flow')

        #. TRANSLATORS: percentage size that the image will be expanded
        scale = _('Scale by %:')

        # stop PyCharm removing the Preference import on optimisation
        pref = Preferences()


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

        self.locations = ['library-toolbar', 'queue-toolbar', 'playsource-toolbar']
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
        toolbar_item.set_label('…')
        cl.switch_locale(cl.Locale.RB)

        toolbar_item.set_submenu(menu)
        for location in self.locations:
            app.add_plugin_menu_item(location, self.app_id, toolbar_item)
        
        if hasattr(self.shell, "alternative_toolbar"):
            from alttoolbar_type import AltToolbarHeaderBar
    
            if isinstance(self.shell.alternative_toolbar.toolbar_type, AltToolbarHeaderBar):
                self._add_coverart_header_switch()
        
    def _add_coverart_header_switch(self):
        stack = Gtk.Stack()
        stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        stack.set_transition_duration(1000)
        
        theme = Gtk.IconTheme()
        default = theme.get_default()
        image_name = 'view-list-symbolic'

        box_listview = Gtk.Box()
        stack.add_named(box_listview, "listview")
        stack.child_set_property(box_listview, "icon-name", image_name)
        
        box_coverview = Gtk.Box()
        
        image_name = 'view-cover-symbolic'
        width, height = get_stock_size()
        
        pixbuf = create_button_image_symbolic(stack.get_style_context(), image_name)
        default.add_builtin_icon('coverart_browser_'+image_name, width, pixbuf)
        stack.add_named(box_coverview, "coverview")
        stack.child_set_property(box_coverview, "icon-name", 'coverart_browser_'+image_name)
        
        self.stack_switcher = Gtk.StackSwitcher()
        self.stack_switcher.set_stack(stack)
        self.stack_switcher.show_all()
        
        self.shell.alternative_toolbar.toolbar_type.headerbar.pack_start(self.stack_switcher)
        
        # now move current RBDisplayPageTree to listview stack
        display_tree = self.shell.alternative_toolbar.find(self.shell.props.window, 'RBDisplayPageTree', 'by_name')
        parent = display_tree.get_parent()
        print (parent)
        parent.remove(display_tree)
        box_listview.pack_start(display_tree, True, True, 0)
        box_listview.show_all()
        parent.pack1(stack, True, True)
        
        store = Gtk.ListStore(str, str)
        for view_name in self._views.get_view_names():
            list_iter = store.append([self._views.get_menu_name(view_name), view_name])
            
        tree = Gtk.TreeView(store)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("CoverArt"), renderer, text=0)
        tree.append_column(column)
        
        box_coverview.pack_start(tree, True, True, 0)
        
        stack.show_all()
            
        
    def on_page_change(self, display_page_tree, page):
        '''
        Called when the display page changes. Grabs query models and sets the 
        active view.
        '''

        if page == self.shell.props.library_source:
            self.action.set_state(self._views.get_action_name(ListView.name))
        elif page == self.shell.props.queue_source:
            self.action.set_state(self._views.get_action_name(QueueView.name))
            # elif page == self.source.playlist_source:
            #    self.action.set_state(self._views.get_action_name(PlaySourceView.name))


    def view_change_cb(self, action, current):
        '''
        Called when the view state on a page is changed. Sets the new 
        state.
        '''
        action.set_state(current)
        view_name = self._views.get_view_name_for_action(current)
        if view_name != ListView.name and \
                        view_name != QueueView.name:  # and \
            # view_name != PlaySourceView.name:
            gs = GSetting()
            setting = gs.get_setting(gs.Path.PLUGIN)
            setting[gs.PluginKey.VIEW_NAME] = view_name
            player = self.shell.props.shell_player
            player.set_selected_source(self.source.playlist_source)

            GLib.idle_add(self.shell.props.display_page_tree.select,
                          self.source)
        elif view_name == ListView.name:
            GLib.idle_add(self.shell.props.display_page_tree.select,
                          self.shell.props.library_source)
        elif view_name == QueueView.name:
            GLib.idle_add(self.shell.props.display_page_tree.select,
                          self.shell.props.queue_source)
