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

from collections import OrderedDict
from os.path import expanduser

from gi.repository import RB
from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import GdkPixbuf
from gi.repository import Gdk
from gi.repository import GLib

from coverart_rb3compat import Menu
from coverart_rb3compat import ActionGroup
from coverart_browser_prefs import GSetting
from coverart_browser_prefs import CoverLocale
from coverart_external_plugins import CreateExternalPluginMenu
from coverart_playlists import LastFMTrackPlaylist
from coverart_playlists import EchoNestPlaylist
from coverart_playlists import EchoNestGenrePlaylist
from coverart_utils import create_button_image
from coverart_external_plugins import ExternalPlugin
from stars import ReactiveStar
from coverart_search import CoverSearchPane
from coverart_widgets import PixbufButton
from coverart_widgets import PressButton
from coverart_window import CoverWindow

MIN_IMAGE_SIZE = 100


class EntryViewPane(object):
    '''
        encapulates all of the Track Pane objects
    '''

    def __init__(self, shell, plugin, source, entry_view_grid, viewmgr):
        self.gs = GSetting()

        self.entry_view_grid = entry_view_grid
        self.shell = shell
        self.viewmgr = viewmgr
        self.plugin = plugin
        self.source = source

        # setup entry-view objects and widgets
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(750)

        # create entry views. Don't allow to reorder until the load is finished
        self.entry_view_compact = CoverArtCompactEntryView(self.shell, self.source)
        self.entry_view_full = CoverArtEntryView(self.shell, self.source)
        self.entry_view = self.entry_view_compact
        self.shell.props.library_source.get_entry_view().set_columns_clickable(
            False)

        self.entry_view_results = ResultsGrid()
        self.entry_view_results.initialise(self.entry_view_grid, source)

        self.stack.add_titled(self.entry_view_results, "notebook_tracks", _("Tracks"))
        self.entry_view_grid.attach(self.stack, 0, 0, 3, 1)

    def setup_source(self):

        colour = self.viewmgr.get_selection_colour()
        self.cover_search_pane = CoverSearchPane(self.plugin, colour)

        self.stack.add_titled(self.cover_search_pane, "notebook_covers", _("Covers"))

        # define entry-view toolbar
        self.stars = ReactiveStar()
        self.stars.set_rating(0)
        self.stars.connect('changed', self.rating_changed_callback)
        self.stars.props.valign = Gtk.Align.CENTER
        self.entry_view_grid.attach(self.stars, 1, 1, 1, 1)
        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_stack(self.stack)

        whatsplayingbutton = PressButton()
        whatsplayingbutton.set_image(create_button_image(self.plugin, "whatsplaying.png"))
        whatsplayingbutton.connect('clicked', self.whatsplayingbutton_callback)
        whatsplayingbutton.props.halign = Gtk.Align.START

        leftgrid = Gtk.Grid()
        leftgrid.attach(whatsplayingbutton, 0, 0, 1, 1)
        leftgrid.attach(stack_switcher, 1, 0, 1, 1)
        self.entry_view_grid.attach(leftgrid, 0, 1, 1, 1)

        viewtoggle = PixbufButton()
        viewtoggle.set_image(create_button_image(self.plugin, "entryview.png"))
        self.viewtoggle_id = None

        setting = self.gs.get_setting(self.gs.Path.PLUGIN)
        viewtoggle.set_active(not setting[self.gs.PluginKey.ENTRY_VIEW_MODE])
        self.entry_view_toggled(viewtoggle, True)
        viewtoggle.connect('toggled', self.entry_view_toggled)

        smallwindowbutton = PixbufButton()
        smallwindowbutton.set_image(create_button_image(self.plugin, "view-restore.png"))
        smallwindowbutton.connect('toggled', self.smallwindowbutton_callback)

        self.smallwindowext = ExternalPlugin()
        self.smallwindowext.appendattribute('plugin_name', 'smallwindow')
        self.smallwindowext.appendattribute('action_group_name', 'small window actions')
        self.smallwindowext.appendattribute('action_name', 'SmallWindow')
        self.smallwindowext.appendattribute('action_type', 'app')

        rightgrid = Gtk.Grid()
        rightgrid.props.halign = Gtk.Align.END

        rightgrid.attach(viewtoggle, 1, 0, 1, 1)
        rightgrid.attach(smallwindowbutton, 2, 0, 1, 1)

        self.entry_view_grid.attach_next_to(rightgrid, self.stars, Gtk.PositionType.RIGHT, 1, 1)
        self.stack.set_visible_child(self.entry_view_results)
        self.stack.connect('notify::visible-child-name', self.notebook_switch_page_callback)

        self.entry_view_grid.show_all()
        smallwindowbutton.set_visible(self.smallwindowext.is_activated())

    def whatsplayingbutton_callback(self, widget):
        self.entry_view_results.emit('whats-playing')

    def smallwindowbutton_callback(self, widget):
        if widget.get_active():
            self.smallwindowext.activate(self.shell)
            widget.emit('clicked')

    def entry_view_toggled(self, widget, initialised=False):
        print("DEBUG - entry_view_toggled")
        if widget.get_active():
            next_view = self.entry_view_full
            show_coverart = False
            if self.viewtoggle_id:
                self.shell.props.window.disconnect(self.viewtoggle_id)
                self.viewtoggle_id = None
        else:
            next_view = self.entry_view_compact
            show_coverart = True
            self.viewtoggle_id = self.shell.props.window.connect('check_resize', self.entry_view_results.window_resize)

        setting = self.gs.get_setting(self.gs.Path.PLUGIN)
        setting[self.gs.PluginKey.ENTRY_VIEW_MODE] = not widget.get_active()

        self.entry_view_results.change_view(next_view, show_coverart)
        self.entry_view = next_view
        if not initialised:
            self.source.update_with_selection()

    def notebook_switch_page_callback(self, *args):
        '''
        Callback called when the notebook page gets switched. It initiates
        the cover search when the cover search pane's page is selected.
        '''
        print("CoverArtBrowser DEBUG - notebook_switch_page_callback")

        if self.stack.get_visible_child_name() == 'notebook_covers':
            self.viewmgr.current_view.switch_to_coverpane(self.cover_search_pane)
        else:
            entries = self.entry_view.get_selected_entries()
            if entries and len(entries) > 0:
                self.entry_view_results.emit('update-cover', self.source, entries[0])
            else:
                selected = self.viewmgr.current_view.get_selected_objects()
                tracks = selected[0].get_tracks()
                self.entry_view_results.emit('update-cover', self.source, tracks[0].entry)

        print("CoverArtBrowser DEBUG - end notebook_switch_page_callback")

    def rating_changed_callback(self, widget):
        '''
        Callback called when the Rating stars is changed
        '''
        print("CoverArtBrowser DEBUG - rating_changed_callback")

        rating = widget.get_rating()

        for album in self.viewmgr.current_view.get_selected_objects():
            album.rating = rating

        print("CoverArtBrowser DEBUG - end rating_changed_callback")

    def get_entry_view(self):
        return self.entry_view

    def update_cover(self, album_artist, manager):
        if not self.stack.get_visible_child_name() == "notebook_covers":
            return

        self.cover_search_pane.clear()
        self.cover_search(album_artist, manager)

    def cover_search(self, album_artist, manager):
        self.cover_search_pane.do_search(album_artist,
                                         manager.cover_man.update_cover)

    def update_selection(self, last_selected_album, click_count):
        '''
        Update the source view when an item gets selected.
        '''
        print("DEBUG - update_with_selection")
        selected = self.viewmgr.current_view.get_selected_objects()

        # clear the entry view
        self.entry_view.clear()

        cover_search_pane_visible = self.stack.get_visible_child_name() == "notebook_covers"

        if not selected:
            # clean cover tab if selected
            if cover_search_pane_visible:
                self.cover_search_pane.clear()

            self.entry_view_results.emit('update-cover', self.source, None)
            return last_selected_album, click_count
        elif len(selected) == 1:
            self.stars.set_rating(selected[0].rating)

            if selected[0] is not last_selected_album:
                # when the selection changes we've to take into account two
                # things
                if not click_count:
                    # we may be using the arrows, so if there is no mouse
                    # involved, we should change the last selected
                    last_selected_album = selected[0]
                else:
                    # we may've doing a fast change after a valid second click,
                    # so it shouldn't be considered a double click
                    click_count -= 1
        else:
            self.stars.set_rating(0)

        if len(selected) == 1:
            self.source.artist_info.emit('selected',
                                         selected[0].artist,
                                         selected[0].name)

        self.entry_view.set_sorting_order('track-number', Gtk.SortType.ASCENDING)

        for album in selected:
            # add the album to the entry_view
            self.entry_view.add_album(album)

        if len(selected) > 0:
            def cover_update(*args):
                print("emitting")
                self.entry_view_results.emit('update-cover',
                                             self.source,
                                             selected[0].get_tracks()[0].entry)

            # add a short delay to give the entry-pane time to expand etc.
            Gdk.threads_add_timeout(GLib.PRIORITY_DEFAULT_IDLE, 250, cover_update, None)

        # update the cover search pane with the first selected album
        if cover_search_pane_visible:
            self.cover_search_pane.do_search(selected[0],
                                             self.source.album_manager.cover_man.update_cover)

        return last_selected_album, click_count


