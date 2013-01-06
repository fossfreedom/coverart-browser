# -*- Mode: python; coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
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

from bisect import bisect_left, bisect_right
from gi.repository import GdkPixbuf
from gi.repository import Gdk
from gi.repository import GLib
import xml.etree.cElementTree as ET
import rb
import re


class NaturalString(str):
    '''
    this class implements an object that can naturally compare
    strings
    i.e. "15 album" < "100 album"
    '''

    def __init__(self, string):
        super(NaturalString, self).__init__(
            string)
        convert = lambda text: int(text) if text.isdigit() else text.lower()
        alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)',
            key)]

        self._string_elements = alphanum_key(string)

    def __lt__(self, other):
        if type(other) is str:
            return super(NaturalString, self).__lt__(other)
        else:
            return self._string_elements < other._string_elements

    def __le__(self, other):
        if type(other) is str:
            return super(NaturalString, self).__le__(other)
        else:
            return self._string_elements <= other._string_elements

    def __gt__(self, other):
        if type(other) is str:
            return super(NaturalString, self).__gt__(other)
        else:
            return self._string_elements > other._string_elements

    def __ge__(self, other):
        if type(other) is str:
            return super(NaturalString, self).__ge__(other)
        else:
            return self._string_elements >= other._string_elements


class SortedCollection(object):
    '''Sequence sorted by a key function.

    SortedCollection() is much easier to work with than using bisect() directly.
    It supports key functions like those use in sorted(), min(), and max().
    The result of the key function call is saved so that keys can be searched
    efficiently.

    Instead of returning an insertion-point which can be hard to interpret, the
    five find-methods return a specific item in the sequence. They can scan for
    exact matches, the last item less-than-or-equal to a key, or the first item
    greater-than-or-equal to a key.

    Once found, an item's ordinal position can be located with the index() method.
    New items can be added with the insert() and insert_right() methods.
    Old items can be deleted with the remove() method.

    The usual sequence methods are provided to support indexing, slicing,
    length lookup, clearing, copying, forward and reverse iteration, contains
    checking, item counts, item removal, and a nice looking repr.

    Finding and indexing are O(log n) operations while iteration and insertion
    are O(n).  The initial sort is O(n log n).

    The key function is stored in the 'key' attibute for easy introspection or
    so that you can assign a new key function (triggering an automatic re-sort).

    In short, the class was designed to handle all of the common use cases for
    bisect but with a simpler API and support for key functions.

    >>> from pprint import pprint
    >>> from operator import itemgetter

    >>> s = SortedCollection(key=itemgetter(2))
    >>> for record in [
    ...         ('roger', 'young', 30),
    ...         ('angela', 'jones', 28),
    ...         ('bill', 'smith', 22),
    ...         ('david', 'thomas', 32)]:
    ...     s.insert(record)

    >>> pprint(list(s))         # show records sorted by age
    [('bill', 'smith', 22),
     ('angela', 'jones', 28),
     ('roger', 'young', 30),
     ('david', 'thomas', 32)]

    >>> s.find_le(29)           # find oldest person aged 29 or younger
    ('angela', 'jones', 28)
    >>> s.find_lt(28)           # find oldest person under 28
    ('bill', 'smith', 22)
    >>> s.find_gt(28)           # find youngest person over 28
    ('roger', 'young', 30)

    >>> r = s.find_ge(32)       # find youngest person aged 32 or older
    >>> s.index(r)              # get the index of their record
    3
    >>> s[3]                    # fetch the record at that index
    ('david', 'thomas', 32)

    >>> s.key = itemgetter(0)   # now sort by first name
    >>> pprint(list(s))
    [('angela', 'jones', 28),
     ('bill', 'smith', 22),
     ('david', 'thomas', 32),
     ('roger', 'young', 30)]

    '''

    def __init__(self, iterable=(), key=None):
        self._given_key = key
        key = (lambda x: x) if key is None else key
        decorated = sorted((key(item), item) for item in iterable)
        self._keys = [k for k, item in decorated]
        self._items = [item for k, item in decorated]
        self._key = key

    def _getkey(self):
        return self._key

    def _setkey(self, key):
        if key is not self._key:
            self.__init__(self._items, key=key)

    def _delkey(self):
        self._setkey(None)

    key = property(_getkey, _setkey, _delkey, 'key function')

    def clear(self):
        self.__init__([], self._key)

    def copy(self):
        return self.__class__(self, self._key)

    def __len__(self):
        return len(self._items)

    def __getitem__(self, i):
        return self._items[i]

    def __iter__(self):
        return iter(self._items)

    def __reversed__(self):
        return ReversedSortedCollection(self)

    def __repr__(self):
        return '%s(%r, key=%s)' % (
            self.__class__.__name__,
            self._items,
            getattr(self._given_key, '__name__', repr(self._given_key))
        )

    def __reduce__(self):
        return self.__class__, (self._items, self._given_key)

    def __contains__(self, item):
        k = self._key(item)
        i = bisect_left(self._keys, k)
        j = bisect_right(self._keys, k)
        return item in self._items[i:j]

    def index(self, item):
        'Find the position of an item.  Raise ValueError if not found.'
        k = self._key(item)
        i = bisect_left(self._keys, k)
        j = bisect_right(self._keys, k)
        return self._items[i:j].index(item) + i

    def count(self, item):
        'Return number of occurrences of item'
        k = self._key(item)
        i = bisect_left(self._keys, k)
        j = bisect_right(self._keys, k)
        return self._items[i:j].count(item)

    def insert(self, item):
        'Insert a new item.  If equal keys are found, add to the left'
        k = self._key(item)
        i = bisect_left(self._keys, k)
        self._keys.insert(i, k)
        self._items.insert(i, item)

        return i

    def reorder(self, item):
        '''Reorder an item. If its key changed, then the item is
        repositioned, otherwise the item stays untouched'''
        index = self._items.index(item)
        new_index = -1

        if self._keys[index] != self._key(item):
            del self._keys[index]
            del self._items[index]

            new_index = self.insert(item)

        return new_index

    def insert_all(self, items):
        for item in items:
            self.insert(item)

    def remove(self, item):
        'Remove first occurence of item.  Raise ValueError if not found'
        i = self.index(item)
        del self._keys[i]
        del self._items[i]


