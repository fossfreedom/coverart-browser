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


# generic class from which implementation inherit from
class PopupButton(Gtk.Button):
    # the following vars are to be defined in the inherited classes
    #__gtype_name__ = gobject typename
    #default_image = default image to be displayed

    def __init__(self, **kargs):
        '''
        Initializes the button.
        '''
        super(PopupButton, self).__init__(
            **kargs)

        self._builder = Gtk.Builder()
        self._builder.add_from_string(ui_string)

        self._popup_menu = self._builder.get_object('popupbutton_menu')

        # initialise some variables
        self._first_menu_item = None
        self._current_val = None
        self.is_initialised = False

    def initialise(self, shell, callback, initial_label):
        '''
        initialise - derived objects call this first
        shell = rhythmbox shell
        callback = function to call when a menuitem is selected
        '''
        if self.is_initialised:
            return

        self.is_initialised = True

        self.shell = shell
        self.callback = callback
        self.set_popup_value(initial_label)

        self.resize_button_image()

    def clear_popupmenu(self):
        '''
        reinitialises/clears the current popup menu and associated actions
        '''
        for menu_item in self._popup_menu:
            self._popup_menu.remove(menu_item)

            self._popup_menu.show_all()
            self.shell.props.ui_manager.ensure_update()

        self._first_menu_item = None

    def add_menuitem(self, label, func, val):
        '''
        add a new menu item to the popup
        '''
        if not self._first_menu_item:
            new_menu_item = Gtk.RadioMenuItem(label=label)
            self._first_menu_item = new_menu_item
        else:
            new_menu_item = Gtk.RadioMenuItem.new_with_label_from_widget(
                group=self._first_menu_item, label=label)

        if label == self._current_val:
            new_menu_item.set_active(True)

        new_menu_item.connect('toggled', func, val)
        new_menu_item.show()

        self._popup_menu.append(new_menu_item)

    def show_popup(self):
        '''
        show the current popup menu
        '''
        self._popup_menu.popup(None, None, None, None, 0,
            Gtk.get_current_event_time())

    def set_popup_value(self, val):
        '''
        set the tooltip according to the popup menu chosen
        '''
        self.set_tooltip_text(val)
        self._current_val = val

    def do_clicked(self):
        '''
        when button is clicked, update the popup with the sorting options
        before displaying the popup
        '''
        self.show_popup()

    def resize_button_image(self, pixbuf=None):
        '''
        if the button contains an image rather than stock icon
        this function will ensure the image is resized correctly to
        fit the button style
        '''

        what, width, height = Gtk.icon_size_lookup(Gtk.IconSize.BUTTON)
        image = self.get_image()

        try:
            if pixbuf:
                pixbuf = pixbuf.scale_simple(width, height,
                    GdkPixbuf.InterpType.BILINEAR)
            else:
                pixbuf = self.default_image.get_pixbuf().scale_simple(width,
                    height, GdkPixbuf.InterpType.BILINEAR)

            image.set_from_pixbuf(pixbuf)
        except:
            pass

    def do_delete_thyself(self):
        self.clear_popupmenu()
        del self._popupmenu
        del self._actiongroup
        del self._builder


