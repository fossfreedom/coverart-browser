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
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject

import rb


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
    __gtype_name__ = "SearchEntry"

    # signals
    __gsignals__ = {
        'item-clicked': (GObject.SIGNAL_RUN_LAST, None, (str,))
        }

    def __init__(self, *args, **kwargs):
        RB.SearchEntry.__init__(self, *args, **kwargs)
        OptionsPopupWidget.__init__(self)

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


class QuickSearchEntry(Gtk.Frame):
    __gtype_name__ = "QuickSearchEntry"

    # signals
    __gsignals__ = {
        'quick-search': (GObject.SIGNAL_RUN_LAST, None, (str,)),
        'arrow-pressed': (GObject.SIGNAL_RUN_LAST, None, (object,))
        }

    def __init__(self, *args, **kwargs):
        super(QuickSearchEntry, self).__init__(*args, **kwargs)
        self._idle = 0

        # text entry for the quick search input
        text_entry = Gtk.Entry(halign='center', valign='center',
            margin=5)

        self.add(text_entry)

        self.connect_signals(text_entry)

    def get_text(self):
        return self.get_child().get_text()

    def set_text(self, text):
        self.get_child().set_text(text)

    def connect_signals(self, text_entry):
        text_entry.connect('changed', self._on_quick_search)
        text_entry.connect('focus-out-event', self._on_focus_lost)
        text_entry.connect('key-press-event', self._on_key_pressed)

    def _hide_quick_search(self):
        self.hide()

    def _add_hide_on_timeout(self):
        self._idle += 1

        def hide_on_timeout(*args):
            self._idle -= 1

            if not self._idle:
                self._hide_quick_search()

            return False

        Gdk.threads_add_timeout_seconds(GLib.PRIORITY_DEFAULT_IDLE, 4,
            hide_on_timeout, None)

    def do_parent_set(self, old_parent, *args):
        if old_parent:
            old_parent.disconnect(self._on_parent_key_press_id)

        parent = self.get_parent()
        self._on_parent_key_press_id = parent.connect('key-press-event',
            self._on_parent_key_press, self.get_child())

    def _on_parent_key_press(self, parent, event, entry):
        if not self.get_visible() and \
            event.keyval not in [Gdk.KEY_Shift_L, Gdk.KEY_Shift_R,
            Gdk.KEY_Control_L, Gdk.KEY_Control_R, Gdk.KEY_Escape]:
            # grab focus, redirect the pressed key and make the quick search
            # entry visible
            entry.set_text('')
            entry.grab_focus()
            entry.im_context_filter_keypress(event)
            self.show_all()

        elif self.get_visible() and event.keyval == Gdk.KEY_Escape:
            self._hide_quick_search()

        return False

    def _on_quick_search(self, entry, *args):
        if entry.get_visible():
            # emit the quick-search signal
            search_text = entry.get_text()
            self.emit('quick-search', search_text)

            # add a timeout to hide the search entry
            self._add_hide_on_timeout()

    def _on_focus_lost(self, entry, *args):
        self._hide_quick_search()

        return False

    def _on_key_pressed(self, entry, event, *args):
        arrow = event.keyval in [Gdk.KEY_Up, Gdk.KEY_Down]

        if arrow:
            self.emit('arrow-pressed', event.keyval)
            self._add_hide_on_timeout()

        return arrow


class EnhancedIconView(Gtk.IconView):
    __gtype_name__ = "EnhancedIconView"

    object_column = GObject.property(type=int, default=-1)

    def __init__(self, *args, **kwargs):
        super(EnhancedIconView, self).__init__(*args, **kwargs)

        self._last_width = 0
        self._popup = None

    @property
    def popup(self):
        return self._popup

    @popup.setter
    def popup(self, popup):
        self._popup = popup

    def do_size_allocate(self, *args):
        width = self.get_allocated_width()

        if width != self.last_width:
            # don't need to reacommodate if the bottom pane is being resized
            self.covers_view.set_columns(0)
            self.covers_view.set_columns(-1)

            # update width
            self.last_width = width

    def do_button_press_event(self, event):
        x = int(event.x)
        y = int(event.y)
        current_path = self.get_path_at_pos(x, y)

        if event.type is Gdk.EventType.BUTTON_PRESS and current_path and \
            event.triggers_context_menu():
            # if the item being clicked isn't selected, we should clear
            # the current selection
            if len(self.get_selected_objects()) > 0 and \
                not self.path_is_selected(current_path):
                self.unselect_all()

            self.select_path(current_path)
            self.set_cursor(current_path, None, False)

            if self.popup:
                self.popup_menu.popup(None, None, None, None, event.button,
                    event.time)

    def get_selected_objects(self):
        selected_items = self.get_selected_items()

        if not self.object_column:
            # if no object_column is setted, return the selected rows
            return selected_items

        selected_objects = []

        for selected in selected_items:
            selected_objects.append(self.model[selected][self.object_column])

        return selected_objects


