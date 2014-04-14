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
from coverart_utils import idle_iterator
import rb
import urllib.parse
import json
import os
import random

LOAD_CHUNK = 50

class WebPlaylist(object):
    MAX_TRACKS_TO_ADD = 3 # number of tracks to add to a source for each fetch
    MIN_TRACKS_TO_FETCH = 5 # number of tracks in source before a fetch will be required
    TOTAL_TRACKS_REMEMBERED = 25 # total number of tracks for all artists before a fetch is allowed
    MAX_TRACKS_PER_ARTIST = 3 # number of tracks allowed to be remembered per artist
    
    def __init__(self, shell, source, playlist_name):
       
        self.shell = shell
        #lets fill up the queue with artists
        self.candidate_artist = {}
        self.shell.props.shell_player.connect('playing-song-changed', self.playing_song_changed)
        self.source = source
        self.search_entry = None
        self.playlist_started = False
        self.played_artist = {}
        self.tracks_not_played = 0
        # cache for artist information: valid for a month, can be used indefinitely
        # if offline, discarded if unused for six months
        self.info_cache = rb.URLCache(name = playlist_name,
                                      path = os.path.join('coverart_browser', playlist_name),
                                      refresh = 30,
                                      discard = 180)
        self.info_cache.clean()
    
    def playing_song_changed(self, player, entry):
        if not entry:
            return
            
        if player.get_playing_source() != self.source:
            self.playlist_started = False
            self.played_artist.clear()
            self.tracks_not_played = 0
            
        if self.playlist_started and len(self.source.props.query_model) < self.MIN_TRACKS_TO_FETCH:
            self.start(entry)
    
    def start(self, seed_entry, reinitialise = False):
        artist = seed_entry.get_string(RB.RhythmDBPropType.ARTIST)
        
        if reinitialise:
            self.played_artist.clear()
            self.tracks_not_played = 0
            self.playlist_started = False
            
            player = self.shell.props.shell_player
            _, is_playing =  player.get_playing()
        
            if is_playing:
                player.stop()
            
            for row in self.source.props.query_model:
                self.source.props.query_model.remove_entry(row[0])
            
        if self.tracks_not_played > self.TOTAL_TRACKS_REMEMBERED:
            print(("we have plenty of tracks to play yet - no need to fetch more %d", self.tracks_not_played))
            self.add_tracks_to_source()
            return
            
        search_artist = urllib.parse.quote(artist.encode("utf8"))
        if search_artist in self.played_artist:
            print ("we have already searched for that artist")
            return
            
        self.search_entry = seed_entry
        self.played_artist[search_artist] = True
        
        self.playlist_started = True
        self._running = False
        self._start_process()

    def _start_process(self):
        if not self._running:
            self._running = True
            self.search_website()
     
    def search_website(self):
        pass
        
    def _clear_next(self):
        self.search_artists = ""
        self._running  = False
                
    @idle_iterator
    def _load_albums(self):
        def process(row, data):
            entry = data['model'][row.path][0]

            lookup = entry.get_string(RB.RhythmDBPropType.ARTIST_FOLDED)
            lookup_title = entry.get_string(RB.RhythmDBPropType.TITLE_FOLDED)

            if lookup in self.artist and \
                lookup_title in \
                    self.artist[lookup]:

                if lookup not in self.candidate_artist:
                    self.candidate_artist[lookup] = []

                # N.B. every artist has an array of dicts with a known format of track & add-to-source elements
                # the following extracts the track-title and add-to-source to form a dict of track-title and a value
                # of the add-to-source
                d=dict((i['track-title'], i['add-to-source']) for i in self.candidate_artist[lookup]) 
                if len(d) < self.MAX_TRACKS_PER_ARTIST and lookup_title not in d:
                    # we only append a max of three tracks to each artist
                    self.candidate_artist[lookup].append({
                        'track':entry, 
                        'add-to-source':False, 
                        'track-title':lookup_title})
                    self.tracks_not_played = self.tracks_not_played + 1
                    
            
        def after(data):
            # update the progress
            pass

        def error(exception):
            print(('Error processing entries: ' + str(exception)))

        def finish(data):
            
            self.add_tracks_to_source()    
            self._clear_next()

        return LOAD_CHUNK, process, after, error, finish
        
    def add_tracks_to_source(self):
        entries = []
        for artist in self.candidate_artist:
        
            d=dict((i['track'], (self.candidate_artist[artist].index(i), 
                                i['add-to-source'], 
                                artist)) for i in self.candidate_artist[artist])

            for entry, elements in d.items():
                element_pos, add_to_source, artist = elements
                if not add_to_source:
                    entries.append({entry: elements})
                
        random.shuffle(entries)
        
        count = 0
        for row in entries:
            print (row)
            entry, elements = list(row.items())[0]
            element_pos, add_to_source, artist = elements
            self.source.add_entry(entry, -1)
            self.candidate_artist[artist][element_pos]['add-to-source'] = True

            count = count + 1
            self.tracks_not_played = self.tracks_not_played - 1
            if count == self.MAX_TRACKS_TO_ADD:
                break
                
        player = self.shell.props.shell_player
        
        _, is_playing =  player.get_playing()
        
        if len(self.source.props.query_model) > 0 and not is_playing:
            player.play_entry(self.source.props.query_model[0][0], self.source)
            
