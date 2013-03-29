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
from gi.repository import Gtk

class ExternalPlugin(GObject.Object):
    '''
    Base class for all supported ExternalPlugins
    At a minimum, the following `attributes` keys must be defined:
    
    :plugin_name: `str` module name of the plugin
    :action_group_name: `str` plugin GtkActionGroup
    :action: `str` plugin GtkAction - this is the action which is activated
    :is_album_menu: `bool` if the menu is applicable to albums
       by default, menus are created only for EntryViews
    '''
    def __init__(self, **kargs):
        super(ExternalPlugin, self).__init__(**kargs)

        self.attributes = {}
        self.attributes['is_album_menu'] = False

    def is_activated(self):
        '''
        method to test whether the plugin is actually loaded. Returns a bool
        '''
        peas = Peas.Engine.get_default()
        loaded_plugins = peas.get_loaded_plugins()

        print loaded_plugins
        if self.attributes['plugin_name'] in loaded_plugins:
            return True

        return False

    def create_menu_item(self, menu_name, shell,
        save_actiongroup, for_album = False):
        '''
        method to create the menu item appropriate to the plugin
        
        :menu_name: `str` unique name for the calling (popup) menu
        :shell: `RB.Shell` rhythmbox shell
        :save_actiongroup: `GtkActionGroup` - this is our action-group
          where our menus are described
        :for_album: `bool` create the menu for the album - if not given
          then its assumed the menu item is appropriate just for tracks
        '''

        if for_album and not self.attributes['is_album_menu']:
            return False
            
        if not self.is_activated():
            return False

        uim = shell.props.ui_manager
        ui_actiongroups = uim.get_action_groups()

        actiongroup = None
        for actiongroup in ui_actiongroups:
            if actiongroup.get_name() == self.attributes['action_group_name']:
                break

        action = None
        if actiongroup:
            action = actiongroup.get_action(self.attributes['action_name'])

        if action:
            self.attributes['action']=action
            self.attributes['tooltip']=action.get_tooltip()
            self.attributes['label']=action.get_label()
            self.attributes['visible']=action.get_visible()
            self.attributes['sensitive']=action.get_sensitive()
        else:
            return False

        new_menu_item = Gtk.MenuItem(label=self.attributes['label'])
        new_menu_item.set_visible(self.attributes['visible'])
        new_menu_item.set_sensitive(self.attributes['sensitive'])

        action = Gtk.Action(label=self.attributes['label'],
            name=menu_name + self.attributes['label'],
            tooltip=self.attributes['tooltip'], stock_id=Gtk.STOCK_CLEAR)
           
        action.connect('activate', self.menuitem_callback, for_album, shell)
        new_menu_item.set_related_action(action)
        save_actiongroup.add_action(action)

        return new_menu_item
        
    def do_deactivate(self):
        pass

    def set_entry_view_selected_entries(self, shell):
        '''
        method called just before the external plugin action is activated

        Normally only called for album menus to mimic selecting all the
        EntryView rows
        '''
        page = shell.props.selected_page
        if not hasattr(page, "get_entry_view"):
            return

        page.get_entry_view().select_all()

    def menuitem_callback(self, menu, for_album, shell):
        '''
        method called when a menu-item is clicked
        '''
        if for_album:
            self.set_entry_view_selected_entries(shell)
            
        self.attributes['action'].activate()

class OpenContainingFolder(ExternalPlugin):
    def __init__(self, **kargs):
        super(OpenContainingFolder, self).__init__(**kargs)
        
        self.attributes['plugin_name'] = 'opencontainingfolder'
        self.attributes['action_group_name'] = 'OpenContainingFolderActions'
        self.attributes['action_name'] = 'OpenContainingFolder'
        self.attributes['is_album_menu'] = True

class SendFirst(ExternalPlugin):
    def __init__(self, **kargs):
        super(SendFirst, self).__init__(**kargs)

        self.attributes['plugin_name'] = 'send_first'
        self.attributes['action_group_name'] = 'SendFirstPluginActionGroup'
        self.attributes['action_name'] = 'QueueFirstAction'
        self.attributes['is_album_menu'] = True

class SendTo(ExternalPlugin):
    def __init__(self, **kargs):
        super(SendTo, self).__init__(**kargs)

        self.attributes['plugin_name'] = 'sendto'
        self.attributes['action_group_name'] = 'SendToActionGroup'
        self.attributes['action_name'] = 'SendTo'
        self.attributes['is_album_menu'] = True

class LastFMExtensionFingerprinter(ExternalPlugin):
    def __init__(self, **kargs):
        super(LastFMExtensionFingerprinter, self).__init__(**kargs)

        self.attributes['plugin_name'] = 'lastfm_extension'
        self.attributes['action_group_name'] = 'LastFMExtensionFingerprinter'
        self.attributes['action_name'] = 'FingerprintSong'
        self.attributes['is_album_menu'] = False

class CreateExternalPluginMenu(GObject.Object):
    '''
    This is the key class called to initialise all supported plugins
    
    :menu_name: `str` unique name of the (popup) menu
    :shell: `RB.Shell` plugin shell attribute
    '''
    def __init__(self, menu_name, shell, **kargs):
        super(CreateExternalPluginMenu, self).__init__(**kargs)

        self.menu_name = menu_name
        self.shell = shell
        self._actiongroup = Gtk.ActionGroup(menu_name + '_externalplugins')
        self._menu_array = []

        # all supported plugins MUST be defined in the following array
        self.supported_plugins = [
            OpenContainingFolder(),
            SendFirst(),
            SendTo(),
            LastFMExtensionFingerprinter() ]

    def create_menu(self, menu_bar, at_position, for_album = False):
        '''
        method to create the menu items for all supported plugins

        :menu_bar: `GtkMenu` - where the menu-items are to be added
        :at_position: `int` - position in the menu list where menu-items
           are to be added
        :for_album: `bool` - create a menu applicable for Albums
          by default a menu is assumed to be applicable to a track in an
          EntryView
        '''
        
        #tidy up old menu items before recreating the list
        for action in self._actiongroup.list_actions():
            print "removing"
            self._actiongroup.remove_action(action)

        for menu_item in self._menu_array:
            menu_bar.remove(menu_item)

        self._menu_array = []

        for plugin in self.supported_plugins:
            menu_item = plugin.create_menu_item(self.menu_name,
                self.shell, self._actiongroup, for_album)

            if menu_item:
                self._menu_array.append(menu_item)

        if len(self._menu_array) > 0:
            menu_item = Gtk.SeparatorMenuItem().new()
            menu_item.set_visible(True)
            self._menu_array.append(menu_item)

        for menu_item in self._menu_array:
            menu_bar.insert(menu_item, at_position)

        uim = self.shell.props.ui_manager
        menu_bar.show_all()
        uim.ensure_update()
