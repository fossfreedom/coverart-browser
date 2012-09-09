coverart-browser
================

UNDER DEVELOPMENT - Feel free to look & help out!
Basics work - at least I think it does :)

Browse your cover-art albums in Rhythmbox

GTK3 port of code.google.com/p/rhythmbox-cover-art-browser

How it works:

1. Click the toolbar button
2. Albums are displayed as clickable buttons containing their album cover
3. Double-click or press space to play the album.
4. Right click menu option to queue an album.

How to install:

1. install git
N.B. for debian - sudo apt-get install git
2. git clone https://github.com/fossfreedom/coverart-browser.git
3. cd coverart-browser
4. sh ./install.sh

Notes:

 - this is a port of the GUI cover-art browser capability.
 
To Do:

1. investigate performance with large music collections
2. When clicking the toolbar option, it should automatically activate the music library source
N.B. currently, the albums are displayed at the top of any source that is currently active.

Random Musings:

1. Possible right click and display all tracks in a submenu to allow you to play a given track.
2. The code currently looks through all the songs in the library and works out what albums are there... but this is already done in the list view on the music source library.  Can we someone get hold of the album info thus saving all this processing.
3. If its possible to workout what signal is being sent when clicking on the album in the music source, should be possible to change focus on the plugin covers view.
4. likewise, clicking on the plugin covers icon, could we send a signal to the music source to the album list thus forcing a filter on the bottom of the screen to show all the tracks for the album

Other random stuff.

1. Integration with other plugins - e.g. WebMenu via right-click - should be useful
2. If the destination drop is enabled for the buttons then maybe possible to drop from file-manager a JPG to update the cover

