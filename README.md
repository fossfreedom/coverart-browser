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

 - *NEW* - Right click to search for missing covers

![Imgur](http://i.imgur.com/QmHzi.png)

 - *NEW* - locale support has been added to display text in your native language.

**HELP WANTED** - We need your help to translate - please help out! (see below)

*How to install (64bit linux distro users only):*

1. install *git&
N.B. for debian based distros - `sudo apt-get install git`
2. install the package *gettext*
N.B. for debian based distros - `sudo apt-get install gettext`

<pre>
rm -rf ~/.local/share/rhythmbox/plugins/coverart_browser
git clone https://github.com/fossfreedom/coverart-browser.git
cd coverart-browser
sh ./install.sh
</pre>

N.B. 32bit users have a serious bug leading to a *segmentation fault*
     The bug occurs when querying the rhythmbox database - 
     Sorry! (https://bugzilla.gnome.org/show_bug.cgi?id=682294)

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
