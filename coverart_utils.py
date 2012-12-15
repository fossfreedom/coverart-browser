# -*- coding: utf-8 *-*
from bisect import bisect_left, bisect_right
from ConfigParser import ConfigParser
from gi.repository import GdkPixbuf



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
        k = self._key(item)
        i = bisect_left(self._keys, k)
        j = bisect_right(self._keys, k)
        return len(self) - self._items[i:j].index(item) + i - 1


class SpriteSheet(object):

    def __init__(self, image, icon_width, icon_height, x_spacing, y_spacing,
        alpha_color=None):
        # load the image
        base_image = GdkPixbuf.Pixbuf.new_from_file(image)

        if alpha_color:
            base_image.add_alpha(True, *alpha_color)

        delta_y = icon_height + y_spacing
        delta_x = icon_width + x_spacing

        self._sprites = []

        for y in range(0, base_image.get_height() / delta_y + 1):
            for x in range(0, base_image.get_width() / delta_x + 1):
                sprite = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True,
                    8, icon_width, icon_height)

                base_image.copy_area(x * delta_x, y * delta_y, icon_width,
                    icon_height, sprite, 0, 0)

                self._sprites.append(sprite)

    def __len__(self):
        return len(self._sprites)

    def __getitem__(self, index):
        return self._sprites[index]


class ConfiguredSpriteSheet(object):
    SECTION = 'SpriteSheet'

    def __init__(self, conf_file):
        config = ConfigParser()
        config.read(conf_file)

        image = config.get(self.SECTION, 'image')
        icon_width = config.getint(self.SECTION, 'icon_width')
        icon_height = config.getint(self.SECTION, 'icon_height')
        x_spacing = config.getint(self.SECTION, 'x_spacing')
        y_spacing = config.getint(self.SECTION, 'y_spacing')

        if config.has_option(self.SECTION, 'alpha_color'):
            alpha_color = map(int,
                config.get(self.SECTION, 'alpha_color').split(' '))
        else:
            alpha_color = None

        self._names = config.get(self.SECTION, 'names').split(', ')

        self._sheet = SpriteSheet(image, icon_width, icon_height, x_spacing,
            y_spacing, alpha_color)

    def __len__(self):
        return len(self._sheet)

    def __getitem__(self, name):
        return self._sheet[self._names.index(name)]
