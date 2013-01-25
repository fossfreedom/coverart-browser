coverart-browser v0.7
================

Browse your coverart albums in Rhythmbox v2.96 and later

![Imgur](http://i.imgur.com/yXYmcOt.png)

-----------

**Please help out with translating - skip to the end for details**

Summary: whats new in this release

 - find & display embedded covers in MP3, M4A, FLAC & Ogg files
 - Optional coverart search from Discogs internet service
 - new filter by decade
 - configurable shadow effect behind cover display
 - Iconised filter & sort buttons that change icon depending upon option chosen
 - popup menu selection for filters
 - brand new icons designed explicitly to the coverart browser plugin
 - one click open and close track view for a cover
 - plugin translated into many more languages
 - plugin code refactored - much faster to start and display without any flashing effects
 - code has been completely documented using doxygen: http://fossfreedom.github.com/coverart-browser/classes.html
 - covers displayed using rhythmbox natural sort i.e. ascending numbers
 - search filter matches upper & lower-case as well as ignoring characters such as accents
 - display covers for play-queue/music library & playlists from within the coverart-view
 - column header sort in track view
 - revamped plugin preferences

*How it works:*

 - Click the new CoverArt source button (left hand side of screen)
 - Albums are displayed as clickable buttons containing their album cover
 - Right click menu option to play, queue & search for coverart for an album.

 - https://github.com/fossfreedom/coverart-browser/wiki/How-the-plugin-works

*How to install:*

for debian & debian-based distros such as Ubuntu & Mint

    sudo apt-get install git gettext python-mako python-mutagen python-requests python-lxml

for fedora and similar:

    yum install git gettext python-mako python-mutagen python-requests python-lxml

Then install the plugin:

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

*installation for embedded coverart*

The plugin makes use of the package `python-mutagen`.  For most distros, the default package is v1.20 which was released in 2010.

Since then, lots of bug fixes have been resolved.  If you know that there is coverart embedded, but is not displayed
in our plugin, then you should install the very latest package:

<pre>
sudo apt-get install python-pip
sudo pip install mutagen
</pre>

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
