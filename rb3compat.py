# -*- Mode: python; coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
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

from gi.repository import Gtk
from gi.repository import Gio
import sys
import rb

PYVER = sys.version_info[0]

if PYVER >= 3:
    import urllib.request, urllib.parse, urllib.error
else:
    import urllib
    from urlparse import urlparse as rb2urlparse

if PYVER >= 3:
    import http.client
else:
    import httplib
    
def responses():
    if PYVER >=3:
        return http.client.responses
    else:
        return httplib.responses

def unicodestr(param, charset):
    if PYVER >=3:
        return str(param, charset)
    else:
        return unicode(param, charset)
        
def unicodeencode(param, charset):
    if PYVER >=3:
        return str(param).encode(charset)
    else:
        return unicode(param).encode(charset)

def urlparse(uri):
    if PYVER >=3:
        return urllib.parse.urlparse(uri)
    else:
        return rb2urlparse(uri)
        
def url2pathname(url):
    if PYVER >=3:
        return urllib.request.url2pathname(url)
    else:
        return urllib.url2pathname(url)

def urlopen(filename):
    if PYVER >=3:
        return urllib.request.urlopen(filename)
    else:
        return urllib.urlopen(filename)
        
def pathname2url(filename):
    if PYVER >=3:
        return urllib.request.pathname2url(filename)
    else:
        return urllib.pathname2url(filename)

def unquote(uri):
    if PYVER >=3:
        return urllib.parse.unquote(uri)
    else:
        return urllib.unquote(uri)
                
def quote(uri, safe=None):
    if PYVER >=3:
        if safe:
            return urllib.parse.quote(uri,safe=safe)
        else:
            return urllib.parse.quote(uri)
    else:
        if safe:
            return urllib.quote(uri, safe=safe)
        else:
            return urllib.quote(uri)
        
def quote_plus(uri):
    if PYVER >=3:
        return urllib.parse.quote_plus(uri)
    else:
        return urllib.quote_plus(uri)

        
def is_rb3(shell):
	if hasattr( shell.props.window, 'add_action' ):
		return True
	else:
		return False 	
		
