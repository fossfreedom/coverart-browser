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

from gi.repository import RB
from gi.repository import Gtk
from gi.repository import GObject


class OptionsWidget(Gtk.Widget):

    def __init__(self, *args, **kwargs):
        super(OptionsWidget, self).__init__(*args, **kwargs)
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
            self._update_options)
        self._current_key_changed_id = self._controller.connect(
            'notify::current-key', self._update_current_key)

        # update the menu and current key
        self.update_options()
        self.update_current_key()

    def _update_options(self, *args):
        self.update_options()

    def update_options(self):
        pass

    def _update_current_key(self, *args):
        self.update_current_key()

    def update_current_key():
        pass


class OptionsPopupWidget(OptionsWidget):

    # signals
    __gsignals__ = {
        'item-clicked': (GObject.SIGNAL_RUN_LAST, None, (str,))
        }

    def __init__(self, *args, **kwargs):
        OptionsWidget.__init__(self, *args, **kwargs)

        self._popup_menu = Gtk.Menu()

    def update_options(self):
        self.clear_popupmenu()

        for key in self._controller.options:
            self.add_menuitem(key)

    def update_current_key(self):
        # select the item if it isn't already
        item = self.get_menuitems()[self._controller.get_current_key_index()]

        if not item.get_active():
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
            self._controller.option_selected(key)

    def show_popup(self):
        '''
        show the current popup menu
        '''
        self._popup_menu.popup(None, None, None, None, 0,
            Gtk.get_current_event_time())

    def do_delete_thyself(self):
        self.clear_popupmenu()
        del self._popupmenu


class PixbufButton(Gtk.Button):

    def __init__(self, *args, **kwargs):
        super(PixbufButton, self).__init__(*args, **kwargs)

    def set_image(self, pixbuf):
        image = self.get_image()

        if not image:
            image = Gtk.Image()
            super(PixbufButton, self).set_image(image)

        self.get_image().set_from_pixbuf(pixbuf)


class PopupButton(PixbufButton, OptionsPopupWidget):
    __gtype_name__ = "PopupButton"

    # signals
    __gsignals__ = {
        'item-clicked': (GObject.SIGNAL_RUN_LAST, None, (str,))
        }

    def __init__(self, *args, **kwargs):
        '''
        Initializes the button.
        '''
        PixbufButton.__init__(self, *args, **kwargs)
        OptionsPopupWidget.__init__(self, *args, **kwargs)

        self._popup_menu = Gtk.Menu()

        # initialise some variables
        self._first_menu_item = None

    def update_current_key(self):
        super(PopupButton, self).update_current_key()

        # update the current image and tooltip
        self.set_image(self._controller.get_current_image())
        self.set_tooltip_text(self._controller.get_current_description())

    def do_clicked(self):
        '''
        when button is clicked, update the popup with the sorting options
        before displaying the popup
        '''
        self.show_popup()


class ImageToggleButton(PixbufButton, OptionsWidget):
    __gtype_name__ = "ImageToggleButton"

    def __init__(self, *args, **kwargs):
        '''
        Initializes the button.
        '''
        PixbufButton.__init__(self, *args, **kwargs)
        OptionsWidget.__init__(self, *args, **kwargs)

        # initialise some variables
        self.image_display = False
        self.initialised = False

    def update_current_key(self):
        # update the current image and tooltip
        self.set_image(self._controller.get_current_image())
        self.set_tooltip_text(self._controller.get_current_description())

    def do_clicked(self):
        if self._controller:
            index = self._controller.get_current_key_index()
            index = (index + 1) % len(self._controller.options)

            # inform the controller
            self._controller.option_selected(
                self._controller.options[index])


class SearchEntry(RB.SearchEntry, OptionsPopupWidget):
    __gtype_name__ = "AlbumSearchEntry"

    # signals
    __gsignals__ = {
        'item-clicked': (GObject.SIGNAL_RUN_LAST, None, (str,))
        }

    def __init__(self, *args, **kwargs):
        RB.SearchEntry.__init__(self, *args, **kwargs)
        OptionsPopupWidget.__init__(self, *args, **kwargs)

    @OptionsPopupWidget.controller.setter
    def controller(self, controller):
        if self._controller:
            # disconnect signals
            self._controller.disconnect(self._search_text_changed_id)

        OptionsPopupWidget.controller.fset(self, controller)

        # connect signals
        self._search_text_changed_id = self._controller.connect(
            'notify::search-text', self._update_search_text)

        # update the current text
        self._update_search_text()

    def _update_search_text(self, *args):
        self.set_text(self._controller.search_text)

    def update_current_key(self):
        super(SearchEntry, self).update_current_key()

        self.set_placeholder(self._controller.get_current_description())

    def do_show_popup(self):
        '''
        Callback called by the search entry when the magnifier is clicked.
        It prompts the user through a popup to select a filter type.
        '''
        self.show_popup()

    def do_search(self, text):
        '''
        Callback called by the search entry when a new search must
        be performed.
        '''
        if self._controller:
            self._controller.do_search(text)
