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

from gi.repository import Gtk
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import RB

from coverart_browser_prefs import GSetting
from coverart_utils import ConfiguredSpriteSheet
from coverart_utils import GenreConfiguredSpriteSheet
from coverart_browser_prefs import CoverLocale
import rb
from datetime import date
from collections import OrderedDict


ui_string = \
"""<interface>
<object class="GtkMenu" id="popupbutton_menu">
    <property name="visible">True</property>
    <property name="can_focus">False</property>
  </object>
</interface>"""


def resize_to_stock(pixbuf):
    what, width, height = Gtk.icon_size_lookup(Gtk.IconSize.BUTTON)

    if pixbuf.get_width() != width and pixbuf.get_height() != height:
        pixbuf = pixbuf.scale_simple(width, height,
            GdkPixbuf.InterpType.BILINEAR)

    return pixbuf


class PixbufButton(Gtk.Button):
    '''
    A base button that allows setting pixbufs directly and resizes them
    according to the default iconsize.
    '''
    def __init__(self, *args, **kwargs):
        super(PixbufButton, self).__init__(*args, **kwargs)

    def set_image(self, pixbuf):
        '''
        Customized set_image method that resizes the setted pixbu
        '''
        pixbuf = resize_to_stock(pixbuf)

        image_widget = self.get_image()
        image_widget.set_from_pixbuf(pixbuf)


# generic class from which implementation inherit from
class PopupButton(PixbufButton):
    # the following vars are to be defined in the inherited classes
    #__gtype_name__ = gobject typename
    #default_image = default image to be displayed

    # signals
    __gsignals__ = {
        'item-clicked': (GObject.SIGNAL_RUN_LAST, None, (object,))
        }

    def __init__(self, *args, **kwargs):
        '''
        Initializes the button.
        '''
        super(PopupButton, self).__init__(*args, **kwargs)

        builder = Gtk.Builder()
        builder.add_from_string(ui_string)

        self._popup_menu = builder.get_object('popupbutton_menu')

        # initialise some variables
        self._current_value = None
        self.initialised = False
        self._first_menu_item = None

    @property
    def current_value(self):
        return self._current_value

    @current_value.setter
    def current_value(self, value):
        self._current_value = value
        self.set_tooltip_text(value)

    def initialise(self, initial_value, shell):
        '''
        initialise - derived objects call this first
        shell = rhythmbox shell
        callback = function to call when a menuitem is selected
        '''
        if not self.initialised:
            self.initialised = True
            self.current_value = initial_value
            self.shell = shell

    def add_menuitem(self, label, val):
        '''
        add a new menu item to the popup
        '''
        if not self._first_menu_item:
            new_menu_item = Gtk.RadioMenuItem(label=label)
            self._first_menu_item = new_menu_item
        else:
            new_menu_item = Gtk.RadioMenuItem.new_with_label_from_widget(
                group=self._first_menu_item, label=label)

        if label == self.current_value:
            new_menu_item.set_active(True)

        new_menu_item.connect('toggled', self._fire_item_clicked, val)
        new_menu_item.show()

        self._popup_menu.append(new_menu_item)

    def clear_popupmenu(self):
        '''
        reinitialises/clears the current popup menu and associated actions
        '''
        for menu_item in self._popup_menu:
            self._popup_menu.remove(menu_item)

            self._popup_menu.show_all()
            self.shell.props.ui_manager.ensure_update()

        self._first_menu_item = None

    def _fire_item_clicked(self, menu_item, value):
        '''
        Fires the item-clicked signal if the item is selected, passing the
        given value as a parameter. Also updates the current value with the
        value of the selected item.
        '''
        if menu_item.get_active():
            self.current_value = menu_item.get_label()
            self.emit('item-clicked', value)

    def do_clicked(self):
        '''
        when button is clicked, update the popup with the sorting options
        before displaying the popup
        '''
        self.show_popup()

    def show_popup(self):
        '''
        show the current popup menu
        '''
        self._popup_menu.popup(None, None, None, None, 0,
            Gtk.get_current_event_time())

    def do_delete_thyself(self):
        self.clear_popupmenu()
        del self._popupmenu
        del self._actiongroup


