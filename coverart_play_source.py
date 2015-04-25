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
from gi.repository import GLib
from gi.repository import Gdk

from coverart_rb3compat import Menu
from coverart_external_plugins import CreateExternalPluginMenu
from coverart_entryview import CoverArtEntryView
from coverart_rb3compat import ActionGroup
from coverart_rb3compat import ApplicationShell
from coverart_browser_prefs import CoverLocale
from coverart_widgets import PressButton
from coverart_utils import create_button_image
import xml.etree.ElementTree as ET

import rb
import os

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


class CoverArtPlaySource(RB.BrowserSource):
    def __init__(self, **kwargs):
        '''
        Initializes the source.
        '''
        super(CoverArtPlaySource, self).__init__(**kwargs)
        #self.external_plugins = None
        self.hasActivated = False

        self.save_in_progress = False
        self.save_interrupt = False
        self.filename = RB.user_cache_dir() + "/coverart_browser/playlist.xml"

    def do_selected(self):
        '''
        Called by Rhythmbox when the source is selected. It makes sure to
        create the ui the first time the source is showed.
        '''
        print("CoverArtBrowser DEBUG - do_selected")

        # first time of activation -> add graphical stuff
        if not self.hasActivated:
            self.do_impl_activate()

            # indicate that the source was activated before
            self.hasActivated = True

        print("CoverArtBrowser DEBUG - end do_selected")


    def do_impl_activate(self):
        '''
        Called by do_selected the first time the source is activated.
        It creates all the source ui and connects the necessary signals for it
        correct behavior.
        '''
        print('do_impl_activate')

        self.plugin = self.props.plugin
        self.shell = self.props.shell

        player = self.shell.props.shell_player
        player.set_playing_source(self)
        player.set_selected_source(self)


        # define a query model that we'll use for playing
        self.source_query_model = self.plugin.source_query_model

        grid = Gtk.Grid()

        self.entryview = self.get_entry_view()

        child = self.get_children()
        print (child)

        grid = child[0]
        self.rbsourcetoolbar = grid.get_children()[1] # need to remember the reference to stop crashes when python cleans up unlinked objects
        grid.remove(grid.get_children()[1])

        self.get_entry_view().set_model(self.source_query_model)
        '''
        # enable sorting on the entryview
         entryview.set_columns_clickable(True)
        self.shell.props.library_source.get_entry_view().set_columns_clickable(
            True)
        '''
        cl = CoverLocale()
        cl.switch_locale(cl.Locale.LOCALE_DOMAIN)
        location = rb.find_plugin_file(self.plugin, 'ui/playsource-toolbar.ui')
        ui = Gtk.Builder()
        ui.set_translation_domain(cl.Locale.RB)
        ui.add_from_file(location)
        toolbar_menu = ui.get_object('playsource-toolbar')
        app = self.shell.props.application
        app.link_shared_menus(toolbar_menu)
        self.toolbar = RB.ButtonBar.new(toolbar_menu, toolbar_menu)
        self.toolbar.props.hexpand_set = False
        grid.attach(self.toolbar, 0, 0, 1, 1)

        grid.show_all()

        appshell = ApplicationShell(self.shell)
        action_group = ActionGroup(self.shell, 'PlaySourceActions')
        action_group.add_action(func=self.clear_playsource,
                                action_name='playsource-clear', action_state=ActionGroup.STANDARD,
                                action_type='app')
        action_group.add_action(func=self.shuffle_playsource,
                                action_name='playsource-shuffle', action_state=ActionGroup.STANDARD,
                                action_type='app')
        appshell.insert_action_group(action_group)


        # if the alternative-toolbar is loaded then lets connect to the toolbar-visibility signal
        # to control our sources toolbar visibility

        #if hasattr(self.shell, 'alternative_toolbar'):
        #    self.shell.alternative_toolbar.connect('toolbar-visibility', self._visibility)

        self._load_model()

        self.source_query_model.connect('row-inserted', self.save_changed_model)
        self.source_query_model.connect('row-changed', self.save_changed_model)
        self.source_query_model.connect('row-deleted', self.save_changed_model)

    def _load_model(self):
        if not os.path.isfile(self.filename):
            return

        parser = ET.XMLParser(encoding="utf-8")
        tree = ET.parse(self.filename, parser=parser)

        root = tree.getroot()

        for child in root.findall('./entry/text'):
            location = child.text
            entry = self.shell.props.db.entry_lookup_by_location(location)
            if entry:
                self.source_query_model.add_entry(entry, -1)

        self.props.query_model = self.source_query_model

    def clear_playsource(self, *args):
        for row in self.get_entry_view().props.model:
            self.get_entry_view().props.model.remove_entry(row[0])

    def shuffle_playsource(self, *args):
        self.get_entry_view().props.model.shuffle_entries()
        self._save_model()

    def save_changed_model(self, *args):

        if self.save_in_progress:
            self.save_interrupt = True
            return

        self.save_in_progress = True

        Gdk.threads_add_timeout_seconds(GLib.PRIORITY_DEFAULT_IDLE, 1, self._save_model, None)

    def _save_model(self, *args):
        if self.save_interrupt:
            self.save_interrupt = False
            return True

        root = ET.Element('root')
        element = ET.SubElement(root, 'entry')
        for row in self.source_query_model:
            location = row[0].get_string(RB.RhythmDBPropType.LOCATION)
            subelement = ET.SubElement(element, 'text')
            subelement.text = location

        tree = ET.ElementTree(root)
        tree.write(self.filename)

        self.save_in_progress = False
        return False

GObject.type_register(CoverArtPlayEntryView)
