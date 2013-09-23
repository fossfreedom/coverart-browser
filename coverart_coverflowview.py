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

from coverart_external_plugins import CreateExternalPluginMenu
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gio
from coverart_browser_prefs import GSetting
from coverart_browser_prefs import webkit_support
from coverart_album import AlbumsModel
from coverart_widgets import AbstractView
from coverart_widgets import PanedCollapsible
import rb
import json
import os
from os.path import expanduser
from xml.sax.saxutils import escape
from collections import namedtuple

class FlowShowingPolicy(GObject.Object):
    '''
    Policy that mostly takes care of how and when things should be showed on
    the view that makes use of the `AlbumsModel`.
    '''

    def __init__(self, flow_view):
        super(FlowShowingPolicy, self).__init__()

        self._flow_view = flow_view
        self.counter = 0
        self._has_initialised = False

    def initialise(self, album_manager):
        if self._has_initialised:
            return

        self._has_initialised = True
        self._album_manager = album_manager
        self._model = album_manager.model

class CoverFlowView(AbstractView):
    __gtype_name__ = "CoverFlowView"

    name = 'coverflowview'

    #properties
    flow_background = GObject.property(type=str, default='W')
    flow_automatic = GObject.property(type=bool, default=False)
    flow_scale = GObject.property(type=int, default=100)
    flow_hide = GObject.property(type=bool, default=False)
    flow_width = GObject.property(type=int, default=600)
    flow_appearance = GObject.property(type=str, default='coverflow')
    flow_max = GObject.property(type=int, default=100)
    panedposition = PanedCollapsible.Paned.EXPAND

    def __init__(self):
        super(CoverFlowView, self).__init__()
        
        self.ext_menu_pos = 0
        self._external_plugins = None
        self.show_policy = FlowShowingPolicy(self)
        if webkit_support():
            from gi.repository import WebKit
            self.view = WebKit.WebView()
        else:
            self.view = None
            
        self._last_album = None
        self._has_initialised = False
        self._filter_changed_inprogress = False
        self._on_first_use = True
        
    def _connect_properties(self):
        gs = GSetting()
        settings = gs.get_setting(gs.Path.PLUGIN)
        settings.bind(gs.PluginKey.FLOW_APPEARANCE, self,
            'flow_appearance', Gio.SettingsBindFlags.GET)
        settings.bind(gs.PluginKey.FLOW_HIDE_CAPTION, self,
            'flow_hide', Gio.SettingsBindFlags.GET)
        settings.bind(gs.PluginKey.FLOW_SCALE, self,
            'flow_scale', Gio.SettingsBindFlags.GET)
        settings.bind(gs.PluginKey.FLOW_AUTOMATIC, self,
            'flow_automatic', Gio.SettingsBindFlags.GET)
        settings.bind(gs.PluginKey.FLOW_BACKGROUND_COLOUR, self,
            'flow_background', Gio.SettingsBindFlags.GET)
        settings.bind(gs.PluginKey.FLOW_WIDTH, self,
            'flow_width', Gio.SettingsBindFlags.GET)
        settings.bind(gs.PluginKey.FLOW_MAX, self,
            'flow_max', Gio.SettingsBindFlags.GET)
            
    def _connect_signals(self, source):
        self.connect('notify::flow-background',
            self.filter_changed)
        self.connect('notify::flow-scale',
            self.filter_changed)
        self.connect('notify::flow-hide',
            self.filter_changed)
        self.connect('notify::flow-width',
            self.filter_changed)
        self.connect('notify::flow-appearance',
            self.filter_changed)
        self.connect('notify::flow-max',
            self.filter_changed)

    def filter_changed(self, *args):
        # we can get several filter_changed calls per second
        # lets simplify the processing & potential flickering when the
        # call to this method has slowed stopped
        
        self._filter_changed_event = True

        if self._filter_changed_inprogress:
            return

        self._filter_changed_inprogress = True

        def filter_events(*args):
            if not self._filter_changed_event:
                self._filter_changed()
                self._filter_changed_inprogress = False
            else:
                self._filter_changed_event = False
                return True
                
        Gdk.threads_add_timeout(GLib.PRIORITY_DEFAULT_IDLE, 250, filter_events, None)
        
    
    def _filter_changed(self, *args):
        path = rb.find_plugin_file(self.plugin, 'coverflow/index.html')
        f = open(path)
        string = f.read()
        f.close()
    
        if self.flow_background == 'W':
            background_colour = 'white'
            if len(self.album_manager.model.store) <= self.flow_max:
                foreground_colour = 'white'
            else:
                foreground_colour = 'black'
        else:
            background_colour = 'black'
            if len(self.album_manager.model.store) <= self.flow_max:
                foreground_colour = 'black'
            else:
                foreground_colour = 'white'

        string = string.replace('#BACKGROUND_COLOUR', background_colour)
        string = string.replace('#FOREGROUND_COLOUR', foreground_colour)
        string = string.replace('#FACTOR', str(float(self.flow_scale)/100))

        if  self.flow_hide:
            caption = ""
        else:
            caption = '<div class="globalCaption"></div>'
            
        string = string.replace('#GLOBAL_CAPTION', caption)

        addon = background_colour
        if self.flow_appearance == 'flow-vert':
            addon += " vertical"
        elif self.flow_appearance == 'carousel':
            addon += " carousel"
        elif self.flow_appearance == 'roundabout':
            addon += " roundabout"

        string = string.replace('#ADDON', addon)

        string = string.replace('#WIDTH', str(self.flow_width))

        identifier = self.flow.get_identifier(self.last_album)
        if not identifier:
            identifier = "'start'"
        else:
            identifier = str(identifier)
            
        string = string.replace('#START', identifier)
        
        #TRANSLATORS: for example 'Number of covers limited to 150'
        display_message = _("Number of covers limited to %d") % self.flow_max
        string = string.replace('#MAXCOVERS',
          '<p>' + display_message + '</p>')

        items = self.flow.initialise(self.album_manager.model, self.flow_max)

        string = string.replace('#ITEMS', items)
        
        base =  os.path.dirname(path) + "/"
        Gdk.threads_enter()
        print (string)
        self.view.load_string(string, "text/html", "UTF-8", "file://" + base)
        Gdk.threads_leave()

        if self._on_first_use:
            self._on_first_use = False
            Gdk.threads_add_timeout(GLib.PRIORITY_DEFAULT_IDLE, 250,
                    self.source.show_hide_pane, (self.last_album, PanedCollapsible.Paned.EXPAND))

    def get_view_icon_name(self):
        return "flowview.png"

    def scroll_to_album(self):
        self.flow.scroll_to_album(self.last_album, self.view)
        
    def initialise(self, source):
        if self._has_initialised:
            return
            
        self._has_initialised = True

        self.source = source
        self.plugin = source.plugin
        self.album_manager = source.album_manager
        self.ext_menu_pos = 6
        
        self._connect_properties()
        self._connect_signals(source)
        
        # lets check that all covers have finished loading before
        # initialising the flowcontrol and other signals
        if not self.album_manager.cover_man.has_finished_loading:
            self.album_manager.cover_man.connect('load-finished', self._covers_loaded)
        else:
            self._covers_loaded()

    def _covers_loaded(self, *args):
        self.flow = FlowControl(self)
        self.view.connect("notify::title", self.flow.receive_message_signal)

        #self.album_manager.model.connect('album-updated', self.flow.update_album, self.view)
        #self.album_manager.model.connect('visual-updated', self.flow.update_album, self.view)
        self.album_manager.model.connect('album-updated', self.filter_changed)
        self.album_manager.model.connect('visual-updated', self.filter_changed)
        self.album_manager.model.connect('filter-changed', self.filter_changed)
        
        self.filter_changed()

    @property
    def last_album(self):
        return self._last_album

    @last_album.setter
    def last_album(self, new_album):
        if self._last_album != new_album:
            self._last_album = new_album
            self.source.click_count = 0
            self.selectionchanged_callback()

    def item_rightclicked_callback(self, album):
        if not self._external_plugins:
            # initialise external plugin menu support
            self._external_plugins = \
            CreateExternalPluginMenu("ca_covers_view",
                self.ext_menu_pos, self.popup)
            self._external_plugins.create_menu('popup_menu', True)
            
        self.last_album = album
        self.popup.get_gtkmenu(self.source, 'popup_menu').popup(None,
                        None, 
                        None,
                        None,
                        3,
                        Gtk.get_current_event_time())

    def item_clicked_callback(self, album):
        '''
        Callback called when the user clicks somewhere on the flow_view.
        Along with source "show_hide_pane", takes care of showing/hiding the bottom
        pane after a second click on a selected album.
        '''
        # to expand the entry view
        if self.flow_automatic:
            self.source.click_count += 1
            
        self.last_album = album

        if self.source.click_count == 1:
            Gdk.threads_add_timeout(GLib.PRIORITY_DEFAULT_IDLE, 250,
                self.source.show_hide_pane, album)

    def item_activated_callback(self, album):
        '''
        Callback called when the flow view is double clicked. It plays the selected album
        '''
        self.last_album = album
        self.source.play_selected_album()

        return True

    def item_drop_callback(self, album, webpath):
        '''
        Callback called when something is dropped onto the flow view - hopefully a webpath
        to a picture
        '''
        print ("item_drop_callback %s" % webpath)
        print ("dropped on album %s" % album)
        self.album_manager.cover_man.update_cover(album, uri=webpath)

    def get_selected_objects(self):
        if self.last_album:
            return [self.last_album]
        else:
            return []

    def select_and_scroll_to_path(self, path):
        album = self.source.album_manager.model.get_from_path(path)
        self.flow.scroll_to_album(album, self.view)
        self.item_clicked_callback(album)

    def switch_to_view(self, source, album):
        self.initialise(source)
        self.show_policy.initialise(source.album_manager)
        
        self.last_album = album
        self.scroll_to_album()
        
    def grab_focus(self):
        self.view.grab_focus()