class PlaylistPopupButton(PopupButton):
    __gtype_name__ = 'PlaylistPopupButton'

    def __init__(self, *args, **kwargs):
        '''
        Initializes the button.
        '''
        super(PlaylistPopupButton, self).__init__(*args, **kwargs)

    def initialise(self, plugin, shell, album_model):
        '''
        extend the default initialise function
        because we need to also resize the picture
        associated with the playlist button
        '''
        if self.initialised:
            return

        self._album_model = album_model

        # get the library name and initialize the superclass with it
        self._library_name = shell.props.library_source.props.name

        super(PlaylistPopupButton, self).initialise(self._library_name, shell)

        # get the queue name
        self._queue_name = shell.props.queue_source.props.name

        if " (" in self._queue_name:
            self._queue_name = self._queue_name[0:self._queue_name.find(" (")]

        # configure the sprite sheet
        self._spritesheet = ConfiguredSpriteSheet(plugin, 'playlist')

        # get the playlist manager and it's model
        playlist_manager = shell.props.playlist_manager
        playlist_model = playlist_manager.props.display_page_model

        # connect signals to update playlists
        playlist_model.connect('row-inserted', self._update_popup,
            playlist_manager)
        playlist_model.connect('row-deleted', self._update_popup,
            playlist_manager)
        playlist_model.connect('row-changed', self._update_popup,
            playlist_manager)

        # generate initial popup
        self._update_popup(None, playlist_manager)

        # update the button
        self.do_item_clicked(None)

    def _update_popup(self, *args):
        playlist_manager = args[-1]
        still_exists = False

        # clear and recreate popup
        self.clear_popupmenu()

        # library and play queue sources
        self.add_menuitem(self._library_name, None)
        self.add_menuitem(self._queue_name, self.shell.props.queue_source)

        playlists_entries = playlist_manager.get_playlists()

        for playlist in playlists_entries:
            if playlist.props.is_local:
                name = playlist.props.name
                self.add_menuitem(name, playlist)

                still_exists = still_exists or name == self.current_value

        if not still_exists:
            self.do_item_clicked(None)

    def do_item_clicked(self, playlist):
        '''
        when a popup menu item is chosen change the button tooltip
        before invoking the source callback function
        '''
        if not playlist:
            model = None
            self.current_value = self._library_name
            self.set_image(self._spritesheet['music'])
        elif self._queue_name in playlist.props.name:
            model = playlist.get_query_model()
            self.current_value = self._queue_name
            self.set_image(self._spritesheet['queue'])
        else:
            model = playlist.get_query_model()
            self.current_value = playlist.props.name
            if isinstance(playlist, RB.StaticPlaylistSource):
                self.set_image(self._spritesheet['playlist'])
            else:
                self.set_image(self._spritesheet['smart'])

        if not model:
            self._album_model.remove_filter('model')
        else:
            self._album_model.replace_filter('model', model)


