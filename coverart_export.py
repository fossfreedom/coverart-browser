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

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import RB
from gi.repository import Gdk
from coverart_album import Album
import rb
import shutil
import rb3compat
import os.path
import os
import sys
import subprocess

class CoverArtExport(GObject.Object):
    '''
    This class provides for various export routines
    
    '''
    def __init__(self, plugin, shell, album_manager):
        self.plugin = plugin
        self.shell = shell
        self.album_manager = album_manager
        
    def is_search_plugin_enabled(self):
        # very dirty hack - lets tidy this correctly for v0.9
        
        try:
            from coverart_search_tracks import CoverArtTracks
        except:
            return False
        
        return True
        
    def embed_albums(self, selected_albums):
        '''
        method to create the menu items for all supported plugins

        :selected_albums: `Album` - array of albums
        
        '''
        # temporarily move this import to here for v0.8
        # need to separate the two plugins correctly for v0.9
        from coverart_search_tracks import CoverArtTracks
        
        search_tracks = CoverArtTracks()
        playlist_manager = self.shell.props.playlist_manager
        playlists_entries = playlist_manager.get_playlists()

        ui = Gtk.Builder()
        ui.add_from_file(rb.find_plugin_file(self.plugin,
            'ui/coverart_exportembed.ui'))
        ui.connect_signals(self)
        embeddialog = ui.get_object('exportembeddialog')
        folderchooserbutton  = ui.get_object('folderchooserbutton')
        use_album_name_checkbutton = ui.get_object('use_album_name_checkbutton')
        open_filemanager_checkbutton = ui.get_object('open_filemanager_checkbutton')
        
        downloads_dir = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
        folderchooserbutton.set_current_folder(downloads_dir)

        response = embeddialog.run()
        
        if response != Gtk.ResponseType.OK:
            embeddialog.destroy()
            return

        #ok pressed - now fetch values from the dialog
        final_folder_store = folderchooserbutton.get_current_folder()
        use_album_name = use_album_name_checkbutton.get_active()
        open_filemanager = open_filemanager_checkbutton.get_active()
        
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
                #code taken from http://stackoverflow.com/questions/1795111/is-there-a-cross-platform-way-to-open-a-file-browser-in-python
                if sys.platform=='win32':
                    import winreg
                    path= r('SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon')
                    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                        try:
                            with winreg.OpenKey(root, path) as k:
                                value, regtype= winreg.QueryValueEx(k, 'Shell')
                        except WindowsError:
                            pass
                        else:
                            if regtype in (winreg.REG_SZ, winreg.REG_EXPAND_SZ):
                                shell= value
                            break
                    else:
                        shell= 'Explorer.exe'
                    subprocess.Popen([shell, final_folder_store])

                elif sys.platform=='darwin':
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
                shutil.copy(finalPath, folder_store)
            except IOError as err:
                print(err.args[0])
                return False

            dest = os.path.join(folder_store, os.path.basename(finalPath))
            desturi = 'file://' + rb3compat.pathname2url(dest)
            
            return search_tracks.embed(desturi, key)

        data = None
        
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, idle_call, data)
        