class ResultsGrid(Gtk.Grid):
    # signals
    __gsignals__ = {
        'update-cover': (GObject.SIGNAL_RUN_LAST, None, (GObject.Object, RB.RhythmDBEntry)),
        'whats-playing': (GObject.SIGNAL_RUN_LAST, None, ())
    }
    image_width = 0

    def __init__(self, *args, **kwargs):
        super(ResultsGrid, self).__init__(*args, **kwargs)

    def initialise(self, entry_view_grid, source):
        self.pixbuf = None

        self.entry_view_grid = entry_view_grid
        self.source = source

        self.oldval = 0
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(350)

        self.image1 = Gtk.Image()
        self.image1.props.hexpand = True
        self.image1.props.vexpand = True
        self.stack.add_named(self.image1, "image1")

        self.image2 = Gtk.Image()
        self.image2.props.hexpand = True
        self.image2.props.vexpand = True
        self.stack.add_named(self.image2, "image2")

        self.frame = Gtk.Frame.new()  # "", 0.5, 0.5, 1, False)
        try:
            # correct from Gtk 3.12 onwards
            self.frame.set_margin_end(5)
        except:
            self.frame.set_margin_right(5)

        self.update_cover(None, None, None)
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.add(self.stack)
        self.scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.scroll.set_resize_mode(Gtk.ResizeMode.QUEUE)

        self.frame.add(self.scroll)
        self._signal_connected = None

        '''
          when we hover over the coverart then a zoom icon is overlayed with the coverart
          when we move the mouse pointer from the coverart then the zoom icon is hidden

          this is achieved by a GtkOverlay - the stack doesnt normally have a mouse over event so
          we need to understand when a mouse pointer enters or leaves the stack.

          Also a peculiarity is that moving the pointer over the overlay zoom icon causes
          enter and leave events ... so we need to monitor the mouse over for the icon as well
        '''
        self.overlay = Gtk.Overlay()
        self.overlay.add(self.frame)

        image = Gtk.Image.new_from_icon_name(Gtk.STOCK_ZOOM_FIT, Gtk.IconSize.SMALL_TOOLBAR)
        self.cw_btn = Gtk.Button(label=None, image=image)

        self.cw_btn.set_valign(Gtk.Align.END)
        self.cw_btn.set_halign(Gtk.Align.CENTER)
        self.cw_btn_state = False
        self.hover = False
        self.overlay.add_overlay(self.cw_btn)

        self.attach(self.overlay, 6, 0, 1, 1)

        self.stack.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK)
        self.stack.add_events(Gdk.EventMask.LEAVE_NOTIFY_MASK)
        self.stack.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
        self.cw_btn.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
        self.stack.connect('enter-notify-event', self.stack_notify_event)
        self.stack.connect('leave-notify-event', self.stack_notify_event)
        self.stack.connect('motion-notify-event', self.motion_notify_event)
        self.cw_btn.connect('clicked', self.cw_btn_clicked)
        self.cw_btn.connect('motion-notify-event', self.motion_notify_event)
        self.cw_btn.connect('show', self.cw_btn_show_event)
        self.cw = None
        self.hover_time_out = None
        self.connect('update-cover', self.update_cover)
        self.connect('whats-playing', self.display_whats_playing)

        # lets fix the situation where some-themes background colour is incorrectly defined
        # in these cases the background colour is black
        context = self.get_style_context()
        bg_colour = context.get_background_color(Gtk.StateFlags.NORMAL)
        if bg_colour == Gdk.RGBA(0, 0, 0, 0):
            color = context.get_color(Gtk.StateFlags.NORMAL)
            self.override_background_color(Gtk.StateType.NORMAL, color)

    '''
      when a show, show_all is used lets make sure we set the icon visibility correctly
    '''

    def cw_btn_show_event(self, *args):
        self.cw_btn.set_visible(self.hover)

    '''
      when mousing over the stack/icon we need to remember that we are hovering ... so the visibility
      is set correctly - in the stack notify event
    '''

    def motion_notify_event(self, *args):
        self.hover = True

    def cw_btn_clicked(self, *args):
        def cleanup(arg):
            del self.cw
            self.cw = None

        if not self.cw:
            home = expanduser("~")
            self.cw = CoverWindow(self.source.plugin, self.cw_btn.get_toplevel(), home)
            self.cw.connect('close-window', cleanup)

        self.cw.show_all(' ', self.pixbuf)

    '''
      when entering and leaving the stack (also the icon) then we assume the icon is to be invisible
      Use a short delay to allow the motion events to kick in - if we are still in the stack/icon
      then the hover visibility will be changed
    '''

    def stack_notify_event(self, widget, event_crossing):

        if self.hover_time_out:
            GLib.source_remove(self.hover_time_out)
            self.hover_time_out = None

        def set_hover():
            if self.pixbuf:
                self.cw_btn.set_visible(self.hover)
            else:
                self.cw_btn.set_visible(False)

            self.hover_time_out = None
            return False

        self.hover = False

        self.hover_time_out = GLib.timeout_add(350, set_hover)

        return False

    def update_cover(self, widget, source, entry):

        print('update_cover')
        self.oldval = 0  # force a redraw
        if entry:
            print('entry')
            album = source.album_manager.model.get_from_dbentry(entry)
            self.pixbuf = GdkPixbuf.Pixbuf().new_from_file(album.cover.original)
            self.window_resize(None)
            self.frame.set_shadow_type(Gtk.ShadowType.NONE)
        else:
            print('no pixbuf')
            self.pixbuf = None
            self.frame.set_shadow_type(Gtk.ShadowType.ETCHED_OUT)

        if self.stack.get_visible_child_name() == "image1":
            self.image1.queue_draw()
        else:
            self.image2.queue_draw()

    def display_whats_playing(self, *args):
        '''
          switch to the coverart_play_source

          to do this we need to first expand the source tree to allow the select method to work

          Unfortunately, rhythmbox api does not allow us to do this directly - there is only a toggle
          method. Also - no direct access to the source tree-view.

          Use a trick from alternative-toolbar to search for objects beneath other objects i.e.
          tree-view is below the model

        '''

        def find(node, search_id, search_type):
            if isinstance(node, Gtk.Buildable):
                if search_type == 'by_id':
                    if Gtk.Buildable.get_name(node) == search_id:
                        return node
                elif search_type == 'by_name':
                    if node.get_name() == search_id:
                        return node

            if isinstance(node, Gtk.Container):
                for child in node.get_children():
                    ret = find(child, search_id, search_type)
                    if ret:
                        return ret
            return None

        tree_view = find(self.source.shell.props.display_page_tree, "GtkTreeView", "by_name")
        print (tree_view)

        iter = Gtk.TreeIter()
        self.source.shell.props.display_page_tree.props.model.find_page(self.source, iter)
        path = self.source.shell.props.display_page_tree.props.model.get_path(iter)

        if not tree_view.row_expanded(path):
            tree_view.expand_row(path, False)

        GLib.idle_add( self.source.shell.props.display_page_tree.select, self.source.playlist_source)

    def window_resize(self, widget):
        alloc = self.get_allocation()
        if alloc.height < 10:
            return

        entry_grid_alloc = self.entry_view_grid.get_allocation()

        if (alloc.width / 4) <= (MIN_IMAGE_SIZE + 30) or \
                        (entry_grid_alloc.height) <= (MIN_IMAGE_SIZE + 30):
            self.overlay.set_visible(False)
            return
        else:
            self.overlay.set_visible(True)
            vbar = self.scroll.get_vscrollbar()
            if vbar:
                vbar.set_visible(False)
            hbar = self.scroll.get_hscrollbar()
            if hbar:
                hbar.set_visible(False)

        minval = min((alloc.width / 4), (alloc.height))
        if self.oldval == minval:
            return
        self.oldval = minval
        if minval < MIN_IMAGE_SIZE:
            minval = MIN_IMAGE_SIZE

        if self.pixbuf:
            p = self.pixbuf.scale_simple(minval - 15, minval - 15, GdkPixbuf.InterpType.BILINEAR)
        else:
            p = None

        if self.stack.get_visible_child_name() == "image1":
            self.image2.set_from_pixbuf(p)
            self.stack.set_visible_child_name("image2")
        else:
            self.image1.set_from_pixbuf(p)
            self.stack.set_visible_child_name("image1")

    def change_view(self, entry_view, show_coverart):
        print("debug - change_view")
        widget = self.get_child_at(0, 0)
        if widget:
            self.remove(widget)

        if not show_coverart:
            widget = self.get_child_at(6, 0)
            if widget:
                self.remove(widget)

        entry_view.props.hexpand = True
        entry_view.props.vexpand = True
        self.attach(entry_view, 0, 0, 3, 1)

        if show_coverart:
            self.attach(self.overlay, 6, 0, 1, 1)

        self.show_all()
        self.cw_btn.set_visible(self.hover)