class ReversedSortedCollection(object):

    def __init__(self, sorted_collection):
        self._sorted_collection = sorted_collection

    def __getattr__(self, name):
        return getattr(self._sorted_collection, name)

    def copy(self):
        return self.__class__(self._sorted_collection)

    def _getkey(self):
        return self._key

    def _setkey(self, key):
        if key is not self._key:
            self.__init__(SortedCollection(self._items, key=key))

    def _delkey(self):
        self._setkey(None)

    key = property(_getkey, _setkey, _delkey, 'key function')

    def __len__(self):
        return len(self._sorted_collection)

    def __getitem__(self, i):
        return self._items[len(self) - i - 1]

    def __iter__(self):
        return iter(reversed(self._items))

    def __reversed__(self):
        return self._sorted_collection

    def __repr__(self):
        return '%s(%r, key=%s)' % (
            self.__class__.__name__,
            reversed(self._items),
            getattr(self._given_key, '__name__', repr(self._given_key))
        )

    def __reduce__(self):
        return self.__class__, (reversed(self._items), self._given_key)

    def insert(self, item):
        'Insert a new item.  If equal keys are found, add to the left'
        i = self._sorted_collection.insert(item)

        return len(self) - i - 1

    def index(self, item):
        'Find the position of an item.  Raise ValueError if not found.'
        return len(self) - self._sorted_collection.index(item) - 1


