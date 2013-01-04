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

from coverart_browser_prefs import GSetting
from coverart_utils import ConfiguredSpriteSheet
from coverart_browser_prefs import CoverLocale
import rb
from datetime import date
from collections import OrderedDict


class PixbufButton(Gtk.Button):

    def set_image(self, pixbuf):
        image = self.get_image()

        if not image:
            image = Gtk.Image()
            super(PixbufButton, self).set_image(image)

        self.get_image().set_from_pixbuf(pixbuf)


# generic class from which implementation inherit from
class PopupButton(PixbufButton):
    # the following vars are to be defined in the inherited classes
    __gtype_name__ = "PopupButton"

    # signals
    __gsignals__ = {
        'item-clicked': (GObject.SIGNAL_RUN_LAST, None, (str,))
        }

    def __init__(self, *args, **kwargs):
        '''
        Initializes the button.
        '''
        super(PopupButton, self).__init__(*args, **kwargs)

        self._popup_menu = Gtk.Menu()

        # initialise some variables
        self._first_menu_item = None
        self._controller = None

    @property
    def controller(self):
        return self._controller

    @controller.setter
    def controller(self, controller):
        if self._controller:
            # disconnect signals
            self._controller.disconnect(self._options_changed_id)
            self._controller.disconnect(self._current_key_changed_id)

        self._controller = controller

        # connect signals
        self._options_changed_id = self._controller.connect('notify::options',
            self._update_menu)
        self._current_key_changed_id = self._controller.connect(
            'notify::current-key', self._update_current_key)

        # update the menu and current key
        self._update_menu()
        self._update_current_key()

    def _update_menu(self, *args):
        self.clear_popupmenu()

        for key in self._controller.options:
            self.add_menuitem(key)

    def _update_current_key(self, *args):
        item = self.get_menuitems()[self._controller.get_current_key_index()]
        item.set_active(True)

    def add_menuitem(self, label):
        '''
        add a new menu item to the popup
        '''
        if not self._first_menu_item:
            new_menu_item = Gtk.RadioMenuItem(label=label)
            self._first_menu_item = new_menu_item
        else:
            new_menu_item = Gtk.RadioMenuItem.new_with_label_from_widget(
                group=self._first_menu_item, label=label)

        new_menu_item.connect('toggled', self._fire_item_clicked)
        new_menu_item.show()

        self._popup_menu.append(new_menu_item)

    def get_menuitems(self):
        return self._popup_menu.get_children()

    def clear_popupmenu(self):
        '''
        reinitialises/clears the current popup menu and associated actions
        '''
        for menu_item in self._popup_menu:
            self._popup_menu.remove(menu_item)

        self._first_menu_item = None

    def _fire_item_clicked(self, menu_item):
        '''
        Fires the item-clicked signal if the item is selected, passing the
        given value as a parameter. Also updates the current value with the
        value of the selected item.
        '''
        if menu_item.get_active():
            self.emit('item-clicked', menu_item.get_label())

    def do_item_clicked(self, key):
        if self._controller:
            # inform the controller
            self._controller.handler_block(self._current_key_changed_id)
            self._controller.item_selected(key)
            self._controller.handler_unblock(self._current_key_changed_id)

            # update the current image and tooltip
            self.set_image(self._controller.get_current_image())
            self.set_tooltip_text(self._controller.get_current_tooltip())

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


class ImageToggleButton(Gtk.Button):
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
