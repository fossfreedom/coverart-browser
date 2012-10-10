coverart-browser v0.5
================

Browse your coverart albums in Rhythmbox v2.96 and later

![Imgur](http://i.imgur.com/LJUif.png)

-----------

Summary: whats new in this release

 - Tracks & Covers pane - display tracks for the selected album and built-in coverart web-search
 - Drag & Drop coverart update support
 - Display Album & Artist name under the cover
 - Support for assigning track-rating and playing/queuing your favourite rated tracks
 - Multiple album selection
 - Double click playing of albums
 - Sort covers by album name and artist, both in ascending and descending order
 - Set the coverart size displayed in the main view
 - Multiple user-configurable options to tailor what you see and use.
 - Examine and change properties for an Album
 - Examine and change properties for a track

How it works:

 - Click the new CoverArt source button (left hand side of screen)
 - Albums are displayed as clickable buttons containing their album cover
 - Right click menu option to play, queue & search for coverart for an album.

![Imgur](http://i.imgur.com/D5Nq9.png)

 - multi-select albums to play, queue, search for covers and edit properties

![Imgur](http://i.imgur.com/LF6nh.png)

 - Right click to see and edit the properties for an album:

![Imgur](http://i.imgur.com/U1YyX.png)

*hint* - change both the album name and album artist and all the tracks for 
  the selected album will be combined under one album.

 - locale support has been added to display text in your native language.

**HELP WANTED** - We need your help to translate - please help out! (see below)

 - Filter your albums

![Imgur](http://i.imgur.com/1QEfH.png)

 - Right click to search for missing covers

![Imgur](http://i.imgur.com/QmHzi.png)

 - Display tracks for an album

![Imgur](http://i.imgur.com/0QG1g.png)

 - Find additional coverart

![Imgur](http://i.imgur.com/78pkf.png)

Either double-click the picture or drag-and-drop to update the coverart for the selected album

Tailor the search for album covers:

![Imgur](http://i.imgur.com/N7cy6.png)

The cover-view accept images dropped from nautilus (for example) or URLs from the web.

 - Rate tracks and play your favourite tracks from albums

Rate your tracks:

![Imgur](http://i.imgur.com/ju5Yl.png)

Then use the Rate Threshold...

![Imgur](http://i.imgur.com/3flms.png)

... to enable you to play your favourite tracks from an album:

![Imgur](http://i.imgur.com/NrJAe.png)

 - Define your own preferences

![Imgur](http://i.imgur.com/XIevz.png)

 - Display the name and artist for covers

![Imgur](http://i.imgur.com/3xDfI.png)

 - both 32bit & 64bit support available
 - icon-tooltip shows all the track artists for multi-artist albums
 - automatic album focus when right-click an album to display album choices.
 - ... and a number of bug-fixes as well.

*How to install:*

1. install *git*
N.B. for debian based distros - `sudo apt-get install git`
2. install the package *gettext*
N.B. for debian based distros - `sudo apt-get install gettext`

<pre>
rm -rf ~/.local/share/rhythmbox/plugins/coverart_browser
git clone https://github.com/fossfreedom/coverart-browser.git -b master
cd coverart-browser
sh ./install.sh
</pre>

*For Ubuntu 12.04 & 12.10:*

This is now available in my rhythmbox PPA - installation instructions in this AskUbuntu Q&A:

http://askubuntu.com/questions/147942/how-do-i-install-third-party-rhythmbox-plugins

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
 - our Translators: jrbastien, asermax, mateuswetah

GTK3 port of code.google.com/p/rhythmbox-cover-art-browser