class Menu(object):
    '''
    Menu object used to create window popup menus
    '''
	def __init__(self, source, plugin, shell):
        '''
        Initializes the menu.
        '''
		self.plugin = plugin
		self.shell = shell
		self.source = source
        
        self._rb3menu_items = {}
        
    def add_menu_item(self, menubar, label, action):
        '''
        add a new menu item to the popup
        :param menubar: `str` is the name of the section to add the item to
        :param label: `str` is the text of the menu item displayed to the user
        :param action: `GtkAction` or `Gio.SimpleAction associated with the menu item
        '''
        if is_rb3(self.shell):
            app = self.shell.props.application
            item = Gio.MenuItem()
            item.set_label(label)
            item.set_detailed_action('win.'+label)
            
            if not menubar in self._rb3menu_items:
                self._rb3menu_items[menubar] = []
            self._rb3menu_items[menubar].append(label)
            
            app.add_plugin_menu_item(menubar, label, item)
        else:
            new_menu_item = Gtk.MenuItem(label=label)
            new_menu_item.set_related_action(action)
            bar = self.get_menu_object(menubar)
            bar.append(new_menu_item)
            bar.show_all()
            uim = self.shell.props.ui_manager
            uim.ensure_update()
            
        
    def remove_menu_items(self, menubar):
        '''
        utility function to remove all menuitems associated with the menu section
        :param menubar: `str` is the name of the section containing the menu items
        '''
        if is_rb3(self.shell):
            
            if not menubar in self._rb3menu_items:
                return
                
            app = self.shell.props.application
            
            for menu_item in self._rb3menu_items[menubar]:
                app.remove_plugin_menu_item(menubar, menu_item)
                
            del self._rb3menu_items[menubar][:]
            
        else:
            uim = self.shell.props.ui_manager
            count = 0

            bar = self.get_menu_object(menubar)
            for menu_item in bar:
                if count > 1:  # ignore the first two menu items
                    bar.remove(menu_item)
                count += 1

            bar.show_all()
            uim.ensure_update()
		
	def load_from_file(self, rb2_ui_filename, rb3_ui_filename ):
        '''
        utility function to load the menu structure
        :param rb2_ui_filename: `str` RB2.98 and below UI file
        :param rb3_ui_filename: `str` RB2.99 and higher UI file
        '''
		from coverart_browser_prefs import CoverLocale
		cl = CoverLocale()
		self.builder = Gtk.Builder()
        self.builder.set_translation_domain(cl.Locale.LOCALE_DOMAIN)
        
        if is_rb3(self.shell):
			ui_filename = rb3_ui_filename
		else:
			ui_filename = rb2_ui_filename
			
        self.builder.add_from_file(rb.find_plugin_file(self.plugin,
            ui_filename))
            			
        self.builder.connect_signals(self.source)
        
    def _connect_rb3_signals(self, signals):
		def _menu_connect(action_name, func):
			action = Gio.SimpleAction(name=action_name)
			action.connect('activate', func)
			action.set_enabled(True)
			self.shell.props.window.add_action(action)
			
		for key,value in signals.items():
			_menu_connect( key, value)
		
	def _connect_rb2_signals(self, signals):
		def _menu_connect(menu_item_name, func):
			menu_item = self.builder.get_object(menu_item_name)
			menu_item.connect('activate', func)
			
		for key,value in signals.items():
			_menu_connect( key, value)
			
	def connect_signals(self, signals):
        '''
        connect all signal handlers with their menuitem counterparts
        :param signals: `dict` key is the name of the menuitem 
             and value is the function callback when the menu is activated
        '''		
        if is_rb3(self.shell):
			self._connect_rb3_signals(signals)
		else:
			self._connect_rb2_signals(signals)
            
    def create_gtkmenu(self, popup_name):
        '''
        utility function to obtain the GtkMenu from the menu UI file
        :param popup_name: `str` is the name menu-id in the UI file
        '''
        item = self.builder.get_object(popup_name)
        
        if is_rb3(self.shell):
            app = self.shell.props.application
            app.link_shared_menus(item)
            popup_menu = Gtk.Menu.new_from_model(item)
            popup_menu.attach_to_widget(self.source, None)
        else:
            popup_menu = item
        
        return popup_menu
			
	def get_menu_object(self, menu_name_or_link):
        '''
        utility function returns the GtkMenuItem/Gio.MenuItem
        :param menu_name_or_link: `str` to search for in the UI file
        '''
		item = self.builder.get_object(menu_name_or_link)
		
		if is_rb3(self.shell):
            if item:
                popup_menu = item
            else:
                app = self.shell.props.application
                popup_menu = app.get_plugin_menu(menu_name_or_link)
		else:
			popup_menu = item
			
		return popup_menu

	def set_sensitive(self, menu_or_action_item, enable):
		'''
        utility function to enable/disable a menu-item
        :param menu_or_action_item: `GtkMenuItem` or `Gio.SimpleAction`
           that is to be enabled/disabled
        :param enable: `bool` value to enable/disable
        '''
        
		if is_rb3(self.shell):
			item = self.shell.props.window.lookup_action(menu_or_action_item)
			item.set_enabled(enable)
		else:
			item = self.builder.get_object(menu_or_action_item)
			item.set_sensitive(enable)
			
class ActionGroup(object):
	def __init__(self, shell, group_name):
		self.group_name = group_name
		self.shell = shell
        
		if is_rb3(self.shell):
			self.actiongroup = Gio.SimpleActionGroup()
		else:			
			self.actiongroup = Gtk.ActionGroup(group_name)
			uim = self.shell.props.ui_manager
			uim.insert_action_group(self.actiongroup)
            
    def remove_actions(self):
        for action in self.actiongroup.list_actions():
            self.actiongroup.remove_action(action)
            
    def add_action(self, func, action_name, *args):
        if is_rb3(self.shell):
            action = Gio.SimpleAction.new(action_name, None)
            action.connect('activate', func, args)
            self.shell.props.window.add_action(action)
            self.actiongroup.add_action(action)
        else:
            action = Gtk.Action(label=action_name,
                name=action_name,
               tooltip='', stock_id=Gtk.STOCK_CLEAR)
            action.connect('activate', func, None, args)
            self.actiongroup.add_action(action)
	
        return action
