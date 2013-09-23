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

from coverart_widgets import EnhancedIconView
from coverart_external_plugins import CreateExternalPluginMenu
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gio
from coverart_browser_prefs import GSetting
from gi.repository import Pango
from coverart_album import AlbumsModel
from coverart_widgets import AbstractView
import coverart_rb3compat as rb3compat 
import rb

class AlbumShowingPolicy(GObject.Object):
    '''
    Policy that mostly takes care of how and when things should be showed on
    the view that makes use of the `AlbumsModel`.
    '''

    def __init__(self, cover_view):
        super(AlbumShowingPolicy, self).__init__()

        self._cover_view = cover_view  # this will need to be reworked for all views
        self._visible_paths = None
        self._has_initialised = False

    def initialise(self, album_manager):
        if self._has_initialised:
            return

        self._album_manager = album_manager
        self._model = album_manager.model
        self._connect_signals()
        self._has_initialised = True

    def _connect_signals(self):
        self._cover_view.props.vadjustment.connect('value-changed',
            self._viewport_changed)
        self._model.connect('album-updated', self._album_updated)
        self._model.connect('visual-updated', self._album_updated)

    def _viewport_changed(self, *args):
        visible_range = self._cover_view.get_visible_range()

        if visible_range:
            init, end = visible_range

            # i have to use the tree iter instead of the path to iterate since
            # for some reason path.next doesn't work with the filtermodel
            tree_iter = self._model.store.get_iter(init)

            self._visible_paths = []

            while init and init != end:
                self._visible_paths.append(init)

                tree_iter = self._model.store.iter_next(tree_iter)
                init = self._model.store.get_path(tree_iter)

            self._visible_paths.append(end)

    def _album_updated(self, model, album_path, album_iter):
        # get the currently showing paths
        if not self._visible_paths:
            self._viewport_changed()

        if (album_path and self._visible_paths) and album_path in self._visible_paths:
            # if our path is on the viewport, emit the signal to update it
            self._cover_view.queue_draw()

