# coverart-browser - v2.1.2 (Penfold)

Browse your coverart albums in Rhythmbox v3 and later.  

 - rhythmbox 2.96 - 2.99: https://github.com/fossfreedom/coverart-browser/tree/release-1.2

![Imgur](http://i.imgur.com/tTnHbE1.png)

-----------

## Authors

 - asermax <asermax@gmail.com>, website - https://github.com/asermax

[![Flattr Button](http://api.flattr.com/button/button-compact-static-100x17.png "Flattr This!")](http://flattr.com/thing/1262052/asermax-on-GitHub "asermax")

 - fossfreedom <foss.freedom@gmail.com>, website - https://github.com/fossfreedom

[![Flattr Button](http://api.flattr.com/button/button-compact-static-100x17.png "Flattr This!")](http://flattr.com/thing/1811704/ "fossfreedom")  [![paypaldonate](https://www.paypalobjects.com/en_GB/i/btn/btn_donate_SM.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=KBV682WJ3BDGL)
-----------

## Summary: whats new in this release

 - Allow switching between coverart-browser and the coverart-playlist sources via picture buttons on each source
 - tighter integration with Rhythmbox - addition of select and play using Rhythmbox's own toolbar play button 
 - Support the [alternative-toolbar](https://github.com/fossfreedom/alternative-toolbar) capability to hide/show the coverart-toolbar
 - Support for GTK 3.14
 - Support for the upcoming release of Rhythmbox (3.2)
 - Single click icon display position changes consistently depending upon the cover-tile style (shadow/no shadow etc.)
 - view/zoom/save the chosen cover - hover over the coverart on the track pane to reveal
 - coverart information in tile-view can be now left/centre & right aligned
 - Double click track & cover pane handle to open full height or to close
 - Play Next (album)- add the selected album(s) to be the next album after the current playing album
 - Play Next (track)- add the selected track(s) to be the next track after the current playing track
 - Track Artist and Artist Information Panes can be opened and closed via double-click of the pane-handle
 - Bottom Track & Cover Pane has more space - the expander & label has been removed
 - Tidied display - visible pane handles disappear after the plugin has been run 5 times 
 - Add ability to resize Icon-view with CTRL+mouse wheel scroll 
 - Translated into 27 languages and locales
 - for developers - doxygen documentation: http://fossfreedom.github.io/coverart-browser/classes.html
 - v2.1.1 - v2.1.2 - translation updates

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

for Debian & Debian-based distros such as Ubuntu & Mint:

    sudo apt-get install git gettext python3-mako gir1.2-notify-0.7 python3-lxml python3-gi-cairo python3-cairo gstreamer1.0-plugins-ugly gstreamer1.0-plugins-good gstreamer1.0-plugins-bad rhythmbox-plugins gir1.2-webkit-3.0

for Fedora and similar:

    sudo yum install git gettext python3-mako python3-lxml python3-cairo webkitgtk3

NOTE: it is assumed that you have separately installed the patent encumbered codecs found in the good/bad & ugly packages
To install the plugin:

<pre>
rm -rf ~/.local/share/rhythmbox/plugins/coverart_browser
git clone https://github.com/fossfreedom/coverart-browser.git
cd coverart-browser
./install.sh
</pre>

*Support for Debian 12 (Bookworm):*

To make it work on Debian 12 (Bookworm), you need to add the stretch repository (as the necessary packages stopped at stretch). Don't worry, this tip has already been tested and it doesn't break the system.

<pre>
echo "deb https://archive.debian.org/debian/ stretch main" | sudo tee -a /etc/apt/sources.list
sudo apt update
sudo apt install gir1.2-webkit-3.0
</pre>


*Support for Ubuntu 20.04:*

To make it work on Ubuntu 20.04, you need to add the bionic (ubuntu 18.04) repository (as the necessary packages stopped at bionic). Don't worry, this tip has already been tested and it doesn't break the system.

<pre>
echo "deb http://de.archive.ubuntu.com/ubuntu/ bionic main universe" | sudo tee -a /etc/apt/sources.list
sudo apt update
sudo apt-get install git gettext python3-mako gir1.2-notify-0.7 python3-lxml python3-gi-cairo python3-cairo gstreamer1.0-plugins-ugly gstreamer1.0-plugins-good gstreamer1.0-plugins-bad rhythmbox-plugins gir1.2-webkit-3.0
</pre>

To uninstall the plugin:

<pre>
cd coverart-browser
./install.sh --uninstall
</pre>

Note 1 - the CoverArt Browser plugin also requires installing the following plugin:

 - https://github.com/fossfreedom/coverart-search-providers

*For Ubuntu 14.04 and later:*

V2.1.2 is now available in my rhythmbox PPA - installation instructions in this AskUbuntu Q&A:

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

 Licenses:

 This plugin code is released under the GPL3+ license.
 
 Contentflow source is released under the MIT license

 All translations are released under the BSD license

 Genre icon-set:
 
 <a rel="license" href="http://creativecommons.org/licenses/by-nc-nd/3.0/deed.en_US"><img alt="Creative Commons License" style="border-width:0" src="http://i.creativecommons.org/l/by-nc-nd/3.0/80x15.png" /></a><br /><span xmlns:dct="http://purl.org/dc/terms/" href="http://purl.org/dc/dcmitype/StillImage" property="dct:title" rel="dct:type">Music Genre Icons</span> by <a xmlns:cc="http://creativecommons.org/ns#" href="http://meghnlofing.com" property="cc:attributionName" rel="cc:attributionURL">Meghn Lofing</a> is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-nc-nd/3.0/deed.en_US">Creative Commons Attribution-NonCommercial-NoDerivs 3.0 Unported License</a>

Contrast of the iconset has been altered as agreed by the author.  Thanks Meghn!

------

GTK3 port of code.google.com/p/rhythmbox-cover-art-browser