class BaseView(RB.EntryView):
    def __init__(self, shell, source):
        '''
        Initializes the entryview.
        '''
        self.shell = shell
        self.source = source
        self.plugin = self.source.props.plugin

        super(RB.EntryView, self).__init__(db=shell.props.db,
                                           shell_player=shell.props.shell_player, is_drag_source=True,
                                           visible_columns=[])

        cl = CoverLocale()
        cl.switch_locale(cl.Locale.RB)

        self.display_columns()

        cl.switch_locale(cl.Locale.LOCALE_DOMAIN)

        self.define_menu()

        # connect signals to the shell to know when the playing state changes
        self.shell.props.shell_player.connect('playing-song-changed',
                                              self.playing_song_changed)
        self.shell.props.shell_player.connect('playing-changed',
                                              self.playing_changed)

        self.actiongroup = ActionGroup(self.shell, 'coverentryplaylist_submenu')

        self.external_plugins = None

        self.source_query_model = self.source.source_query_model  # RB.RhythmDBQueryModel.new_empty(self.shell.props.db)
        self.qm = RB.RhythmDBQueryModel.new_empty(self.shell.props.db)
        self.set_model(self.qm)

        self.connect_library_signals()
        self.echonest_similar_playlist = None
        self.echonest_similar_genre_playlist = None
        self.lastfm_similar_playlist = None

        self.connect('selection-changed', self.selection_changed)

        self.artists = ""

        print("end constructor")

    def __del__(self):
        del self.action_group
        del self.play_action
        del self.queue_action

    def connect_library_signals(self):
        # connect the sort-order to the library source sort
        library_view = self.shell.props.library_source.get_entry_view()
        library_view.connect('notify::sort-order',
                             self._on_library_sorting_changed)
        self._on_library_sorting_changed(library_view,
                                         library_view.props.sort_order)

        # connect to the sort-order property
        self.connect('notify::sort-order', self._notify_sort_order,
                     library_view)

        self.set_columns_clickable(False)


    def display_playing_tracks(self, show_playing):
        pass

    def define_menu(self):
        pass

    def display_columns(self):
        pass

    def selection_changed(self, entry_view):
        entries = entry_view.get_selected_entries()
        if entries and len(entries) > 0:
            self.source.entryviewpane.entry_view_results.emit('update-cover', self.source, entries[0])

    def add_album(self, album):
        print("CoverArtBrowser DEBUG - add_album()")
        tracks = album.get_tracks()

        for track in tracks:
            self.qm.add_entry(track.entry, -1)

        (_, playing) = self.shell.props.shell_player.get_playing()
        self.playing_changed(self.shell.props.shell_player, playing)

        artists = album.artists.split(', ')
        if self.artists == "":
            self.artists = artists
        else:
            self.artists = list(set(self.artists + artists))

        print("CoverArtBrowser DEBUG - add_album()")

    def clear(self):
        print("CoverArtBrowser DEBUG - clear()")

        for row in self.qm:
            self.qm.remove_entry(row[0])

        self.artists = ""

        print("CoverArtBrowser DEBUG - clear()")

    def do_entry_activated(self, entry):
        print("CoverArtBrowser DEBUG - do_entry_activated()")
        self.select_entry(entry)
        self.play_track_menu_item_callback(entry)
        print("CoverArtBrowser DEBUG - do_entry_activated()")
        return True

    def pre_popup_menu_callback(self, *args):
        pass

    def do_show_popup(self, over_entry):
        if over_entry:
            print("CoverArtBrowser DEBUG - do_show_popup()")

            self.popup.popup(self.source,
                             'entryview_popup_menu', 0, Gtk.get_current_event_time())

        return over_entry

    def play_similar_artist_menu_item_callback(self, *args):
        if not self.echonest_similar_playlist:
            self.echonest_similar_playlist = \
                EchoNestPlaylist(self.shell,
                                 self.shell.props.queue_source)

        selected = self.get_selected_entries()
        entry = selected[0]
        self.echonest_similar_playlist.start(entry, reinitialise=True)

    def play_similar_genre_menu_item_callback(self, *args):
        if not self.echonest_similar_genre_playlist:
            self.echonest_similar_genre_playlist = \
                EchoNestGenrePlaylist(self.shell,
                                      self.shell.props.queue_source)

        selected = self.get_selected_entries()
        entry = selected[0]
        self.echonest_similar_genre_playlist.start(entry, reinitialise=True)

    def play_similar_track_menu_item_callback(self, *args):
        if not self.lastfm_similar_playlist:
            self.lastfm_similar_playlist = \
                LastFMTrackPlaylist(self.shell,
                                    self.shell.props.queue_source)

        selected = self.get_selected_entries()
        entry = selected[0]
        self.lastfm_similar_playlist.start(entry, reinitialise=True)

    def play_next_track_menu_item_callback(self, *args):
        source = self.source_query_model

        selected = self.get_selected_entries()
        selected.reverse()

        selected = sorted(selected,
                          key=lambda song: song.get_ulong(RB.RhythmDBPropType.TRACK_NUMBER))

        entry = self.shell.props.shell_player.get_playing_entry()

        if not entry:
            return

        index = 0

        source = self.source_query_model

        # the API doesnt provide a method to find the index position of the entry that is playing
        # so lets reverse through the model calculating the position

        while entry is not None:
            index = index + 1
            entry = source.get_previous_from_entry(entry)

        for entry in selected:
            source.add_entry(entry, index)
            index = index + 1

    def play_track_menu_item_callback(self, *args):
        print("CoverArtBrowser DEBUG - play_track_menu_item_callback()")

        for row in self.source_query_model:
            self.source_query_model.remove_entry(row[0])

        selected = self.get_selected_entries()
        entry = selected[0]

        if len(selected) == 1:
            self.source_query_model.copy_contents(self.qm)
        else:
            self.add_tracks_to_source(self.source_query_model)

        self.source.props.query_model = self.source_query_model

        # library_view = self.shell.props.library_source.get_entry_view()
        # library_view.set_sorting_order('track-number', Gtk.SortType.ASCENDING)
        #self.set_sorting_order('track-number', Gtk.SortType.ASCENDING)

        # Start the music
        player = self.shell.props.shell_player
        player.play_entry(entry, self.source)

        print("CoverArtBrowser DEBUG - play_track_menu_item_callback()")

    def queue_track_menu_item_callback(self, *args):
        print("CoverArtBrowser DEBUG - queue_track_menu_item_callback()")

        self.add_tracks_to_source(self.shell.props.queue_source)

    def add_to_playing_menu_item_callback(self, *args):
        print("CoverArtBrowser DEBUG - add_to_playing_menu_item_callback()")
        self.add_tracks_to_source(None)

    def add_tracks_to_source(self, source):

        if source == None:
            source = self.source_query_model

        selected = self.get_selected_entries()
        selected.reverse()

        selected = sorted(selected,
                          key=lambda song: song.get_ulong(RB.RhythmDBPropType.TRACK_NUMBER))

        for entry in selected:
            source.add_entry(entry, -1)

        print("CoverArtBrowser DEBUG - queue_track_menu_item_callback()")

    def love_track(self, rating):
        '''
        utility function to set the rating for selected tracks
        '''
        selected = self.get_selected_entries()

        for entry in selected:
            self.shell.props.db.entry_set(entry, RB.RhythmDBPropType.RATING,
                                          rating)

        self.shell.props.db.commit()

    def show_properties_menu_item_callback(self, *args):
        print("CoverArtBrowser DEBUG - show_properties_menu_item_callback()")

        info_dialog = RB.SongInfo(source=self.source, entry_view=self)
        info_dialog.show_all()

        print("CoverArtBrowser DEBUG - show_properties_menu_item_callback()")

    def playing_song_changed(self, shell_player, entry):
        print("CoverArtBrowser DEBUG - playing_song_changed()")

        if entry is not None and self.get_entry_contained(entry):
            self.set_state(RB.EntryViewState.PLAYING)
        else:
            self.set_state(RB.EntryViewState.NOT_PLAYING)

        print("CoverArtBrowser DEBUG - playing_song_changed()")

    def playing_changed(self, shell_player, playing):
        print("CoverArtBrowser DEBUG - playing_changed()")
        entry = shell_player.get_playing_entry()

        if entry is not None and self.get_entry_contained(entry):
            if playing:
                self.set_state(RB.EntryViewState.PLAYING)
            else:
                self.set_state(RB.EntryViewState.PAUSED)
        else:
            self.set_state(RB.EntryViewState.NOT_PLAYING)

        print("CoverArtBrowser DEBUG - playing_changed()")

    def add_playlist_menu_item_callback(self, *args):
        print("CoverArtBrowser DEBUG - add_playlist_menu_item_callback")
        playlist_manager = self.shell.props.playlist_manager
        playlist = playlist_manager.new_playlist(_('New Playlist'), False)

        self.add_tracks_to_source(playlist)

    def playlist_menu_item_callback(self, *args):
        pass

    def add_to_static_playlist_menu_item_callback(self, action, param, args):
        print("CoverArtBrowser DEBUG - " + \
              "add_to_static_playlist_menu_item_callback")

        playlist = args['playlist']
        self.add_tracks_to_source(playlist)

    def _on_library_sorting_changed(self, view, _):
        self._old_sort_order = self.props.sort_order

        self.set_sorting_type(view.props.sort_order)

    def _notify_sort_order(self, view, _, library_view):
        if self.props.sort_order != self._old_sort_order:
            self.resort_model()

            # update library source's view direction
            library_view.set_sorting_type(self.props.sort_order)


