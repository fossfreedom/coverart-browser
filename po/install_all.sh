#!/bin/sh
default="/usr/share/locale/"
echo "installing languages to $default"
for i in *.po; do
	lang=`basename $i .po`
	echo "installing $lang"
	install -d $default$lang/LC_MESSAGES
	msgfmt -c $lang.po -o $default$lang/LC_MESSAGES/coverart_browser.mo
done