class GenrePopupButton(PopupButton):
    __gtype_name__ = 'GenrePopupButton'

    def __init__(self, *args, **kwargs):
        '''
        Initializes the button.
        '''
        super(GenrePopupButton, self).__init__(*args, **kwargs)

    def initialise(self, plugin, shell, album_model):
        '''
        extend the default initialise function
        because we need to also resize the picture
        associated with the genre button
        '''
        if self.initialised:
            return

        self._album_model = album_model

        # create a new model and initialise the superclass
        self._genres_model = RB.RhythmDBPropertyModel.new(shell.props.db,
            RB.RhythmDBPropType.GENRE)

        query = shell.props.library_source.props.base_query_model
        self._genres_model.props.query_model = query

        super(GenrePopupButton, self).initialise(self._genres_model[0][0],
            shell)

        # initialise the button spritesheet
        self._spritesheet = GenreConfiguredSpriteSheet(plugin, 'genre')
        self._default_image = \
            GdkPixbuf.Pixbuf.new_from_file(rb.find_plugin_file(plugin,
                'img/default_genre.png'))
        self._unrecognised_image = \
            GdkPixbuf.Pixbuf.new_from_file(rb.find_plugin_file(plugin,
                'img/unrecognised_genre.png'))

        # connect signals to update genres
        query.connect('row-inserted', self._update_popup)
        query.connect('row-deleted', self._update_popup)
        query.connect('row-changed', self._update_popup)

        # generate initial popup
        self._update_popup(query)

        # update the button
        self.do_item_clicked(self._genres_model[0][0])

    def _update_popup(self, *args):
        still_exists = False

        # clear and recreate popup
        self.clear_popupmenu()

        for row in self._genres_model:
            genre = row[0]
            self.add_menuitem(genre, genre)

            still_exists = still_exists or genre == self.current_value

        if not still_exists:
            self.do_item_clicked(self._genres_model[0][0])

    def do_item_clicked(self, genre):
        '''
        called when genre popup menu item chosen
        return None if the first entry in popup returned
        '''
        test_genre = genre.lower()

        if test_genre == self._genres_model[0][0].lower():
            self.set_image(self._default_image)
        elif not test_genre in self._spritesheet:
            self.set_image(self._find_alternates(test_genre))
        else:
            self.set_image(self._spritesheet[test_genre])

        if genre == self._genres_model[0][0]:
            self.set_tooltip_text(_('All Genres'))
            self._album_model.remove_filter('genre')
        else:
            self._album_model.replace_filter('genre', genre)

    def _find_alternates(self, test_genre):

        # first check if any of the default genres are a substring
        # of test_genre - check in reverse order so that we
        # test largest strings first (prevents spurious matches with
        # short strings)
        for genre in sorted(self._spritesheet.names,
            key=lambda b: (-len(b), b)):
            if genre in test_genre:
                return self._spritesheet[genre]

        # next check alternates
        if test_genre in self._spritesheet.alternate:
            return self._spritesheet[self._spritesheet.alternate[test_genre]]

        # if no matches then default to unrecognised image
        return self._unrecognised_image


class SortPopupButton(PopupButton):
    __gtype_name__ = 'SortPopupButton'

    sort_by = GObject.property(type=str)

    def __init__(self, *args, **kwargs):
        '''
        Initializes the button.
        '''
        cl = CoverLocale()
        cl.switch_locale(cl.Locale.LOCALE_DOMAIN)

        self.sorts = {'name': _('Sort by album name'),
        'artist': _('Sort by album artist'),
        'year': _('Sort by year'),
        'rating': _('Sort by rating')}

        super(SortPopupButton, self).__init__(*args, **kwargs)

    def initialise(self, plugin, shell, album_model):
        '''
        extend the default initialise function
        because we need to also resize the picture
        associated with the sort button as well as find the
        saved sort order
        '''
        if self.initialised:
            return

        self._album_model = album_model

        # get the current sort key and initialise the superclass
        gs = GSetting()
        source_settings = gs.get_setting(gs.Path.PLUGIN)
        source_settings.bind(gs.PluginKey.SORT_BY,
            self, 'sort_by', Gio.SettingsBindFlags.DEFAULT)

        super(SortPopupButton, self).initialise(self.sorts[self.sort_by],
            shell)

        # initialise spritesheet
        self._spritesheet = ConfiguredSpriteSheet(plugin, 'sort')

        # create the pop up menu
        for key, text in sorted(self.sorts.iteritems()):
            self.add_menuitem(text, key)

        self.do_item_clicked(self.sort_by)

    def do_item_clicked(self, sort):
        '''
        called when sort popup menu item chosen
        '''
        self.set_tooltip_text(self.sorts[sort])

        gs = GSetting()
        settings = gs.get_setting(gs.Path.PLUGIN)
        settings[gs.PluginKey.SORT_BY] = sort

        self.set_image(self._spritesheet[sort])

        self._album_model.sort(sort)


