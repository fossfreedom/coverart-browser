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

from coverart_external_plugins import CreateExternalPluginMenu
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import GdkPixbuf
from gi.repository import RB

from coverart_browser_prefs import GSetting
from coverart_album import Cover
from coverart_album import Album
from coverart_widgets import AbstractView
from coverart_utils import SortedCollection
from coverart_widgets import PanedCollapsible
from coverart_toolbar import ToolbarObject
import rb

from collections import namedtuple

class Artist(GObject.Object):
    '''
    An album. It's conformed from one or more tracks, and many of it's
    information is deduced from them.

    :param name: `str` name of the artist.
    :param cover: `Cover` cover for this artist.
    '''
    # signals
    __gsignals__ = {
        'modified': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'emptied': (GObject.SIGNAL_RUN_LAST, None, ()),
        'cover-updated': (GObject.SIGNAL_RUN_LAST, None, ())
        }

    __hash__ = GObject.__hash__
    
    def __init__(self, name, cover):
        super(Artist, self).__init__()

        self.name = name
        self._cover = None
        self.cover = cover

        self._signals_id = {}

    @property
    def cover(self):
        return self._cover

    @cover.setter
    def cover(self, new_cover):
        if self._cover:
            self._cover.disconnect(self._cover_resized_id)

        self._cover = new_cover
        self._cover_resized_id = self._cover.connect('resized',
            lambda *args: self.emit('cover-updated'))

        self.emit('cover-updated')