class PlaylistPopupButton(PopupButton):
    __gtype_name__ = 'PlaylistPopupButton'

    def __init__(self, **kargs):
        '''
        Initializes the button.
        '''
        super(PlaylistPopupButton, self).__init__(
            **kargs)

        #weird introspection - do_clicked is overridden but
        #PopupButton version is called not the Playlist version
        #connect the clicked event to this version
        self.connect('clicked', self.do_clicked)

    def initialise(self, plugin, shell, callback):
        '''
        extend the default initialise function
        because we need to also resize the picture
        associated with the playlist button
        '''
        if self.is_initialised:
            return

        self._library_name = shell.props.library_source.props.name
        self._queue_name = shell.props.queue_source.props.name

        if " (" in self._queue_name:
            self._queue_name = self._queue_name[0:self._queue_name.find(" (")]

        self._spritesheet = ConfiguredSpriteSheet(plugin, 'playlist')
        self.default_image = Gtk.Image.new_from_pixbuf(
            self._spritesheet['music'])

        super(PlaylistPopupButton, self).initialise(shell, callback,
            self._library_name)

    def do_clicked(self, button):
        '''
        we need to create the playlist first before showing
        the popup
        N.B. see comment above
        '''
        playlist_manager = self.shell.props.playlist_manager
        playlists_entries = playlist_manager.get_playlists()
        self.clear_popupmenu()
        self.add_menuitem(self._library_name,
            self._change_playlist_source, None)
        self.add_menuitem(self._queue_name,
            self._change_playlist_source, self.shell.props.queue_source)

        if playlists_entries:
            for playlist in playlists_entries:
                if playlist.props.is_local:
                    self.add_menuitem(playlist.props.name,
                        self._change_playlist_source, playlist)

        self.show_popup()

    def _change_playlist_source(self, menu, playlist):
        '''
        when a popup menu item is chosen change the button tooltip
        before invoking the source callback function
        '''
        if menu.get_active():
            if not playlist:
                model = None
                self.set_popup_value(self._library_name)
                self.resize_button_image(self._spritesheet['music'])
            elif self._queue_name in playlist.props.name:
                model = playlist.get_query_model()
                self.set_popup_value(self._queue_name)
                self.resize_button_image(self._spritesheet['queue'])
            else:
                model = playlist.get_query_model()
                self.set_popup_value(playlist.props.name)
                if isinstance(playlist, RB.StaticPlaylistSource):
                    self.resize_button_image(self._spritesheet['playlist'])
                else:
                    self.resize_button_image(self._spritesheet['smart'])

            self.callback(model)

    def show_popup(self):
        '''
        show the current popup menu
        This is a workaround for issue #111
        Basically - move the position of the popup to prevent the popup
        opening in scroll-mode - seems to only affect the playlist popup
        '''
        def pos(menu, icon):
            a, x, y = self.get_window().get_origin()
            x += self.get_allocation().x
            y += self.get_allocation().y + self.get_allocation().height

            from gi.repository import Gdk
            s = Gdk.Screen.get_default()

            if y > (s.get_height() - 180):
                y = s.get_height() - 180

            return x, y, False

        self._popup_menu.popup(None, None, pos, None, 0,
            Gtk.get_current_event_time())


class GenrePopupButton(PopupButton):
    __gtype_name__ = 'GenrePopupButton'

    def __init__(self, **kargs):
        '''
        Initializes the button.
        '''
        super(GenrePopupButton, self).__init__(
            **kargs)

    def initialise(self, plugin, shell, callback):
        '''
        extend the default initialise function
        because we need to also resize the picture
        associated with the genre button
        '''
        if self.is_initialised:
            return

        self._spritesheet = GenreConfiguredSpriteSheet(plugin, 'genre')
        self.default_image = \
            Gtk.Image.new_from_file(rb.find_plugin_file(plugin,
                'img/default_genre.png'))
        self.unrecognised_image = \
            Gtk.Image.new_from_file(rb.find_plugin_file(plugin,
                'img/unrecognised_genre.png'))

        # create a new model
        self.model = RB.RhythmDBPropertyModel.new(shell.props.db,
            RB.RhythmDBPropType.GENRE)

        query = shell.props.library_source.props.base_query_model
        self.model.props.query_model = query

        super(GenrePopupButton, self).initialise(shell, callback,
            self.model[0][0])

        # connect signals to update genres

        query.connect('row-inserted', self._update_popup)
        query.connect('row-deleted', self._update_popup)
        query.connect('row-changed', self._update_popup)

        # generate initial popup
        self._update_popup(query)
        self.set_popup_value(_('All Genres'))

    def _update_popup(self, *args):
        still_exists = False
        current = self._current_val

        # clear and recreate popup
        self.clear_popupmenu()

        for row in self.model:
            genre = row[0]
            self.add_menuitem(genre, self._genre_changed, genre)

            still_exists = still_exists or genre == current

        if not still_exists:
            self._genre_changed(None, self.model[0][0])

    def _genre_changed(self, menu, genre):
        '''
        called when genre popup menu item chosen
        return None if the first entry in popup returned
        '''
        if not menu or menu.get_active():
            test_genre = genre.lower()
            if test_genre == self.model[0][0].lower():
                self.resize_button_image(self.default_image.get_pixbuf())
            elif not test_genre in self._spritesheet:
                self._find_alternates(test_genre)  
            else:
                self.resize_button_image(self._spritesheet[test_genre])

            if genre == self.model[0][0]:
                self.set_popup_value(_('All Genres'))
                self.callback(None)
            else:
                self.set_popup_value(genre)
                self.callback(genre)

    def _find_alternates(self, test_genre):

        # first check if any of the default genres are a substring
        # of test_genre - check in reverse order so that we
        # test largest strings first (prevents spurious matches with
        # short strings)
        for genre in sorted(self._spritesheet.names,
            key=lambda b: (-len(b), b)):
            if genre in test_genre:
                self.resize_button_image(self._spritesheet[genre])
                return

        # next check alternates
        if test_genre in self._spritesheet.alternate:
            self.resize_button_image(
                self._spritesheet[self._spritesheet.alternate[test_genre]])
            return

        # if no matches then default to unrecognised image
        self.resize_button_image(self.unrecognised_image.get_pixbuf())


