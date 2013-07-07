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
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import Gdk
from gi.repository import RB
from gi.repository import Gio
from coverart_browser_prefs import CoverLocale
from coverart_browser_prefs import GSetting
from coverart_utils import create_pixbuf_from_file_at_size
from coverart_utils import GenreConfiguredSpriteSheet
from coverart_utils import ConfiguredSpriteSheet
from coverart_utils import get_stock_size
from coverart_utils import CaseInsensitiveDict
from coverart_utils import Theme
from datetime import date
from collections import OrderedDict
import rb


class OptionsController(GObject.Object):

    # properties
    options = GObject.property(type=object, default=None)
    current_key = GObject.property(type=str, default=None)
    update_image = GObject.property(type=bool, default=False)

    def __init__(self):
        super(OptionsController, self).__init__()

        # connect the variations on the current key to the controllers action
        self.connect('notify::current-key', self._do_action)

    def get_current_key_index(self):
        return self.options.index(self.current_key)

    def option_selected(self, key):
        if key != self.current_key:
            # update the current value
            self.current_key = key

    def _do_action(self, *args):
        self.do_action()

    def do_action(self):
        pass

    def get_current_image(self):
        return None

    def get_current_description(self):
        return self.current_key

    def update_images(self, *args):
        pass

    def create_spritesheet(self, plugin, sheet, typestr):
        '''
        helper function to create a specific spritesheet
        '''
        if sheet:
            del sheet
            
        return ConfiguredSpriteSheet(plugin, typestr, get_stock_size())

    def create_button_image( self, plugin, image, icon_name):
        '''
        helper function to create a button image
        '''
        if image:
            del image

        path = 'img/' + Theme(self.plugin).current + '/'
        
        return create_pixbuf_from_file_at_size(
            rb.find_plugin_file(self.plugin, path + icon_name),
            *get_stock_size())

class PlaylistPopupController(OptionsController):

    def __init__(self, plugin, album_model):
        super(PlaylistPopupController, self).__init__()

        self._album_model = album_model

        shell = plugin.shell
        self.plugin = plugin

        # get the library name and initialize the superclass with it
        self._library_name = shell.props.library_source.props.name

        # get the queue name
        self._queue_name = shell.props.queue_source.props.name

        if " (" in self._queue_name:
            self._queue_name = self._queue_name[0:self._queue_name.find(" (")]

        self._spritesheet = None
        self._update_options(shell)
        
        # get the playlist manager and it's model
        playlist_manager = shell.props.playlist_manager
        playlist_model = playlist_manager.props.display_page_model

        # connect signals to update playlists
        playlist_model.connect('row-inserted', self._update_options, shell)
        playlist_model.connect('row-deleted', self._update_options, shell)
        playlist_model.connect('row-changed', self._update_options, shell)

    def update_images(self, *args):
        self._spritesheet = self.create_spritesheet( self.plugin,
            self._spritesheet, 'playlist')

        if args[-1]:
            self.update_image = True

    def _update_options(self, *args):
        shell = args[-1]
        self.update_images(False)
            
        playlist_manager = shell.props.playlist_manager
        still_exists = self.current_key == self._library_name or\
            self.current_key == self._queue_name

        # retrieve the options
        values = OrderedDict()

        # library and play queue sources
        values[self._library_name] = None
        values[self._queue_name] = shell.props.queue_source

        # playlists
        playlists_entries = playlist_manager.get_playlists()

        for playlist in playlists_entries:
            if playlist.props.is_local:
                name = playlist.props.name
                values[name] = playlist

                still_exists = still_exists or name == self.current_key

        self.values = values
        self.options = list(values.keys())

        self.current_key = self.current_key if still_exists else\
            self._library_name

    def do_action(self):
        playlist = self.values[self.current_key]

        if not playlist:
            self._album_model.remove_filter('model')
        else:
            self._album_model.replace_filter('model',
                playlist.get_query_model())

    def get_current_image(self):
        playlist = self.values[self.current_key]

        if self.current_key == self._library_name:
            image = self._spritesheet['music']
        elif self._queue_name in self.current_key:
            image = self._spritesheet['queue']
        elif isinstance(playlist, RB.StaticPlaylistSource):
            image = self._spritesheet['playlist']
        else:
            image = self._spritesheet['smart']

        return image