class FlowControl(object):
    
    def __init__(self, callback_view):
        self.callback_view = callback_view
        self.album_identifier = {}
        
    def get_identifier(self, album):
        index = -1
        for row in self.album_identifier:
            if self.album_identifier[row] == album:
                index = row
                break

        if index == -1:
            return None
        else:
            return row

    def update_album(self, model, album_path, album_iter, webview):
        album = model.get_from_path(album_path)
        index = -1
        for row in self.album_identifier:
            if self.album_identifier[row] == album:
                index = row
                break

        if index == -1:
            return

        obj = {}
        obj['filename'] = album.cover.original
        obj['title'] = album.artist
        obj['caption'] = album.name
        obj['identifier'] = str(index)

        webview.execute_script("update_album('%s')" % json.dumps(obj))
                 
    def receive_message_signal(self, webview, param):
        # this will be key to passing stuff back and forth - need
        # to develop some-sort of message protocol to distinguish "events"
        
        title = webview.get_title()
        if (not title) or (title == '"clear"'):
            return

        args = json.loads(title)
        try:
            signal = args["signal"]
        except:
            print ("unhandled: %s " % title)
            return

        if signal == 'clickactive':
            self.callback_view.item_clicked_callback(self.album_identifier[int(args['param'][0])])
        elif signal == 'rightclickactive':
            self.callback_view.item_rightclicked_callback(
                self.album_identifier[int(args['param'][0])])
        elif signal == 'doubleclickactive':
            self.callback_view.item_activated_callback(self.album_identifier[int(args['param'][0])])
        elif signal == 'dropactive':
            self.callback_view.item_drop_callback(self.album_identifier[int(args['param'][0])],
                args['param'][1])
        else:
            print ("unhandled signal: %s" % signal)

    def scroll_to_album(self, album, webview):
        for row in self.album_identifier:
            if self.album_identifier[row] == album:
                webview.execute_script("scroll_to_identifier('%s')" % str(row))
                break

    def initialise(self, model, max_covers):

        album_col = model.columns['album']
        index = 0
        items = ""
        self.album_identifier = {}
        
        def html_elements(fullfilename, title, caption, identifier):

            return '<div class="item"><img class="content" src="' +\
                escape(fullfilename) + '" title="' +\
                escape(title) + '" identifier="' +\
                identifier + '"/> <div class="caption">' +\
                escape(caption) + '</div> </div>'


        for row in model.store:

            cover = row[album_col].cover.original
            cover = cover.replace(
                'rhythmbox-missing-artwork.svg',
                'rhythmbox-missing-artwork.png')  ## need a white vs black when we change the background colour

            self.album_identifier[index] = row[album_col]
            items += html_elements(
                fullfilename = cover,
                caption=row[album_col].name,
                title=row[album_col].artist,
                identifier=str(index))

            index += 1

            if index == max_covers:
                break

        if index != 0:
            #self.callback_view.last_album = self.album_identifier[0]
            pass
        else:
            self.callback_view.last_album = None

        return items
