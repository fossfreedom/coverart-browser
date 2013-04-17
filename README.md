#coverart-browser v0.8 (in development)
================

Browse your coverart albums in Rhythmbox v2.96 and later

![Imgur](http://i.imgur.com/yXYmcOt.png)

-----------

##Authors

 - asermax <asermax@gmail.com>, website - https://github.com/asermax

[![Flattr Button](http://api.flattr.com/button/button-compact-static-100x17.png "Flattr This!")](http://flattr.com/thing/1262052/asermax-on-GitHub "asermax")

 - fossfreedom <foss.freedom@gmail.com>, website - https://github.com/fossfreedom

[![Flattr Button](http://api.flattr.com/button/button-compact-static-100x17.png "Flattr This!")](https://flattr.com/thing/1238849/fossfreedom-at-Flattr "fossfreedom")  [![paypaldonate](https://www.paypalobjects.com/en_GB/i/btn/btn_donate_SM.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=KBV682WJ3BDGL)
-----------

##Summary: whats new in this release

 - Export whole albums and embed coverart in the album tracks so that (where required) phones/tablets can display coverart correctly
 - Drag & Drop CoverArt icons onto playlists and sources (such as a phone) so that all tracks for an album are added
 - separated coverart search into separate plugin (this is now a prerequisite) - https://github.com/fossfreedom/coverart-search-providers
 - New light & dark theme buttons to complement light & dark desktop themes
 - optional flat-button toolbar style
 - revised popup menu style genre & playlist windows when number of entries would exceed the desktop height
 - Use album and album-artist sort order tags for sorting if these values are utilised
 - Play from Cover-view and Track view instead of queuing & playing
 - Allow user-defined genre names to be created mapped against default system genre icons
 - Allow user-defined genre icons to be displayed. These can override system genre icons if required
 - Support for other plugins via right-click menu options in a similar manner as the Library Browser - 

 OpenContainingFolder, SendFirst, Send Track, LastFMExtension - Fingerprinter, FileOrganizer, lLyrics, WikipediaSearch

 N.B. if NOT using my PPA then ensure you have the very latest version of the plugins installed.

 - for developers - doxygen documentation: http://fossfreedom.github.io/coverart-browser/classes.html

*How it works:*

 - Click the new CoverArt source button (left hand side of screen)
 - Albums are displayed as clickable buttons containing their album cover
 - Right click menu option to play, queue & search for coverart for an album.

 - https://github.com/fossfreedom/coverart-browser/wiki/How-the-plugin-works

*How to install:*

for debian & debian-based distros such as Ubuntu & Mint

    sudo apt-get install git gettext python-mako python-lxml

for fedora and similar:

    yum install git gettext python-mako python-lxml

Then install the plugin:

<pre>
rm -rf ~/.local/share/rhythmbox/plugins/coverart_browser
git clone https://github.com/fossfreedom/coverart-browser.git -b master
cd coverart-browser
sh ./install.sh
</pre>

Note - the CoverArt Browser plugin also requires installing the following plugin:

 - https://github.com/fossfreedom/coverart-search-providers

*For Ubuntu 12.04 & 12.10:* --- NOT YET - INSTRUCTIONS BELOW ONLY VALID ON RELEASE OF v0.8

This is now available in my rhythmbox PPA - installation instructions in this AskUbuntu Q&A:

http://askubuntu.com/questions/147942/how-do-i-install-third-party-rhythmbox-plugins

Note - installing the package `coverart-browser` will also install `coverart-search-providers`

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

Credits:

 - thanks to Luqman Aden <laden@uwaterloo.ca> for the coverart-search plugin which our cover-search pane is based upon
 - thanks to Canonical for the Star widget which the ratings capabilities use
 - our Translators: Launchpad Translation team, jrbastien (fr_CA), asermax (es), mateuswetah (pt_BR), jrbastien & lannic (fr.po)
 - Button Icons - jrbastien for the three toolbar icon-sets (standard, light & dark)

 Licenses:

 This plugin code is released under the GPL3+ license.

 All translations are released under the BSD license

 Genre icon-set:
 
 <a rel="license" href="http://creativecommons.org/licenses/by-nc-nd/3.0/deed.en_US"><img alt="Creative Commons License" style="border-width:0" src="http://i.creativecommons.org/l/by-nc-nd/3.0/80x15.png" /></a><br /><span xmlns:dct="http://purl.org/dc/terms/" href="http://purl.org/dc/dcmitype/StillImage" property="dct:title" rel="dct:type">Music Genre Icons</span> by <a xmlns:cc="http://creativecommons.org/ns#" href="http://meghnlofing.com" property="cc:attributionName" rel="cc:attributionURL">Meghn Lofing</a> is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-nc-nd/3.0/deed.en_US">Creative Commons Attribution-NonCommercial-NoDerivs 3.0 Unported License</a>

Contrast of the iconset has been altered as agreed by the author.  Thanks Meghn!

------

GTK3 port of code.google.com/p/rhythmbox-cover-art-browser
