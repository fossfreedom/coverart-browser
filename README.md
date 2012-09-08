coverart-browser
================

UNDER DEVELOPMENT - Feel free to look & help out!
Basics work - at least I think it does :)

Browse your cover-art albums in Rhythmbox

GTK3 port of code.google.com/p/rhythmbox-cover-art-browser

How it works:

1. Click the toolbar button
2. Albums are displayed as clickable buttons containing their album cover
3. Double-click the cover to play the album.
4. Right click menu option to queue an album.

How to install:

1. install git
N.B. for debian - sudo apt-get install git
2. git clone https://github.com/fossfreedom/coverart-browser.git
3. cd coverart-browser
4. sh ./install.sh

Notes:

 - this will be a port of the GUI cover-art browser capability.
 - Drag-drop, cover-search and right-click copy is unlikely to be ported

Random Musings:

1. Consider when double clicking the album whether to create a playlist to play the album from or like currently just to wipe the Queue and add the tracks from the album
2. Maybe hover over the album to display important facts - number of tracks, duration etc.  Have a look how other media players handles this
3. Possible right click and display all tracks in a submenu to allow you to play a given track.

Other random stuff.

1. Integration with other plugins - e.g. WebMenu via right-click - should be useful
2. If the destination drop is enabled for the buttons then maybe possible to drop from file-manager a JPG to update the cover
3. May be allow multi-select of buttons, right click and add selected albums to the queue/playlist


