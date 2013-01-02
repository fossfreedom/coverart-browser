# -*- Mode: python; coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
# Copyright (C) 2012 - fossfreedom
# Copyright (C) 2012 - Agustin Carrasco
## adapted from artsearch plugin - Copyright (C) 2012 Jonathan Matthew
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# The Rhythmbox authors hereby grant permission for non-GPL compatible
# GStreamer plugins to be used and distributed together with GStreamer
# and Rhythmbox. This permission is above and beyond the permissions granted
# by the GPL license by which Rhythmbox is covered. If you modify this code
# you may extend this exception to your version of the code, but you are not
# obligated to do so. If you do not wish to do so, delete this exception
# statement from your version.
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
from gi.repository import GLib
from gi.repository import Gdk
from gi.repository import Gio

import os, time,re, urllib
import threading
import discogs_client as discogs

ITEMS_PER_NOTIFICATION = 10
IGNORED_SCHEMES = ('http', 'cdda', 'daap', 'mms')
REPEAT_SEARCH_PERIOD = 86400 * 7

DISC_NUMBER_REGEXS = (
    "\(disc *[0-9]+\)",
    "\(cd *[0-9]+\)",
    "\[disc *[0-9]+\]",
    "\[cd *[0-9]+\]",
    " - disc *[0-9]+$",
    " - cd *[0-9]+$",
    " disc *[0-9]+$",
    " cd *[0-9]+$")

def file_root (f_name):
    return os.path.splitext (f_name)[0].lower ()

class CoverSearch(object):
    def __init__(self, store, key, last_time, searches):
        self.store = store
        self.key = key.copy()
        self.last_time = last_time
        self.searches = searches

    def next_search(self):
        print "next search"
        if len(self.searches) == 0:
            print "no more searches"
            key = RB.ExtDBKey.create_storage("album", self.key.get_field("album"))
            key.add_field("artist", self.key.get_field("artist"))
            self.store.store(key, RB.ExtDBSourceType.NONE, None)
            print "end of next_search False"
            return False

        search = self.searches.pop(0)
        print "calling search"
        search.search(self.key, self.last_time, self.store, self.search_done, None)
        print "end of next_search TRUE"
        return True

    def search_done(self, args):
        self.next_search()

