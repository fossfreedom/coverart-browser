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
from gi.repository import WebKit
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gio
from coverart_browser_prefs import GSetting
from coverart_album import AlbumsModel
from coverart_widgets import AbstractView
import rb
import json
import os
from os.path import expanduser

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

    def initialise(self, album_manager):
        self._album_manager = album_manager
        self._model = album_manager.model
        self._connect_signals()

    def _connect_signals(self):
        #self._model.connect('album-updated', self._album_updated)
        #self._model.connect('visual-updated', self._album_updated)
        pass

    def _album_updated(self, model, album_path, album_iter):
        #print self.counter
        self.counter = self.counter + 1
        # this method is called once for every album in the model if the events above are connected
        #for row in self._model.store:
        #    print row[:]


class CoverFlowView(AbstractView):
    __gtype_name__ = "CoverFlowView"

    name = 'coverflowview'

    def __init__(self, *args, **kwargs):
        super(CoverFlowView, self).__init__(*args, **kwargs)
        
        self.ext_menu_pos = 0
        self._external_plugins = None
        self.gs = GSetting()
        self.show_policy = FlowShowingPolicy(self)
        self.view = WebKit.WebView()

    def filter_changed(self, *args):
        #for some reason three filter change events occur on startup
        path = rb.find_plugin_file(self.plugin, 'coverflow/index.html')
        f = open(path)
        string = f.read()
        f.close()

        string = self.flow.initialise(string, self.album_manager.model)
        base =  os.path.dirname(path) + "/"
        self.view.load_string(string, "text/html", "UTF-8", "file://" + base)
        
    def initialise(self, source):
        if self.has_initialised:
            return
            
        self.has_initialised = True

        self.source = source
        self.plugin = source.plugin
        self.album_manager = source.album_manager
        self.ext_menu_pos = 10
        self.album_manager.model.connect('filter-changed', self.filter_changed)

        self.flow = FlowControl()
        self.view.connect("notify::title", self.flow.receive_message_signal)

        
        # set the model to the view
        #self.set_model(self.album_manager.model.store)

        #self.connect("item-clicked", self.item_clicked_callback)
        #self.connect("selection-changed", self.selectionchanged_callback)
        #self.connect("item-activated", self.item_activated_callback)

    def resize_icon(self, cover_size):
        '''
        Callback called when to resize the icon
        [common to all views]
        '''
        pass

    def selectionchanged_callback(self, _):
        #self.source.update_with_selection()
        pass

    def scroll_to_object(self, path):
        pass

    def pre_display_popup(self):
        if not self._external_plugins:
            # initialise external plugin menu support
            self._external_plugins = \
            CreateExternalPluginMenu("ca_covers_view",
                self.ext_menu_pos, self.popup)
            self._external_plugins.create_menu('popup_menu', True)
            
    def item_clicked_callback(self, iconview, event, path):
        '''
        Callback called when the user clicks somewhere on the cover_view.
        Along with source "show_hide_pane", takes care of showing/hiding the bottom
        pane after a second click on a selected album.
        '''
        # to expand the entry view
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        shift = event.state & Gdk.ModifierType.SHIFT_MASK

        self.source.click_count += 1 if not ctrl and not shift else 0

        if self.source.click_count == 1:
            album = self.album_manager.model.get_from_path(path)\
                if path else None
            Gdk.threads_add_timeout(GLib.PRIORITY_DEFAULT_IDLE, 250,
                self.source.show_hide_pane, album)

    def item_activated_callback(self, iconview, path):
        '''
        Callback called when the cover view is double clicked or space-bar
        is pressed. It plays the selected album
        '''
        self.source.play_selected_album()

        return True

class FlowBatch(object):
    def __init__(self):
        self.filename = []
        self.title = []
        self.caption = []
        self.fetched = False

    def append(self, fullfilename, title, caption):
        self.filename.append(fullfilename)
        self.title.append(title)
        self.caption.append(caption)

    def html_elements(self):
        
        str = ""
        for loop in range(len(self.filename)):
            str = str + '<div class="item"><img class="content" src="' +\
                self.filename[loop] + '" title="' +\
                self.title[loop] + '"/> <div class="caption">' +\
                self.caption[loop] + '</div> </div>'

        self.fetched = True
        return str

class FlowControl(object):
    def __init__(self):
        self.next_batch = 0
        self.batches = []
        
    def get_flow_batch(self, args):
        messagevalue = args[0]
        index = int(args[1])

        obj = {}
        position = 'stop'

        if messagevalue == 'next':
            calc_batch = int(index / 50) + 1
                        
            if ((calc_batch >= self.next_batch) and
                (len(self.batches) > calc_batch) and
                (not self.batches[calc_batch].fetched)):

                position = 'last'
                chosen = self.batches[calc_batch]
                size = len(chosen.filename)
                params = []
            
                for index in range(0, size):
                    batch = {}
                    batch['filename'] = chosen.filename[index]
                    batch['title'] = "tooltip " + chosen.title[index]
                    batch['caption'] = "album name " + chosen.caption[index]

                    params.append(batch)
                obj['flowbatch'] = params
                self.batches[calc_batch].fetched = True
                self.next_batch = calc_batch + 1
        else:
            print ("unknown message %", messagevalue)
            
        obj['batchtype'] = position
        ret = json.dumps(obj)
        return ret
                 
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

        if signal == 'getflowbatch':
            #webview.execute_script("new_flow_batch(%s)" % self.get_flow_batch(args['param']))
            s = self.get_flow_batch(args['param'])
            webview.execute_script("new_flow_batch('%s')" % s)
        

    def initialise(self, string, model):
        element = 0
        batch = None

        album_col = model.columns['album']
        pos = 0
        del self.batches[:]
        print self.batches

        for row in model.store:
            if not (element < 50):
                batch = None
                element = 0
                
            if not batch:
                batch = FlowBatch()
                self.batches.append(batch)

            cover = row[album_col].cover.original.replace(
                'rhythmbox-missing-artwork.svg',
                'rhythmbox-missing-artwork.png')  ## need a white vs black when we change the background colour

            batch.append(
                fullfilename = cover,
                caption=row[album_col].name,
                title=row[album_col].artist)
            pos = pos + 1
            element = element + 1

        items = ""
        if len(self.batches) > 0:
            items = self.batches[0].html_elements() #+\
                    #self.batches[1].html_elements() #+\
                    #self.batches[2].html_elements()
            self.next_batch = 1

        string = string.replace('#ITEMS', items)
        string = string.replace('#BACKGROUND_COLOUR', 'white')
        string = string.replace('#HEIGHT', '200')

        return string