class GenrePopupController(OptionsController):
    # properties
    new_genre_icon = GObject.property(type=bool, default=False)

    def __init__(self, plugin, album_model):
        super(GenrePopupController, self).__init__()

        cl = CoverLocale()
        cl.switch_locale(cl.Locale.LOCALE_DOMAIN)

        self._album_model = album_model

        shell = plugin.shell
        self.plugin = plugin

        # create a new property model for the genres
        genres_model = RB.RhythmDBPropertyModel.new(shell.props.db,
            RB.RhythmDBPropType.GENRE)

        query = shell.props.library_source.props.base_query_model
        genres_model.props.query_model = query

        # initial genre
        self._initial_genre = _('All Genres')

        self._spritesheet = None
        self._default_image = None
        self._unrecognised_image = None

        self._connect_properties()
        self._connect_signals(query, genres_model)
        
        # generate initial popup
        self._update_options(genres_model)

    def update_images(self, *args):
        if self._spritesheet:
            del self._spritesheet
            
        self._spritesheet = GenreConfiguredSpriteSheet(self.plugin,
            'genre', get_stock_size())
        self._default_image = self.create_button_image( self.plugin,
            self._default_image, 'default_genre.png')
        self._unrecognised_image = self.create_button_image( self.plugin,
            self._unrecognised_image, 'unrecognised_genre.png')
        
        if args[-1]:
            self.update_image = True

    def _connect_signals(self, query, genres_model):
        # connect signals to update genres
        self.connect('notify::new-genre-icon', self._update_options, genres_model)
        query.connect('row-inserted', self._update_options, genres_model)
        query.connect('row-deleted', self._update_options, genres_model)
        query.connect('row-changed', self._update_options, genres_model)

    def _connect_properties(self):
        gs = GSetting()
        setting = gs.get_setting(gs.Path.PLUGIN)

        setting.bind(gs.PluginKey.NEW_GENRE_ICON, self, 'new_genre_icon',
            Gio.SettingsBindFlags.GET)

    def _update_options(self, *args):
        genres_model = args[-1]

        self.update_images(False)
        
        still_exists = False

        # retrieve the options
        options = []
        row_num = 0
        for row in genres_model:
            if row_num == 0:
                genre = _('All Genres')
                row_num = row_num + 1
            else:
                genre = row[0]

            options.append(genre)

            still_exists = still_exists or genre == self.current_key

        self.options = options

        self.current_key = self.current_key if still_exists else\
            self._initial_genre

    def do_action(self):
        '''
        called when genre popup menu item chosen
        return None if the first entry in popup returned
        '''
        if self.current_key == self._initial_genre:
            self._album_model.remove_filter('genre')
        else:
            self._album_model.replace_filter('genre', self.current_key)

    def get_current_image(self):
        test_genre = self.current_key.lower()

        if test_genre == self._initial_genre.lower():
            image = self._default_image
        else:
            image = self._find_alternates(test_genre)

            if image == self._unrecognised_image and \
                test_genre in self._spritesheet:
                image = self._spritesheet[test_genre]

        return image

    def _find_alternates(self, test_genre):
        # the following genre checks are required
        # 1. if we have user defined genres
        # 2. then check locale specific system genres
        # 3. then check local specific alternates
        # 4. then check if we system genres

        # where necessary check if any of the genres are a substring
        # of test_genre - check in reverse order so that we
        # test largest strings first (prevents spurious matches with
        # short strings)
        # N.B. we use RB.search_fold since the strings can be
        # in a mixture of cases, both unicode (normalized or not) and str
        # and as usual python cannot mix and match these types.

        
        test_genre = RB.search_fold(test_genre)
        
        ret, sprite = self._match_genres(test_genre, self._spritesheet.GENRE_USER)
        if ret:
            return sprite
                
        for genre in sorted(self._spritesheet.locale_names,
            key=lambda b: (-len(b), b)):
            if RB.search_fold(genre) in test_genre:
                return self._spritesheet[self._spritesheet.locale_names[genre]]

        # next check locale alternates
        ret, sprite = self._match_genres(test_genre, self._spritesheet.GENRE_LOCALE)
        if ret:
            return sprite

        ret, sprite = self._match_genres(test_genre, self._spritesheet.GENRE_SYSTEM)
        if ret:
            return sprite
        
        # check if any of the default genres are a substring
        # of test_genre - check in reverse order so that we
        # test largest strings first (prevents spurious matches with
        # short strings)
        for genre in sorted(self._spritesheet.names,
            key=lambda b: (-len(b), b)):
            if RB.search_fold(genre) in test_genre:
                return self._spritesheet[genre]
                
        # if no matches then default to unrecognised image
        return self._unrecognised_image

    def _match_genres(self, test_genre, genre_type):
        case_search = CaseInsensitiveDict(
            dict((k.name, v) for k, v in self._spritesheet.genre_alternate.items()
                if k.genre_type==genre_type))

        if test_genre in case_search:
            return (True, self._spritesheet[case_search[test_genre]])
        else:
            return (False, None)


    def get_current_description(self):
        if self.current_key == self._initial_genre:
            return _('All Genres')
        else:
            return self.current_key


