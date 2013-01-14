coverart-browser v0.7 - in development
================

Browse your coverart albums in Rhythmbox v2.96 and later

![Imgur](http://i.imgur.com/XM7KW.png)

-----------

**Please help out with translating - skip to the end for details**

Summary: whats new in this release

 - find embedded covers in MP3, MP4, FLAC & OGG files

How it works:

 - Click the new CoverArt source button (left hand side of screen)
 - Albums are displayed as clickable buttons containing their album cover
 - Right click menu option to play, queue & search for coverart for an album.

![Imgur](http://i.imgur.com/cGUTr.png)

 - multi-select albums to play, queue, add to playlists, search for covers and edit properties

![Imgur](http://i.imgur.com/Od0Bc.png)

 - Right click to see and edit the properties for an album:

![Imgur](http://i.imgur.com/U1YyX.png)

*hint* - Select multiple albums - change both the album name and album artist and all the tracks for 
  the selected albums will be combined under one album.

 - locale support has been added to display text in your native language.

**HELP WANTED** - We need your help to translate - please help out! (see below)

 - Filter your albums

![Imgur](http://i.imgur.com/1QEfH.png)

 - Open Coverart Browser from playlist, music queue or music library views

![Imgur](http://i.imgur.com/i7rGj.png)

 - Right click to search for missing covers

![Imgur](http://i.imgur.com/QmHzi.png)

 - Right click to add albums or tracks to Playlists

![Imgur](http://i.imgur.com/gN6Xd.png)

 - Display tracks for an album

![Imgur](http://i.imgur.com/TFzgM.png)

 - Find additional coverart

![Imgur](http://i.imgur.com/swQ7R.png)

Either double-click the picture or drag-and-drop to update the coverart for the selected album

Tailor the search for album covers:

![Imgur](http://i.imgur.com/N7cy6.png)

The cover-view accept images dropped from nautilus (for example) or URLs from the web.

 - Display Filter and sort options in left or right side of Rhythmbox

![Imgur](http://i.imgur.com/MDfCP.png)

 - Optional extra genre filter & new sort options by Favourite Rating and Album Year

![Imgur](http://i.imgur.com/xJIN9.png)

 - Rate whole albums & individual tracks to play your favourite albums & tracks from albums

Rate your albums:

![Imgur](http://i.imgur.com/k0rTU.png)

Rate your favourite tracks:

![Imgur](http://i.imgur.com/JWNVH.png)

Then use the Favourites Threshold...

![Imgur](http://i.imgur.com/SMyrL.png)

... to enable you to play your favourite albums and tracks in those albums:

![Imgur](http://i.imgur.com/0fnzv.png)


Lets say you have given some albums a rating - 5 stars, 4 stars, 3 stars etc.

You select lots of albums - right click and chose "add to rated playlist" - only those albums that have a rating are added to the playlist.

You can adjust this in the preferences - favourites threshold. If you set a threshold of - for example - 3 stars, then only albums rated 3 stars and higher are added.

You can fine-tune this with individual tracks - lets say you have 10 tracks in an album. You like only 5 of them. Give the 5 tracks a rating. Then you can play, queue or add just those "favourite" tracks to a playlist.


 - Define your own preferences

![Imgur](http://i.imgur.com/rro0A.png)

 - Display the name and artist for covers

![Imgur](http://i.imgur.com/3xDfI.png)

 - Define your own Genre lookups

By default the plugin will try to match genres in your collection and display the correct genre-icon.  
If you have custom genre names, then you can add them to the file `po/popups.xml`.

You'll see in that file a section

     <alt>
     ...
     </alt>
     
You can define a language specific alternative genre section like this:

     <alt xml:lang='fr'>
     ....
     </alt>
     
Remember to raise an issue on GitHub if you want your custom genres wrapped up in the next release of this plugin

 - Find embedded covers

 New plugin (Edit - Plugins - CoverArt Embedded Cover Search).  When enabled, searches for cover images embedded in tracks within an album.

 *Tip* - untick the default Cover Art Search plugin if you only want to force the search for embedded covers. 

 - icon-tooltip shows all the track artists for multi-artist albums
 - ... and a number of bug-fixes as well.

*How to install:*

for debian & debian-based distros such as Ubuntu & Mint

    sudo apt-get install git gettext python-mako python-mutagen python-requests python-lxml

for fedora and similar:

    yum install git gettext python-mako python-mutagen python-requests python-lxml

Then install the plugin:

<pre>
rm -rf ~/.local/share/rhythmbox/plugins/coverart_browser
git clone https://github.com/fossfreedom/coverart-browser.git -b master
cd coverart-browser
sh ./install.sh
</pre>

*For Ubuntu 12.04 & 12.10:*

<del>This is now available in my rhythmbox PPA - installation instructions in this AskUbuntu Q&A:

http://askubuntu.com/questions/147942/how-do-i-install-third-party-rhythmbox-plugins</del>

**IMPORTANT NOTE**

For Ubuntu 12.04 users that have upgraded to Rhythmbox v2.98 using the webupd8 PPA, this version 
of rhythmbox crashes when used with python plugins such as coverart-browser and replaygain.

It is strongly recommended that you either upgrade to 12.10 where v2.98 works great, or 
downgrade to v2.96 or v2.97 as per:
 - http://askubuntu.com/questions/201093/how-do-i-downgrade-rhythmbox-v2-98

**Please help out with translating**

We need you to help us translate the english text to your native language.

Don't worry - it is easier that you think.

Just visit:

 - https://translations.launchpad.net/coverartbrowser

Remember to set your preferred language and then just submit your translation.

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
 - our Translators: Launchpad Translation team, jrbastien (fr_CA), asermax (es), mateuswetah (pt_BR), jrbastien & lannic (fr.po)
 - Button Icons - jrbastien for the new iconset

 Licenses:

 This plugin code is released under the GPL3+ license.

 All translations are released under the BSD license

 Genre icon-set:
 
 <a rel="license" href="http://creativecommons.org/licenses/by-nc-nd/3.0/deed.en_US"><img alt="Creative Commons License" style="border-width:0" src="http://i.creativecommons.org/l/by-nc-nd/3.0/80x15.png" /></a><br /><span xmlns:dct="http://purl.org/dc/terms/" href="http://purl.org/dc/dcmitype/StillImage" property="dct:title" rel="dct:type">Music Genre Icons</span> by <a xmlns:cc="http://creativecommons.org/ns#" href="http://meghnlofing.com" property="cc:attributionName" rel="cc:attributionURL">Meghn Lofing</a> is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-nc-nd/3.0/deed.en_US">Creative Commons Attribution-NonCommercial-NoDerivs 3.0 Unported License</a>

Contrast of the iconset has been altered as agreed by the author.  Thanks Meghn!

------

GTK3 port of code.google.com/p/rhythmbox-cover-art-browser
