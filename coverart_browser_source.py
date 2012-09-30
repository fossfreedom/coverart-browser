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

import rb
import locale
import gettext


from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import RB

from coverart_album import AlbumLoader
from coverart_album import Album
from coverart_album import Cover
from coverart_entryview import CoverArtEntryView


class CoverArtBrowserSource(RB.Source):
    '''
    Source utilized by the plugin to show all it's ui.
    '''
    LOCALE_DOMAIN = 'coverart_browser'
    filter_type = Album.FILTER_ALL
    search_text = ''

    custom_statusbar_enabled = GObject.property(type=bool, default=False)
    display_tracks_enabled = GObject.property(type=bool, default=False)
    display_text_enabled = GObject.property(type=bool, default=False)
    display_text_loading_enabled = GObject.property(type=bool, default=True)
    display_text_ellipsize_enabled = GObject.property(type=bool, default=False)
    display_text_ellipsize_length = GObject.property(type=int, default=20)

    def __init__(self):
        '''
        Initializes the source.
        '''

        self.hasActivated = False
        super(CoverArtBrowserSource, self).__init__(
            name="CoverArtBrowserPlugin")

    def do_get_status(self, *args):
        '''
        Method called by Rhythmbox to figure out what to show on this source
        statusbar.
        If the custom statusbar is disabled, the source will
        show the selected album info.
        Also, it makes sure to show the progress on the album loading.s
        '''
        try:
            progress = self.loader.progress
            progress_text = 'Loading...' if progress < 1 else ''
        except:
            progress = 1
            progress_text = ''

        return (self.status, progress_text, progress)

    def do_show_popup(self):
        '''
        Method called by Rhythmbox when an action on our source prompts it
        to show a popup.
        '''
        self.source_menu.popup(None, None, None, None, 0,
            Gtk.get_current_event_time())

        return True

    def do_selected(self):
        '''
        Called by Rhythmbox when the source is selected. It makes sure to
        create the ui the first time the source is showed.
        '''
        # first time of activation -> add graphical stuff
        if not self.hasActivated:
            self.do_impl_activate()

            #indicate that the source was activated before
            self.hasActivated = True

    def do_impl_activate(self):
        '''
        Called by do_selected the first time the source is activated.
        It creates all the source ui and connects the necesary signals for it
        correct behavior.
        '''
        print "do_impl_activate"

        # initialise some variables
        self.plugin = self.props.plugin
        self.shell = self.props.shell
        self.status = ''
        self.search_text = ''
        self.filter_type = Album.FILTER_ALL
        self.compare_albums = Album.compare_albums_by_name

        # connect properties signals
        self.connect('notify::custom-statusbar-enabled',
            self.on_notify_custom_statusbar_enabled)

        self.connect('notify::display-tracks-enabled',
            self.on_notify_display_tracks_enabled)

        self.connect('notify::display-text-enabled',
            self.on_notify_display_text_enabled)

        self.connect('notify::display-text-loading-enabled',
            self.on_notify_display_text_loading_enabled)

        self.connect('notify::display-text-ellipsize-enabled',
            self.on_notify_display_text_ellipsize)

        self.connect('notify::display-text-ellipsize-length',
            self.on_notify_display_text_ellipsize)

        # setup translation support
        locale.setlocale(locale.LC_ALL, '')
        locale.bindtextdomain(self.LOCALE_DOMAIN, "/usr/share/locale")
        locale.textdomain(self.LOCALE_DOMAIN)
        gettext.bindtextdomain(self.LOCALE_DOMAIN, "/usr/share/locale")
        gettext.textdomain(self.LOCALE_DOMAIN)
        gettext.install(self.LOCALE_DOMAIN)

        #indicate that the source was activated before
        self.hasActivated = True

        # dialog has not been created so lets do so.
        ui = Gtk.Builder()
        ui.set_translation_domain(self.LOCALE_DOMAIN)
        ui.add_from_file(rb.find_plugin_file(self.plugin,
            'coverart_browser.ui'))
        ui.connect_signals(self)

        # load the page and put it in the source
        self.page = ui.get_object('main_box')
        self.pack_start(self.page, True, True, 0)

        # get widgets for main icon-view
        self.status_label = ui.get_object('status_label')
        self.covers_view = ui.get_object('covers_view')
        self.search_entry = ui.get_object('search_entry')
        self.popup_menu = ui.get_object('popup_menu')
        self.cover_search_menu_item = ui.get_object('cover_search_menu_item')
        self.status_label = ui.get_object('status_label')
        self.status_separator = ui.get_object('status_separator')
        self.request_status_box = ui.get_object('request_status_box')
        self.request_spinner = ui.get_object('request_spinner')
        self.request_statusbar = ui.get_object('request_statusbar')
        self.request_cancel_button = ui.get_object('request_cancel_button')
        self.sort_by_album_radio = ui.get_object('album_name_sort_radio')
        self.sort_by_artist_radio = ui.get_object('artist_name_sort_radio')
        self.descending_sort_radio = ui.get_object('descending_sort_radio')
        self.ascending_sort_radio = ui.get_object('ascending_sort_radio')

        # setup the sorting
        self.sort_by_album_radio.set_mode(False)
        self.sort_by_artist_radio.set_mode(False)
        self.descending_sort_radio.set_mode(False)
        self.ascending_sort_radio.set_mode(False)

        # workaround for some RBSearchEntry's problems
        search_entry = ui.get_object('search_entry')
        search_entry.set_placeholder(_('Search album'))
        search_entry.show_all()

        # setup entry-view objects and widgets
        self.paned = ui.get_object('paned')
        self.entry_view_expander = ui.get_object('entryviewexpander')
        self.entry_view = CoverArtEntryView(self.shell, self)
        self.entry_view.show_all()
        self.entry_view_expander.add(self.entry_view)
        self.paned_position = 0
        self.entry_view_box = ui.get_object('entryview_box')

        self.on_notify_display_tracks_enabled(_)

        # get widgets for source popup
        self.source_menu = ui.get_object('source_menu')
        self.source_menu_search_all_item = ui.get_object(
            'source_search_menu_item')

        # get widgets for filter popup
        self.filter_menu = ui.get_object('filter_menu')
        self.filter_menu_all_item = ui.get_object('filter_all_menu_item')
        self.filter_menu_artist_item = ui.get_object('filter_artist_menu_item')
        self.filter_menu_album_artist_item = ui.get_object(
            'filter_album_artist_menu_item')
        self.filter_menu_album_item = ui.get_object('filter_album_menu_item')
        self.filter_menu_track_title_item = ui.get_object(
            'filter_track_title_menu_item')

        # set the ellipsize
        if self.display_text_ellipsize_enabled:
            Album.set_ellipsize_length(self.display_text_ellipsize_length)

        # get the loader
        self.loader = AlbumLoader.get_instance(self.plugin,
            ui.get_object('covers_model'), self.props.query_model)

        # if the source is fully loaded, enable the full cover search item
        if self.loader.progress == 1:
            self.load_finished_callback()

        # if the text during load is enabled, activate it
        if self.display_text_loading_enabled:
            self.on_notify_display_text_enabled()

        # retrieve and set the model, it's filter and the sorting column
        self.covers_model_store = self.loader.cover_model

        self.covers_model_store.set_sort_column_id(2, Gtk.SortType.DESCENDING)
        self.covers_model_store.set_sort_func(2, self.sort_albums)

        self.covers_model = self.covers_model_store.filter_new()
        self.covers_model.set_visible_func(self.visible_covers_callback)

        self.covers_view.set_model(self.covers_model)

        # connect some signals to the loader to keep the source informed
        self.album_mod_id = self.loader.connect('album-modified',
            self.album_modified_callback)
        self.load_fin_id = self.loader.connect('load-finished',
            self.load_finished_callback)
        self.reload_fin_id = self.loader.connect('reload-finished',
            self.reload_finished_callback)
        self.notify_prog_id = self.loader.connect('notify::progress',
            lambda *args: self.notify_status_changed())

        print "CoverArtBrowser DEBUG - end show_browser_dialog"

    def load_finished_callback(self, _):
        '''
        Callback called when the loader finishes loading albums into the
        covers view model.
        '''
        print 'CoverArt Load Finished'
        if not self.request_status_box.get_visible():
            # it should only be enabled if no cover request is going on
            self.source_menu_search_all_item.set_sensitive(True)

        # enable markup if necesary
        if self.display_text_enabled and not self.display_text_loading_enabled:
            self.activate_markup(True)

    def reload_finished_callback(self, _):
        '''
        Callback called when the loader finishes reloading albums into the
        covers view model.
        '''
        if self.display_text_enabled and \
            not self.display_text_loading_enabled \
            and self.loader.progress == 1:
            self.activate_markup(True)

    def on_notify_custom_statusbar_enabled(self, *args):
        '''
        Callback for when the option to show the custom statusbar is enabled
        or disabled from the plugin's preferences dialog.
        '''
        if self.custom_statusbar_enabled:
            self.status = ''
            self.notify_status_changed()
        else:
            self.status_label.hide()
            self.status_separator.hide()

        self.selectionchanged_callback(self.covers_view)

    def on_notify_display_tracks_enabled(self, *args):
        '''
        Callback called when the option 'display tracks' is enabled or disabled
        on the plugin's preferences dialog
        '''
        if self.display_tracks_enabled:
            # make the entry view visible
            self.entry_view_box.set_visible(True)

            self.entry_view_expander_expanded_callback(
                self.entry_view_expander, None)

            # update it with the current selected album
            self.selectionchanged_callback(self.covers_view)

        else:
            if self.entry_view_expander.get_expanded():
                self.paned_position = self.paned.get_position()

            self.entry_view_box.set_visible(False)

    def on_notify_display_text_enabled(self, *args):
        '''
        Callback called when the option 'display text under cover' is enabled
        or disabled on the plugin's preferences dialog
        '''
        self.activate_markup(self.display_text_enabled)

    def on_notify_display_text_loading_enabled(self, *args):
        '''
        Callback called when the option 'show text while loading' is enabled
        or disabled on the plugin's prefereces dialog.
        This option only makes a visible effect if it's toggled during the
        album loading.
        '''
        if self.loader.progress < 1 or self.loader.reloading:
            self.activate_markup(self.display_text_loading_enabled)

    def activate_markup(self, activate):
        '''
        Utility method to activate/deactivate the markup text on the
        cover view.
        '''
        if activate:
            column = 3
            item_width = Cover.COVER_SIZE + 20
        else:
            column = item_width = -1

        self.covers_view.set_markup_column(column)
        self.covers_view.set_item_width(item_width)

    def on_notify_display_text_ellipsize(self, *args):
        '''
        Callback called when one of the properties related with the ellipsize
        option is changed.
        '''
        if self.display_text_ellipsize_enabled:
            Album.set_ellipsize_length(self.display_text_ellipsize_length)
        else:
            Album.set_ellipsize_length(0)

        if not self.display_text_loading_enabled:
            self.activate_markup(False)

        self.loader.reload_model()

    def album_modified_callback(self, _, modified_album):
        '''
        Callback called by the album loader when one of the albums managed
        by him gets modified in some way.
        '''
        print "CoverArtBrowser DEBUG - album_modified_callback"
        try:
            album = \
                self.covers_model[self.covers_view.get_selected_items()[0]][2]
        except:
            return

        if album is modified_album:
            self.selectionchanged_callback(self.covers_view)

        print "CoverArtBrowser DEBUG - end album_modified_callback"

    def visible_covers_callback(self, model, iter, data):
        '''
        Callback called by the model filter to decide wheter to filter or not
        an album.
        '''
        if self.search_text == "":
            return True

        return model[iter][2].contains(self.search_text, self.filter_type)

    def search_show_popup_callback(self, entry):
        '''
        Callback called by the search entry when the magnifier is clicked.
        It prompts the user through a popup to select a filter type.
        '''
        self.filter_menu.popup(None, None, None, None, 0,
            Gtk.get_current_event_time())

    def searchchanged_callback(self, entry, text):
        '''
        Callback called by the search entry when a new search must
        be performed.
        '''
        print "CoverArtBrowser DEBUG - searchchanged_callback"

        self.search_text = text
        self.covers_model.refilter()

        print "CoverArtBrowser DEBUG - end searchchanged_callback"

    def update_iconview_callback(self, *args):
        '''
        Callback called by the cover view when its view port gets resized.
        It forces the cover_view to redraw it's contents to fill the available
        space.
        '''
        self.covers_view.set_columns(0)
        self.covers_view.set_columns(-1)

    def mouseclick_callback(self, iconview, event):
        '''
        Callback called when the user clicks somewhere on the cover_view.
        If it's a right click, it shows a popup showing different actions to
        perform with the selected album.
        '''
        print "CoverArtBrowser DEBUG - mouseclick_callback()"
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = iconview.get_path_at_pos(x, y)

            if pthinfo is None:
                return

            iconview.grab_focus()
            iconview.select_path(pthinfo)

            self.popup_menu.popup(None, None, None, None, event.button, time)

        print "CoverArtBrowser DEBUG - end mouseclick_callback()"
        return

    def item_activated_callback(self, iconview, path):
        '''
        Callback called when the cover view is double clicked or space-bar
        is pressed. It plays the selected album
        '''
        iconview.grab_focus()
        iconview.select_path(path)

        self.play_album_menu_item_callback(_)
        return True

    def get_selected_albums(self):
        '''
        Retrieves the currently selected albums on the cover_view.
        '''
        selected_albums = []

        model = self.covers_model

        for selected in self.covers_view.get_selected_items():
            selected_albums.append(model[selected][2])

        return selected_albums

    def play_album_menu_item_callback(self, _):
        '''
        Callback called when the play album item from the cover view popup is
        selected. It cleans the play queue and queues the selected album.
        '''
        # callback when play an album
        print "CoverArtBrowser DEBUG - play_menu_callback"

        # clear the queue
        play_queue = self.shell.props.queue_source
        for row in play_queue.props.query_model:
            play_queue.remove_entry(row[0])

        self.queue_selected_album()

        # Start the music
        player = self.shell.props.shell_player
        player.stop()
        player.set_playing_source(self.shell.props.queue_source)
        player.playpause(True)
        print "CoverArtBrowser DEBUG - end play_menu_callback"

    def queue_album_menu_item_callback(self, _):
        '''
        Callback called when the queue album item from the cover view popup is
        selected. It queues the selected album at the end of the play queue.
        '''
        print "CoverArtBrowser DEBUG - queue_menu_callback()"

        self.queue_selected_album()

        print "CoverArtBrowser DEBUG - queue_menu_callback()"

    def queue_selected_album(self):
        '''
        Utilitary method that queues all entries from an album into the play
        queue.
        '''
        selected_albums = self.get_selected_albums()

        for album in selected_albums:
            # Retrieve and sort the entries of the album
            songs = sorted(album.entries, key=lambda song:
                song.get_ulong(RB.RhythmDBPropType.TRACK_NUMBER))

            # Add the songs to the play queue
            for song in songs:
                self.shell.props.queue_source.add_entry(song, -1)

    def cover_search_menu_item_callback(self, menu_item):
        '''
        Callback called when the search cover option is selected from the
        cover view popup. It prompts the album loader to retrieve the selected
        album cover
        '''
        print "CoverArtBrowser DEBUG - cover_search_menu_item_callback()"
        selected_albums = self.get_selected_albums()

        self.request_status_box.show_all()
        self.source_menu_search_all_item.set_sensitive(False)
        self.cover_search_menu_item.set_sensitive(False)

        self.loader.search_covers(selected_albums,
            self.update_request_status_bar)

        print "CoverArtBrowser DEBUG - end cover_search_menu_item_callback()"

    def show_properties_menu_item_callback(self, menu_item):
        '''
        Callback called when the show album properties option is selected from
        the cover view popup. It shows a SongInfo dialog showing the selected
        albums' entries info, which can be modified.
        '''
        self.entry_view.select_all()

        info_dialog = RB.SongInfo(source=self, entry_view=self.entry_view)

        info_dialog.show_all()

    def search_all_covers_callback(self, _):
        '''
        Callback called when the search all covers option is selected from the
        source's popup. It prompts the album loader to request ALL album's
        covers
        '''
        print "CoverArtBrowser DEBUG - search_all_covers_callback()"
        self.request_status_box.show_all()
        self.source_menu_search_all_item.set_sensitive(False)
        self.cover_search_menu_item.set_sensitive(False)
        self.loader.search_covers(callback=self.update_request_status_bar)

        print "CoverArtBrowser DEBUG - end search_all_covers_callback()"

    def update_request_status_bar(self, album):
        '''
        Callback called by the album loader starts performing a new cover
        request. It prompts the source to change the content of the request
        statusbar.
        '''
        if album:
            self.request_statusbar.set_text(
                (_('Requesting cover for %s - %s...') % (album.name,
                album.album_artist)).decode('UTF-8'))
        else:
            self.request_status_box.hide()
            self.source_menu_search_all_item.set_sensitive(True)
            self.cover_search_menu_item.set_sensitive(True)
            self.request_cancel_button.set_sensitive(True)

    def cancel_request_callback(self, _):
        '''
        Callback connected to the cancel button on the request statusbar.
        When called, it prompts the album loader to cancel the full cover
        search after the current cover.
        '''
        self.request_cancel_button.set_sensitive(False)
        self.loader.cancel_cover_request()

    def selectionchanged_callback(self, widget):
        '''
        Callback called when an item from the cover view gets selected.
        It changes the content of the statusbar (which statusbar is dependant
        on the custom_statusbar_enabled property) to show info about the
        current selected album.
        '''
        print "CoverArtBrowser DEBUG - selectionchanged_callback"

        # clear the entry view
        self.entry_view.clear()

        model = widget.get_model()

        if model is None:
            if self.custom_statusbar_enabled:
                # if the custom statusbar is enabled, this should hide it and
                # the separator
                # Note: we hide just in case, maybe they are already hidden
                self.status_label.hide()
                self.status_separator.hide()
            else:
                # set the status to an empty string and notify the change
                self.status = ''
                self.notify_status_changed()

            return

        selected = self.get_selected_albums()

        track_count = 0
        duration = 0

        for album in selected:
            # Calculate duration and number of tracks from that album
            track_count += album.get_track_count()
            duration += album.calculate_duration_in_mins()

            # add teh album to the entry_view
            self.entry_view.add_album(album)

        # now lets build up a status label containing some 'interesting stuff'
        #about the album
        if len(selected) == 1:
            status = (_('%s by %s') % (album.name, album.album_artist)).decode(
                'UTF-8')
        else:
            status = (_('%d selected albums ') % (len(selected))).decode(
                'UTF-8')

        if track_count == 1:
            status += (_(' with 1 track')).decode('UTF-8')
        else:
            status += (_(' with %d tracks') % track_count).decode('UTF-8')

        if duration == 1:
            status += (_(' and a duration of 1 minute')).decode('UTF-8')
        else:
            status += (_(' and a duration of %d minutes') % duration).decode(
                'UTF-8')

        if self.custom_statusbar_enabled:
            # if the custom statusbar is enabled... use it.
            self.status_label.set_text(status)
            self.status_label.show()

            if self.request_status_box.get_visible():
                self.status_separator.show()

        else:
            # use the global statusbar from Rhythmbox
            self.status = status
            self.notify_status_changed()

    def filter_menu_callback(self, radiomenu):
        '''
        Callback called when an item from the filters popup menu is clicked.
        It changes the current filter type for the search to the one selected
        on the popup.
        '''
        # radiomenu is of type GtkRadioMenuItem

        if radiomenu == self.filter_menu_all_item:
            self.filter_type = Album.FILTER_ALL
        elif radiomenu == self.filter_menu_album_item:
            self.filter_type = Album.FILTER_ALBUM
        elif radiomenu == self.filter_menu_artist_item:
            self.filter_type = Album.FILTER_ARTIST
        elif radiomenu == self.filter_menu_album_artist_item:
            self.filter_type = Album.FILTER_ALBUM_ARTIST
        elif radiomenu == self.filter_menu_track_title_item:
            self.filter_type = Album.FILTER_TRACK_TITLE
        else:
            assert "unknown radiomenu"

        self.searchchanged_callback(_, self.search_text)

    def entry_view_expander_expanded_callback(self, action, param):
        '''
        Callback connected to expanded signal of the paned GtkExpander
        '''
        expand = action.get_expanded()

        if not expand:
            (x, y) = Gtk.Widget.get_toplevel(self.status_label).get_size()
            self.paned_position = self.paned.get_position()
            self.paned.set_position(y - 10)
        else:
            (x, y) = Gtk.Widget.get_toplevel(self.status_label).get_size()
            if self.paned_position == 0:
                self.paned_position = (y / 2)

            self.paned.set_position(self.paned_position)

    def paned_button_press_callback(self, *args):
        '''
        This callback allows or denies the paned handle to move depending on
        the expanded state of the entry_view
        '''
        return not self.entry_view_expander.get_expanded()

    def sorting_criteria_changed(self, radio):
        '''
        Callback called when a radio corresponding to a sorting order is
        toggled. It changes the sorting function and reorders the cover model.
        '''
        if not radio.get_active():
            return

        if radio is self.sort_by_album_radio:
            self.compare_albums = Album.compare_albums_by_name
        else:
            self.compare_albums = Album.compare_albums_by_album_artist

        if self.display_text_enabled and not self.display_text_loading_enabled:
            self.activate_markup(False)

        self.loader.reload_model()

    def sorting_direction_changed(self, radio):
        '''
        Callback calledn when a radio corresponding to a sorting direction is
        toggled. It changes the sorting direction and reorders the cover model
        '''
        if not radio.get_active():
            return

        if radio is self.descending_sort_radio:
            sort_direction = Gtk.SortType.DESCENDING
        else:
            sort_direction = Gtk.SortType.ASCENDING

        if self.display_text_enabled and not self.display_text_loading_enabled:
            self.activate_markup(False)

        self.loader.reload_model()
        self.covers_model_store.set_sort_column_id(2, sort_direction)

    def sort_albums(self, model, iter1, iter2, _):
        '''
        Utility function used as the sorting function for our model.
        It actually just retrieves the albums and delegates the comparison
        to the current comparation function.
        '''
        return self.compare_albums(model[iter1][2], model[iter2][2])

    def do_delete_thyself(self):
        '''
        Method called by Rhythmbox's when the source is deleted. It makes sure
        to free all the source's related resources to avoid memory leaking and
        loose signals.
        '''
        if not self.hasActivated:
            del self.hasActivated

            return

        # destroy the ui
        self.page.destroy()

        # disconnect signals
        self.loader.disconnect(self.load_fin_id)
        self.loader.disconnect(self.reload_fin_id)
        self.loader.disconnect(self.album_mod_id)
        self.loader.disconnect(self.notify_prog_id)

        # delete references
        del self.shell
        del self.plugin
        del self.loader
        del self.covers_model_store
        del self.covers_model
        del self.covers_view
        del self.filter_menu
        del self.filter_menu_album_artist_item
        del self.filter_menu_album_item
        del self.filter_menu_all_item
        del self.filter_menu_artist_item
        del self.filter_menu_track_title_item
        del self.filter_type
        del self.page
        del self.paned
        del self.popup_menu
        del self.request_cancel_button
        del self.request_spinner
        del self.request_status_box
        del self.request_statusbar
        del self.search_entry
        del self.search_text
        del self.source_menu
        del self.source_menu_search_all_item
        del self.sort_by_album_radio
        del self.sort_by_artist_radio
        del self.descending_sort_radio
        del self.ascending_sort_radio
        del self.status
        del self.status_label
        del self.status_separator
        del self.reload_fin_id
        del self.load_fin_id
        del self.album_mod_id
        del self.notify_prog_id
        del self.hasActivated

GObject.type_register(CoverArtBrowserSource)
