# -*- Mode: python; coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
#
# Copyright (C) 2012 - fossfreedom
# Copyright (C) 2012 - Agustin Carrasco
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of thie GNU General Public License as published by
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

from gi.repository import Peas
from gi.repository import GObject
import lxml.etree as ET

import rb
from coverart_rb3compat import ActionGroup
from coverart_rb3compat import ApplicationShell
from coverart_utils import CaseInsensitiveDict


class ExternalPlugin(GObject.Object):
    """
    class for all supported ExternalPlugins
    """

    def __init__(self, **kargs):
        super(ExternalPlugin, self).__init__(**kargs)

        # dict of attributes associated with the external plugin
        self.attributes = {}
        self.attributes['is_album_menu'] = False
        self.attributes['new_menu_name'] = ''
        self.attributes['action_type'] = ''
        self.attributes['action_group_name'] = ''

    def appendattribute(self, key, val):
        """
        append another attribute to the dict
        
        :param key: `str` name of attribute
        :param val: `str` value of attribute
        """

        if key == 'is_album_menu':
            if val == 'yes':
                self.attributes[key] = True
            else:
                self.attributes[key] = False
        else:
            self.attributes[key] = val

    def is_activated(self):
        """
        method to test whether the plugin is actually loaded. Returns a bool
        """
        peas = Peas.Engine.get_default()
        loaded_plugins = peas.get_loaded_plugins()

        if self.attributes['plugin_name'] in CaseInsensitiveDict(loaded_plugins):
            print("found %s" % self.attributes['plugin_name'])
            return True

        print("search for %s" % self.attributes['plugin_name'])
        print(loaded_plugins)

        return False

    def create_menu_item(self, menubar, section_name, at_position,
                         save_actiongroup, save_menu, for_album=False):
        """
        method to create the menu item appropriate to the plugin.
        A plugin can have many menu items - all menuitems are enclosed
        in a section.
        
        :param menubar: `str` name for the GtkMenu - ignored for RB2.99
        :param section_name: `str` unique name of the section holding the menu items
        :param at_position: `int` position within the GtkMenu to create menu - ignored for RB2.99
        :param save_actiongroup: `ActionGroup` container for all menu-item Actions
        :param save_menu: `Menu` whole popupmenu including sub-menus
        :param for_album: `bool` create the menu for the album - if not given
          then its assumed the menu item is appropriate just for tracks
        """
        if for_album and not self.attributes['is_album_menu']:
            return False

        if not self.is_activated():
            return False

        action = ApplicationShell(save_menu.shell).lookup_action(self.attributes['action_group_name'],
                                                                 self.attributes['action_name'],
                                                                 self.attributes['action_type'])

        if action:
            self.attributes['action'] = action

            if self.attributes['new_menu_name'] != '':
                self.attributes['label'] = self.attributes['new_menu_name']
            else:
                self.attributes['label'] = action.label
                # self.attributes['sensitive']=action.get_sensitive()
        else:
            print("action not found")
            print(self.attributes)
            return False

        action = save_actiongroup.add_action(func=self.menuitem_callback,
                                             action_name=self.attributes['action_name'], album=for_album,
                                             shell=save_menu.shell, label=self.attributes['label'])

        new_menu_item = save_menu.insert_menu_item(menubar, section_name,
                                                   at_position, action)
        return new_menu_item

    def do_deactivate(self):
        pass

    def set_entry_view_selected_entries(self, shell):
        """
        method called just before the external plugin action is activated

        Normally only called for album menus to mimic selecting all the
        EntryView rows
        """
        page = shell.props.selected_page
        if not hasattr(page, "get_entry_view"):
            return

        page.get_entry_view().select_all()

    def activate(self, shell):
        """
        method called to initiate the external plugin action
        the action is defined by defining the action_group_name, action_name and action_type
        """

        action = ApplicationShell(shell).lookup_action(self.attributes['action_group_name'],
                                                       self.attributes['action_name'],
                                                       self.attributes['action_type'])

        if action:
            action.activate()

    def menuitem_callback(self, action, param, args):
        """
        method called when a menu-item is clicked.  Basically, an Action
        is activated by the user
        
        :param action: `Gio.SimpleAction` or `Gtk.Action`
        :param param: Not used
        :param args: dict associated with the action
        """
        for_album = args['album']
        shell = args['shell']
        if for_album:
            self.set_entry_view_selected_entries(shell)

        self.attributes['action'].activate()


class CreateExternalPluginMenu(GObject.Object):
    """
    This is the key class called to initialise all supported plugins
    
    :param section_name: `str` unique name of the section holding the menu items
    :param at_position: `int` position within the GtkMenu to create menu - ignored for RB2.99
    :param popup: `Menu` whole popupmenu including sub-menus
    """

    def __init__(self, section_name, at_position, popup, **kargs):
        super(CreateExternalPluginMenu, self).__init__(**kargs)

        self.menu = popup
        self.section_name = section_name
        self.at_position = at_position

        self._actiongroup = ActionGroup(popup.shell, section_name + '_externalplugins')

        # all supported plugins will be defined in the following array by parsing
        # the plugins XML file for the definition.

        self.supported_plugins = []

        extplugins = rb.find_plugin_file(popup.plugin, 'ui/coverart_external_plugins.xml')
        root = ET.parse(open(extplugins)).getroot()

        base = 'rb3/plugin'

        for elem in root.xpath(base):
            pluginname = elem.attrib['name']

            basemenu = base + "[@name='" + pluginname + "']/menu"

            for menuelem in root.xpath(basemenu):
                ext = ExternalPlugin()
                ext.appendattribute('plugin_name', pluginname)

                label = menuelem.attrib['label']
                if label != "":
                    ext.appendattribute('new_menu_name', label)
                    baseattrib = basemenu + "[@label='" + label + "']/attribute"
                else:
                    baseattrib = basemenu + "/attribute"

                for attribelem in root.xpath(baseattrib):
                    key = attribelem.attrib['name']
                    val = attribelem.text
                    ext.appendattribute(key, val)

                self.supported_plugins.append(ext)

    def create_menu(self, menu_name, for_album=False):
        """
        method to create the menu items for all supported plugins

        :param menu_name: `str` unique name (GtkMenu) id for the menu to create
        :for_album: `bool` - create a menu applicable for Albums
          by default a menu is assumed to be applicable to a track in an
          EntryView
        """
        self.menu_name = menu_name

        self._actiongroup.remove_actions()
        self.menu.remove_menu_items(self.menu_name, self.section_name)

        items_added = False

        for plugin in self.supported_plugins:
            new_menu_item = plugin.create_menu_item(self.menu_name, self.section_name,
                                                    self.at_position, self._actiongroup, self.menu, for_album)

            if (not items_added) and new_menu_item:
                items_added = True

        if items_added:
            self.menu.insert_separator(self.menu_name, self.at_position)
