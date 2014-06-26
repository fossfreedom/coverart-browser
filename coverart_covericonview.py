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

from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import Pango
from gi.repository import PangoCairo
from gi.repository import GdkPixbuf

from coverart_widgets import EnhancedIconView
from coverart_browser_prefs import GSetting
from coverart_browser_prefs import CoverLocale
from coverart_album import AlbumsModel
from coverart_widgets import AbstractView
from coverart_widgets import PanedCollapsible
import coverart_rb3compat as rb3compat
import rb
import gettext

PLAY_SIZE_X = 30
PLAY_SIZE_Y = 30


class CellRendererThumb(Gtk.CellRendererPixbuf):
    markup = GObject.property(type=str, default="")

    def __init__(self, font_description, cell_area_source):
        super(CellRendererThumb, self).__init__()
        self.font_description = font_description
        self.cell_area_source = cell_area_source
        ypad = 0

    def do_render(self, cr, widget,
                  background_area,
                  cell_area,
                  flags):


        x_offset = cell_area.x + 1
        y_offset = cell_area.y + 1
        wi = 0
        he = 0
        #IMAGE
        pixbuf = self.props.pixbuf.scale_simple(cell_area.width - 2, cell_area.height - 2,
                                                GdkPixbuf.InterpType.NEAREST)
        Gdk.cairo_set_source_pixbuf(cr, pixbuf, x_offset, y_offset)
        cr.paint()

        alpha = 0.40

        if ((flags & Gtk.CellRendererState.PRELIT) == Gtk.CellRendererState.PRELIT):
            alpha -= 0.15

            if hasattr(Gtk.IconView, "get_cell_rect") and self.cell_area_source.hover_pixbuf:
                # this only works on Gtk+3.6 and later
                Gdk.cairo_set_source_pixbuf(cr,
                                            self.cell_area_source.hover_pixbuf, x_offset, y_offset)
                cr.paint()

        #if((flags & Gtk.CellRendererState.SELECTED) == Gtk.CellRendererState.SELECTED or \
        #   (flags & Gtk.CellRendererState.FOCUSED) == Gtk.CellRendererState.FOCUSED):
        #    alpha -= 0.15


        if not (self.cell_area_source.display_text and self.cell_area_source.display_text_pos == False):
            return

        #PANGO LAYOUT
        layout_width = cell_area.width - 2
        pango_layout = PangoCairo.create_layout(cr)
        pango_layout.set_markup(self.markup, -1)
        pango_layout.set_alignment(Pango.Alignment.CENTER)
        pango_layout.set_font_description(self.font_description)
        pango_layout.set_width(int(layout_width * Pango.SCALE))
        pango_layout.set_wrap(Pango.WrapMode.WORD_CHAR)
        wi, he = pango_layout.get_pixel_size()

        rect_offset = y_offset + (int((2.0 * self.cell_area_source.cover_size) / 3.0))
        rect_height = int(self.cell_area_source.cover_size / 3.0)
        was_to_large = False;
        if (he > rect_height):
            was_to_large = True
            pango_layout.set_ellipsize(Pango.EllipsizeMode.END)
            pango_layout.set_height(int((self.cell_area_source.cover_size / 3.0) * Pango.SCALE))
            wi, he = pango_layout.get_pixel_size()

        #RECTANGLE
        cr.set_source_rgba(0.0, 0.0, 0.0, alpha)
        cr.set_line_width(0)
        cr.rectangle(x_offset,
                     rect_offset,
                     cell_area.width - 1,
                     rect_height - 1)
        cr.fill()

        #DRAW FONT
        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        cr.move_to(x_offset,
                   y_offset
                   + 2.0 * self.cell_area_source.cover_size / 3.0
                   + (((self.cell_area_source.cover_size / 3.0) - he) / 2.0)
        )
        PangoCairo.show_layout(cr, pango_layout)


