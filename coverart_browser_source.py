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
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import RB
from gi.repository import Gdk
from gi.repository import GdkPixbuf

from coverart_album import AlbumLoader
from coverart_album import Album


class CoverArtBrowserSource(RB.Source):
    '''
    Source utilized by the plugin to show all it's ui.
    '''
    LOCALE_DOMAIN = 'coverart_browser'
    filter_type = Album.FILTER_ALL
    search_text = ''

    custom_statusbar_enabled = GObject.property(type=bool, default=False)
    display_tracks_enabled = GObject.property(type=bool, default=False)

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

        # connect properties signals
        self.connect('notify::custom-statusbar-enabled',
            self.on_notify_custom_statusbar_enabled)

        self.connect('notify::display-tracks-enabled',
            self.on_notify_display_tracks_enabled)

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

        # workaround for some RBSearchEntry's problems
        search_entry = ui.get_object('search_entry')
        search_entry.set_placeholder(_('Search album'))
        search_entry.show_all()

        # setup entry-view
        self.entry_view_expander = ui.get_object( 'entryviewexpander' )
        self.entry_view = RB.EntryView.new(self.shell.props.db, self.shell.props.shell_player, True,False)
        self.entry_view.append_column(RB.EntryViewColumn.TRACK_NUMBER, True)
        self.entry_view.append_column(RB.EntryViewColumn.GENRE, True)
        self.entry_view.append_column(RB.EntryViewColumn.TITLE, True)
        self.entry_view.append_column(RB.EntryViewColumn.ARTIST, True)
        self.entry_view.append_column(RB.EntryViewColumn.ALBUM, True)
        self.entry_view.append_column(RB.EntryViewColumn.DURATION, True)
        self.entry_view.set_columns_clickable(False)
        self.entry_view.show_all()
        self.entry_view_expander.add(self.entry_view)
        

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

        # set the model for the icon view
        self.covers_model_store = Gtk.ListStore(GObject.TYPE_STRING,
            GdkPixbuf.Pixbuf, object)

        self.covers_model = self.covers_model_store.filter_new()
        self.covers_model.set_visible_func(self.visible_covers_callback)

        self.covers_view.set_model(self.covers_model)

        # size pixbuf updated workaround
        self.covers_model_store.connect('row-changed',
            self.update_iconview_callback)

        # load the albums
        self.loader = AlbumLoader(self.plugin, self.covers_model_store)
        self.loader.connect('load-finished', self.load_finished_callback)
        self.loader.connect('album-modified', self.album_modified_callback)
        self.loader.connect('notify::progress', lambda *args:
            self.notify_status_changed())

        self.loader.load_albums(
            self.shell.props.library_source.props.base_query_model)

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
        
        self.selectionchanged_callback( self.covers_view )

        self.selectionchanged_callback(self.covers_view)

    def on_notify_display_tracks_enabled(self, *args):
        self.selectionchanged_callback(self.covers_view)

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
            
        return model[iter][2].contains( self.search_text, self.filter_type )

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

            model = iconview.get_model()
            self.selected_album = model[pthinfo][2]

            self.popup_menu.popup(None, None, None, None, event.button, time)

        print "CoverArtBrowser DEBUG - end mouseclick_callback()"
        return

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
        # Retrieve and sort the entries of the album
        songs = sorted(self.selected_album.entries,
            key=lambda song: song.get_ulong(RB.RhythmDBPropType.TRACK_NUMBER))

        # Add the songs to the play queue
        for song in songs:
            self.shell.props.queue_source.add_entry(song, -1)

    def cover_search_menu_item_callback(self, menu_item):
        '''
        Callback called when the search cover option is selected from the
        cover view popup. It promps the album loader to retrieve the selected
        album cover
        '''
        print "CoverArtBrowser DEBUG - cover_search_menu_item_callback()"
        # don't start another fetch if we are in middle of one right now
        if self.request_status_box.get_visible():
            return

        # fetch the album and hide the status_box once finished
        def cover_search_callback(*args):
            self.request_spinner.hide()

            # all args except for args[0] are None if no cover was found
            if args[1]:
                self.request_statusbar.set_text(_('Cover found!'))
            else:
                self.request_statusbar.set_text(_('No cover found.'))

            def restore(_):
                self.request_status_box.hide()
                self.cover_search_menu_item.set_sensitive(True)
                self.source_menu_search_all_item.set_sensitive(
                    self.loader.progress == 1)

                # hide separator just in case
                self.status_separator.hide()

            # set a timeout to hide the box and enable items
            Gdk.threads_add_timeout(GLib.PRIORITY_DEFAULT, 1500, restore,
                None)

        self.loader.search_cover_for_album(self.selected_album,
            cover_search_callback)

        # show the status bar indicating we're fetching the cover
        self.request_statusbar.set_text(
            (_('Requesting cover for %s - %s...') %
            (self.selected_album.name,
                self.selected_album.album_artist)).decode('UTF-8'))
        self.request_status_box.show_all()
        self.request_cancel_button.hide()

        if self.status_label.get_visible():
            self.status_separator.show()

        # disable full cover search and cover search items
        self.cover_search_menu_item.set_sensitive(False)
        self.source_menu_search_all_item.set_sensitive(False)

        print "CoverArtBrowser DEBUG - end cover_search_menu_item_callback()"

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
        self.loader.search_all_covers(self.update_request_status_bar)

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
        # callback when focus had changed on an album
        model = widget.get_model()
        try:
            album = model[widget.get_selected_items()[0]][2]
        except:
            if self.custom_statusbar_enabled:
                # if the custom statusbar is enabled, this should hide it and
                # the separator
                # Note: we hide just in case, maybe they are already hided
                self.status_label.hide()
                self.status_separator.hide()
            else:
                # set the status to an empty string and notify the change
                self.status = ''
                self.notify_status_changed()
            return

        # now lets build up a status label containing some 'interesting stuff'
        #about the album
        status = ('%s - %s' % (album.name, album.album_artist)).decode('UTF-8')

        # Calculate duration and number of tracks from that album
        track_count = album.get_track_count()
        duration = album.calculate_duration_in_mins()

        if track_count == 1:
            status += (_(' has 1 track')).decode('UTF-8')
        else:
            status += (_(' has %d tracks') % track_count).decode('UTF-8')

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

        qm = RB.RhythmDBQueryModel.new_empty(self.shell.props.db)
        album.get_entries(qm)
        self.entry_view.set_model(qm)

        if self.display_tracks_enabled:
        #    self.paned.set_position( self.status_label.get_position() - 10)
            self.entry_view_expander.show_all()
        else:
            self.entry_view_expander.hide()

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

    def entry_view_expander_expanded_callback( self, action, param):
        expand = action.get_expanded()

        self.entry_view_expander.set_property("expand", expand)
        #self.entry_view.set_property("vexpand", expand)
        
GObject.type_register(CoverArtBrowserSource)

