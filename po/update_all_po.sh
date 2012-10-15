#!/bin/sh
echo "updating po files"
for i in *.po; do
	lang=`basename $i .po`
	echo "updating $lang"
    intltool-update --dist $lang -g package
done