class AlbumArtCellArea(Gtk.CellAreaBox):
    font_family = GObject.property(type=str, default="Sans")
    font_size = GObject.property(type=int, default=10)
    cover_size = GObject.property(type=int, default=0)
    display_text_pos = GObject.property(type=bool, default=False)
    display_text = GObject.property(type=bool, default=False)
    hover_pixbuf = GObject.property(type=object, default=None)

    def __init__(self, ):
        super(AlbumArtCellArea, self).__init__()

        self.font_description = Pango.FontDescription.new()
        self.font_description.set_family(self.font_family)
        self.font_description.set_size(int(self.font_size * Pango.SCALE))

        self._connect_properties()

        #Add own cellrenderer
        renderer_thumb = CellRendererThumb(self.font_description, self)

        self.pack_start(renderer_thumb, False, False, False)
        self.attribute_connect(renderer_thumb, "pixbuf", AlbumsModel.columns['pixbuf'])
        self.attribute_connect(renderer_thumb, "markup", AlbumsModel.columns['markup'])
        self.props.spacing = 2

    def _connect_properties(self):
        gs = GSetting()
        setting = gs.get_setting(gs.Path.PLUGIN)

        setting.bind(gs.PluginKey.COVER_SIZE, self, 'cover-size',
                     Gio.SettingsBindFlags.GET)

        setting.bind(gs.PluginKey.DISPLAY_TEXT_POS, self, 'display-text-pos',
                     Gio.SettingsBindFlags.GET)

        setting.bind(gs.PluginKey.DISPLAY_TEXT, self, 'display-text',
                     Gio.SettingsBindFlags.GET)


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
    display_text_pos = GObject.property(type=bool, default=False)
    name = 'coverview'
    panedposition = PanedCollapsible.Paned.COLLAPSE

    __gsignals__ = {
        'update-toolbar': (GObject.SIGNAL_RUN_LAST, None, ())
    }


    def __init__(self, *args, **kwargs):
        if not rb3compat.compare_pygobject_version("3.9"):
            super(CoverIconView, self).__init__(cell_area=AlbumArtCellArea(), *args, **kwargs)
        else:
            # this works in trusty but not in earlier versions - define in the super above
            super(CoverIconView, self).__init__(*args, **kwargs)
            self.props.cell_area = AlbumArtCellArea()

        self.gs = GSetting()
        # custom text renderer
        self._text_renderer = None
        self.show_policy = AlbumShowingPolicy(self)
        self.view = self
        self._has_initialised = False
        self._last_path = None
        self._calc_motion_step = 0

    def initialise(self, source):
        if self._has_initialised:
            return

        self._has_initialised = True

        self.view_name = "covers_view"
        super(CoverIconView, self).initialise(source)

        self.shell = source.shell
        self.album_manager = source.album_manager

        # setup iconview drag&drop support
        # first drag and drop on the coverart view to receive coverart
        self.enable_model_drag_dest([], Gdk.DragAction.COPY)
        self.drag_dest_add_image_targets()
        self.drag_dest_add_text_targets()
        self.connect('drag-drop', self.on_drag_drop)
        self.connect('drag-data-received',
                     self.on_drag_data_received)
        self.source.paned.connect("expanded", self.bottom_expander_expanded_callback)

        # lastly support drag-drop from coverart to devices/nautilus etc
        self.connect('drag-begin', self.on_drag_begin)
        self.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK,
            [], Gdk.DragAction.COPY)
        #targets = Gtk.TargetList.new([Gtk.TargetEntry.new("application/x-rhythmbox-entry", 0, 0),
        #    Gtk.TargetEntry.new("text/uri-list", 0, 1) ])
        targets = Gtk.TargetList.new([Gtk.TargetEntry.new("text/uri-list", 0, 0)])
        # N.B. values taken from rhythmbox v2.97 widgets/rb_entry_view.c
        targets.add_uri_targets(1)

        self.drag_source_set_target_list(targets)
        self.connect("drag-data-get", self.on_drag_data_get)

        # set the model to the view
        #self.set_pixbuf_column(AlbumsModel.columns['pixbuf'])
        self.set_model(self.album_manager.model.store)

        # setup view to monitor mouse movements
        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK)

        self.hover_pixbufs = {
            'button_play': None,
            'button_play_hover': None,
            'button_playpause': None,
            'button_playpause_hover': None,
            'button_queue': None,
            'button_queue_hover': None}

        for pixbuf_type in self.hover_pixbufs:
            filename = 'img/' + pixbuf_type + '.png'
            filename = rb.find_plugin_file(self.plugin, filename)
            self.hover_pixbufs[pixbuf_type] = GdkPixbuf.Pixbuf.new_from_file_at_size(filename,
                                                                                     PLAY_SIZE_X, PLAY_SIZE_Y)

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

        setting.bind(self.gs.PluginKey.DISPLAY_TEXT_POS, self,
                     'display-text-pos', Gio.SettingsBindFlags.GET)

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
        self.connect('notify::display-text-pos',
                     self._activate_markup)
        self.connect("motion-notify-event", self.on_pointer_motion)

    def get_view_icon_name(self):
        return "iconview.png"

    def resize_icon(self, cover_size):
        '''
        Callback called when to resize the icon
        [common to all views]
        '''
        self.set_item_width(cover_size)

    def on_drag_drop(self, widget, context, x, y, time):
        '''
        Callback called when a drag operation finishes over the cover view
        of the source. It decides if the dropped item can be processed as
        an image to use as a cover.
        '''

        # stop the propagation of the signal (deactivates superclass callback)
        widget.stop_emission_by_name('drag-drop')

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
        widget.stop_emission_by_name('drag-data-received')

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

        sel = data.set_uris(uris)
        # stop the propagation of the signal (deactivates superclass callback)
        widget.stop_emission_by_name('drag-data-get')

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
        widget.stop_emission_by_name('drag-begin')

    def _cover_play_hotspot(self, path, in_vacinity=False):

        if path and hasattr(self, "get_cell_rect"):
            valid, rect = self.get_cell_rect(path, None)  # rect of widget coords

            cursor_x, cursor_y = self.get_pointer()  # returns widget coords
            c_x = cursor_x - rect.x - (self.icon_padding / 2) - (self.icon_spacing / 2)
            c_y = cursor_y - rect.y - (self.icon_padding / 2) - (self.icon_spacing / 2)

            sizing_x = (rect.width / 2) if in_vacinity else 0
            sizing_y = (rect.width / 2) if in_vacinity else 0

            if c_x < (PLAY_SIZE_X + sizing_x) and \
                            c_y < (PLAY_SIZE_Y + sizing_y) and \
                            c_x > 0 and \
                            c_y > 0:
                return True

        return False

    def on_pointer_motion(self, widget, event):
        self._current_mouse_x = event.x
        self._current_mouse_y = event.y

        if self._calc_motion_step == 0:
            self._calc_motion_step = 1
            Gdk.threads_add_timeout(GLib.PRIORITY_DEFAULT_IDLE, 100,
                                    self._calculate_hotspot)
        else:
            path = self.get_path_at_pos(self._current_mouse_x,
                                    self._current_mouse_y)

            if not self._last_path or self._last_path != path:
                self._display_icon(None, self._last_path)

    def _display_icon(self, icon, path):
        self.props.cell_area.hover_pixbuf = icon
        if path:
            valid, rect = self.get_cell_rect(path, None)
            self.props.window.invalidate_rect(rect, True)

        self.queue_draw()

    def _calculate_hotspot(self, *args):

        path = self.get_path_at_pos(self._current_mouse_x,
                                    self._current_mouse_y)

        # if the current path was not the same as the last path then
        # reset the counter
        if not self._last_path or self._last_path != path:
            self._display_icon(None, self._last_path)
            self._last_path = path
            self._calc_motion_step = 0
            return False

        self._calc_motion_step = self._calc_motion_step + 1

        # if havent yet reached the requisite number of steps then
        # let the thread roll to the next increment
        if self._calc_motion_step < 8:
            return True

        if not self._cover_play_hotspot(path, in_vacinity = True):
            # we are not near the hot-spot so decrement the counter
            # hoping next time around we are near
            self._calc_motion_step = self._calc_motion_step - 1
            self._display_icon(None, self._last_path)
            return True

        # from  here on in, we are going to display a hotspot icon
        # so lets decide which one

        (_, playing) = self.shell.props.shell_player.get_playing()

        calc_path = -1
        if playing:
            entry = self.shell.props.shell_player.get_playing_entry()
            album = self.album_manager.model.get_from_dbentry(entry)
            calc_path = self.album_manager.model.get_path(album)

        if playing and calc_path == path:
            icon = 'button_playpause'
        elif playing:
            icon = 'button_queue'
        else:
            icon = 'button_play'

        # now we've got the icon - lets double check that we are
        # actually hovering exactly on the hotspot because the icon will visually change

        exact_hotspot = self._cover_play_hotspot(path)
        if exact_hotspot:
            icon = icon + '_hover'

        hover = self.hover_pixbufs[icon]

        self._display_icon(hover, path)
        self._calc_motion_step = self._calc_motion_step - 1

        return True

    def item_clicked_callback(self, iconview, event, path):
        '''
        Callback called when the user clicks somewhere on the cover_view.
        Along with source "show_hide_pane", takes care of showing/hiding the bottom
        pane after a second click on a selected album.
        '''

        # first test if we've clicked on the cover-play icon
        if self._cover_play_hotspot(path):
            (_, playing) = self.shell.props.shell_player.get_playing()

            # first see if anything is playing...
            if playing:
                entry = self.shell.props.shell_player.get_playing_entry()
                album = self.album_manager.model.get_from_dbentry(entry)

                # if the current playing entry corresponds to the album
                # we are hovering over then we are requesting to pause
                if self.album_manager.model.get_from_path(path) == album:
                    self._last_path = path
                    self.shell.props.shell_player.pause()
                    self.on_pointer_motion(self, event)
                    return

            # if we are not playing and the last thing played is what
            # we are still hovering over then we must be requesting to play

            #if self._last_path and self._last_path == path:
            #    self.shell.props.shell_player.play()
            #    self.on_pointer_motion(self, event)
            #    return

            # otherwise, this must be a new album so we are asking just
            # to play this new album ... just need a short interval
            # for the selection event to kick in first
            def delay(*args):
                if playing:  # if we are playing then queue up the next album
                    self.source.queue_selected_album(None, self.source.favourites)
                    album = self.get_selected_objects()[0]
                    cl = CoverLocale()
                    cl.switch_locale(cl.Locale.LOCALE_DOMAIN)
                    message  = gettext.gettext('Album has added to list of playing albums')
                    self.display_notification(album.name,
                                            message,
                                            album.cover.original)
                else:  # otherwise just play it
                    self._last_path = path
                    self.source.play_selected_album(self.source.favourites)

                self.props.cell_area.hover_pixbuf = \
                    self.hover_pixbufs['button_play_hover']

            Gdk.threads_add_timeout(GLib.PRIORITY_DEFAULT_IDLE, 250,
                                    delay, None)

            return

        # to expand the entry view
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        shift = event.state & Gdk.ModifierType.SHIFT_MASK

        if self.icon_automatic:
            self.source.click_count += 1 if not ctrl and not shift else 0

        if self.source.click_count == 1:
            album = self.album_manager.model.get_from_path(path) \
                if path else None
            Gdk.threads_add_timeout(GLib.PRIORITY_DEFAULT_IDLE, 250,
                                    self.source.show_hide_pane, album)

    def item_activated_callback(self, iconview, path):
        '''
        Callback called when the cover view is double clicked or space-bar
        is pressed. It plays the selected album
        '''
        self.source.play_selected_album(self.source.favourites)

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
        #Add own cellrenderer
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
        if self.display_text_enabled and self.display_text_pos:
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

        if self.display_text_enabled:
            self.set_tooltip_column(-1)  # turnoff tooltips
        else:
            self.set_tooltip_column(AlbumsModel.columns['tooltip'])

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

        self.scroll_to_album(album)

    def grab_focus(self):
        super(EnhancedIconView, self).grab_focus()