class IdleCallIterator(object):

    def __init__(self, chunk, process, after=None, error=None, finish=None):
        default = lambda *_: None

        self._chunk = chunk
        self._process = process
        self._after = after if after else default
        self._error = error if error else default
        self._finish = finish if finish else default
        self._stop = False

    def __call__(self, iterator, **data):
        self._iter = iterator

        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, self._idle_call, data)

    def _idle_call(self, data):
        if self._stop:
            return False

        for i in range(self._chunk):
            try:
                next_elem = self._iter.next()

                self._process(next_elem, data)
            except StopIteration:
                self._finish(data)
                return False
            except Exception as e:
                self._error(e)

        self._after(data)

        return True

    def stop(self):
        self._stop = True


def idle_iterator(func):
    def iter_function(obj, iterator, **data):
        idle_call = IdleCallIterator(*func(obj))

        idle_call(iterator, **data)

        return idle_call

    return iter_function


class SpriteSheet(object):

    def __init__(self, image, icon_width, icon_height, x_spacing, y_spacing,
        x_start, y_start, alpha_color=None, size=None):
        # load the image
        base_image = GdkPixbuf.Pixbuf.new_from_file(image)

        if alpha_color:
            base_image = base_image.add_alpha(True, *alpha_color)

        delta_y = icon_height + y_spacing
        delta_x = icon_width + x_spacing

        self._sprites = []

        for y in range(0, ((base_image.get_height() - y_start) / delta_y) + 1):
            for x in range(0, ((base_image.get_width() - x_start) / delta_x)
                + 1):
                sprite = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True,
                    8, icon_width, icon_height)

                base_image.copy_area(x_start + (x * delta_x),
                    y_start + (y * delta_y), icon_width, icon_height,
                    sprite, 0, 0)

                if size:
                    sprite = sprite.scale_simple(size, size,
                        GdkPixbuf.InterpType.BILINEAR)

                self._sprites.append(sprite)

    def __len__(self):
        return len(self._sprites)

    def __getitem__(self, index):
        return self._sprites[index]


class ConfiguredSpriteSheet(object):
    popups = 'img/popups.xml'

    def __init__(self, plugin, sprite_name, size=None):
        self.plugin = plugin
        self.popups = rb.find_plugin_file(plugin, self.popups)
        self.tree = ET.ElementTree(file=self.popups)
        root = self.tree.getroot()
        base = 'spritesheet[@name="' + sprite_name + '"]/'
        image = rb.find_plugin_file(plugin, 'img/' +
            root.findall(base + 'image')[0].text)
        icon_width = int(root.findall(base + 'icon')[0].attrib['width'])
        icon_height = int(root.findall(base + 'icon')[0].attrib['height'])
        x_spacing = int(root.findall(base + 'spacing')[0].attrib['x'])
        y_spacing = int(root.findall(base + 'spacing')[0].attrib['y'])
        x_start = int(root.findall(base + 'start-position')[0].attrib['x'])
        y_start = int(root.findall(base + 'start-position')[0].attrib['y'])

        try:
            alpha_color = map(int,
                    root.findall(base + 'alpha')[0].text.split(' '))
        except:
            alpha_color = None

        self.names = []

        for elem in root.findall(sprite_name + '/' + sprite_name +
            '[@spritesheet="' + sprite_name + '"]'):
                self.names.append(elem.attrib['name'])

        self._sheet = SpriteSheet(image, icon_width, icon_height, x_spacing,
            y_spacing, x_start, y_start, alpha_color, size)

    def __len__(self):
        return len(self._sheet)

    def __getitem__(self, name):
        try:
            return self._sheet[self.names.index(name)]
        except:
            return None

    def __contains__(self, name):
        return name in self.names


class GenreConfiguredSpriteSheet(ConfiguredSpriteSheet):
    def __init__(self, plugin, sprite_name, size=None):
        super(GenreConfiguredSpriteSheet, self).__init__(
            plugin, sprite_name, size)
        root = self.tree.getroot()
        self.alternate = {}
        for elem in root.findall(sprite_name + '/alt'):
                self.alternate[elem.text] = elem.attrib['genre']

