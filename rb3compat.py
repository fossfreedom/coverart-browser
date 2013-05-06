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


def unicodestr(param, charset):
    if PYVER >=3:
        return str(param, charset)
    else:
        return unicode(param, charset)
    
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
        
def is_rb3(shell):
	if hasattr( shell.props.window, 'add_action' ):
		return True
	else:
		return False 	
		
class Menu(object):
	def __init__(self, source, plugin, shell):
		self.plugin = plugin
		self.shell = shell
		self.source = source
		
	def load_from_file(self, rb2_ui_filename, rb3_ui_filename ):
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
        
    def connect_rb3_signals(self, signals):
		def _menu_connect(action_name, func):
			action = Gio.SimpleAction(name=action_name)
			action.connect('activate', func)
			action.set_enabled(True)
			self.shell.props.window.add_action(action)
			
		for key,value in signals.items():
			_menu_connect( key, value)
		
	def connect_rb2_signals(self, signals):
		def _menu_connect(menu_item_name, func):
			menu_item = self.builder.get_object(menu_item_name)
			menu_item.connect('activate', func)
			
		for key,value in signals.items():
			_menu_connect( key, value)
			
	def connect_signals(self, signals):
		if is_rb3(self.shell):
			self.connect_rb3_signals(signals)
		else:
			self.connect_rb2_signals(signals)
			
	def get_menu_object(self, menu_name):
		item = self.builder.get_object(menu_name)
		
		if is_rb3(self.shell):
			popup_menu = Gtk.Menu.new_from_model(item)
		else:
			popup_menu = item
			
		popup_menu.attach_to_widget(self.source, None)
			
		return popup_menu

	def set_sensitive(self, menu_or_action_item, enable):
		
		if is_rb3(self.shell):
			item = self.shell.props.window.lookup_action(menu_or_action_item)
			item.set_enabled(enable)
		else:
			item = self.builder.get_object(menu_or_action_item)
			item.set_sensitive(enable)
			
class ActionGroup(object):
	def __init__(self, shell, group_name):
		self.group_name = group_name
		
		if is_rb3(shell):
			self.actiongroup = Gio.SimpleActionGroup()
		else:			
			self.actiongroup = Gtk.ActionGroup(group_name)
			uim = shell.props.ui_manager
			uim.insert_action_group(self.actiongroup)
	