class SortPopupController(OptionsController):

    def __init__(self, plugin, album_model):
        super(SortPopupController, self).__init__()

        self._album_model = album_model
        self.plugin = plugin
        # sorts dictionary
        cl = CoverLocale()
        cl.switch_locale(cl.Locale.LOCALE_DOMAIN)

        self.values = OrderedDict([(_('Sort by album name'), 'name'),
            (_('Sort by album artist'), 'artist'),
            (_('Sort by year'), 'year'),
            (_('Sort by rating'), 'rating')])

        self.options = list(self.values.keys())
        
        # get the current sort key and initialise the superclass
        gs = GSetting()
        source_settings = gs.get_setting(gs.Path.PLUGIN)
        value = source_settings[gs.PluginKey.SORT_BY]

        self._spritesheet = None
        self.update_images(False)
        
        self.current_key = list(self.values.keys())[
            list(self.values.values()).index(value)]

    def update_images(self, *args):
        self._spritesheet = self.create_spritesheet( self.plugin,
            self._spritesheet, 'sort')
        
        if args[-1]:
            self.update_image = True
            
    def do_action(self):
        sort = self.values[self.current_key]

        gs = GSetting()
        settings = gs.get_setting(gs.Path.PLUGIN)
        settings[gs.PluginKey.SORT_BY] = sort

        self._album_model.sort(sort)

    def get_current_image(self):
        sort = self.values[self.current_key]
        return self._spritesheet[sort]


class DecadePopupController(OptionsController):

    def __init__(self, plugin, album_model):
        super(DecadePopupController, self).__init__()

        self._album_model = album_model
        self.plugin = plugin

        self._spritesheet = None
            
        # decade options
        cl = CoverLocale()
        cl.switch_locale(cl.Locale.LOCALE_DOMAIN)

        self.values = OrderedDict()

        self.values[_('All Decades')] = [-1, 'All Decades']
        #'20s' as in the decade 2010
        self.values[_('20s')] = [2020, '20s']
        #'10s' as in the decade 2010
        self.values[_('10s')] = [2010, '10s']
        #'00s' as in the decade 2000
        self.values[_('00s')] = [2000, '00s']
        #'90s' as in the decade 1990
        self.values[_('90s')] = [1990, '90s']
        #'80s' as in the decade 1980
        self.values[_('80s')] = [1980, '80s']
        #'70s' as in the decade 1970
        self.values[_('70s')] = [1970, '70s']
        #'60s' as in the decade 1960
        self.values[_('60s')] = [1960, '60s']
        #'50s' as in the decade 1950
        self.values[_('50s')] = [1950, '50s']
        #'40s' as in the decade 1940
        self.values[_('40s')] = [1940, '40s']
        #'30s' as in the decade 1930
        self.values[_('30s')] = [1930, '30s']
        #'Older' as in 'older than the year 1930'
        self.values[_('Older')] = [-1, 'Older']

        self.options = list(self.values.keys())

        # if we aren't on the 20s yet, remove it
        if date.today().year < 2020:
            self.options.remove(_('20s'))

        # define a initial decade an set the initial key
        self._initial_decade = self.options[0]
        self.update_images(False)
        
        self.current_key = self._initial_decade

    def update_images(self, *args):
        self._spritesheet = self.create_spritesheet( self.plugin,
            self._spritesheet, 'decade')
        
        if args[-1]:
            self.update_image = True

    def do_action(self):
        if self.current_key == self._initial_decade:
            self._album_model.remove_filter('decade')
        else:
            self._album_model.replace_filter('decade',
                self.values[self.current_key][0])

    def get_current_image(self):
        decade = self.values[self.current_key][1]
        return self._spritesheet[decade]

    def get_current_description(self):
        return self.current_key


