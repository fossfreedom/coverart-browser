coverart-browser v0.6
================

Browse your coverart albums in Rhythmbox v2.96 and later

*update pictures below*

![Imgur](http://i.imgur.com/QyCXA.png)

-----------

Summary: whats new in this release

 - Playlist support: display coverart from a playlist, queue & main library
 - Playlist support: add albums and selected tracks from the coverart browser to playlists
 - Ratings: update album and track ratings from easy-to-use Star visual object
 - Sort & Search bar: optional display of these options on the left or right side of Rhythmbox panes
 - Sort & Search bar: optional year and rating sort options
 - Covers pane: simplified view showing album art first hiding initial search options until requested.
 - Plugin Preferences: revamped the preferences dialog to tailor what your see and use.

How it works:

 - Click the new CoverArt source button (left hand side of screen)
 - Albums are displayed as clickable buttons containing their album cover
 - Right click menu option to play, queue & search for coverart for an album.

![Imgur](http://i.imgur.com/D5Nq9.png)

 - multi-select albums to play, queue, search for covers and edit properties

![Imgur](http://i.imgur.com/LF6nh.png)

 - Right click to see and edit the properties for an album:

![Imgur](http://i.imgur.com/U1YyX.png)

*hint* - Select multiple albums - change both the album name and album artist and all the tracks for 
  the selected albums will be combined under one album.

 - locale support has been added to display text in your native language.

**HELP WANTED** - We need your help to translate - please help out! (see below)

 - Filter your albums

![Imgur](http://i.imgur.com/1QEfH.png)

 - Open Coverart Browser from playlist, music queue or music library views

*picture*

 - Right click to search for missing covers

![Imgur](http://i.imgur.com/QmHzi.png)

 - Right click to add albums or tracks to Playlists

*picture*

 - Display tracks for an album

![Imgur](http://i.imgur.com/TFzgM.png)

 - Find additional coverart

![Imgur](http://i.imgur.com/swQ7R.png)

Either double-click the picture or drag-and-drop to update the coverart for the selected album

Tailor the search for album covers:

![Imgur](http://i.imgur.com/N7cy6.png)

The cover-view accept images dropped from nautilus (for example) or URLs from the web.

 - Rate whole albums & individual tracks to play your favourite albums & tracks from albums

Rate your albums:

*picture*

Rate your tracks:

![Imgur](http://i.imgur.com/ju5Yl.png)

Then use the Rate Threshold...

![Imgur](http://i.imgur.com/3flms.png)

... to enable you to play your favourite albums and tracks in those albums:

![Imgur](http://i.imgur.com/NrJAe.png)

 - Define your own preferences

![Imgur](http://i.imgur.com/n2OcH.png)

 - Display the name and artist for covers

![Imgur](http://i.imgur.com/3xDfI.png)

 - icon-tooltip shows all the track artists for multi-artist albums
 - ... and a number of bug-fixes as well.

*How to install:*

1. install *git*
N.B. for debian based distros - `sudo apt-get install git`
2. install the package *gettext*
N.B. for debian based distros - `sudo apt-get install gettext`

<pre>
rm -rf ~/.local/share/rhythmbox/plugins/coverart_browser
git clone https://github.com/fossfreedom/coverart-browser.git
cd coverart-browser
sh ./install.sh
</pre>

*For Ubuntu 12.04 & 12.10:*

This is now available in my rhythmbox PPA - installation instructions in this AskUbuntu Q&A:

http://askubuntu.com/questions/147942/how-do-i-install-third-party-rhythmbox-plugins

**IMPORTANT NOTE**

For Ubuntu 12.04 users that have upgraded to Rhythmbox v2.98 using the webupd8 PPA, this version 
of rhythmbox crashes when used with python plugins such as coverart-browser and replaygain.

It is strongly recommended that you either upgrade to 12.10 where v2.98 works great, or 
downgrade to v2.96 or v2.97 as per:
 - http://askubuntu.com/questions/201093/how-do-i-downgrade-rhythmbox-v2-98

You can use this plugin with v2.98 but you'll need to change the file *coverart_album.py* and
comment out the following lines (i.e. add a # as shown)

<pre>
#self.entry_changed_id = self.db.connect('entry-changed',
#            self._entry_changed_callback)
</pre>

If you do this, rhythmbox does not crash - however, if you change and album or track details
via the properties option in the music pane, these changes are not updated in the plugin until
you restart rhythmbox.


**Please help out with translating**

We need you to help us translate the english text to your native language.

Don't worry - it is easier that you think.

Instructions are in the file TRANSLATE_README. Post a link to the file as a new issue, or
if you are feeling generous - fork and push a pull-request. Thanks!

If they look scary - just email me (foss dot freedom at gmail dot com) and I'll send you the 
file that needs to be translated - it is less than 20 text strings so it should only take a
few minutes.

When emailing - tell me your locale & language.  You can find these by typing:

    echo $LANG
    echo $LANGUAGE

-------

Authors:

The authors of this plugin are fossfreedom <foss.freedom@gmail.com>, Agustín Carrasco <asermax@gmail.com>

-------

Credits:

 - thanks to Luqman Aden <laden@uwaterloo.ca> for the coverart-search plugin which our cover-search pane is based upon
 - thanks to Canonical for the Star widget which the ratings capabilities use
 - our Translators: jrbastien (fr_CA), asermax (es), mateuswetah (pt_BR), jrbastien & lannic (fr.po)

GTK3 port of code.google.com/p/rhythmbox-cover-art-browser