class CoverIconView(EnhancedIconView, AbstractView):
    __gtype_name__ = "CoverIconView"

    icon_spacing = GObject.property(type=int, default=0)
    icon_padding = GObject.property(type=int, default=0)
    icon_automatic = GObject.property(type=bool, default=True)

    display_text_enabled = GObject.property(type=bool, default=False)
    name = 'coverview'

    def __init__(self, *args, **kwargs):
        super(CoverIconView, self).__init__(*args, **kwargs)
        
        self.ext_menu_pos = 0
        self._external_plugins = None
        self.gs = GSetting()
        # custom text renderer
        self._text_renderer = None
        self.show_policy = AlbumShowingPolicy(self)
        self.view = self
        self._has_initialised = False
        
    def initialise(self, source):
        if self._has_initialised:
            return
            
        self._has_initialised = True

        self.view_name = "covers_view"
        self.source = source
        self.plugin = source.plugin
        self.shell = source.shell
        self.album_manager = source.album_manager
        self.ext_menu_pos = 6

        # setup iconview drag&drop support
        # first drag and drop on the coverart view to receive coverart
        self.enable_model_drag_dest([], Gdk.DragAction.COPY)
        self.drag_dest_add_image_targets()
        self.drag_dest_add_text_targets()
        self.connect('drag-drop', self.on_drag_drop)
        self.connect('drag-data-received',
            self.on_drag_data_received)
        self.connect('drag-begin', self.on_drag_begin)
        self.source.paned.connect("expanded", self.bottom_expander_expanded_callback)
        
        self.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK,
            [], Gdk.DragAction.COPY)

        # lastly support drag-drop from coverart to devices/nautilus etc
        targets = Gtk.TargetList.new([Gtk.TargetEntry.new("application/x-rhythmbox-entry", 0, 0),
            Gtk.TargetEntry.new("text/uri-list", 0, 1) ])
        # N.B. values taken from rhythmbox v2.97 widgets/rb_entry_view.c
        targets.add_uri_targets(2)
        
        self.drag_source_set_target_list(targets)
        self.connect("drag-data-get", self.on_drag_data_get)

        # set the model to the view
        self.set_model(self.album_manager.model.store)

        self._connect_properties()
        self._connect_signals()

        self._activate_markup()
        self.on_notify_icon_padding()
        self.on_notify_icon_spacing()

    def _connect_properties(self):
        setting = self.gs.get_setting(self.gs.Path.PLUGIN)
        setting.bind(
            self.gs.PluginKey.ICON_SPACING,
            self,
            'icon_spacing',
            Gio.SettingsBindFlags.GET)
        setting.bind(
            self.gs.PluginKey.ICON_PADDING,
            self,
            'icon_padding',
            Gio.SettingsBindFlags.GET)

        setting.bind(self.gs.PluginKey.DISPLAY_TEXT, self,
            'display_text_enabled', Gio.SettingsBindFlags.GET)

        setting.bind(self.gs.PluginKey.ICON_AUTOMATIC, self,
            'icon_automatic', Gio.SettingsBindFlags.GET)

    def _connect_signals(self):
        self.connect("item-clicked", self.item_clicked_callback)
        self.connect("selection-changed", self.selectionchanged_callback)
        self.connect("item-activated", self.item_activated_callback)        
        self.connect('notify::icon-spacing',
            self.on_notify_icon_spacing)
        self.connect('notify::icon-padding',
            self.on_notify_icon_padding)
        self.connect('notify::display-text-enabled',
            self._activate_markup)

    def get_view_icon_name(self):
        return "iconview.png"

    def resize_icon(self, cover_size): 
        '''
        Callback called when to resize the icon
        [common to all views]
        '''
        self.set_item_width(cover_size)

    def pre_display_popup(self):
        if not self._external_plugins:
            # initialise external plugin menu support
            self._external_plugins = \
            CreateExternalPluginMenu("ca_covers_view",
                self.ext_menu_pos, self.popup)
            self._external_plugins.create_menu('popup_menu', True)

    def on_drag_drop(self, widget, context, x, y, time):
        '''
        Callback called when a drag operation finishes over the cover view
        of the source. It decides if the dropped item can be processed as
        an image to use as a cover.
        '''

        # stop the propagation of the signal (deactivates superclass callback)
        if rb3compat.is_rb3(self.shell):
            widget.stop_emission_by_name('drag-drop')
        else:
            widget.stop_emission('drag-drop')

        # obtain the path of the icon over which the drag operation finished
        path, pos = widget.get_dest_item_at_pos(x, y)
        result = path is not None

        if result:
            target = self.drag_dest_find_target(context, None)
            widget.drag_get_data(context, target, time)

        return result

    def on_drag_data_received(self, widget, drag_context, x, y, data, info,
        time):
        '''
        Callback called when the drag source has prepared the data (pixbuf)
        for us to use.
        '''

        # stop the propagation of the signal (deactivates superclass callback)
        if rb3compat.is_rb3(self.shell):
            widget.stop_emission_by_name('drag-data-received')
        else:
            widget.stop_emission('drag-data-received')

        # get the album and the info and ask the loader to update the cover
        path, pos = widget.get_dest_item_at_pos(x, y)
        album = widget.get_model()[path][2]

        pixbuf = data.get_pixbuf()

        if pixbuf:
            self.album_manager.cover_man.update_cover(album, pixbuf)
        else:
            uri = data.get_text()
            self.album_manager.cover_man.update_cover(album, uri=uri)

        # call the context drag_finished to inform the source about it
        drag_context.finish(True, False, time)


    def on_drag_data_get(self, widget, drag_context, data, info, time):
        '''
        Callback called when the drag destination (playlist) has
        requested what album (icon) has been dragged
        '''

        uris = []
        for album in widget.get_selected_objects():
            for track in album.get_tracks():
                uris.append(track.location)

        data.set_uris(uris)
        # stop the propagation of the signal (deactivates superclass callback)
        if rb3compat.is_rb3(self.shell):
            widget.stop_emission_by_name('drag-data-get')
        else:
            widget.stop_emission('drag-data-get')

    def on_drag_begin(self, widget, context):
        '''
        Callback called when the drag-drop from coverview has started
        Changes the drag icon as appropriate
        '''
        album_number = len(widget.get_selected_objects())

        if album_number == 1:
            item = Gtk.STOCK_DND
        else:
            item = Gtk.STOCK_DND_MULTIPLE

        widget.drag_source_set_icon_stock(item)
        if rb3compat.is_rb3(self.shell):
            widget.stop_emission_by_name('drag-begin')
        else:
            widget.stop_emission('drag-begin')

    def item_clicked_callback(self, iconview, event, path):
        '''
        Callback called when the user clicks somewhere on the cover_view.
        Along with source "show_hide_pane", takes care of showing/hiding the bottom
        pane after a second click on a selected album.
        '''
        # to expand the entry view
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        shift = event.state & Gdk.ModifierType.SHIFT_MASK

        if self.icon_automatic:
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

    def on_notify_icon_padding(self, *args):
        '''
        Callback called when the icon-padding gsetting value is changed
        '''
        self.set_item_padding(self.icon_padding)

    def on_notify_icon_spacing(self, *args):
        '''
        Callback called when the icon-spacing gsetting value is changed
        '''
        self.set_row_spacing(self.icon_spacing)
        self.set_column_spacing(self.icon_spacing)

    def _create_and_configure_renderer(self):
        self._text_renderer = Gtk.CellRendererText()

        self._text_renderer.props.alignment = Pango.Alignment.CENTER
        self._text_renderer.props.wrap_mode = Pango.WrapMode.WORD
        self._text_renderer.props.xalign = 0.5
        self._text_renderer.props.yalign = 0
        self._text_renderer.props.width = \
            self.album_manager.cover_man.cover_size
        self._text_renderer.props.wrap_width = \
            self.album_manager.cover_man.cover_size

    def _activate_markup(self, *args):
        '''
        Utility method to activate/deactivate the markup text on the
        cover view.
        '''
        if self.display_text_enabled:
            if not self._text_renderer:
                # create and configure the custom cell renderer
                self._create_and_configure_renderer()

            # set the renderer
            self.pack_end(self._text_renderer, False)
            self.add_attribute(self._text_renderer,
                'markup', AlbumsModel.columns['markup']) 

        elif self._text_renderer:
            # remove the cell renderer
            self.props.cell_area.remove(self._text_renderer)
            
    def bottom_expander_expanded_callback(self, paned, expand):
        '''
        Callback connected to expanded signal of the paned GtkExpander
        '''
        if expand:
            # accommodate the viewport if there's an album selected
            if self.source.last_selected_album:
                def scroll_to_album(*args):
                    # accommodate the viewport if there's an album selected
                    path = self.album_manager.model.get_path(
                        self.source.last_selected_album)

                    self.scroll_to_path(path, False, 0, 0)
                    
                    return False

                Gdk.threads_add_idle(GObject.PRIORITY_DEFAULT_IDLE,
                    scroll_to_album, None)


    def switch_to_view(self, source, album):
        self.initialise(source)
        self.show_policy.initialise(source.album_manager)
        if album:
            path = source.album_manager.model.get_path(album)
            self.select_and_scroll_to_path(path)

    def grab_focus(self):
        super(EnhancedIconView, self).grab_focus()