class SortOrderToggleController(OptionsController):

    def __init__(self, plugin, album_model):
        super(SortOrderToggleController, self).__init__()

        self._album_model = album_model
        self.plugin = plugin

        # options
        self.values = OrderedDict([(_('Sort in descending order'), False),
            (_('Sort in ascending order'), True)])
        self.options = list(self.values.keys())

        self._images = []
        
        # set the current key
        self.gs = GSetting()
        self.settings = self.gs.get_setting(self.gs.Path.PLUGIN)
        sort_order = self.settings[self.gs.PluginKey.SORT_ORDER]
        self.current_key = list(self.values.keys())[
            list(self.values.values()).index(sort_order)]
        self.update_images(False)
        
    def update_images(self, *args):
        # initialize images
        if len(self._images) > 0:
            del self._images[:]
                        
        self._images.append(self.create_button_image( self.plugin,
            None, 'arrow_down.png'))
        self._images.append(self.create_button_image( self.plugin,
            None, 'arrow_up.png'))

        if args[-1]:
            self.update_image = True
            
    def do_action(self):
        sort_order = self.values[self.current_key]

        if not sort_order or\
            sort_order != self.settings[self.gs.PluginKey.SORT_ORDER]:
            self._album_model.sort(reverse=True)

        self.settings[self.gs.PluginKey.SORT_ORDER] = sort_order

    def get_current_image(self):
        return self._images[self.get_current_key_index()]


class AlbumSearchEntryController(OptionsController):

    # properties
    search_text = GObject.property(type=str, default='')

    def __init__(self, album_model):
        super(AlbumSearchEntryController, self).__init__()

        self._album_model = album_model
        self._filter_type = 'all'

        # options
        self.values = OrderedDict()
        self.values[_('Search all fields')] = 'all'
        self.values[_('Search album artists')] = 'album_artist'
        self.values[_('Search track artists')] = 'artist'
        self.values[_('Search albums')] = 'album_name'
        self.values[_('Search tracks')] = 'track'

        self.options = list(self.values.keys())
        self.current_key = list(self.values.keys())[0]

    def do_action(self):
        # remove old filter
        self._album_model.remove_filter(self._filter_type, False)

        # asign the new filter
        self._filter_type = self.values[self.current_key]

        self.do_search(self.search_text, True)

    def do_search(self, search_text, force=False):
        if self.search_text != search_text or force:
            self.search_text = search_text

            if search_text:
                self._album_model.replace_filter(self._filter_type,
                    search_text)
            elif not force:
                self._album_model.remove_filter(self._filter_type)

class AlbumQuickSearchController(object):

    def __init__(self, album_manager):
        self._album_manager = album_manager

    def connect_quick_search(self, quick_search):
        quick_search.connect('quick-search', self._on_quick_search)
        quick_search.connect('arrow-pressed', self._on_arrow_pressed)
        quick_search.connect('hide', self._on_hide)

    def _on_quick_search(self, quick_search, search_text, *args):
        album = self._album_manager.model.find_first_visible('album_name',
            search_text)

        if album:
            path = self._album_manager.model.get_path(album)
            self._album_manager.current_view.select_and_scroll_to_path(path)

    def _on_arrow_pressed(self, quick_search, key, *args):
        current = self._album_manager.current_view.get_selected_objects()[0]
        search_text = quick_search.get_text()
        album = None

        if key == Gdk.KEY_Up:
            album = self._album_manager.model.find_first_visible(
                'album_name', search_text, current, True)
        elif key == Gdk.KEY_Down:
            album = self._album_manager.model.find_first_visible(
                'album_name', search_text, current)

        if album:
            path = self._album_manager.model.get_path(album)
            self._album_manager.current_view.select_and_scroll_to_path(path)

    def _on_hide(self, quick_search, *args):
        self._album_manager.current_view.grab_focus()

class ViewController(OptionsController):

    def __init__(self, plugin, viewmgr):
        super(ViewController, self).__init__()

        self._viewmgr = viewmgr
        self._plugin = plugin
        self._keys = {}
        viewmgr.connect('notify::view-name', self.on_notify_view_name)

    def add_key_pair(self, view_name, button_name):
        self._keys[view_name] = button_name
        
    def on_notify_view_name(self, *args):
        print "on notify"
        self.current_key = self._keys[self._viewmgr.view_name]    
        
    def update_images(self, *args):
        # initialize images
        print "update_images"
        pass
            
    def do_action(self):
        print "do_action"
        # now search keys list by value to find the key name (which is the viewname)
        controller_current_view = self._keys.keys()[self._keys.values().index(self.current_key)]

        if controller_current_view != self._viewmgr.view_name:
            self._viewmgr.view_name = controller_current_view 
        
        
    def get_current_image(self):
        print "get_current_image"
        return None