class ArtistsModel(GObject.Object):
    '''
    Model that contains artists, keeps them sorted, filtered and provides an
    external `Gtk.TreeModel` interface to use as part of a Gtk interface.

    The `Gtk.TreeModel` haves the following structure:
    column 0 -> string containing the artist name
    column 1 -> pixbuf of the artist's cover.
    column 2 -> instance of the artist or album itself.
    column 3 -> boolean that indicates if the row should be shown
    '''
    # signals
    __gsignals__ = {
        'update-path': (GObject.SIGNAL_RUN_LAST, None, (object,))
        }

    # list of columns names and positions on the TreeModel
    columns = {'tooltip': 0, 'pixbuf': 1, 'artist_album': 2, 'show': 3, 'empty': 4}

    def __init__(self, album_manager):
        super(ArtistsModel, self).__init__()

        self._connect_signals()
        self.album_manager = album_manager
        self._iters = {}
        self._artists = SortedCollection(
            key=lambda artist: getattr(artist, 'name'))

        self._tree_store = Gtk.TreeStore(str, GdkPixbuf.Pixbuf, object, 
            bool,  str)
            
        # filters
        self._filters = {}

        # sorting idle call
        self._sort_process = None

        # create the filtered store that's used with the view
        self._filtered_store = self._tree_store.filter_new()
        self._filtered_store.set_visible_column(ArtistsModel.columns['show'])
        
        self._tree_sort = Gtk.TreeModelSort(model=self._filtered_store)            
        self._tree_sort.set_sort_func(0, self._compare, None)

    def _connect_signals(self):
        self.connect('update-path', self._on_update_path)
        
    def _compare(self, model, row1, row2, user_data):
        sort_column = 0
        
        #if sort_column:
        value1 = RB.search_fold(model.get_value(row1, sort_column))
        value2 = RB.search_fold(model.get_value(row2, sort_column))
        if value1 < value2:
            return -1
        elif value1 == value2:
            return 0
        else:
            return 1
        
    @property
    def store(self):
        #return self._filtered_store
        return self._tree_sort

    def add(self, artist):
        '''
        Add an artist to the model.

        :param artist: `Artist` to be added to the model.
        '''
        # generate necessary values
        values = self._generate_artist_values(artist)
        # insert the values
        pos = self._artists.insert(artist)
        tree_iter = self._tree_store.insert(None,pos, values)
        child_iter = self._tree_store.insert(tree_iter, pos, values) # dummy child row so that the expand is available
        if not artist.name in self._iters:
            self._iters[artist.name] = {}
        self._iters[artist.name] = {'artist_album': artist,
            'iter': tree_iter, 'dummy_iter': child_iter}
        return tree_iter
        
    def _on_update_path(self, widget, treepath):
        '''
        Add an album to the artist in the model.

        :param artist: `Artist` for the album to be added to (i.e. the parent)
        :param album: `Album` is the child of the Artist
        
        '''
        artist = self.get_from_path(treepath)
        albums = self.album_manager.model.get_all()
        # get the artist iter
        artist_iter = self._iters[artist.name]['iter']
        
        # now remove the dummy_iter - if this fails, we've removed this 
        # before and have no need to add albums
        
        if 'dummy_iter' in self._iters[artist.name]:
            self._iters[artist.name]['album'] = []
            for album in albums:
                if RB.search_fold(artist.name) in RB.search_fold(album.artists):
                    # generate necessary values
                    values = self._generate_album_values(album)
                    # insert the values
                    tree_iter = self._tree_store.append(artist_iter, values)
                    self._iters[artist.name]['album'].append(tree_iter)
                    
            self._tree_store.remove(self._iters[artist.name]['dummy_iter'])
            del self._iters[artist.name]['dummy_iter']
            
    def _generate_artist_values(self, artist):
        tooltip = artist.name
        pixbuf = artist.cover.pixbuf.scale_simple(48,48,GdkPixbuf.InterpType.BILINEAR)
        hidden = self._artist_filter(artist)

        return tooltip, pixbuf, artist, hidden, ''
    
    def _generate_album_values(self, album):
        tooltip = album.name
        pixbuf = album.cover.pixbuf.scale_simple(48,48,GdkPixbuf.InterpType.BILINEAR)
        hidden = True

        return tooltip, pixbuf, album, hidden, ''

    def remove(self, artist):
        '''
        Removes this album from the model.

        :param artist: `Artist` to be removed from the model.
        '''
        self._artists.remove(artist)
        self._tree_store.remove(self._iters[artist.name]['iter'])

        del self._iters[artist.name]

    def contains(self, artist_name):
        '''
        Indicates if the model contains a specific artist.

        :param artist_name: `str` name of the artist.
        '''
        return artist_name in self._iters

    def get(self, artist_name):
        '''
        Returns the requested artist.

        :param artist_name: `str` name of the artist.
        '''
        return self._iters[artist]['artist_album']
        
    def get_from_path(self, path):
        '''
        Returns the Artist or Album referenced by a `Gtk.TreeModel` path.

        :param path: `Gtk.TreePath` referencing the artist.
        '''
        return self._filtered_store[path][self.columns['artist_album']]

    def get_path(self, artist):
        return self._filtered_store.convert_child_path_to_path(
            self._tree_store.get_path(
                self._iters[artist.name]['iter']))

    def show(self, artist, show):
        '''
        Unfilters an artist, making it visible to the publicly available model's
        `Gtk.TreeModel`

        :param artist: `Artist` to show or hide.
        :param show: `bool` indcating whether to show(True) or hide(False) the
            album.
        '''
        artist_iter = self._iters[artist.name]['iter']

        if self._tree_store.iter_is_valid(artist_iter):
            self._tree_store.set_value(artist_iter, self.columns['show'], show)

    def _artist_filter(self, artist):
            for f in list(self._filters.values()):
                if not f(artist):
                    return False

            return True

class ArtistCellRenderer(Gtk.CellRendererPixbuf):
    
    def __init__(self):
        super(ArtistCellRenderer, self).__init__()
        
    def do_render(self, cr, widget,  
                background_area,
                cell_area,
                flags):
        
        newpix = self.props.pixbuf #.copy()
        #newpix = newpix.scale_simple(48,48,GdkPixbuf.InterpType.BILINEAR)
        
        Gdk.cairo_set_source_pixbuf(cr, newpix, 0, 0)
        cr.paint()
    