class CoverAlbumSearch:
    def __init__ (self):
        pass

    def finished(self, results):
        parent = self.file.get_parent()
        
        base = file_root (self.file.get_basename())
        for f_name in results:
            if file_root (f_name) == base:
                uri = parent.resolve_relative_path(f_name).get_parse_name()
                found = self.get_embedded_image(uri)
                if found:
                    break
                                
        self.callback(self.callback_args)

    def _enum_dir_cb(self, fileenum, result, results):
        try:
            files = fileenum.next_files_finish(result)
            if files is None or len(files) == 0:
                print "okay, done; got %d files" % len(results)
                self.finished(results)
                return

            for f in files:
                ct = f.get_attribute_string("standard::content-type")
                # assume readable unless told otherwise
                readable = True
                if f.has_attribute("access::can-read"):
                    readable = f.get_attribute_boolean("access::can-read")
                
                if ct is not None and ct.startswith("audio/") and readable:
                    print "_enum_dir_cb %s " % f.get_name()
                    results.append(f.get_name())

            fileenum.next_files_async(ITEMS_PER_NOTIFICATION, GLib.PRIORITY_DEFAULT, None, self._enum_dir_cb, results)
        except Exception, e:
            print "okay, probably done: %s" % e
            import sys
            sys.excepthook(*sys.exc_info())
            self.finished(results)


    def _enum_children_cb(self, parent, result, data):
        try:
            enumfiles = parent.enumerate_children_finish(result)
            enumfiles.next_files_async(ITEMS_PER_NOTIFICATION, GLib.PRIORITY_DEFAULT, None, self._enum_dir_cb, [])
        except Exception, e:
            print "okay, probably done: %s" % e
            import sys
            sys.excepthook(*sys.exc_info())
            self.callback(self.callback_args)


    def search (self, key, last_time, store, callback, args):
        # ignore last_time
        print "calling search"
        location = key.get_info("location")
        if location is None:
            print "not searching, we don't have a location"
            callback(args)
            return

        self.file = Gio.file_new_for_uri(location)
        if self.file.get_uri_scheme() in IGNORED_SCHEMES:
            print 'not searching for local art for %s' % (self.file.get_uri())
            callback(args)
            return

        self.album = key.get_field("album")
        self.artists = key.get_field_values("artist")
        self.store = store
        self.callback = callback
        self.callback_args = args

        print 'searching for local art for %s' % (self.file.get_uri())
        parent = self.file.get_parent()
        enumfiles = parent.enumerate_children_async("standard::content-type,access::can-read,standard::name", 0, 0, None, self._enum_children_cb, None)

    def get_embedded_image(self, search):
        print "get_embedded_image"
        import tempfile
        imagefilename = tempfile.NamedTemporaryFile(delete=False)
        
        key = RB.ExtDBKey.create_storage("album", self.album)
        key.add_field("artist", self.artists[0])
        parent = self.file.get_parent()

        try:
            from mutagen.mp4 import MP4
            mp = MP4(search)
        
            if len(mp['covr']) >= 1:
                imagefilename.write(mp['covr'][0])
                uri = parent.resolve_relative_path(imagefilename.name).get_uri()
                imagefilename.close()
                self.store.store_uri(key, RB.ExtDBSourceType.USER, uri)
                return True 
        except:
            pass
            
        try:
            #flac 
            from mutagen import File

            music = File(search)
            imagefilename.write(music.pictures[0].data)
            imagefilename.close()
            uri = parent.resolve_relative_path(imagefilename.name).get_uri()
            self.store.store_uri(key, RB.ExtDBSourceType.USER, uri)
            return True 
        except:
            pass
                
        try:
            from mutagen.oggvorbis import OggVorbis

            o = OggVorbis(search)
            
            try:
                pic=o['COVERART'][0]
            except:
                pic=o['METADATA_BLOCK_PICTURE'][0]
                
            y=pic.decode('base64','strict')
            imagefilename.write(y)
            imagefilename.close()
            uri = parent.resolve_relative_path(imagefilename.name).get_uri()
            self.store.store_uri(key, RB.ExtDBSourceType.USER, uri)
            return True 
        except:
            pass
            
        try:
            from mutagen.mp3 import MP3, ID3

            i = ID3(search)

            apic = i.getall('APIC')[0]
            imagefilename.write(apic.data)
            imagefilename.close()
            uri = parent.resolve_relative_path(imagefilename.name).get_uri()
            self.store.store_uri(key, RB.ExtDBSourceType.USER, uri)
            return True 
        except:
            pass
            
        imagefilename.delete=True
        imagefilename.close()
        
        return False


class DiscogsSearch (object):
    def __init__(self):
        discogs.user_agent = 'CoverartBrowserSearch/0.7alpha +https://github.com/fossfreedom/coverart-browser'

    def search_url (self, artist, album):
        # Remove variants of Disc/CD [1-9] from album title before search
        orig_album = album
        for exp in DISC_NUMBER_REGEXS:
            p = re.compile (exp, re.IGNORECASE)
            album = p.sub ('', album)

        album.strip()
        url = "%s/%s" % (artist,album)
        print "discogs url = %s" % url
        return url

    def get_release_cb(self, key, store, url, cbargs, callback):
        try:
            s = discogs.Search(url)
            url = s.results()[0].data['images'][0]['uri150']
            self.store.store_uri(self.current_key, RB.ExtDBSourceType.SEARCH, url)
        except:
            pass

        self.callback(cbargs)
        return False
    
    def search(self, key, last_time, store, callback, args):
        if last_time > (time.time() - REPEAT_SEARCH_PERIOD):
            callback (args)
            return

        album = key.get_field("album")
        artists = key.get_field_values("artist")

        artists = filter(lambda x: x not in (None, "", _("Unknown")), artists)
        if album in ("", _("Unknown")):
            album = None

        if album == None or len(artists) == 0:
            callback (args)
            return

        self.searches = []
        for a in artists:
            self.searches.append([a, album])
        self.searches.append(["Various Artists", album])

        self.current_key = RB.ExtDBKey.create_storage("album", album)
        self.current_key.add_field("artist", artists[0])

        self.store = store
        self.callback = callback
        self.callback_args = args

        url = self.search_url(album, artists[0])
        threading.Thread( target=self.get_release_cb, args=(key, store, url, args, callback)).start()
        