class DecadePopupButton(PopupButton):
    __gtype_name__ = 'DecadePopupButton'

    def __init__(self, *args, **kwargs):
        '''
        Initializes the button.
        '''
        super(DecadePopupButton, self).__init__(*args, **kwargs)

        self._decade = OrderedDict([('All', -1), ('20s', 2020),
            ('10s', 2010), ('00s', 2000), ('90s', 1990), ('80s', 1980),
            ('70s', 1970), ('60s', 1960), ('50s', 1950), ('40s', 1940),
            ('30s', 1930), ('Old', -1)])

        cl = CoverLocale()
        cl.switch_locale(cl.Locale.LOCALE_DOMAIN)
        self._translation = {'All': _('All'), 'Old': _('Old')}

        self._initial = 'All'

    def initialise(self, plugin, shell, album_model):
        '''
        extend the default initialise function
        because we need to also resize the picture
        associated with the decade button
        '''
        if self.initialised:
            return

        self._album_model = album_model

        super(DecadePopupButton, self).initialise(self._initial, shell)

        self._spritesheet = ConfiguredSpriteSheet(plugin, 'decade')
        self._default_image = self._spritesheet[self._initial]

        # generate initial popup
        '''
        we need only add 2020s to the popup if the current year
        warrants it...

        and yes this means that the plugin decade functionality
        will not work in 2030 and onwards ... but I'll worry about that
        then :)
        '''
        firstval = '20s'
        current_year = date.today().year

        for decade in self._decade:
            if  (current_year >= 2020 and decade == firstval) or \
                (current_year < 2020 and decade != firstval):
                if decade in self._translation:
                    menutext = self._translation[decade]
                else:
                    menutext = decade

                self.add_menuitem(menutext, decade)

        self.do_item_clicked(self._initial)

    def do_item_clicked(self, decade):
        '''
        called when genre popup menu item chosen
        return None if the first entry in popup returned
        '''
        self.set_image(self._spritesheet[decade])

        print decade

        if decade == self._initial:
            self.set_tooltip_text(_('All Decades'))
            self._album_model.remove_filter('decade')
        else:
            self.set_tooltip_text(decade)
            self._album_model.replace_filter('decade', self._decade[decade])


class ImageToggleButton(PixbufButton):
    '''
    generic class from which implementation inherit from
    '''
    # the following vars are to be defined in the inherited classes
    #__gtype_name__ = gobject typename

    # signals
    __gsignals__ = {
        'toggled': (GObject.SIGNAL_RUN_LAST, None, ())
        }

    def __init__(self, *args, **kwargs):
        '''
        Initializes the button.
        '''
        super(ImageToggleButton, self).__init__(*args, **kwargs)

        # initialise some variables
        self.image_display = False
        self.initialised = False

    def initialise(self, image1, image2):
        '''
        initialise - derived objects call this first
        callback = function to call when button is clicked
        image1 = by default (image_display is True), first image displayed
        image2 = (image display is False), second image displayed
        '''
        if self.initialised:
            return

        self.initialised = True

        self._image1 = resize_to_stock(image1)
        self._image2 = resize_to_stock(image2)

        self.update_button_image()

    def do_clicked(self):
        self.image_display = not self.image_display

        self.update_button_image()
        self.emit('toggled')

    def update_button_image(self):
        if self.image_display:
            self.set_image(self._image1)
        else:
            self.set_image(self._image2)

    def do_delete_thyself(self):
        del self._image1
        del self._image2


class SortOrderButton(ImageToggleButton):
    __gtype_name__ = 'SortOrderButton'

    def __init__(self, *args, **kwargs):
        '''
        Initializes the button.
        '''
        super(SortOrderButton, self).__init__(*args, **kwargs)

        self.gs = GSetting()

    def initialise(self, plugin, album_model):
        '''
        set up the images we will use for this widget
        '''
        if self.initialised:
            return

        self._album_model = album_model

        image1 = GdkPixbuf.Pixbuf.new_from_file(rb.find_plugin_file(plugin,
        'img/arrow_down.png'))
        image2 = GdkPixbuf.Pixbuf.new_from_file(rb.find_plugin_file(plugin,
        'img/arrow_up.png'))

        super(SortOrderButton, self).initialise(image1, image2)

        # get the current sort order
        gs = GSetting()
        settings = gs.get_setting(gs.Path.PLUGIN)
        sort_order = settings[gs.PluginKey.SORT_ORDER]

        if sort_order:
            self.do_clicked()

        # set the tooltip
        self.set_tooltip(sort_order)

    def do_toggled(self):
        val = self.image_display

        # update settings
        self.gs.set_value(self.gs.Path.PLUGIN,
                    self.gs.PluginKey.SORT_ORDER, val)

        # set the tooltip
        self.set_tooltip(val)

        # resort the model
        self._album_model.sort(reverse=True)

    def set_tooltip(self, val):
        cl = CoverLocale()
        cl.switch_locale(cl.Locale.LOCALE_DOMAIN)

        if val:
            self.set_tooltip_text(_('Sort in descending order'))
        else:
            self.set_tooltip_text(_('Sort in ascending order'))