class ArtistLoader(GObject.Object):
    '''
    Loads Artists - updating the model accordingly.

    :param artistmanager: `ArtistManager` responsible for this loader.
    '''
    # signals
    __gsignals__ = {
        'albums-load-finished': (GObject.SIGNAL_RUN_LAST, None, (object,)),
        'model-load-finished': (GObject.SIGNAL_RUN_LAST, None, ())
        }

    def __init__(self, artistmanager):
        super(ArtistLoader, self).__init__()

        self.shell = artistmanager.shell
        self._connect_signals()
        
        self.cover_size = 128
        
        self.unknown_cover = Cover(self.cover_size, 
            rb.find_plugin_file(artistmanager.plugin, 'img/microphone.png'))
        self.model = artistmanager.model
    
        artist_pview = None
        for view in self.shell.props.library_source.get_property_views():
            if view.props.title == _("Artist"):
                artist_pview = view
                break

        assert artist_pview, "cannot find artist property view"

        for row in artist_pview.get_model():
            if row[0] != _('All'):
                self.model.add(Artist(row[0], self.unknown_cover))
        
    def _connect_signals(self):
        # connect signals for updating the albums
        #self.entry_changed_id = self._album_manager.db.connect('entry-changed',
        #    self._entry_changed_callback)
        pass
        
class ArtistManager(GObject.Object):
    '''
    Main construction that glues together the different managers, the loader
    and the model. It takes care of initializing all the system.

    :param plugin: `Peas.PluginInfo` instance.
    :param current_view: `ArtistView` where the Artists are shown.
    '''
    # singleton instance
    instance = None

    # properties
    progress = GObject.property(type=float, default=0)
    
    def __init__(self, plugin, current_view, shell):
        super(ArtistManager, self).__init__()

        self.current_view = current_view
        self.db = plugin.shell.props.db
        self.shell = shell
        self.plugin = plugin

        self.model = ArtistsModel(current_view.album_manager)
        self._loader = ArtistLoader(self)
        # connect signals
        self._connect_signals()

    def _connect_signals(self):
        '''
        Connects the manager to all the needed signals for it to work.
        '''
        # connect signal to the loader so it shows the albums when it finishes
        pass

class ArtistShowingPolicy(GObject.Object):
    '''
    Policy that mostly takes care of how and when things should be showed on
    the view that makes use of the `AlbumsModel`.
    '''

    def __init__(self, flow_view):
        super(ArtistShowingPolicy, self).__init__()

        self._flow_view = flow_view
        self.counter = 0
        self._has_initialised = False

    def initialise(self, album_manager):
        if self._has_initialised:
            return

        self._has_initialised = True
        self._album_manager = album_manager
        self._model = album_manager.model
        