class LastFMTrackPlaylist(WebPlaylist):
    
    def __init__(self, shell, source):
        WebPlaylist.__init__(self, shell, source, "lastfm_trackplaylist")
        
    def search_website(self):
        # unless already cached - directly fetch from lastfm similar track information
        apikey = "844353bce568b93accd9ca47674d6c3e"
        url = "http://ws.audioscrobbler.com/2.0/?method=track.getsimilar&api_key={0}&artist={1}&track={2}&format=json"
        
        artist = self.search_entry.get_string(RB.RhythmDBPropType.ARTIST)
        title = self.search_entry.get_string(RB.RhythmDBPropType.TITLE)
        artist = urllib.parse.quote(artist.encode("utf8"))
        title = urllib.parse.quote(title.encode("utf8"))
        formatted_url = url.format(urllib.parse.quote(apikey),
                                   artist,
                                   title)

        print (formatted_url)
        cachekey = "artist:%s:title:%s" % (artist, title)     
        self.info_cache.fetch(cachekey, formatted_url, self.similar_info_cb, None)
        
    def similar_info_cb(self, data, _):
                
        if not data:
            print ("nothing to do")
            self._clear_next()
            return
            
        similar = json.loads(data.decode('utf-8'))
        
        # loop through the response and find all titles for the artists returned
        self.artist = {}
        
        if 'similartracks' not in similar:
            print ("No matching data returned from LastFM")
            self._clear_next()
            return
        for song in similar['similartracks']['track']:
            name = RB.search_fold(song['artist']['name'])
            if name not in self.artist:
                self.artist[name] = []
                
            self.artist[name].append(RB.search_fold(song['name']))
            
        if len(self.artist) == 0:
            print ("no artists returned")
            self._clear_next()
            return
            
        # loop through every track - see if the track contains the artist & title
        # if yes then this is a candidate similar track to remember
        
        query_model = self.shell.props.library_source.props.base_query_model
        
        self._load_albums(iter(query_model), albums={}, model=query_model,
            total=len(query_model), progress=0.)

class EchoNestPlaylist(WebPlaylist):
    
    def __init__(self, shell, source):
        WebPlaylist.__init__(self, shell, source, "echonest_playlist")
        
    def search_website(self):
        # unless already cached - directly fetch from echonest similar artist information
        apikey = "N685TONJGZSHBDZMP"
        url = "http://developer.echonest.com/api/v4/playlist/basic?api_key={0}&artist={1}&format=json&results=100&type=artist-radio&limited_interactivity=true"
            
        artist = self.search_entry.get_string(RB.RhythmDBPropType.ARTIST)
        artist = urllib.parse.quote(artist.encode("utf8"))
        formatted_url = url.format(urllib.parse.quote(apikey),
                                   artist)

        print (formatted_url)
        cachekey = "artist:%s" % artist    
        self.info_cache.fetch(cachekey, formatted_url, self.similar_info_cb, None)
                            
    def similar_info_cb(self, data, _):
                
        if not data:
            print ("nothing to do")
            self._clear_next()
            return
            
        similar = json.loads(data.decode('utf-8'))
        
        # loop through the response and find all titles for the artists returned
        self.artist = {}
        
        if 'songs' not in similar['response']:
            print ("No matching data returned from EchoNest")
            self._clear_next()
            return
        for song in similar['response']['songs']:
            name = RB.search_fold(song['artist_name'])
            if name not in self.artist:
                self.artist[name] = []
                
            self.artist[name].append(RB.search_fold(song['title']))
            
        if len(self.artist) == 0:
            print ("no artists returned")
            self._clear_next()
            return
            
        # loop through every track - see if the track contains the artist & title
        # if yes then this is a candidate similar track to remember
        
        query_model = self.shell.props.library_source.props.base_query_model
        
        self._load_albums(iter(query_model), albums={}, model=query_model,
            total=len(query_model), progress=0.)