class ProxyPopupButton(Gtk.Frame):
    __gtype_name__ = "ProxyPopupButton"

    def __init__(self, *args, **kwargs):
        super(ProxyPopupButton, self).__init__(*args, **kwargs)
        self._delegate = None

    @property
    def controller(self):
        if self._delegate:
            return self._delegate.controller

    @controller.setter
    def controller(self, controller):
        if self._delegate:
            self.remove(self._delegate)

        if len(controller.options) < 12:
            self._delegate = PopupButton()
        else:
            self._delegate = ListViewButton()

        self._delegate.set_visible(True)
        self._delegate.set_relief(Gtk.ReliefStyle.HALF)
        self._delegate.set_has_tooltip(True)

        self._delegate.controller = controller
        self.add(self._delegate)

class OptionsListViewWidget(OptionsWidget):

    # signals
    __gsignals__ = {
        'item-clicked': (GObject.SIGNAL_RUN_LAST, None, (str,))
        }

    def __init__(self, *args, **kwargs):
        OptionsWidget.__init__(self, *args, **kwargs)

    @OptionsWidget.controller.setter
    def controller(self, controller):
        ui = Gtk.Builder()
        ui.add_from_file(rb.find_plugin_file(controller.plugin,
            'ui/coverart_listwindow.ui'))
        ui.connect_signals(self)
        self._listwindow = ui.get_object('listwindow')
        self._liststore = ui.get_object('liststore')
        self._listwindow.set_size_request(200, 200)
        self._treeview = ui.get_object('treeview')

        # hide the listwindow instead of destroying it
        self._listwindow.hide_on_delete()

        OptionsWidget.controller.fset(self, controller)

    def update_options(self):
        self.clear_options()
        self.add_options(self._controller.options)

    def update_current_key(self):
        self.select(self.controller.get_current_key_index())

    def do_item_clicked(self, key):
        if self._controller:
            # inform the controller
            self._controller.option_selected(key)

    def show_popup(self):
        '''
        show the listview window
        '''
        self._listwindow.show_all()

    def clear_options(self):
        self._liststore.clear()

    def add_options(self, iterable):
        for label in iterable:
            self._liststore.append((label,))

    def select(self, index):
        self._treeview.get_selection().select_iter(self._liststore[index].iter)
        self._treeview.scroll_to_cell(self._liststore[index].path)

    def view_changed(self, view):
        try:
            liststore, viewiter = view.get_selected()
            label = liststore.get_value(viewiter, 0)
            self.emit('item-clicked', label)
        except:
            pass

        self._listwindow.hide()

    def on_cancel(self, *args):
        self._listwindow.hide()
        return True

    def do_delete_thyself(self):
        self.clear_list()
        del self._listwindow

class ListViewButton(PixbufButton, OptionsListViewWidget):
    __gtype_name__ = "ListViewButton"

    # signals
    __gsignals__ = {
        'item-clicked': (GObject.SIGNAL_RUN_LAST, None, (str,))
        }

    def __init__(self, *args, **kwargs):
        '''
        Initializes the button.
        '''
        PixbufButton.__init__(self, *args, **kwargs)
        OptionsListViewWidget.__init__(self, *args, **kwargs)

    def update_current_key(self):
        super(ListViewButton, self).update_current_key()

        # update the current image and tooltip
        self.set_image(self._controller.get_current_image())
        self.set_tooltip_text(self._controller.get_current_description())

    def do_clicked(self):
        '''
        when button is clicked, update the popup with the sorting options
        before displaying the popup
        '''
        self.show_popup()