class SortPopupButton(PopupButton):
    __gtype_name__ = 'SortPopupButton'

    sort_by = GObject.property(type=str)

    def __init__(self, **kargs):
        '''
        Initializes the button.
        '''
        cl = CoverLocale()
        cl.switch_locale(cl.Locale.LOCALE_DOMAIN)
        
        self.sorts = {'name': _('Sort by album name'),
        'artist': _('Sort by album artist'),
        'year': _('Sort by year'),
        'rating': _('Sort by rating')}

        super(SortPopupButton, self).__init__(
            **kargs)

    def initialise(self, plugin, shell, callback):
        '''
        extend the default initialise function
        because we need to also resize the picture
        associated with the sort button as well as find the
        saved sort order
        '''
        if self.is_initialised:
            return

        self._spritesheet = ConfiguredSpriteSheet(plugin, 'sort')

        gs = GSetting()
        source_settings = gs.get_setting(gs.Path.PLUGIN)
        source_settings.bind(gs.PluginKey.SORT_BY,
            self, 'sort_by', Gio.SettingsBindFlags.DEFAULT)

        super(SortPopupButton, self).initialise(shell, callback,
            self.sorts[self.sort_by])

        # create the pop up menu
        for key, text in sorted(self.sorts.iteritems()):
            self.add_menuitem(text, self._sort_changed, key)

        self._sort_changed(None, self.sort_by)

    def _sort_changed(self, menu, sort):
        '''
        called when sort popup menu item chosen
        '''
        if not menu or menu.get_active():
            self.set_popup_value(self.sorts[sort])
            #self.sort_by = sort
            print sort
            gs = GSetting()
            settings = gs.get_setting(gs.Path.PLUGIN)
            settings[gs.PluginKey.SORT_BY] = sort

            self.resize_button_image(self._spritesheet[sort])

            self.callback(sort)

class DecadePopupButton(PopupButton):
    __gtype_name__ = 'DecadePopupButton'

    def __init__(self, **kargs):
        '''
        Initializes the button.
        '''
        super(DecadePopupButton, self).__init__(**kargs)

        self._decade=OrderedDict([('All',-1), ('20s',2020), \
            ('10s',2010), ('00s',2000), ('90s',1990), ('80s',1980), \
            ('70s',1970), ('60s',1960), ('50s',1950), ('40s',1940), \
            ('30s',1930), ('Old',-1)])

        cl = CoverLocale()
        cl.switch_locale(cl.Locale.LOCALE_DOMAIN)
        self._translation={'All':_('All'), 'Old':_('Old')}
        
        self._initial='All'

    def initialise(self, plugin, shell, callback):
        '''
        extend the default initialise function
        because we need to also resize the picture
        associated with the decade button
        '''
        if self.is_initialised:
            return

        self._spritesheet = ConfiguredSpriteSheet(plugin, 'decade')
        self.default_image = Gtk.Image.new_from_pixbuf(
            self._spritesheet[self._initial])

        super(DecadePopupButton, self).initialise(shell, callback,
            self._initial)
        
        # generate initial popup
        self._update_popup()

    def _update_popup(self, *args):
        
        # clear and recreate popup
        self.clear_popupmenu()

        '''
        we need only add 2020s to the popup if the current year
        warrants it...

        and yes this means that the plugin decade functionality
        will not work in 2030 and onwards ... but I'll worry about that
        then :)
        '''
        firstval='20s'
        current_year = date.today().year
            
        for decade in self._decade:
            if  (current_year >= 2020 and decade==firstval) or \
                (current_year < 2020 and decade!=firstval):
                if decade in self._translation:
                    menutext=self._translation[decade]
                else:
                    menutext=decade
                self.add_menuitem(menutext, self._decade_changed, \
                    decade)

        self._decade_changed(None, self._initial)

    def _decade_changed(self, menu, decade):
        '''
        called when genre popup menu item chosen
        return None if the first entry in popup returned
        '''
        if not menu or menu.get_active():
            self.resize_button_image(self._spritesheet[decade])

            if decade == self._initial:
                self.set_popup_value(_('All Decades'))
                self.callback(None)
            else:
                self.set_popup_value(decade)
                self.callback(self._decade[decade])