class CoverArtCompactEntryView(BaseView):
    __hash__ = GObject.__hash__

    def __init__(self, shell, source):
        '''
        Initializes the entryview.
        '''
        super(CoverArtCompactEntryView, self).__init__(shell, source)

    def display_columns(self):

        self.col_map = OrderedDict([
            ('track-number', RB.EntryViewColumn.TRACK_NUMBER),
            ('title', RB.EntryViewColumn.TITLE),
            ('artist', RB.EntryViewColumn.ARTIST),
            ('rating', RB.EntryViewColumn.RATING),
            ('duration', RB.EntryViewColumn.DURATION)
        ])

        for entry in self.col_map:
            visible = False if entry == 'artist' else True
            self.append_column(self.col_map[entry], visible)

    def add_album(self, album):
        super(CoverArtCompactEntryView, self).add_album(album)

        if len(self.artists) > 1:
            self.get_column(RB.EntryViewColumn.ARTIST).set_visible(True)
        else:
            self.get_column(RB.EntryViewColumn.ARTIST).set_visible(False)

    def define_menu(self):
        popup = Menu(self.plugin, self.shell)
        popup.load_from_file('N/A',
                             'ui/coverart_entryview_compact_pop_rb3.ui')
        signals = {
            'ev_compact_play_track_menu_item': self.play_track_menu_item_callback,
            'ev_compact_play_next_track_menu_item': self.play_next_track_menu_item_callback,
            'ev_compact_queue_track_menu_item': self.queue_track_menu_item_callback,
            'ev_compact_add_to_playing_menu_item': self.add_to_playing_menu_item_callback,
            'ev_compact_new_playlist': self.add_playlist_menu_item_callback,
            'ev_compact_show_properties_menu_item': self.show_properties_menu_item_callback,
            'ev_compact_similar_track_menu_item': self.play_similar_track_menu_item_callback,
            'ev_compact_similar_artist_menu_item': self.play_similar_artist_menu_item_callback,
            'ev_compact_similar_genre_menu_item': self.play_similar_genre_menu_item_callback}

        popup.connect_signals(signals)
        popup.connect('pre-popup', self.pre_popup_menu_callback)
        self.popup = popup

    def playlist_menu_item_callback(self, *args):
        print("CoverArtBrowser DEBUG - playlist_menu_item_callback")

        self.source.playlist_fillmenu(self.popup, 'ev_compact_playlist_sub_menu_item', 'ev_compact_playlist_section',
                                      self.actiongroup, self.add_to_static_playlist_menu_item_callback)

    def pre_popup_menu_callback(self, *args):
        '''
        Callback when the popup menu is about to be displayed
        '''

        state, sensitive = self.shell.props.shell_player.get_playing()
        if not state:
            sensitive = False

        self.popup.set_sensitive('ev_compact_add_to_playing_menu_item', sensitive)
        self.popup.set_sensitive('ev_compact_play_next_track_menu_item', sensitive)

        if not self.external_plugins:
            self.external_plugins = \
                CreateExternalPluginMenu("ev_compact_entryview", 6, self.popup)
            self.external_plugins.create_menu('entryview_compact_popup_menu')

        self.playlist_menu_item_callback()


