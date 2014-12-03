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
from gi.repository import Gtk
from gi.repository import RB
from gi.repository import GObject

from coverart_rb3compat import Menu
from coverart_external_plugins import CreateExternalPluginMenu
from coverart_entryview import CoverArtEntryView
from coverart_rb3compat import ActionGroup
from coverart_rb3compat import ApplicationShell
from coverart_browser_prefs import CoverLocale
import rb


class CoverArtPlayEntryView(CoverArtEntryView):
    __hash__ = GObject.__hash__

    def __init__(self, shell, source):
        '''
        Initializes the entryview.
        '''
        super(CoverArtPlayEntryView, self).__init__(shell, source)

    def define_menu(self):
        popup = Menu(self.plugin, self.shell)
        popup.load_from_file('N/A',
                             'ui/coverart_play_pop_rb3.ui')
        signals = {
            'remove_from_playlist_menu_item': self.remove_from_playlist_menu_item_callback
        }

        popup.connect_signals(signals)
        popup.connect('pre-popup', self.pre_popup_menu_callback)
        self.popup = popup

    def pre_popup_menu_callback(self, *args):
        '''
        Callback when the popup menu is about to be displayed
        '''

        if not self.external_plugins:
            self.external_plugins = \
                CreateExternalPluginMenu("playlist_entry_view", 1, self.popup)
            self.external_plugins.create_menu('play_popup_menu')

    def remove_from_playlist_menu_item_callback(self, *args):
        print("remove_from_playlist_menu_item_callback")
        entries = self.get_selected_entries()
        for entry in entries:
            print(entry)
            self.source.source_query_model.remove_entry(entry)

    def do_show_popup(self, over_entry):
        if over_entry:
            print("CoverArtBrowser DEBUG - do_show_popup()")

            self.popup.popup(self.source,
                             'play_popup_menu', 0, Gtk.get_current_event_time())

        return over_entry

    def play_track_menu_item_callback(self, *args):
        print("CoverArtBrowser DEBUG - play_track_menu_item_callback()")

        selected = self.get_selected_entries()
        entry = selected[0]

        # Start the music
        player = self.shell.props.shell_player
        player.play_entry(entry, self.source)

        print("CoverArtBrowser DEBUG - play_track_menu_item_callback()")


class CoverArtPlaySource(RB.Source):
    '''
    Source utilized by the plugin to show all it's ui.
    '''

    def __init__(self, **kwargs):
        '''
        Initializes the source.
        '''
        super(CoverArtPlaySource, self).__init__()
        self.external_plugins = None
        self.hasActivated = False

    def initialise(self, plugin, shell, source):
        self.plugin = plugin
        self.shell = shell
        self.source = source

    def do_selected(self):
        '''
        Called by Rhythmbox when the source is selected. It makes sure to
        create the ui the first time the source is shown.
        '''
        print("CoverArtBrowser DEBUG - do_selected")

        # first time of activation -> add graphical stuff
        if not self.hasActivated:
            self.do_impl_activate()

            # indicate that the source was activated before
            self.hasActivated = True

        print("CoverArtBrowser DEBUG - end do_selected")

    def connect_library_signals(self):
        pass

    def do_impl_activate(self):
        '''
        Called by do_selected the first time the source is activated.
        It creates all the source ui and connects the necessary signals for it
        correct behavior.
        '''
        print('do_impl_activate')
        self.hasActivated = True

        self.entryview = CoverArtPlayEntryView(self.shell, self.source)
        self.entryview.props.hexpand = True
        self.entryview.props.vexpand = True
        grid = Gtk.Grid()
        grid.attach(self.entryview, 0, 1, 1, 1)

        self.entryview.set_model(self.source.source_query_model)

        # enable sorting on the entryview
        # entryview.set_columns_clickable(True)
        self.shell.props.library_source.get_entry_view().set_columns_clickable(
            True)

        cl = CoverLocale()
        cl.switch_locale(cl.Locale.LOCALE_DOMAIN)
        location = rb.find_plugin_file(self.plugin, 'ui/playsource-toolbar.ui')
        ui = Gtk.Builder()
        ui.set_translation_domain(cl.Locale.RB)
        ui.add_from_file(location)
        toolbar_menu = ui.get_object('playsource-toolbar')
        app = self.shell.props.application
        app.link_shared_menus(toolbar_menu)
        bar = RB.ButtonBar.new(toolbar_menu, toolbar_menu)
        grid.attach(bar, 0, 0, 1, 1)

        grid.show_all()
        self.pack_start(grid, True, True, 0)

        appshell = ApplicationShell(self.shell)
        action_group = ActionGroup(self.shell, 'PlaySourceActions')
        action_group.add_action(func=self.clear_playsource,
                                action_name='playsource-clear', action_state=ActionGroup.STANDARD,
                                action_type='app')
        action_group.add_action(func=self.shuffle_playsource,
                                action_name='playsource-shuffle', action_state=ActionGroup.STANDARD,
                                action_type='app')
        appshell.insert_action_group(action_group)

    def clear_playsource(self, *args):
        for row in self.entryview.props.model:
            self.entryview.props.model.remove_entry(row[0])

    def shuffle_playsource(self, *args):
        self.entryview.props.model.shuffle_entries()


GObject.type_register(CoverArtPlayEntryView)
