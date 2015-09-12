# -*- Mode: python; coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
#
# Copyright (C) 2012 - fossfreedom
# Copyright (C) 2012 - Agustin Carrasco
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of thie GNU General Public License as published by
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

import shutil
import os
import sys
import subprocess

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import RB
from gi.repository import Gdk
from gi.repository import Peas
from gi.repository import Gst

from coverart_utils import NaturalString
import rb
import coverart_rb3compat as rb3compat


class CoverArtExport(GObject.Object):
    """
    This class provides for various export routines
    
    """
    TARGET_BITRATE = 128

    def __init__(self, plugin, shell, album_manager):
        self.plugin = plugin
        self.shell = shell
        self.album_manager = album_manager

        self._gstreamer_has_initialised = False
        self.has_opened_previously = False
        self._values = {}

    def is_search_plugin_enabled(self):
        peas = Peas.Engine.get_default()
        loaded_plugins = peas.get_loaded_plugins()

        result = False
        if 'coverart_search_providers' in loaded_plugins:
            info = peas.get_plugin_info('coverart_search_providers')
            version = info.get_version()

            if NaturalString(version) >= "0.9":
                result = True

        return result

    def embed_albums(self, selected_albums):
        """
        method to export and embed coverart to chosen albums

        :selected_albums: `Album` - array of albums
        """

        self._initialise_gstreamer()

        from coverart_search_tracks import CoverArtTracks

        search_tracks = CoverArtTracks()
        playlist_manager = self.shell.props.playlist_manager
        playlists_entries = playlist_manager.get_playlists()

        ui = Gtk.Builder()
        ui.add_from_file(rb.find_plugin_file(self.plugin,
                                             'ui/coverart_exportembed.ui'))
        ui.connect_signals(self)
        embeddialog = ui.get_object('exportembeddialog')
        embeddialog.set_transient_for(self.shell.props.window)
        folderchooserbutton = ui.get_object('folderchooserbutton')
        use_album_name_checkbutton = ui.get_object('use_album_name_checkbutton')
        open_filemanager_checkbutton = ui.get_object('open_filemanager_checkbutton')
        convert_checkbutton = ui.get_object('convert_checkbutton')
        bitrate_spinbutton = ui.get_object('bitrate_spinbutton')
        resize_checkbutton = ui.get_object('resize_checkbutton')
        resize_spinbutton = ui.get_object('resize_spinbutton')

        # predefine values if not previously opened the dialog
        if self.has_opened_previously:
            print(self._values)
            if not self._values['toresize']:
                resize_spinbutton.set_value(128)
            else:
                resize_spinbutton.set_value(self._values['resize'])

            if not self._values['convert']:
                bitrate_spinbutton.set_value(self.TARGET_BITRATE)
            else:
                bitrate_spinbutton.set_value(self._values['bitrate'])

            folderchooserbutton.set_current_folder(self._values['final_folder_store'])
            use_album_name_checkbutton.set_active(self._values['use_album_name'])
            open_filemanager_checkbutton.set_active(self._values['open_filemanager'])
            convert_checkbutton.set_active(self._values['convert'])
            resize_checkbutton.set_active(self._values['toresize'])

        else:
            bitrate_spinbutton.set_value(self.TARGET_BITRATE)
            resize_spinbutton.set_value(128)

            downloads_dir = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
            folderchooserbutton.set_current_folder(downloads_dir)

        response = embeddialog.run()

        if response != Gtk.ResponseType.OK:
            embeddialog.destroy()
            return

        self.has_opened_previously = True
        # ok pressed - now fetch values from the dialog
        final_folder_store = folderchooserbutton.get_current_folder()
        use_album_name = use_album_name_checkbutton.get_active()
        open_filemanager = open_filemanager_checkbutton.get_active()
        convert = convert_checkbutton.get_active()
        bitrate = bitrate_spinbutton.get_value()
        toresize = resize_checkbutton.get_active()
        if toresize:
            resize = int(resize_spinbutton.get_value())
        else:
            resize = -1

        self._values['bitrate'] = bitrate
        self._values['resize'] = resize
        self._values['final_folder_store'] = final_folder_store
        self._values['use_album_name'] = use_album_name
        self._values['open_filemanager'] = open_filemanager
        self._values['convert'] = convert
        self._values['toresize'] = toresize

        print(self._values)
        embeddialog.destroy()

        albums = {}
        total = 0

        for album in selected_albums:
            albums[album] = album.get_tracks()
            total = total + len(albums[album])

        self._track_count = 1

        def complete():
            self.album_manager.progress = 1

            if open_filemanager:
                # code taken from http://stackoverflow.com/questions/1795111/is-there-a-cross-platform-way-to-open-a-file-browser-in-python
                if sys.platform == 'win32':
                    import winreg

                    path = r('SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon')
                    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                        try:
                            with winreg.OpenKey(root, path) as k:
                                value, regtype = winreg.QueryValueEx(k, 'Shell')
                        except WindowsError:
                            pass
                        else:
                            if regtype in (winreg.REG_SZ, winreg.REG_EXPAND_SZ):
                                shell = value
                            break
                    else:
                        shell = 'Explorer.exe'
                    subprocess.Popen([shell, final_folder_store])

                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', final_folder_store])

                else:
                    subprocess.Popen(['xdg-open', final_folder_store])

        self._albumiter = iter(albums)
        self._tracknumber = 0
        self._album = next(self._albumiter)

        def idle_call(data):
            exit_idle = True

            track = albums[self._album][self._tracknumber]

            if not process_track(self._album, track):
                exit_idle = False

            self._tracknumber = self._tracknumber + 1

            if self._tracknumber >= len(albums[self._album]):
                try:
                    self._tracknumber = 0
                    self._album = next(self._albumiter)
                except StopIteration:
                    exit_idle = False

            if not exit_idle:
                complete()

            return exit_idle

        def process_track(album, track):
            self.album_manager.progress = self._track_count / total
            self._track_count = self._track_count + 1

            key = album.create_ext_db_key()
            finalPath = rb3compat.unquote(track.location)[7:]
            album_name = RB.search_fold(album.name)

            if use_album_name:
                folder_store = final_folder_store + '/' + album_name
            else:
                folder_store = final_folder_store

            try:
                if not os.path.exists(folder_store):
                    os.makedirs(folder_store)

                if convert:
                    self.convert_to_mp3(finalPath, folder_store, bitrate)
                    finalPath = self._calc_mp3_filename(finalPath, folder_store)
                    print(finalPath)
                else:
                    shutil.copy(finalPath, folder_store)
            except IOError as err:
                print(err.args[0])
                return False

            dest = os.path.join(folder_store, os.path.basename(finalPath))
            desturi = 'file://' + rb3compat.pathname2url(dest)

            return search_tracks.embed(desturi, key, resize)

        data = None

        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, idle_call, data)

    def _initialise_gstreamer(self):

        if self._gstreamer_has_initialised:
            return

        self._gstreamer_has_initialised = True
        Gst.init(None)

        def on_new_decoded_pad(dbin, pad):
            decode = pad.get_parent()
            pipeline = decode.get_parent()
            convert = pipeline.get_by_name('convert')
            decode.link(convert)

        # we are going to mimic the following
        # gst-launch-1.0 filesrc location="02 - ABBA - Knowing Me, Knowing You.ogg" ! 
        # decodebin ! audioconvert ! audioresample ! lamemp3enc target=bitrate bitrate=128 ! 
        # xingmux ! id3v2mux ! filesink location="mytrack.mp3"

        converter = Gst.Pipeline.new('converter')

        source = Gst.ElementFactory.make('filesrc', None)

        decoder = Gst.ElementFactory.make('decodebin', 'decoder')
        convert = Gst.ElementFactory.make('audioconvert', 'convert')
        sample = Gst.ElementFactory.make('audioresample', 'sample')
        encoder = Gst.ElementFactory.make('lamemp3enc', 'encoder')
        encoder.set_property('target', 'bitrate')
        encoder.set_property('bitrate', self.TARGET_BITRATE)

        xing = Gst.ElementFactory.make('xingmux', 'xing')  # needed to make bitrate more accurate
        mux = Gst.ElementFactory.make('id3v2mux', 'mux')
        if not mux:
            # use id3mux where not available
            mux = Gst.ElementFactory.make('id3mux', 'mux')

        sink = Gst.ElementFactory.make('filesink', 'sink')

        converter.add(source)
        converter.add(decoder)
        converter.add(convert)
        converter.add(sample)
        converter.add(encoder)
        converter.add(xing)
        converter.add(mux)
        converter.add(sink)

        Gst.Element.link(source, decoder)
        # note - a decodebin cannot be linked at compile since
        # it doesnt have source-pads (http://stackoverflow.com/questions/2993777/gstreamer-of-pythons-gst-linkerror-problem)

        decoder.connect("pad-added", on_new_decoded_pad)

        Gst.Element.link(convert, sample)
        Gst.Element.link(sample, encoder)
        Gst.Element.link(encoder, xing)
        Gst.Element.link(xing, mux)
        Gst.Element.link(mux, sink)

        self.converter = converter
        self.source = source
        self.sink = sink
        self.encoder = encoder

    def _calc_mp3_filename(self, filename, save_folder):
        finalname = os.path.basename(filename)
        finalname = finalname.rsplit('.')[0] + ".mp3"
        return save_folder + "/" + finalname

    def convert_to_mp3(self, filename, save_folder, bitrate):

        self.source.set_property('location', filename)
        self.sink.set_property('location', self._calc_mp3_filename(filename, save_folder))
        print(bitrate)
        if bitrate < 32:
            bitrate = self.TARGET_BITRATE

        self.encoder.set_property('bitrate', int(bitrate))
        print(bitrate)

        # Start playing
        ret = self.converter.set_state(Gst.State.PLAYING)

        if ret == Gst.StateChangeReturn.FAILURE:
            print("Unable to set the pipeline to the playing state.", sys.stderr)
            exit(-1)

        # Wait until error or EOS
        bus = self.converter.get_bus()
        try:
            msg = bus.timed_pop_filtered(
                Gst.CLOCK_TIME_NONE, Gst.MessageType.ERROR | Gst.MessageType.EOS)
        except:
            # for some reason in ubuntu 12.04 Gst.CLOCK_TIME_NONE fails
            msg = bus.timed_pop_filtered(
                18446744073709551615, Gst.MessageType.ERROR | Gst.MessageType.EOS)

        # Parse message
        if (msg):
            if msg.type == Gst.MessageType.ERROR:
                err, debug = msg.parse_error()
                print("Error received from element %s: %s" % (
                    msg.src.get_name(), err), sys.stderr)
                print("Debugging information: %s" % debug, sys.stderr)
            elif msg.type == Gst.MessageType.EOS:
                print("End-Of-Stream reached.")
            else:
                print("Unexpected message received.", sys.stderr)

        # Free resources
        self.converter.set_state(Gst.State.NULL)