class CoverArtEntryView(BaseView):
    __hash__ = GObject.__hash__

    def __init__(self, shell, source):
        '''
        Initializes the entryview.
        '''
        super(CoverArtEntryView, self).__init__(shell, source)

    def display_columns(self):

        self.col_map = OrderedDict([
            ('track-number', RB.EntryViewColumn.TRACK_NUMBER),
            ('title', RB.EntryViewColumn.TITLE),
            ('genre', RB.EntryViewColumn.GENRE),
            ('artist', RB.EntryViewColumn.ARTIST),
            ('album', RB.EntryViewColumn.ALBUM),
            ('composer', RB.EntryViewColumn.COMPOSER),
            ('date', RB.EntryViewColumn.YEAR),
            ('duration', RB.EntryViewColumn.DURATION),
            ('bitrate', RB.EntryViewColumn.QUALITY),
            ('play-count', RB.EntryViewColumn.PLAY_COUNT),
            ('beats-per-minute', RB.EntryViewColumn.BPM),
            ('comment', RB.EntryViewColumn.COMMENT),
            ('location', RB.EntryViewColumn.LOCATION),
            ('rating', RB.EntryViewColumn.RATING),
            ('last-played', RB.EntryViewColumn.LAST_PLAYED),
            ('first-seen', RB.EntryViewColumn.FIRST_SEEN)
        ])

        for entry in self.col_map:
            visible = True if entry == 'title' else False
            self.append_column(self.col_map[entry], visible)

        # connect the visible-columns global setting to update our entryview
        gs = GSetting()
        rhythm_settings = gs.get_setting(gs.Path.RBSOURCE)
        rhythm_settings.connect('changed::visible-columns',
                                self.on_visible_columns_changed)
        self.on_visible_columns_changed(rhythm_settings, 'visible-columns')

    def on_visible_columns_changed(self, settings, key):
        print("CoverArtBrowser DEBUG - on_visible_columns_changed()")
        # reset current columns
        print("CoverArtBrowser DEBUG - end on_visible_columns_changed()")
        for entry in self.col_map:
            col = self.get_column(self.col_map[entry])
            if entry in settings[key]:
                col.set_visible(True)
            else:
                if entry != 'title':
                    col.set_visible(False)

        print("CoverArtBrowser DEBUG - end on_visible_columns_changed()")

    def define_menu(self):
        popup = Menu(self.plugin, self.shell)
        popup.load_from_file('N/A',
                             'ui/coverart_entryview_full_pop_rb3.ui')
        signals = {
            'ev_full_play_track_menu_item': self.play_track_menu_item_callback,
            'ev_full_play_next_track_menu_item': self.play_next_track_menu_item_callback,
            'ev_full_queue_track_menu_item': self.queue_track_menu_item_callback,
            'ev_full_add_to_playing_menu_item': self.add_to_playing_menu_item_callback,
            'ev_full_new_playlist': self.add_playlist_menu_item_callback,
            'ev_full_show_properties_menu_item': self.show_properties_menu_item_callback,
            'ev_full_similar_track_menu_item': self.play_similar_track_menu_item_callback,
            'ev_full_similar_artist_menu_item': self.play_similar_artist_menu_item_callback,
            'ev_full_similar_genre_menu_item': self.play_similar_genre_menu_item_callback}

        popup.connect_signals(signals)
        popup.connect('pre-popup', self.pre_popup_menu_callback)
        self.popup = popup

    def playlist_menu_item_callback(self, *args):
        print("CoverArtBrowser DEBUG - playlist_menu_item_callback")

        self.source.playlist_fillmenu(self.popup, 'ev_full_playlist_sub_menu_item', 'ev_full_playlist_section',
                                      self.actiongroup, self.add_to_static_playlist_menu_item_callback)

    def pre_popup_menu_callback(self, *args):
        '''
        Callback when the popup menu is about to be displayed
        '''

        state, sensitive = self.shell.props.shell_player.get_playing()
        if not state:
            sensitive = False

        self.popup.set_sensitive('ev_full_add_to_playing_menu_item', sensitive)
        self.popup.set_sensitive('ev_full_play_next_track_menu_item', sensitive)

        if not self.external_plugins:
            self.external_plugins = \
                CreateExternalPluginMenu("ev_full_entryview", 6, self.popup)
            self.external_plugins.create_menu('entryview_full_popup_menu')

        self.playlist_menu_item_callback()


GObject.type_register(CoverArtEntryView)
GObject.type_register(CoverArtCompactEntryView)