class ImageToggleButton(Gtk.Button):
    '''
    generic class from which implementation inherit from
    '''
    # the following vars are to be defined in the inherited classes
    #__gtype_name__ = gobject typename

    def __init__(self, **kargs):
        '''
        Initializes the button.
        '''
        super(ImageToggleButton, self).__init__(
            **kargs)

        # initialise some variables
        self.image_display = False
        self.is_initialised = False

    def initialise(self, callback, image1, image2):
        '''
        initialise - derived objects call this first
        callback = function to call when button is clicked
        image1 = by default (image_display is True), first image displayed
        image2 = (image display is False), second image displayed
        '''
        if self.is_initialised:
            return

        self.is_initialised = True

        self.callback = callback
        self._image1 = image1
        self._image2 = image2
        self._image1_pixbuf = self._resize_button_image(self._image1)
        self._image2_pixbuf = self._resize_button_image(self._image2)

        self._update_button_image()

    def on_clicked(self):
        self.image_display = not self.image_display
        self._update_button_image()
        self.callback(self.image_display)

    def _update_button_image(self):
        image = self.get_image()

        if image:
            if self.image_display:
                image.set_from_pixbuf(self._image1_pixbuf)
            else:
                image.set_from_pixbuf(self._image2_pixbuf)

    def _resize_button_image(self, image):
        '''
        this function will ensure the image is resized correctly to
        fit the button style
        '''

        what, width, height = Gtk.icon_size_lookup(Gtk.IconSize.BUTTON)

        pixbuf = None
        try:
            pixbuf = image.get_pixbuf().scale_simple(width, height,
                    GdkPixbuf.InterpType.BILINEAR)
        except:
            pass

        return pixbuf

    def do_delete_thyself(self):
        del self._image1_pixbuf
        del self._image2_pixbuf


class SortOrderButton(ImageToggleButton):
    __gtype_name__ = 'SortOrderButton'

    def __init__(self, **kargs):
        '''
        Initializes the button.
        '''
        super(SortOrderButton, self).__init__(
            **kargs)

        self.gs = GSetting()

    def initialise(self, plugin, callback, sort_order):
        '''
        set up the images we will use for this widget
        '''
        self.image_display = sort_order
        self.set_tooltip(self.image_display)

        if not self.is_initialised:
            image1 = Gtk.Image.new_from_file(rb.find_plugin_file(plugin,
            'img/arrow_up.png'))
            image2 = Gtk.Image.new_from_file(rb.find_plugin_file(plugin,
            'img/arrow_down.png'))

            super(SortOrderButton, self).initialise(callback,
               image1, image2)

    def do_clicked(self):

        val = not self.image_display
        self.gs.set_value(self.gs.Path.PLUGIN,
                    self.gs.PluginKey.SORT_ORDER, val)
        self.set_tooltip(val)
        self.on_clicked()

    def set_tooltip(self, val):
        cl = CoverLocale()
        cl.switch_locale(cl.Locale.LOCALE_DOMAIN)
        if not val:
            self.set_tooltip_text(_('Sort in descending order'))
        else:
            self.set_tooltip_text(_('Sort in ascending order'))