class ArtistView(Gtk.TreeView, AbstractView):
    __gtype_name__ = "ArtistView"

    name = 'artistview'
    icon_automatic = GObject.property(type=bool, default=True)
    panedposition = PanedCollapsible.Paned.COLLAPSE
    
    __gsignals__ = {
        'update-toolbar': (GObject.SIGNAL_RUN_LAST, None, ())
        }
    

    def __init__(self, *args, **kwargs):
        super(ArtistView, self).__init__(*args, **kwargs)
        
        self.ext_menu_pos = 0
        self._external_plugins = None
        self.gs = GSetting()
        self.show_policy = ArtistShowingPolicy(self)
        self.view = self
        self._has_initialised = False        
            
    def initialise(self, source):
        if self._has_initialised:
            return
            
        self._has_initialised = True

        self.view_name = "artist_view"
        super(ArtistView, self).initialise(source)
        #self.source = source
        self.album_manager = source.album_manager
        #self.plugin = source.plugin
        self.shell = source.shell
        self.ext_menu_pos = 6
        
        self.set_enable_tree_lines(True)
        #self.set_grid_lines(Gtk.TreeViewGridLines.BOTH)

        pixbuf = Gtk.CellRendererPixbuf()
        #pixbuf.set_fixed_size(48,48)
        col = Gtk.TreeViewColumn('', pixbuf, pixbuf=1)
        #col.set_cell_data_func(pixbuf, self._pixbuf_func, None)

        self.append_column(col)
        
        col = Gtk.TreeViewColumn(_('Track Artist'), Gtk.CellRendererText(), text=0)
        col.set_sort_column_id(0)
        col.set_sort_indicator(True)
        self.append_column(col)
        col = Gtk.TreeViewColumn('', Gtk.CellRendererText(), text=4)
        self.append_column(col) # dummy column to expand horizontally
        
        self.artistmanager = ArtistManager(self.plugin, self, self.shell)
        self.set_model(self.artistmanager.model.store)
        
        self._connect_properties()
        self._connect_signals()
        
    def _pixbuf_func(self, col, cell, tree_model, tree_iter, data):
        #new_pix = cell.props.pixbuf.copy()
        #cell.props.pixbuf = new_pix.scale_simple(48,48,GdkPixbuf.InterpType.BILINEAR)
        cell.props.pixbuf = tree_model.get_value(tree_iter, 1).scale_simple(48,48,GdkPixbuf.InterpType.BILINEAR)
        
    def _connect_properties(self):
        setting = self.gs.get_setting(self.gs.Path.PLUGIN)
        setting.bind(self.gs.PluginKey.ICON_AUTOMATIC, self,
            'icon_automatic', Gio.SettingsBindFlags.GET)
        
    def _connect_signals(self):
        self.connect('row-activated', self._row_activated)
        self.connect('row-expanded', self._row_expanded)
        self.connect('button-press-event', self._row_click)
        self.get_selection().connect('changed', self._selection_changed)
        
    def _row_expanded(self, treeview, treeiter, treepath):
        '''
        event called when clicking the expand icon on the treeview
        '''
        self._row_activated(treeview, treepath, _)
        
    def _row_activated(self, treeview, treepath, treeviewcolumn):
        '''
        event called when double clicking on the tree-view or by keyboard ENTER
        '''
        active_object = self.artistmanager.model.get_from_path(treepath)
        if isinstance(active_object, Artist):
            self.artistmanager.model.emit('update-path', treepath)
            self.expand_row(treepath, False)
        else:
            #we need to play this album
            self.source.play_selected_album(self.source.favourites)
            
    def _row_click(self, widget, event):
        '''
        event called when clicking on a row
        '''
        
        treepath, treecolumn, cellx, celly = self.get_path_at_pos(event.x, event.y)
        active_object = self.artistmanager.model.get_from_path(treepath)
            
        if event.button == 1 and isinstance(active_object, Album):
            # on click
                    
            # to expand the entry view
            ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
            shift = event.state & Gdk.ModifierType.SHIFT_MASK

            if self.icon_automatic:
                self.source.click_count += 1 if not ctrl and not shift else 0

            if self.source.click_count == 1:
                Gdk.threads_add_timeout(GLib.PRIORITY_DEFAULT_IDLE, 250,
                    self.source.show_hide_pane, active_object)
            
    def get_view_icon_name(self):
        return "artistview.png"
        
    def _selection_changed(self, *args):
        self.source.update_with_selection()

    def get_selected_objects(self):
        '''
        finds what has been selected

        returns an array of `Album`
        '''
        selection = self.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter:
            active_object = model.get_value(treeiter,ArtistsModel.columns['artist_album'])
            if isinstance(active_object, Album):
                return [active_object]
        
        return []
        
    def switch_to_view(self, source, album):
        self.initialise(source)
        self.show_policy.initialise(source.album_manager)
        
        
        #if album:
        #    path = source.album_manager.model.get_path(album)
        #    self.select_and_scroll_to_path(path)
        
    def do_update_toolbar(self, *args):
        self.source.toolbar_manager.set_enabled(False, ToolbarObject.SORT_BY)
        self.source.toolbar_manager.set_enabled(False, ToolbarObject.SORT_ORDER)
        
