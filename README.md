#coverart-browser v1.0
================

Browse your coverart albums in Rhythmbox v2.96 and later

![Imgur](http://i.imgur.com/yXYmcOt.png)

-----------

##Authors

 - asermax <asermax@gmail.com>, website - https://github.com/asermax

[![Flattr Button](http://api.flattr.com/button/button-compact-static-100x17.png "Flattr This!")](http://flattr.com/thing/1262052/asermax-on-GitHub "asermax")

 - fossfreedom <foss.freedom@gmail.com>, website - https://github.com/fossfreedom

[![Flattr Button](http://api.flattr.com/button/button-compact-static-100x17.png "Flattr This!")](http://flattr.com/thing/1811704/ "fossfreedom")  [![paypaldonate](https://www.paypalobjects.com/en_GB/i/btn/btn_donate_SM.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=KBV682WJ3BDGL)
-----------

##Summary: whats new in this release

 - 
 - Translated into 21 languages and locales
 - for developers - doxygen documentation: http://fossfreedom.github.io/coverart-browser/classes.html

*How it works:*

 - Click the new CoverArt source button (left hand side of screen)
 - Albums are displayed as clickable buttons containing their album cover
 - Right click menu option to play, queue & search for coverart for an album.
 
 - https://github.com/fossfreedom/coverart-browser/wiki/how-to-for-version-0.9

*How to install:*

for debian & debian-based distros such as Ubuntu & Mint:

    sudo apt-get install git gettext python-mako python-lxml

for fedora and similar:

    yum install git gettext python-mako python-lxml
    
for opensuse

    sudo zypper in git gettext-runtime python-mako python-lxml typelib-1_0-WebKit-3_0

Then install the plugin for rhythmbox version 2.96 to 2.99:

<pre>
rm -rf ~/.local/share/rhythmbox/plugins/coverart_browser
git clone https://github.com/fossfreedom/coverart-browser.git
cd coverart-browser
./install.sh
</pre>

To install the plugin for rhythmbox version 3.0 and later:

<pre>
rm -rf ~/.local/share/rhythmbox/plugins/coverart_browser
git clone https://github.com/fossfreedom/coverart-browser.git
cd coverart-browser
./install.sh --rb3
</pre>

Note 1 - the CoverArt Browser plugin also requires installing the following plugin:

 - https://github.com/fossfreedom/coverart-search-providers

Note 2 - IMPORTANT NOTE - for some distros that do not have rhythmbox webkit support, DO NOT install your
webkit library.  For these distros, it is highly likely that installing webkit v3 will
crash rhythmbox if this plugin is also installed and activated.

For example, opensuse 12.3 please do NOT install `typelib-1_0-WebKit-3_0`.

You also need to make the following change to enable the plugin to work:

    gsettings set org.gnome.rhythmbox.plugins.coverart_browser webkit-support false

Note 3 - Due to an upstream Rhythmbox bug affecting RB V2.98 & V2.99 only - any changes made to the details of a track 
are not reflected back into the plugin.  This can lead to inconsistencies.  Please restart rhythmbox for these details
to be correctly cached.  This bug is fixed in RB3.0 and does not affect RB2.96 & RB2.97 users

*For Ubuntu 12.04, 12.10, 13.04, 13.10 & 14.04:* - only applicable when master branch is released

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
 - Button Icons - jrbastien for the three toolbar icon-sets (standard, light & dark)
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
