#coverart-browser v1.1 beta
================

Browse your coverart albums in Rhythmbox v2.96 and later

![Imgur](http://i.imgur.com/YoEQ8fc.png)

-----------

##Authors

 - asermax <asermax@gmail.com>, website - https://github.com/asermax

[![Flattr Button](http://api.flattr.com/button/button-compact-static-100x17.png "Flattr This!")](http://flattr.com/thing/1262052/asermax-on-GitHub "asermax")

 - fossfreedom <foss.freedom@gmail.com>, website - https://github.com/fossfreedom

[![Flattr Button](http://api.flattr.com/button/button-compact-static-100x17.png "Flattr This!")](http://flattr.com/thing/1811704/ "fossfreedom")  [![paypaldonate](https://www.paypalobjects.com/en_GB/i/btn/btn_donate_SM.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=KBV682WJ3BDGL)
-----------
##Summary: whats new in this release 1.1
 - This is primarily a bug-fix release
 - fix for right-click playlist support for Ubuntu 14.04
 - check if lastfm plugin is activated correctly implemented for artist-view
 - fix for "shudder" in artist-view for RB2.99

##Summary: whats new in this release 1.0

 - single click play for O/S's using GTK+3.6 or later for Tile-view
 - new artists view: displays album-artists in a tree-view
 - artists view: clicking on an album-artist displays the albums for that artist
 - artists view: Download all artist covers using the covers properties menu option
 - artists view: ... or drag and drop covers from cover view or from nautilus/firefox
 - artists view: drag and drop of albums to playlists
 - artists view: Filter buttons or filter search/quick track filter correctly filters view to show only the artists that have those filtered albums
 - artists view: hovering the mouse pointer over the artist cover displays a tooltip of a larger version of the cover
 - artists view: supports sorting of album-artist via clicking on its column header - ascending/descending/unsorted.
 - artists view: right click of albums displays the same right click menu as in tile view or coverflow view
 - artists view: right click of artists to play or queue all albums for that artist
 - artists view: independent sort toolbar buttons - for example show albums for an artist by ascending year whilst in the tile view show albums by name
 - new look (optional) to display album information within (on top of) the cover rather than below (beneath) the cover
 - new lighter icon-theme from the brilliant designer - jrbastien
 - new Rhythmbox 3 coverart source icon - again from jrbastien
 - Look & Feel integration: Rhythmbox 3 style toolbar and button popup menus
 - Look & Feel integration: New toolbar menu-button to switch between views including RB's own library view
 - Look & Feel integration: New toolbar menu-button in RB's library view to switch to plugin views (RB v3 and later)
 - Optional export and embed coverart from most file-formats to MP3.
 - Remember quick artist filter between rhythmbox sessions
 - support drag-and-drop of albums onto playlists or external devices for RB2.99 and later
 - Rework Album & Playlist favourite supports - this declutters menus and now can be optionally enabled through properties button
 - Right click support for the external plugin Repeat One Song
 - Optionally use sort fields for album artists or album artists (right click - properties - sort tab)
 - Use new Rhythmbox 3 progress bars for loading
 - Tooltip support to display cover name and artist only if album information is not already displayed
 - Translated into 25 languages and locales
 - for developers - doxygen documentation: http://fossfreedom.github.io/coverart-browser/classes.html

*How it works:*

 - Click the new CoverArt source button (left hand side of screen)
 - Albums are displayed as clickable buttons containing their album cover
 - Right click menu option to play, queue & search for coverart for an album.
 - Download Album & artist artwork via the properties toolbar button
 
 - https://github.com/fossfreedom/coverart-browser/wiki/how-to-for-version-1.0
 - https://github.com/fossfreedom/coverart-browser/wiki/Screenshots

*How to install - Rhythmbox 2.96 to 2.99.1:*

for debian & debian-based distros such as Ubuntu & Mint:

    sudo apt-get install git gettext python-mako python-lxml python-gi-cairo python-cairo gstreamer0.10-plugins-ugly gstreamer0.10-plugins-good gstreamer0.10-plugins-bad

for fedora and similar:

    yum install git gettext python-mako python-lxml
    
what is the fedora equivalent of gstreamer0.10-plugins-ugly/gstreamer0.10-plugins-good/gstreamer0.10-plugins-bad ?
    
for opensuse

    sudo zypper in git gettext-runtime python-mako python-lxml typelib-1_0-WebKit-3_0
    
what is the opensuse equivalent of gstreamer0.10-plugins-ugly/gstreamer0.10-plugins-good/gstreamer0.10-plugins-bad? 

Then install the plugin:

<pre>
rm -rf ~/.local/share/rhythmbox/plugins/coverart_browser
git clone https://github.com/fossfreedom/coverart-browser.git
cd coverart-browser
./install.sh
</pre>

*How to install - Rhythmbox 3.0 and later:*

for debian & debian-based distros such as Ubuntu & Mint:

    sudo apt-get install git gettext python3-mako python3-lxml python3-gi-cairo python3-cairo gstreamer1.0-plugins-ugly gstreamer1.0-plugins-good gstreamer1.0-plugins-bad

python3 based package instructions for OpenSuse and Fedora not known

To install the plugin:

<pre>
rm -rf ~/.local/share/rhythmbox/plugins/coverart_browser
git clone https://github.com/fossfreedom/coverart-browser.git
cd coverart-browser
./install.sh --rb3
</pre>

Note 1 - the CoverArt Browser plugin also requires installing the following plugin:

 - https://github.com/fossfreedom/coverart-search-providers

Note 2 - IMPORTANT NOTE - for some distros (e.g. OpenSuse 12.3) that do not have rhythmbox webkit support, DO NOT install your
webkit library.  For these distros, it is highly likely that installing webkit v3 will
crash rhythmbox if this plugin is also installed and activated.

If your distro crashes with the webkit elements of the application (CoverFlow or CoverArt) use the following workaround:

    gsettings set org.gnome.rhythmbox.plugins.coverart_browser webkit-support false

Note 3 - Due to an upstream Rhythmbox bug affecting RB V2.98 & V2.99 only - any changes made to the details of a track 
are not reflected back into the plugin.  This can lead to inconsistencies.  Please restart rhythmbox for these details
to be correctly cached.  This bug is fixed in RB3.0 and does not affect RB2.96 & RB2.97 users

Note 3 - For ubuntu and Gnome-Shell users

If you have install Gnome-Shell and you see ugly black areas in the track-cover area when expanded, this is a known Ubuntu bug due to overlay scrollbars.

One suggested workaround is to turn off overlay scrollbars:

    gsettings set com.canonical.desktop.interface scrollbar-mode normal

*For Ubuntu 12.04, 12.10, 13.04, 13.10 & 14.04:*

V1.0 is now available in my rhythmbox PPA - installation instructions in this AskUbuntu Q&A:

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
 - Button Icons - jrbastien for the four toolbar icon-sets (standard, light, lighter & dark)
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
