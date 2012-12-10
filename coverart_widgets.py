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

    _first_menu_item = None
    _current_val = None

    def __init__(self, **kargs):
        '''
        Initializes the button.
        '''
        super(PopupButton, self).__init__(
            **kargs)

        self._builder = Gtk.Builder()
        self._builder.add_from_string(ui_string)

        self._popup_menu = self._builder.get_object('popupbutton_menu')
        self._actiongroup = Gtk.ActionGroup((self.__gtype_name__ + "menu"))

    def initialise(self, shell, callback):
        '''
        initialise - derived objects call this first
        shell = rhythmbox shell
        callback = function to call when a menuitem is selected
        '''
        self.shell = shell
        self.callback = callback
        self.set_popup_value(self.get_initial_label())

    def clear_popupmenu(self):
        '''
        reinitialises/clears the current popup menu and associated actions
        '''
        for menu_item in self._popup_menu:
            self._popup_menu.remove(menu_item)

            self._popup_menu.show_all()
            self.shell.props.ui_manager.ensure_update()

        for action in self._actiongroup.list_actions():
            self._actiongroup.remove_action(action)
            
        self._first_menu_item = None

    def add_menuitem(self, label, func, val):
        '''
        add a new menu item to the popup
        '''
        #if not self._first_menu_item:
        #    new_menu_item = Gtk.RadioMenuItem(label=label)            
        #    self._first_menu_item = new_menu_item
        #else:
        #    new_menu_item=Gtk.RadioMenuItem.new_with_label_from_widget(
        #        group=self._first_menu_item, label=label)
        new_menu_item = Gtk.MenuItem(label=label)

        #if label== self._current_val:
        #    new_menu_item.set_active(True)

        action = Gtk.Action(label=label, name=label,
                       tooltip='', stock_id=Gtk.STOCK_APPLY)
        action.connect('activate', func, val)
        new_menu_item.set_related_action(action)
        self._popup_menu.append(new_menu_item)
        self._actiongroup.add_action(action)

    def show_popup(self):
        '''
        show the current popup menu
        '''
        self._popup_menu.show_all()
        self.shell.props.ui_manager.ensure_update()
    
        self._popup_menu.popup(None, None, None, None, 0,
            Gtk.get_current_event_time())

    def set_popup_value(self, val):
        '''
        set the tooltip according to the popup menu chosen
        '''
        if not val:
            val = self.get_initial_label()
        
        self.set_tooltip_text(val)
        self._current_val = val

    def set_initial_label(self, val):
        '''
        all popup's should have a default initial value
        '''
        self._initial_label = val

    def get_initial_label(self):
        '''
        get the first initial value stored in a popup
        '''
        return self._initial_label

    def resize_button_image(self):
        '''
        if the button contains an image rather than stock icon
        this function will ensure the image is resized correctly to
        fit the button style
        '''

        what, width, height = Gtk.icon_size_lookup(Gtk.IconSize.BUTTON)
        image = self.get_image()

        pixbuf = image.get_pixbuf().scale_simple(width, height,
                 GdkPixbuf.InterpType.BILINEAR)

        image.set_from_pixbuf(pixbuf)

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

        self.set_initial_label(_("Music"))

    def do_clicked(self):
        '''
        when button is clicked, update the popup with current playlists
        before displaying the popup
        '''
        playlist_manager = self.shell.props.playlist_manager
        playlists_entries = playlist_manager.get_playlists()

        self.clear_popupmenu()
        self.add_menuitem(self.get_initial_label(),
            self._change_playlist_source, None)

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
            
        try:
            model = playlist.get_query_model()
            self.set_popup_value(playlist.props.name)
            print "here %s" % playlist.props.name
        except:
            model = None
            self.set_popup_value(self.get_initial_label())
            print "no here"

        self.callback(model)


class GenrePopupButton(PopupButton):
    __gtype_name__ = 'GenrePopupButton'

    def __init__(self, **kargs):
        '''
        Initializes the button.
        '''
        super(GenrePopupButton, self).__init__(
            **kargs)

    def initialise(self, shell, callback):
        '''
        extend the default initialise function
        because we need to also resize the picture
        associated with the genre button
        '''
        self.shell = shell

        # seems like view [0] is the genre property view
        model = self.shell.props.library_source.get_property_views()[0].\
            get_model()

        self._genres = []

        for genre in model:
            self._genres.append(genre[0])

        self.set_initial_label(self._genres[0])

        super(GenrePopupButton, self).initialise(shell, callback)

        self.resize_button_image()

    def do_clicked(self):
        '''
        when button is clicked, update the popup with current genres
        before displaying the popup
        '''
        self.clear_popupmenu()

        for entry in self._genres:
            self.add_menuitem(entry, self._genre_changed, entry)

        self.show_popup()

    def _genre_changed(self, menu, genre):
        '''
        called when genre popup menu item chosen
        return None if the first entry in popup returned
        '''
        self.set_popup_value(genre)

        if genre == self.get_initial_label():
            self.callback(None)
        else:
            self.callback(genre)


class SortPopupButton(PopupButton):
    __gtype_name__ = 'SortPopupButton'

    sorts = {'name': _('Sort by album name'),
        'album_artist': _('Sort by album artist'),
        'year': _('Sort by year'),
        'rating': _('Sort by rating')}

    sort_by = GObject.property(type=str)

    def __init__(self, **kargs):
        '''
        Initializes the button.
        '''
        super(SortPopupButton, self).__init__(
            **kargs)

        self.set_initial_label(self.sorts['name'])

    def initialise(self, shell, callback):
        '''
        extend the default initialise function
        because we need to also resize the picture
        associated with the sort button as well as find the
        saved sort order
        '''
        super(SortPopupButton, self).initialise(shell, callback)
        self.resize_button_image()

        # create the pop up menu
        for key, text in sorted(self.sorts.iteritems()):
            self.add_menuitem(text, self._sort_changed, key)

        gs = GSetting()
        source_settings = gs.get_setting(gs.Path.PLUGIN)
        source_settings.bind(gs.PluginKey.SORT_BY,
            self, 'sort_by', Gio.SettingsBindFlags.DEFAULT)
        #self.sort_by = 'album_artist'
        self._sort_changed(None, self.sort_by)

    def do_clicked(self):
        '''
        when button is clicked, update the popup with the sorting options
        before displaying the popup
        '''
        self.show_popup()

    def _sort_changed(self, menu, sort):
        '''
        called when sort popup menu item chosen
        '''
        self.set_popup_value(self.sorts[sort])
        self.sort_by = sort
        self.callback(sort)
