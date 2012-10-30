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

from gi.repository import GObject
from gi.repository import Gio
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import RB

from coverart_album import AlbumLoader
from coverart_album import Album
from coverart_entryview import CoverArtEntryView
from coverart_search import CoverSearchPane
from coverart_browser_prefs import GSetting
from coverart_browser_prefs import CoverLocale


class CoverArtBrowserSource(RB.Source):
    '''
    Source utilized by the plugin to show all it's ui.
    '''
    custom_statusbar_enabled = GObject.property(type=bool, default=False)
    display_bottom_enabled = GObject.property(type=bool, default=False)
    display_text_enabled = GObject.property(type=bool, default=False)
    display_text_loading_enabled = GObject.property(type=bool, default=True)
    rating_threshold = GObject.property(type=float, default=0)
    toolbar_pos = GObject.property(type=int, default=0)
    genre_filter_visible = GObject.property(type=bool, default=True)
    rating_sort_visible = GObject.property(type=bool, default=False)
    year_sort_visible = GObject.property(type=bool, default=False)

    def __init__(self, **kargs):
        '''
        Initializes the source.
        '''
        super(CoverArtBrowserSource, self).__init__(
            **kargs)

        # create source_source_settings and connect the source's properties
        self.gs = GSetting()

        self._connect_properties()

        self.filter_type = Album.FILTER_ALL
        self.search_text = ''
        self.hasActivated = False
        self.last_toolbar_pos = 0
        self.genre_changed_ignore = False

    def _connect_properties(self):
        '''
        Connects the source properties to the saved preferences.
        '''
        print "CoverArtBrowser DEBUG - _connect_properties"
        setting = self.gs.get_setting(self.gs.Path.PLUGIN)

        setting.bind(self.gs.PluginKey.CUSTOM_STATUSBAR, self,
            'custom_statusbar_enabled', Gio.SettingsBindFlags.GET)
        setting.bind(self.gs.PluginKey.DISPLAY_BOTTOM, self,
            'display_bottom_enabled', Gio.SettingsBindFlags.GET)
        setting.bind(self.gs.PluginKey.DISPLAY_TEXT, self,
            'display_text_enabled', Gio.SettingsBindFlags.GET)
        setting.bind(self.gs.PluginKey.DISPLAY_TEXT_LOADING, self,
            'display_text_loading_enabled', Gio.SettingsBindFlags.GET)
        setting.bind(self.gs.PluginKey.RATING, self,
            'rating_threshold', Gio.SettingsBindFlags.GET)
        setting.bind(self.gs.PluginKey.TOOLBAR_POS, self,
            'toolbar_pos', Gio.SettingsBindFlags.GET)
        setting.bind(self.gs.PluginKey.YEAR_SORT_VISIBLE, self,
            'year_sort_visible', Gio.SettingsBindFlags.GET)
        setting.bind(self.gs.PluginKey.RATING_SORT_VISIBLE, self,
            'rating_sort_visible', Gio.SettingsBindFlags.GET)
        setting.bind(self.gs.PluginKey.GENRE_FILTER_VISIBLE, self,
            'genre_filter_visible', Gio.SettingsBindFlags.GET)
        
        print "CoverArtBrowser DEBUG - end _connect_properties"
        

    def do_get_status(self, *args):
        '''
        Method called by Rhythmbox to figure out what to show on this source
        statusbar.
        If the custom statusbar is disabled, the source will
        show the selected album info.
        Also, it makes sure to show the progress on the album loading.s
        '''
        print "CoverArtBrowser DEBUG - do_get_status"
        try:
            progress = self.loader.progress
            progress_text = _('Loading...') if progress < 1 else ''
        except:
            progress = 1
            progress_text = ''

		print "CoverArtBrowser DEBUG - end do_get_status"
        return (self.status, progress_text, progress)
        
    def do_show_popup(self):
        '''
        Method called by Rhythmbox when an action on our source prompts it
        to show a popup.
        '''
        print "CoverArtBrowser DEBUG - do_show_popup"
        self.source_menu.popup(None, None, None, None, 0,
            Gtk.get_current_event_time())

		print "CoverArtBrowser DEBUG - end do_show_popup"
        return True

    def do_selected(self):
        '''
        Called by Rhythmbox when the source is selected. It makes sure to
        create the ui the first time the source is showed.
        '''
        print "CoverArtBrowser DEBUG - do_selected"

        # first time of activation -> add graphical stuff
        if not self.hasActivated:
            self.do_impl_activate()

            #indicate that the source was activated before
            self.hasActivated = True
            
        print "CoverArtBrowser DEBUG - end do_selected"


    def do_impl_activate(self):
        '''
        Called by do_selected the first time the source is activated.
        It creates all the source ui and connects the necesary signals for it
        correct behavior.
        '''
        print "CoverArtBrowser DEBUG - do_impl_activate"

        # initialise some variables
        self.plugin = self.props.plugin
        self.shell = self.props.shell
        self.status = ''
        self.search_text = ''
        self.compare_albums = Album.compare_albums_by_name

        # connect properties signals
        self.connect('notify::custom-statusbar-enabled',
            self.on_notify_custom_statusbar_enabled)

        self.connect('notify::display-bottom-enabled',
            self.on_notify_display_bottom_enabled)

        self.connect('notify::display-text-enabled',
            self.activate_markup)

        self.connect('notify::display-text-loading-enabled',
            self.activate_markup)

        self.connect('notify::rating-threshold',
            self.on_notify_rating_threshold)

        self.connect('notify::rating-sort-visible',
            self.on_notify_rating_sort_visible)

        self.connect('notify::year-sort-visible',
            self.on_notify_year_sort_visible)
            
        self.connect('notify::genre-filter-visible',
            self.on_notify_genre_filter_visible)

        #indicate that the source was activated before
        self.hasActivated = True

        self._create_ui()
        self._setup_source()
        self._apply_settings()
        
        print "CoverArtBrowser DEBUG - end do_impl_activate"


    def _create_ui(self):
        '''
        Creates the ui for the source and saves the important widgets onto
        properties.
        '''
        print "CoverArtBrowser DEBUG - _create_ui"

        # dialog has not been created so lets do so.
        cl = CoverLocale()
        ui = Gtk.Builder()
        ui.set_translation_domain(cl.Locale.LOCALE_DOMAIN)
        ui.add_from_file(rb.find_plugin_file(self.plugin,
            'ui/coverart_browser.ui'))
        
        self.toolbar_box = ui.get_object('toolbar_box')
        
        si = Gtk.Builder()
        si.set_translation_domain(cl.Locale.LOCALE_DOMAIN)
        si.add_from_file(rb.find_plugin_file(self.plugin,
            'ui/coverart_sidebar.ui'))
        
        # load the page and put it in the source
        self.sidebar = si.get_object('main_box')
        
        # load the page and put it in the source
        self.page = ui.get_object('main_box')
        self.pack_start(self.page, True, True, 0)
        
        # covers model
        self.covers_model_store = ui.get_object('covers_model')

        # get widgets for main icon-view
        self.status_label = ui.get_object('status_label')
        self.covers_view = ui.get_object('covers_view')
        self.popup_menu = ui.get_object('popup_menu')
        self.cover_search_menu_item = ui.get_object('cover_search_menu_item')
        self.status_label = ui.get_object('status_label')
        self.request_status_box = ui.get_object('request_status_box')
        self.request_spinner = ui.get_object('request_spinner')
        self.request_statusbar = ui.get_object('request_statusbar')
        self.request_cancel_button = ui.get_object('request_cancel_button')
        self.paned = ui.get_object('paned')
        self.bottom_box = ui.get_object('bottom_box')
        self.bottom_expander = ui.get_object('bottom_expander')
        self.notebook = ui.get_object('bottom_notebook')

        # get widgets for source popup
        self.source_menu = ui.get_object('source_menu')
        self.source_menu_search_all_item = ui.get_object(
            'source_search_menu_item')
        self.play_favourites_album_menu_item = ui.get_object(
            'play_favourites_album_menu_item')
        self.queue_favourites_album_menu_item = ui.get_object(
            'queue_favourites_album_menu_item')

        # get widgets for filter popup
        self.filter_menu = ui.get_object('filter_menu')
        self.filter_menu_all_item = ui.get_object('filter_all_menu_item')
        self.filter_menu_artist_item = ui.get_object('filter_artist_menu_item')
        self.filter_menu_album_artist_item = ui.get_object(
            'filter_album_artist_menu_item')
        self.filter_menu_album_item = ui.get_object('filter_album_menu_item')
        self.filter_menu_track_title_item = ui.get_object(
            'filter_track_title_menu_item')

		self.ui = ui
		self.si = si
		
		print "CoverArtBrowser DEBUG - end _create_ui"

		
	def _toolbar( self, ui ):
		'''
        setup toolbar ui - called for sidebar and main-view
        '''
        print "CoverArtBrowser DEBUG - _toolbar"

		# dialog has not been created so lets do so.
        cl = CoverLocale()
        
        # get widgets for main icon-view
        # the first part is to first remove the current search-entry
        # before recreating it again - we have to do this to ensure
        # the locale is set correctly i.e. the overall ui is coverart
        # locale but the search-entry uses rhythmbox translation
        align = ui.get_object('entry_search_alignment')
        align.remove(align.get_child())
        cl.switch_locale(cl.Locale.RB)
        self.search_entry = RB.SearchEntry(has_popup=True)
        align.add(self.search_entry)
        align.show_all()
        cl.switch_locale(cl.Locale.LOCALE_DOMAIN)

        self.search_entry.connect('search', self.searchchanged_callback)
        self.search_entry.connect('show-popup',
            self.search_show_popup_callback)

        self.sort_by_album_radio = ui.get_object('album_name_sort_radio')
        self.sort_by_artist_radio = ui.get_object('artist_name_sort_radio')
        self.sort_by_year_radio = ui.get_object('year_sort_radio')
        self.sort_by_rating_radio = ui.get_object('rating_sort_radio')
        self.on_notify_rating_sort_visible(_)
        self.on_notify_year_sort_visible(_)
        self.sort_order = ui.get_object('sort_order')
        self.arrow_down = ui.get_object('arrow_down')
        self.arrow_up = ui.get_object('arrow_up')

        # setup the sorting
        self.sort_by_album_radio.set_mode(False)
        self.sort_by_artist_radio.set_mode(False)
        self.sort_by_year_radio.set_mode(False)
        self.sort_by_rating_radio.set_mode(False)

        # get widget for search and apply some workarounds
        search_entry = ui.get_object('search_entry')
        search_entry.set_placeholder(_('Search album'))
        search_entry.show_all()
        self.search_entry.set_placeholder(ui.get_object('filter_all_menu_item').get_label())

        # genre
        self.genre_combobox = ui.get_object('genre_combobox')
        self.on_notify_genre_filter_visible(_)
        self.genre_fill_combo(_)
        print "CoverArtBrowser DEBUG - end _toolbar"

        
    def genre_fill_combo(self, *args):
        '''
        fills the genre combobox with all current genres found
        in the library source
        '''
        print "CoverArtBrowser DEBUG - genre_fill_combo"
		
		genres = self.loader.get_genres()
		if len(genres) == (len(self.genre_combobox.get_model())-1):
			return # nothing to do
			
		self.genre_changed_ignore = True ## we dont want the combobox signal to fire
        views = self.shell.props.library_source.get_property_views()
        view = views[0] # seems like view 0 is the genre property view
        model = view.get_model()   
        
        self.genre_combobox.remove_all()
        
        entry = model[0][0]
        self.genre_combobox.append_text(entry)

        for entry in genres:
            self.genre_combobox.append_text(entry)

        self.genre_combobox.set_active(0)
        
        self.genre_changed_ignore = False
        
        print "CoverArtBrowser DEBUG - end genre_fill_combo"


    def genre_changed(self, widget):
        '''
        signal called when genre value changed
        '''
        if self.genre_changed_ignore:
			return
			
		print "CoverArtBrowser DEBUG - genre_changed"

        if widget.get_active() == 0:
            self.filter_type = Album.FILTER_ALL
            self.filter_menu_all_item.set_active(True)
        else:
            self.filter_type = Album.FILTER_GENRE

        try:
            self.covers_model.refilter()
        except:
            pass
            
        print "CoverArtBrowser DEBUG - end genre_changed"

            
    def _setup_source(self):
        '''
        Setups the differents parts of the source so they are ready to be used
        by the user. It also creates and configure some custom widgets.
        '''        
        print "CoverArtBrowser DEBUG - _setup_source"

        # setup iconview drag&drop support
        self.covers_view.enable_model_drag_dest([], Gdk.DragAction.COPY)
        self.covers_view.drag_dest_add_image_targets()
        self.covers_view.drag_dest_add_text_targets()
        self.covers_view.connect('drag-drop', self.on_drag_drop)
        self.covers_view.connect('drag-data-received',
            self.on_drag_data_received)

        # setup entry-view objects and widgets
        y = self.gs.get_value(self.gs.Path.PLUGIN,
            self.gs.PluginKey.PANED_POSITION)
        self.paned.set_position(y)

        self.entry_view = CoverArtEntryView(self.shell, self)
        self.entry_view.show_all()
        self.notebook.append_page(self.entry_view, Gtk.Label(_("Tracks")))

        # setup cover search pane
        try:
			color = self.covers_view.get_style_context().get_background_color(Gtk.StateFlags.SELECTED)
			color = '#%s%s%s' % (str(hex(int(color.red*255))).replace('0x', ''),
				str(hex(int(color.green*255))).replace('0x', ''),
				str(hex(int(color.blue*255))).replace('0x', ''))
		except:
			color = '#0000FF'
			
        self.cover_search_pane = CoverSearchPane(self.plugin, color)
        self.notebook.append_page(self.cover_search_pane, Gtk.Label(
            _("Covers")))

        # setup the album loader and the cover view to use it's model + filter
        self.loader = AlbumLoader.get_instance(self.plugin,
            self.covers_model_store, self.props.query_model)

        self.covers_model_store = self.loader.cover_model
        self.covers_model_store.set_sort_func(2, self.sort_albums)
        self.covers_model = self.covers_model_store.filter_new()
        self.covers_model.set_visible_func(self.visible_covers_callback)
        self.covers_view.set_model(self.covers_model)
        
        print "CoverArtBrowser DEBUG - end _setup_source"


    def _apply_settings(self):
        '''
        Applies all the settings related to the source and connects those that
        must be updated when the preferences dialog changes it's values. Also
        enables differents parts of the ui if the settings says so.
        '''
        print "CoverArtBrowser DEBUG - _apply_settings"

        # connect some signals to the loader to keep the source informed
        self.si.connect_signals(self)
        self.ui.connect_signals(self)
        self.album_mod_id = self.loader.connect('album-modified',
            self.album_modified_callback)
        self.album_post_view_mod_id = self.loader.connect('album-post-view-modified',
            self.album_post_view_callback)
        self.load_fin_id = self.loader.connect('load-finished',
            self.load_finished_callback)
        self.reload_fin_id = self.loader.connect('reload-finished',
            self.reload_finished_callback)
        self.notify_prog_id = self.loader.connect('notify::progress',
            lambda *args: self.notify_status_changed())
        self.notify_ellipsize = self.loader.connect(
            'notify::display-text-ellipsize-enabled',
            self.on_notify_display_text_ellipsize)
        self.notify_ellipsize_length = self.loader.connect(
            'notify::display-text-ellipsize-length',
            self.on_notify_display_text_ellipsize)
        self.notify_cover_size = self.loader.connect('notify::cover-size',
            self.on_notify_cover_size)
        self.toolbar_pos = self.connect('notify::toolbar-pos',
            self.on_notify_toolbar_pos)

        # apply/connect some settings
        source_settings = self.gs.get_setting(self.gs.Path.PLUGIN)
        source_settings.bind(self.gs.PluginKey.SORT_BY_ALBUM,
            self.sort_by_album_radio, 'active', Gio.SettingsBindFlags.DEFAULT)
        source_settings.bind(self.gs.PluginKey.SORT_BY_ARTIST,
            self.sort_by_artist_radio, 'active', Gio.SettingsBindFlags.DEFAULT)
        source_settings.bind(self.gs.PluginKey.SORT_BY_RATING,
            self.sort_by_rating_radio, 'active', Gio.SettingsBindFlags.DEFAULT)
        source_settings.bind(self.gs.PluginKey.SORT_BY_YEAR,
            self.sort_by_year_radio, 'active', Gio.SettingsBindFlags.DEFAULT)
        source_settings.bind(self.gs.PluginKey.SORT_ORDER,
            self.sort_order, 'active',
            Gio.SettingsBindFlags.DEFAULT)

        # enable some ui if necesary
        self.on_notify_rating_threshold(_)
        self.on_notify_display_bottom_enabled(_)
        self.activate_markup()
        self.sorting_direction_changed(self.sort_order)
        #self.on_notify_toolbar_pos(_)

        if self.loader.progress == 1:
            # if the source is fully loaded, enable the full cover search item
            self.load_finished_callback()

        print "CoverArtBrowser DEBUG - end _apply_settings"

    def load_finished_callback(self, _):
        '''
        Callback called when the loader finishes loading albums into the
        covers view model.
        '''
        print "CoverArtBrowser DEBUG - load_finished_callback"

        if not self.request_status_box.get_visible():
            # it should only be enabled if no cover request is going on
            self.source_menu_search_all_item.set_sensitive(True)

        # enable markup if necesary
        self.activate_markup()
        
        print "CoverArtBrowser DEBUG - end load_finished_callback"


    def reload_finished_callback(self, _):
        '''
        Callback called when the loader finishes reloading albums into the
        covers view model.
        '''
        print "CoverArtBrowser DEBUG - reload_finished_callback"

        if self.display_text_enabled and \
            not self.display_text_loading_enabled \
            and self.loader.progress == 1:
            self.activate_markup()
            
        print "CoverArtBrowser DEBUG - end reload_finished_callback"


    def on_notify_custom_statusbar_enabled(self, *args):
        '''
        Callback for when the option to show the custom statusbar is enabled
        or disabled from the plugin's preferences dialog.
        '''
        print "CoverArtBrowser DEBUG - on_notify_custom_statusbar_enabled"

        if self.custom_statusbar_enabled:
            self.status = ''
            self.notify_status_changed()
        else:
            self.status_label.hide()

        self.selectionchanged_callback(self.covers_view)
        
        print "CoverArtBrowser DEBUG - end on_notify_custom_statusbar_enabled"


    def on_notify_rating_threshold(self, *args):
        '''
        Callback called when the option rating threshold is changed
        on the plugin's preferences dialog
        If the threshold is zero then the rating menu options in the
        coverview should not be enabled
        '''
		print "CoverArtBrowser DEBUG - on_notify_rating_threshold"

        if self.rating_threshold > 0:
            enable_menus = True
        else:
            enable_menus = False

        self.play_favourites_album_menu_item.set_sensitive(enable_menus)
        self.queue_favourites_album_menu_item.set_sensitive(enable_menus)
        
        print "CoverArtBrowser DEBUG - end on_notify_rating_threshold"

    def on_notify_rating_sort_visible(self, *args):
        '''
        Callback called when the option rating sort visibility is changed
        on the plugin's preferences dialog
        '''
		print "CoverArtBrowser DEBUG - on_notify_rating_sort_visible"

        self.sort_by_rating_radio.set_visible(self.rating_sort_visible)
        
        print "CoverArtBrowser DEBUG - end on_notify_rating_sort_visible"

    def on_notify_year_sort_visible(self, *args):
        '''
        Callback called when the option year sort visibility is changed
        on the plugin's preferences dialog
        '''
		print "CoverArtBrowser DEBUG - on_notify_year_sort_visible"

        self.sort_by_year_radio.set_visible(self.year_sort_visible)
        
        print "CoverArtBrowser DEBUG - end on_notify_year_sort_visible"

    def on_notify_genre_filter_visible(self, *args):
        '''
        Callback called when the option genre filter visibility is changed
        on the plugin's preferences dialog
        '''
		print "CoverArtBrowser DEBUG - on_notify_genre_filter_visible"

        self.genre_combobox.set_visible(self.genre_filter_visible)
        
        print "CoverArtBrowser DEBUG - end on_notify_genre_filter_visible"


    def on_notify_toolbar_pos(self, *args):
        '''
        Callback called when the toolbar position is changed in
        preferences
        '''
		print "CoverArtBrowser DEBUG - on_notify_toolbar_pos"

        setting = self.gs.get_setting(self.gs.Path.PLUGIN)

        toolbar_pos = setting[self.gs.PluginKey.TOOLBAR_POS]

        if toolbar_pos == 0:
			self._toolbar(self.ui)
            self.toolbar_box.set_visible(True)
			
        if toolbar_pos == 1:
            self.toolbar_box.set_visible(False)
            print "hi"
            self._toolbar(self.si)
            self.shell.add_widget( 	self.sidebar,
                        RB.ShellUILocation.SIDEBAR,
                        expand=False,
                        fill=False)
            print "bye"

        if toolbar_pos == 2:
            self.toolbar_box.set_visible(False)
			self._toolbar(self.si)
            self.shell.add_widget( 	self.sidebar,
                        RB.ShellUILocation.RIGHT_SIDEBAR,
                        expand=False,
                        fill=False) 

        if self.last_toolbar_pos == 1:
            self.shell.remove_widget(   self.sidebar,
                                        RB.ShellUILocation.SIDEBAR )
        if self.last_toolbar_pos == 2:
            self.shell.remove_widget(   self.sidebar,
                                        RB.ShellUILocation.RIGHT_SIDEBAR )

        self.last_toolbar_pos = toolbar_pos
        
        print "CoverArtBrowser DEBUG - end on_notify_toolbar_pos"


    def on_notify_display_bottom_enabled(self, *args):
        '''
        Callback called when the option 'display tracks' is enabled or disabled
        on the plugin's preferences dialog
        '''
        print "CoverArtBrowser DEBUG - on_notify_display_bottom_enabled"

        if self.display_bottom_enabled:
            # make the entry view visible
            self.bottom_box.set_visible(True)

            self.bottom_expander_expanded_callback(
                self.bottom_expander, None)

            # update it with the current selected album
            self.selectionchanged_callback(self.covers_view)

        else:
            if self.bottom_expander.get_expanded():
                y = self.paned.get_position()
                self.gs.set_value(self.gs.Path.PLUGIN,
                                  self.gs.PluginKey.PANED_POSITION,
                                  y)

            self.bottom_box.set_visible(False)
            
        print "CoverArtBrowser DEBUG - end on_notify_display_bottom_enabled"


    def activate_markup(self, *args):
        '''
        Utility method to activate/deactivate the markup text on the
        cover view.
        '''
        print "CoverArtBrowser DEBUG - activate_markup"

        activate = self.display_text_enabled and \
            (self.display_text_loading_enabled or (self.loader.progress == 1
            and not self.loader.reloading))

        if activate:
            column = 3
            item_width = self.loader.cover_size + 20
        else:
            column = item_width = -1

        self.covers_view.set_markup_column(column)
        self.covers_view.set_item_width(item_width)
        
        print "CoverArtBrowser DEBUG - end activate_markup"


    def on_notify_display_text_ellipsize(self, *args):
        '''
        Callback called when one of the properties related with the ellipsize
        option is changed.
        '''
        print "CoverArtBrowser DEBUG - on_notify_display_text_ellipsize"

        if not self.display_text_loading_enabled:
            self.activate_markup(False)
            
        print "CoverArtBrowser DEBUG - end on_notify_display_text_ellipsize"


    def on_notify_cover_size(self, *args):
        '''
        Callback callend when the coverart size property is changed.
        '''
        print "CoverArtBrowser DEBUG - on_notify_cover_size"

        self.activate_markup(self.display_text_enabled and
            self.display_text_loading_enabled)

        # update the iconview since the new size would change the free space
        self.update_iconview_callback()
        
        print "CoverArtBrowser DEBUG - end on_notify_cover_size"


    def on_paned_button_release_event(self, *args):
        '''
        Callback when the paned handle is released from its mouse click.
        '''
        
        print "CoverArtBrowser DEBUG - on_paned_button_release_event"

        if self.bottom_expander.get_expanded():
            new_y = self.paned.get_position()
            self.gs.set_value(self.gs.Path.PLUGIN,
                self.gs.PluginKey.PANED_POSITION, new_y)
                
        print "CoverArtBrowser DEBUG - end on_paned_button_release_event"


    def album_modified_callback(self, _, modified_album):
        '''
        Callback called by the album loader when one of the albums managed
        by him gets modified in some way.
        '''
        print "CoverArtBrowser DEBUG - album_modified_callback"
        selected = self.get_selected_albums()

        if modified_album in selected:
            # update the selection since it may have changed
            self.selectionchanged_callback(self.covers_view)

            if modified_album is selected[0] and \
                self.notebook.get_current_page() == \
                self.notebook.page_num(self.cover_search_pane):
                # also, if it's the first, update the cover search pane
                self.cover_search_pane.clear()
                self.cover_search_pane.do_search(modified_album)

        print "CoverArtBrowser DEBUG - end album_modified_callback"

    def album_post_view_callback(self, _, path):
        '''
        Callback called by the album loader when one of the albums managed
        by him gets modified in some way - this reselects what was
        selected in the view before modification.
        '''
        print "CoverArtBrowser DEBUG - album_post_view_callback"
        
        #if self.selected_albums is None:
        #    return
            
        #tm = self.covers_view.get_model()
        #print tree_iter
        #path = tm.get_path(tree_iter)
        #print path
        self.covers_view.select_path(path)
        #for album in self.selected_albums:
        #    for item in qm:
        #        if item[2].album_name == album.album_name and \
        #           item[2].album_artist == album.album_artist:
        #            print "found"
                    #
                    # now what? how do we go from the tree-model to selecting the
                    # equivalent in the cover-view
                    #self.covers_view.select_path(i)

        print "CoverArtBrowser DEBUG - end album_post_view_callback"

    def visible_covers_callback(self, model, iter, data):
        '''
        Callback called by the model filter to decide wheter to filter or not
        an album.
        '''
		try:
			if self.genre_combobox.get_active() != 0:
				return model[iter][2].contains(self.genre_combobox.get_active_text(), self.filter_type)
		except:
			return False
			
        if self.search_text == "":
            return True

        return model[iter][2].contains(self.search_text, self.filter_type)

    def search_show_popup_callback(self, entry):
        '''
        Callback called by the search entry when the magnifier is clicked.
        It prompts the user through a popup to select a filter type.
        '''
        print "CoverArtBrowser DEBUG - search_show_popup_callback"

        self.filter_menu.popup(None, None, None, None, 0,
            Gtk.get_current_event_time())
            
        print "CoverArtBrowser DEBUG - end search_show_popup_callback"


    def searchchanged_callback(self, entry, text):
        '''
        Callback called by the search entry when a new search must
        be performed.
        '''
        print "CoverArtBrowser DEBUG - searchchanged_callback"

        self.search_text = text
        self.genre_combobox.set_active(0)
        self.covers_model.refilter()

        print "CoverArtBrowser DEBUG - end searchchanged_callback"

    def update_iconview_callback(self, *args):
        '''
        Callback called by the cover view when its view port gets resized.
        It forces the cover_view to redraw it's contents to fill the available
        space.
        '''
        print "CoverArtBrowser DEBUG - update_iconview_callback"

        self.covers_view.set_columns(0)
        self.covers_view.set_columns(-1)
        
        print "CoverArtBrowser DEBUG - end update_iconview_callback"


    def mouseclick_callback(self, iconview, event):
        '''
        Callback called when the user clicks somewhere on the cover_view.
        If it's a right click, it shows a popup showing different actions to
        perform with the selected album.
        '''
        print "CoverArtBrowser DEBUG - mouseclick_callback()"
        if event.triggers_context_menu() and \
            event.type is Gdk.EventType.BUTTON_PRESS:
            x = int(event.x)
            y = int(event.y)
            pthinfo = iconview.get_path_at_pos(x, y)

            if pthinfo is None:
                return

            # if the current item isn't selected, then we should clear the
            # current selection
            if len(iconview.get_selected_items()) > 0 and \
                not iconview.path_is_selected(pthinfo):
                iconview.unselect_all()

            iconview.grab_focus()
            iconview.select_path(pthinfo)

            self.popup_menu.popup(None, None, None, None, event.button,
                event.time)

        print "CoverArtBrowser DEBUG - end mouseclick_callback()"

    def item_activated_callback(self, iconview, path):
        '''
        Callback called when the cover view is double clicked or space-bar
        is pressed. It plays the selected album
        '''
        print "CoverArtBrowser DEBUG - item_activated_callback"

        iconview.grab_focus()
        iconview.select_path(path)

        self.play_album_menu_item_callback(_)
        
        print "CoverArtBrowser DEBUG - end item_activated_callback"

        return True

    def get_selected_albums(self):
        '''
        Retrieves the currently selected albums on the cover_view.
        '''
        print "CoverArtBrowser DEBUG - get_selected_albums"

        selected_albums = []

        if hasattr(self, 'covers_model'):
            model = self.covers_model

            for selected in self.covers_view.get_selected_items():
                selected_albums.append(model[selected][2])

		print "CoverArtBrowser DEBUG - end get_selected_albums"
        return selected_albums

    def play_album_menu_item_callback(self, _):
        '''
        Callback called when the play album item from the cover view popup is
        selected. It cleans the play queue and queues the selected album.
        '''
        print "CoverArtBrowser DEBUG - play_album_menu_item_callback"

        self.play_selected_album()

        print "CoverArtBrowser DEBUG - end play_album_menu_item_callback"

    def play_selected_album(self, favourites=False):
        '''
        Utilitary method that plays all entries from an album into the play
        queue.
        '''
        # callback when play an album
        print "CoverArtBrowser DEBUG - play_selected_album"

        # clear the queue
        play_queue = self.shell.props.queue_source
        for row in play_queue.props.query_model:
            play_queue.remove_entry(row[0])

        self.queue_selected_album(favourites)

        # Start the music
        player = self.shell.props.shell_player
        player.stop()
        player.set_playing_source(self.shell.props.queue_source)
        player.playpause(True)
        print "CoverArtBrowser DEBUG - end play_selected_album"


    def queue_favourites_album_menu_item_callback(self, _):
        '''
        Callback called when the queue-favourites album item from the cover
        view popup is selected. It queues the selected album at the end of the
        play queue.
        '''
        print "CoverArtBrowser DEBUG - queue_favourites_album_menu_item_callback()"

        self.queue_selected_album(True)

        print "CoverArtBrowser DEBUG - end queue_favourites_album_menu_item_callback()"

    def play_favourites_album_menu_item_callback(self, _):
        '''
        Callback called when the play favourites album item from the cover view
        popup is selected. It queues the selected album at the end of the play
        queue.
        '''
        print "CoverArtBrowser DEBUG - play_favourites_album_menu_item_callback()"

        self.play_selected_album(True)

        print "CoverArtBrowser DEBUG - end play_favourites_album_menu_item_callback()"

    def queue_album_menu_item_callback(self, _):
        '''
        Callback called when the queue album item from the cover view popup is
        selected. It queues the selected album at the end of the play queue.
        '''
        print "CoverArtBrowser DEBUG - queue_album_menu_item_callback()"

        self.queue_selected_album()

        print "CoverArtBrowser DEBUG - end queue_album_menu_item_callback()"

    def queue_selected_album(self, favourites=False):
        '''
        Utilitary method that queues all entries from an album into the play
        queue.
        '''
        print "CoverArtBrowser DEBUG - queue_selected_album"

        selected_albums = self.get_selected_albums()

        for album in selected_albums:
            # Retrieve and sort the entries of the album
            if favourites:
                songs = album.favourite_entries(self.rating_threshold)
            else:
                songs = album.entries

            songs = sorted(songs, key=lambda song:
                song.get_ulong(RB.RhythmDBPropType.TRACK_NUMBER))

            # Add the songs to the play queue
            for song in songs:
                self.shell.props.queue_source.add_entry(song, -1)
                
        print "CoverArtBrowser DEBUG - end queue_select_album"


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
        print "CoverArtBrowser DEBUG - show_properties_menu_item_callback"

        self.entry_view.select_all()

        info_dialog = RB.SongInfo(source=self, entry_view=self.entry_view)

        info_dialog.show_all()
        
        print "CoverArtBrowser DEBUG - end show_properties_menu_item_callback"


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
        print "CoverArtBrowser DEBUG - update_request_status_bar"

        if album:
            self.request_statusbar.set_text(
                (_('Requesting cover for %s - %s...') % (album.name,
                album.album_artist)).decode('UTF-8'))
        else:
            self.request_status_box.hide()
            self.source_menu_search_all_item.set_sensitive(True)
            self.cover_search_menu_item.set_sensitive(True)
            self.request_cancel_button.set_sensitive(True)
            
        print "CoverArtBrowser DEBUG - end update_request_status_bar"


    def cancel_request_callback(self, _):
        '''
        Callback connected to the cancel button on the request statusbar.
        When called, it prompts the album loader to cancel the full cover
        search after the current cover.
        '''
        print "CoverArtBrowser DEBUG - cancel_request_callback"

        self.request_cancel_button.set_sensitive(False)
        self.loader.cancel_cover_request()
        
        print "CoverArtBrowser DEBUG - end cancel_request_callback"


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

        selected = self.get_selected_albums()

        cover_search_pane_visible = self.notebook.get_current_page() == \
            self.notebook.page_num(self.cover_search_pane)

        if not selected:
            # if no album selected, clean the status and the cover tab if
            # if selected
            self.update_statusbar()

            if cover_search_pane_visible:
                self.cover_search_pane.clear()

            return

        track_count = 0
        duration = 0

        for album in selected:
            # Calculate duration and number of tracks from that album
            track_count += album.get_track_count()
            duration += album.calculate_duration_in_mins()

            # add the album to the entry_view
            self.entry_view.add_album(album)

        # now lets build up a status label containing some 'interesting stuff'
        # about the album
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

        self.update_statusbar(status)

        # update the cover search pane with the first selected album
        if cover_search_pane_visible:
            self.cover_search_pane.do_search(selected[0])
            
        print "CoverArtBrowser DEBUG - end selection_changed_callback"


    def update_statusbar(self, status=''):
        '''
        Utility method that updates the status bar.
        '''
        print "CoverArtBrowser DEBUG - update_statusbar"

        if self.custom_statusbar_enabled:
            # if the custom statusbar is enabled... use it.
            self.status_label.set_text(status)
            self.status_label.show()
        else:
            # use the global statusbar from Rhythmbox
            self.status = status
            self.notify_status_changed()
            
        print "CoverArtBrowser DEBUG - end update_statusbar"


    def filter_menu_callback(self, radiomenu):
        '''
        Callback called when an item from the filters popup menu is clicked.
        It changes the current filter type for the search to the one selected
        on the popup.
        '''
        print "CoverArtBrowser DEBUG - filter_menu_callback"

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

        if self.search_text == '':
            self.search_entry.set_placeholder(radiomenu.get_label())


        self.searchchanged_callback(_, self.search_text)
        
        print "CoverArtBrowser DEBUG - end filter_menu_callback"


    def bottom_expander_expanded_callback(self, action, param):
        '''
        Callback connected to expanded signal of the paned GtkExpander
        '''
		print "CoverArtBrowser DEBUG - bottom_expander_expanded_callback"

        expand = action.get_expanded()

        if not expand:
            # move the lower pane to the bottom since it's collapsed
            (x, y) = Gtk.Widget.get_toplevel(self.status_label).get_size()
            new_y = self.paned.get_position()
            self.gs.set_value(self.gs.Path.PLUGIN,
                self.gs.PluginKey.PANED_POSITION, new_y)
            self.paned.set_position(y - 10)
        else:
            # restitute the lower pane to it's expanded size
            new_y = self.gs.get_value(self.gs.Path.PLUGIN,
                self.gs.PluginKey.PANED_POSITION)

            if new_y == 0:
                # if there isn't a saved size, use half of the space
                (x, y) = Gtk.Widget.get_toplevel(self.status_label).get_size()
                new_y = (y / 2)
                self.gs.set_value(self.gs.Path.PLUGIN,
                    self.gs.PluginKey.PANED_POSITION, new_y)

            self.paned.set_position(new_y)
            
        print "CoverArtBrowser DEBUG - end bottom_expander_expanded_callback"


    def paned_button_press_callback(self, *args):
        '''
        This callback allows or denies the paned handle to move depending on
        the expanded state of the entry_view
        '''
        print "CoverArtBrowser DEBUG - paned_button_press_callback"

        return not self.bottom_expander.get_expanded()

    def sorting_criteria_changed(self, radio):
        '''
        Callback called when a radio corresponding to a sorting order is
        toggled. It changes the sorting function and reorders the cover model.
        '''
        print "CoverArtBrowser DEBUG - sorting_criteria_changed"

        if not radio.get_active():
            return

        if radio is self.sort_by_album_radio:
            self.compare_albums = Album.compare_albums_by_name
        if radio is self.sort_by_artist_radio:
            self.compare_albums = Album.compare_albums_by_album_artist
        if radio is self.sort_by_year_radio:
            self.compare_albums = Album.compare_albums_by_year
        if radio is self.sort_by_rating_radio:
            self.compare_albums = Album.compare_albums_by_rating

        if self.display_text_enabled and not self.display_text_loading_enabled:
            self.activate_markup(False)

        self.loader.reload_model()
        
        print "CoverArtBrowser DEBUG - end sorting_criteria_changed"


    def sorting_direction_changed(self, toggle):
        '''
        Callback called when the sort toggle button is
        toggled. It changes the sorting direction and reorders the cover model
        '''
        print "CoverArtBrowser DEBUG - sorting_direction_changed"

        if not toggle.get_active():
            sort_direction = Gtk.SortType.ASCENDING
            toggle.set_image(self.arrow_down)
            toggle.set_tooltip_text(_('Sort in descending order'))
        else:
            sort_direction = Gtk.SortType.DESCENDING
            toggle.set_image(self.arrow_up)
            toggle.set_tooltip_text(_('Sort in ascending order'))
                        
        if self.display_text_enabled and not self.display_text_loading_enabled:
            self.activate_markup(False)

        self.loader.reload_model()
        self.covers_model_store.set_sort_column_id(2, sort_direction)
        
        print "CoverArtBrowser DEBUG - end sorting_direction_changed"


    def sort_albums(self, model, iter1, iter2, _):
        '''
        Utility function used as the sorting function for our model.
        It actually just retrieves the albums and delegates the comparison
        to the current comparation function.
        '''
        return self.compare_albums(model[iter1][2], model[iter2][2])

    def on_drag_drop(self, widget, context, x, y, time):
        '''
        Callback called when a drag operation finishes over the cover view
        of the source. It decides if the dropped item can be processed as
        an image to use as a cover.
        '''
        print "CoverArtBrowser DEBUG - on_drag_drop"

        # stop the propagation of the signal (deactivates superclass callback)
        widget.stop_emission('drag-drop')

        # obtain the path of the icon over which the drag operation finished
        path, pos = widget.get_dest_item_at_pos(x, y)
        result = path is not None

        if result:
            target = self.covers_view.drag_dest_find_target(context, None)
            widget.drag_get_data(context, target, time)

		print "CoverArtBrowser DEBUG - end on_drag_drop"

        return result

    def on_drag_data_received(self, widget, drag_context, x, y, data, info,
        time):
        '''
        Callback called when the drag source has prepared the data (pixbuf)
        for us to use.
        '''
        print "CoverArtBrowser DEBUG - on_drag_data_received"

        # stop the propagation of the signal (deactivates superclass callback)
        widget.stop_emission('drag-data-received')

        # get the album and the info and ask the loader to update the cover
        path, pos = widget.get_dest_item_at_pos(x, y)
        album = widget.get_model()[path][2]

        pixbuf = data.get_pixbuf()

        if pixbuf:
            self.loader.update_cover(album, pixbuf)
        else:
            uri = data.get_text()
            self.loader.update_cover(album, uri=uri)

        # call the context drag_finished to inform the source about it
        drag_context.finish(True, False, time)
        
        print "CoverArtBrowser DEBUG - end on_drag_data_received"


    def notebook_switch_page_callback(self, notebook, page, page_num):
        '''
        Callback called when the notebook page gets switched. It initiates
        the cover search when the cover search pane's page is selected.
        '''
        print "CoverArtBrowser DEBUG - notebook_switch_page_callback"

        if page_num == 1:
            selected_albums = self.get_selected_albums()

            if selected_albums:
                self.cover_search_pane.do_search(selected_albums[0])
                
        print "CoverArtBrowser DEBUG - end notebook_switch_page_callback"


    def do_delete_thyself(self):
        '''
        Method called by Rhythmbox's when the source is deleted. It makes sure
        to free all the source's related resources to avoid memory leaking and
        loose signals.
        '''
        print "CoverArtBrowser DEBUG - do_delete_thyself"
        
        if not self.hasActivated:
            del self.hasActivated

            return

        # destroy the ui
        self.page.destroy()

        # disconnect signals
        self.loader.disconnect(self.load_fin_id)
        self.loader.disconnect(self.reload_fin_id)
        self.loader.disconnect(self.album_mod_id)
        self.loader.disconnect(self.album_post_view_mod_id)
        self.loader.disconnect(self.notify_prog_id)
        self.loader.disconnect(self.notify_ellipsize)
        self.loader.disconnect(self.notify_ellipsize_length)
        self.loader.disconnect(self.notify_cover_size)
        # delete references
        del self.shell
        del self.plugin
        del self.loader
        del self.covers_model_store
        del self.covers_model
        del self.covers_view
        del self.cover_search_pane
        del self.filter_menu
        del self.filter_menu_album_artist_item
        del self.filter_menu_album_item
        del self.filter_menu_all_item
        del self.filter_menu_artist_item
        del self.filter_menu_track_title_item
        del self.filter_type
        del self.notebook
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
        del self.sort_by_year_radio
        del self.sort_by_rating_radio
        del self.sort_order
        del self.status
        del self.status_label
        del self.reload_fin_id
        del self.load_fin_id
        del self.album_mod_id
        del self.album_post_view_mod_id
        del self.notify_prog_id
        del self.hasActivated
        del self.gs
        
        print "CoverArtBrowser DEBUG - end do_delete_thyself"


GObject.type_register(CoverArtBrowserSource)
