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
from coverart_playsourceview import PlaySourceView
from coverart_toolbar import TopToolbar
from coverart_play_source import CoverArtPlaySource


class CoverArtBrowserEntryType(RB.RhythmDBEntryType):
    """
    Entry type for our source.
    """

    def __init__(self):
        """
        Initializes the entry type.
        """
        RB.RhythmDBEntryType.__init__(self, name='CoverArtBrowserEntryType')


class CoverArtBrowserPlugin(GObject.Object, Peas.Activatable):
    """
    Main class of the plugin. Manages the activation and deactivation of the
    plugin.
    """
    __gtype_name = 'CoverArtBrowserPlugin'
    object = GObject.property(type=GObject.Object)

    def __init__(self):
        """
        Initialises the plugin object.
        """
        GObject.Object.__init__(self)
        self._externalmenu = None

    def do_activate(self):
        """
        Called by Rhythmbox when the plugin is activated. It creates the
        plugin's source and connects signals to manage the plugin's
        preferences.
        """

        print("CoverArtBrowser DEBUG - do_activate")
        self.shell = self.object
        self.db = self.shell.props.db

        self.entry_type = CoverArtBrowserEntryType()
        self.db.register_entry_type(self.entry_type)

        # we do some specific functionality when working with alternative toolbar
        # variables defined by the externalpluginmenu
        self.using_alternative_toolbar = False
        self.using_headerbar = False

        cl = CoverLocale()
        cl.switch_locale(cl.Locale.LOCALE_DOMAIN)

        self.entry_type.category = RB.RhythmDBEntryCategory.NORMAL

        group = RB.DisplayPageGroup.get_by_id('library')

        theme = Gtk.IconTheme.get_default()
        theme.append_search_path(rb.find_plugin_file(self, 'img'))

        iconfile = Gio.ThemedIcon(name='coverart-icon-symbolic')

        # our plugin model shared between sources
        self.source_query_model = RB.RhythmDBQueryModel.new_empty(self.shell.props.db)

        self.source = CoverArtBrowserSource(
            shell=self.shell,
            name=_("CoverArt"),
            entry_type=self.entry_type,
            plugin=self,
            icon=iconfile,
            query_model=self.shell.props.library_source.props.base_query_model)

        self.shell.register_entry_type_for_source(self.source, self.entry_type)
        self.source.props.visibility = False
        self.shell.append_display_page(self.source, group)

        self.playlist_source = GObject.new(
            CoverArtPlaySource,
            name=_("CoverArt Playlist"),
            shell=self.shell,
            plugin=self,
            entry_type=self.entry_type)

        self.shell.append_display_page(self.playlist_source, self.source)

        self.shell.props.db.connect('load-complete', self.load_complete)
        # GLib.timeout_add_seconds(3, self.load_complete) # kludge - if plugin activated after RB has loaded then do stuff
        def delayed(*args):
            if self.shell.props.selected_page:
                self._externalmenu = ExternalPluginMenu(self)
                self.playlist_source.load_model(self)
                return False
            else:
                return True

        GLib.timeout_add(100, delayed)

        cl.switch_locale(cl.Locale.RB)
        print("CoverArtBrowser DEBUG - end do_activate")

    def do_deactivate(self):
        """
        Called by Rhythmbox when the plugin is deactivated. It makes sure to
        free all the resources used by the plugin.
        """
        print("CoverArtBrowser DEBUG - do_deactivate")
        self.source.delete_thyself()
        if self._externalmenu:
            self._externalmenu.cleanup(full_cleanup=True)
        del self.shell
        del self.db
        del self.source

        print("CoverArtBrowser DEBUG - end do_deactivate")

    def load_complete(self, *args, **kwargs):
        """
        Called by Rhythmbox when it has completed loading all data
        Used to automatically switch to the browser if the user
        has set in the preferences
        """

        gs = GSetting()
        setting = gs.get_setting(gs.Path.PLUGIN)

        if setting[gs.PluginKey.AUTOSTART]:
            self._externalmenu.autostart_source()

    def _translation_helper(self):
        """
        a method just to help out with translation strings
        it is not meant to be called by itself
        """

        # define .plugin text strings used for translation
        plugin = _('CoverArt Browser')
        desc = _('Browse and play your albums through their covers')

        # . TRANSLATORS: This is the icon-grid view that the user sees
        tile = _('Tiles')

        # . TRANSLATORS: This is the cover-flow view the user sees - they can swipe album covers from side-to-side
        artist = _('Flow')

        # . TRANSLATORS: percentage size that the image will be expanded
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
        self.locations = ['library-toolbar', 'queue-toolbar', 'playsource-toolbar']

        from coverart_browser_source import Views

        self._views = Views(self.shell)

        self._use_standard_control = True
        self.plugin.using_alternative_toolbar = hasattr(self.shell, 'alternative_toolbar')
        if self.plugin.using_alternative_toolbar:
            from alttoolbar_type import AltToolbarHeaderBar
            self.plugin.using_headerbar = isinstance(self.shell.alternative_toolbar.toolbar_type, AltToolbarHeaderBar)

        if self.plugin.using_headerbar:
            self._use_standard_control = False

            # register with headerbar to complete the setup for coverart-browser
            print("registering")
            self.shell.alternative_toolbar.toolbar_type.setup_completed_async(self._headerbar_toolbar_completed)

        if self._use_standard_control:
            # ... otherwise just use the standard menubutton approach
            self.source.props.visibility = True  # make the source visible
            gs = GSetting()
            setting = gs.get_setting(gs.Path.PLUGIN)
            setting.bind(gs.PluginKey.TOOLBAR_POS, self, 'toolbar_pos',
                         Gio.SettingsBindFlags.GET)

            self.connect('notify::toolbar-pos', self._on_notify_toolbar_pos)
            self.shell.props.display_page_tree.connect(
                "selected", self.on_page_change
            )

            self._create_menu()

    def autostart_source(self):
        self.source.props.visibility = True

        if self._use_standard_control:
            GLib.timeout_add(1000, self.shell.props.display_page_tree.select,
                             self.source)

        else:
            # mimic user clicking category button and cover switch
            self.shell.alternative_toolbar.toolbar_type.library_browser_radiobutton.set_active(True)
            self.shell.alternative_toolbar.toolbar_type.stack.set_visible_child_name("coverview")

    def _headerbar_toolbar_completed(self, *args):
        print("headerbar_toolbar_completed")
        # if we are using the alternative_toolbar and headerbar then setup the switch
        # which will control access to the various views
        self._sh_hcc = self.shell.alternative_toolbar.toolbar_type.connect('song-category-clicked',
                                                                           self._headerbar_category_clicked)
        self._add_coverart_header_switch()

        sources = {self.shell.props.queue_source,
                   self.shell.props.library_source,
                   self.source}

        for source in sources:
            self.shell.alternative_toolbar.toolbar_type.add_always_visible_source(source)

    def _on_notify_toolbar_pos(self, *args):
        # for standard menu control ... when moving the toolbar position reposition the menubutton
        if self.toolbar_pos == TopToolbar.name:
            self._create_menu()
        else:
            self.cleanup()

    def cleanup(self, full_cleanup=False):
        # for standard menu control, cleanup where necessary
        if self.app_id:
            app = Gio.Application.get_default()
            for location in self.locations:
                app.remove_plugin_menu_item(location, self.app_id)
            self.app_id = None

        if not self._use_standard_control and full_cleanup:
            self.shell.alternative_toolbar.toolbar_type.stack.disconnect(self._sh_stack_id)
            self.shell.alternative_toolbar.toolbar_type.stack.remove(self._box_coverview)
            self.shell.alternative_toolbar.toolbar_type.disconnect(self._sh_hcc)
            self.shell.alternative_toolbar.toolbar_type.headerbar.remove(self.stack_switcher)
            self.stack_switcher = None
            self._sh_stack_id = None
            self._sh_hcc = None

    def _create_menu(self):
        # for the standard menu control button add the button
        # to all supported view types
        app = Gio.Application.get_default()
        self.app_id = 'coverart-browser'

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

    def _add_coverart_header_switch(self):
        # define the header switch control + stack control for coverart
        self._box_coverview = Gtk.Box()
        image_name = 'view-cover-symbolic'
        stack = self.shell.alternative_toolbar.toolbar_type.stack
        stack.add_named(self._box_coverview, "coverview")
        stack.child_set_property(self._box_coverview, "icon-name", image_name)

        self.stack_switcher = Gtk.StackSwitcher()
        self.stack_switcher.set_stack(stack)
        self.stack_switcher.show_all()
        self.stack_switcher.set_sensitive(
            not self.shell.alternative_toolbar.toolbar_type.library_song_radiobutton.get_active())

        self.shell.alternative_toolbar.toolbar_type.headerbar.pack_start(self.stack_switcher)

        # create a treeview and store for all views coverart supports
        self._store = Gtk.ListStore(str, str)
        for view_name in self._views.get_view_names():
            self._store.append([self._views.get_menu_name(view_name), view_name])

        tree = Gtk.TreeView(self._store)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("CoverArt"), renderer, text=0)
        tree.append_column(column)
        tree.connect('button-press-event', self._tree_row_click)
        self.tree = tree

        self._box_coverview.pack_start(tree, True, True, 0)

        self._sh_stack_id = stack.connect('notify::visible-child-name', self._change_stack)
        stack.show_all()
        self.stack = stack

        self._current_tree_view = None

    def _change_stack(self, widget, value):
        print("changed stack")
        child_name = self.stack.get_visible_child_name()
        print(child_name)
        if child_name == "listview":
            self.source.props.visibility = False
            # if we've toggled to listview then we are no longer in coverart so reset back to songview
            self._current_tree_view = None
            self._select_view(ListView.name)
            if self.shell.alternative_toolbar.toolbar_type.library_song_radiobutton.get_active():
                self.stack_switcher.set_sensitive(False)
            return
        self.source.props.visibility = True

        # so we are in coverview so we need to reset the coverview to what was last selected when in this mode
        selection = self.tree.get_selection()
        liststore, list_iter = selection.get_selected()
        if not list_iter:
            # nothing was selected to set the view back to what was remembered
            self._current_tree_view = self._select_view(None)
            treeiter = liststore.get_iter_first()

            while treeiter != None:
                if liststore[treeiter][1] == self._current_tree_view:
                    print("about to set treeview")
                    print(treeiter)
                    path = liststore.get_path(treeiter)
                    print(path)
                    # self.tree.row_activated(liststore.get_path(treeiter), 0)
                    self.tree.set_cursor(path)
                    break
                treeiter = liststore.iter_next(treeiter)
        else:
            # we have been here before so set the view correctly
            path = liststore.get_path(list_iter)
            self._current_tree_view = liststore[path][1]
            self._select_view(liststore[path][1])

    def _headerbar_category_clicked(self, headerbar, song_category):

        print("clicked headerbar song-category buttons")
        if self.stack.get_visible_child_name() == 'coverview' and song_category:
            # if we've clicked song when in coverview then we disable the switcher
            # and set the view back to song

            # self.stack.set_visible_child_name('listview')

            # if self.shell.props.display_page_tree.select != self.shell.props.library_source:
            #    self._select_view(ListView.name)

            # self.stack_switcher.set_sensitive(not song_category)
            # self.stack_switcher.set_sensitive(False)
            self.source.props.visibility = True

            self._select_view(ListView.name)

        if self.stack.get_visible_child_name() == 'listview' and not song_category:
            # if we've clicked category when in listview then we enable the switcher
            self.stack_switcher.set_sensitive(True)
            self.source.props.visibility = False

        if self.stack.get_visible_child_name() == 'listview' and song_category:
            # if we've clicked song when in listview then we disable the switcher
            self.stack_switcher.set_sensitive(False)
            self.source.props.visibility = False

        if self.stack.get_visible_child_name() == 'coverview' and not song_category:
            # if we've clicked category when in coverview then we move to the last coverart view
            # and ensure the switcher is still enabled
            self.source.props.visibility = True

            self._select_view(None)
            self.stack_switcher.set_sensitive(True)

    def _tree_row_click(self, widget, event):
        """
        event called when clicking on a row in the header treeview
        """
        print('_tree_row_click')

        try:
            treepath, treecolumn, cellx, celly = widget.get_path_at_pos(event.x, event.y)
        except:
            return

        print(self._store[treepath][1])
        self._current_tree_view = self._store[treepath][1]
        self._select_view(self._store[treepath][1])

    def on_page_change(self, display_page_tree, page):
        """
        standard menubutton - Called when the display page changes. Grabs query models and sets the 
        active view.
        """
        print("on_page_change")
        if page == self.shell.props.library_source:
            self.action.set_state(self._views.get_action_name(ListView.name))
        elif page == self.shell.props.queue_source:
            self.action.set_state(self._views.get_action_name(QueueView.name))
        elif page == self.plugin.playlist_source:
            self.action.set_state(self._views.get_action_name(PlaySourceView.name))

    def view_change_cb(self, action, current):
        """
        standard menubutton - Called when the view state on a page is changed. Sets the new 
        state.
        """
        print("view_change_cb")
        action.set_state(current)
        view_name = self._views.get_view_name_for_action(current)
        self._select_view(view_name)

    def _select_view(self, view_name):
        """
          with the view_name decide which view to be displayed
          or if view_name is None then use the last remembered view_name
          
          return view_name
        """

        if not self.shell.props.display_page_tree:
            return

        print("_select_view")
        print(view_name)
        if view_name != ListView.name and \
                        view_name != QueueView.name and \
                        view_name != PlaySourceView.name:
            gs = GSetting()
            setting = gs.get_setting(gs.Path.PLUGIN)
            if view_name:
                setting[gs.PluginKey.VIEW_NAME] = view_name
            else:
                view_name = setting[gs.PluginKey.VIEW_NAME]
            player = self.shell.props.shell_player
            # player.set_selected_source(self.source) #.playlist_source)

            GLib.idle_add(self.shell.props.display_page_tree.select,
                          self.source)
        elif view_name == ListView.name:
            GLib.idle_add(self.shell.props.display_page_tree.select,
                          self.shell.props.library_source)
        elif view_name == QueueView.name:
            GLib.idle_add(self.shell.props.display_page_tree.select,
                          self.shell.props.queue_source)
        elif view_name == PlaySourceView.name:
            GLib.idle_add(self.shell.props.display_page_tree.select,
                          self.plugin.playlist_source)

        return view_name
