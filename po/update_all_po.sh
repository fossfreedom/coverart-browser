#!/bin/sh
echo "updating po files"
for i in *.po; do
	lang=`basename $i .po`
	echo "updating $lang"
    intltool-update --dist $lang -g coverartbrowser
done

echo "update plugin file"

intltool-merge -d . ../coverart_browser.plugin.in ../coverart_browser.plugin
#intltool-merge -x -d . ../img/popups.xml.in ../img/popups.xml
