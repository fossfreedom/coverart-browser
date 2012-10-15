coverart-browser
================

Browse your coverart albums in Rhythmbox v2.96 and later

![Imgur](http://i.imgur.com/JRJKF.png)

GTK3 port of code.google.com/p/rhythmbox-cover-art-browser

How it works:

 - Click the new CoverArt source button (left hand side of screen)
 - Albums are displayed as clickable buttons containing their album cover
 - Right click menu option to play, queue & search for cover art for an album.

![Imgur](http://i.imgur.com/XCAdF.png)

 - Right click to search for missing covers

![Imgur](http://i.imgur.com/QmHzi.png)

 - locale support has been added to display text in your native language.

**HELP WANTED** - We need your help to translate - please help out! (see below)
 - *NEW* - Filter your albums

![Imgur](http://i.imgur.com/1QEfH.png)

 - *NEW* - position of status bar text is configurable

![Imgur](http://i.imgur.com/LWSFR.png)

 - *NEW* - 32bit support now available
 - *NEW* - icon-tooltip now show all the track artists for multi-artist albums
 - *NEW* - automatic album focus when right-click an album to display album choices.
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
