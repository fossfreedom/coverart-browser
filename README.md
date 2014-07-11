#coverart-browser v2.0 release candidate

Browse your coverart albums in Rhythmbox v3 and later.  

![Imgur](http://i.imgur.com/sUgX7d7.png)

-----------

##Authors

 - asermax <asermax@gmail.com>, website - https://github.com/asermax

[![Flattr Button](http://api.flattr.com/button/button-compact-static-100x17.png "Flattr This!")](http://flattr.com/thing/1262052/asermax-on-GitHub "asermax")

 - fossfreedom <foss.freedom@gmail.com>, website - https://github.com/fossfreedom

[![Flattr Button](http://api.flattr.com/button/button-compact-static-100x17.png "Flattr This!")](http://flattr.com/thing/1811704/ "fossfreedom")  [![paypaldonate](https://www.paypalobjects.com/en_GB/i/btn/btn_donate_SM.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=KBV682WJ3BDGL)
-----------

##Summary: whats new in this release

 - Compact & Full track view toggle option:
    1. Compact: fixed track view showing the key album track fields & ratings together with an enlarged album cover
    1. Full: Standard track view configurable via the preferences window
 - Smart continuous playlist: Play Similar Artists as recommended by EchoNest
 - Smart continuous playlist: Play Similar Genres as recommended by EchoNest
 - Smart continuous playlist: Play Similar Tracks as recommended by LastFM
 - New optional theme: darker toolbar icons by the graphics artist [jrbastien](https://github.com/jrbastien)
 - New subtle hover, play & queue icons by the graphics artist [jrbastien](https://github.com/jrbastien)
 - Introduce more modern look & feel through subtle animations
 - Views button ("…") now can navigate to Play Queue.  Allows navigation of key views without the side-bar (F9) being visible
 - Artist & Album information pane with LastFM & EchoNest data
 - Artist & Album information is fully localised (in your native language) if LastFM returns information in your locale
 - Information pane can be made visible or hidden by dragging the pane-handle
 - Track Artist Filter and Artist & Album Information panes individually displayed per view
 - Support Jump To Playing CTRL+J to scroll to the playing album
 - Follow playing song option automatically selects playing album
 - Custom Genres are now saved in an alternative folder location to survive re-installation of the plugin
 - Search Filter by Composer
 - Introduce type-ahead Search filtering to improve searching usability
 - Single click to append album to list of playing albums
 - Right-click to append album to list of playing albums
 - View and modify the list of album tracks being played 
 - Optional support for [SmallWindow](https://github.com/fossfreedom/smallwindow) plugin - allows Rhythmbox to be toggled between its standard application window and its smaller counterpart
 - Translated into 24 languages and locales
 - for developers - doxygen documentation: http://fossfreedom.github.io/coverart-browser/classes.html

*How it works:*

 - Click the new CoverArt Browser source button (left hand side of screen)
 - Albums are displayed as clickable buttons containing their album cover
 - Right click menu option to play, queue & search for coverart for an album.
 - Download Album & artist artwork via the properties toolbar button
 
 - https://github.com/fossfreedom/coverart-browser/wiki/how-to-for-version-2.0
 - https://github.com/fossfreedom/coverart-browser/wiki/Screenshots

*How to install - Rhythmbox 3.0 and later:*

N.B. for earlier Rhythmbox versions use version 1.x

Prerequisite is to use a distribution supporting GTK 3.10 or later - for example, Ubuntu 14.04, Arch or Fedora 20

for debian & debian-based distros such as Ubuntu & Mint:

    sudo apt-get install git gettext python3-mako python3-lxml python3-gi-cairo python3-cairo gstreamer1.0-plugins-ugly gstreamer1.0-plugins-good gstreamer1.0-plugins-bad rhythmbox-plugins

for fedora and similar:

    sudo yum install git gettext python3-mako python3-lxml python3-cairo

NOTE: it is assumed that you have separately installed the patent encumbered codecs found in the good/bad & ugly packages
To install the plugin:

<pre>
rm -rf ~/.local/share/rhythmbox/plugins/coverart_browser
git clone https://github.com/fossfreedom/coverart-browser.git
cd coverart-browser
./install.sh
</pre>

To uninstall the plugin:

<pre>
cd coverart-browser
./install.sh --uninstall
</pre>

Note 1 - the CoverArt Browser plugin also requires installing the following plugin:

 - https://github.com/fossfreedom/coverart-search-providers

*For Ubuntu 14.04 and later:*

V2.0 is now available in my rhythmbox PPA - installation instructions in this AskUbuntu Q&A:

http://askubuntu.com/questions/147942/how-do-i-install-third-party-rhythmbox-plugins

Note - installing the package `rhythmbox-plugin-coverart-browser` will also install `rhythmbox-plugin-coverart-search`

**Please help out with translating**

We need you to help us translate the english text to your native language.

Don't worry - it is easier that you think. Just visit:

 - https://translations.launchpad.net/coverartbrowser

Remember to set your preferred language and then just submit your translation.

-------

Credits:

 - thanks to Luqman Aden <laden@uwaterloo.ca> for the coverart-search plugin which our cover-search pane is based upon
 - thanks to Canonical for the Star widget which the ratings capabilities use
 - our Translators: Launchpad Translation team - individual credits for each locale is shown in the plugin preferences dialog
 - Button Icons - [jrbastien](https://github.com/jrbastien) for the five toolbar icon-sets
 - Flow view is based upon [Contentflow](http://jacksasylum.eu/ContentFlow)
 - Chief Tester and all-round good egg - jrbastien!

 Licenses:

 This plugin code is released under the GPL3+ license.
 
 Contentflow source is released under the MIT license

 All translations are released under the BSD license

 Genre icon-set:
 
 <a rel="license" href="http://creativecommons.org/licenses/by-nc-nd/3.0/deed.en_US"><img alt="Creative Commons License" style="border-width:0" src="http://i.creativecommons.org/l/by-nc-nd/3.0/80x15.png" /></a><br /><span xmlns:dct="http://purl.org/dc/terms/" href="http://purl.org/dc/dcmitype/StillImage" property="dct:title" rel="dct:type">Music Genre Icons</span> by <a xmlns:cc="http://creativecommons.org/ns#" href="http://meghnlofing.com" property="cc:attributionName" rel="cc:attributionURL">Meghn Lofing</a> is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-nc-nd/3.0/deed.en_US">Creative Commons Attribution-NonCommercial-NoDerivs 3.0 Unported License</a>

Contrast of the iconset has been altered as agreed by the author.  Thanks Meghn!

------

GTK3 port of code.google.com/p/rhythmbox-cover-art-browser
