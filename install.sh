#!/bin/bash
SCRIPT_NAME=`basename "$0"`
SCRIPT_PATH=${0%`basename "$0"`}
PLUGIN_PATH="/home/${USER}/.local/share/rhythmbox/plugins/coverart_browser/"
GLIB_SCHEME="org.gnome.rhythmbox.plugins.coverart_browser.gschema.xml"
SCHEMA_FOLDER="schema/"
GLIB_DIR="/usr/share/glib-2.0/schemas/"

#build the dirs
mkdir -p $PLUGIN_PATH

#copy the files
cp -r "${SCRIPT_PATH}"* "$PLUGIN_PATH"

#remove the install script from the dir (not needed)
rm "${PLUGIN_PATH}${SCRIPT_NAME}"

#install translations
cd po; sudo ./lang.sh /usr/share/locale/

#install the glib schema
echo "Installing the glib schema (password needed)"
sudo cp "${PLUGIN_PATH}${SCHEMA_FOLDER}${GLIB_SCHEME}" "$GLIB_DIR"
sudo glib-compile-schemas "$GLIB_DIR"
