#!/bin/bash

################################ USAGE #######################################

usage=$(
cat <<EOF
Usage:
$0 [OPTION]
-h, --help      show this message.
-2, --rb2     install the plugin for rhythmbox version 2.96 to 2.99 (default).
-3, --rb3       install the plugin for rhythmbox 3

EOF
)

########################### OPTIONS PARSING #################################

#parse options
TMP=`getopt --name=$0 -a --longoptions=rb2,rb3,help -o 2,3,h -- $@`

if [[ $? == 1 ]]
then
    echo
    echo "$usage"
    exit
fi

eval set -- $TMP

until [[ $1 == -- ]]; do
    case $1 in
        -2|--rb2)
            RB=true
            ;;
        -3|--rb3)
            RB=false
            ;;
        -h|--help)
            echo "$usage"
            exit
            ;;
    esac
    shift # move the arg list to the next option or '--'
done
shift # remove the '--', now $1 positioned at first argument if any

#default values
RB=${RB:=true}

########################## START INSTALLATION ################################

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

#install the plugin; the install path depends on the install mode
if [[ $RB == false ]]
then
    mv "$PLUGIN_PATH"coverart_browser.plugin3 "$PLUGIN_PATH"coverart_browser.plugin
fi

#remove the install script from the dir (not needed)
rm "${PLUGIN_PATH}${SCRIPT_NAME}"

#install translations
cd po; sudo ./lang.sh /usr/share/locale/

#install the glib schema
echo "Installing the glib schema (password needed)"
sudo cp "${PLUGIN_PATH}${SCHEMA_FOLDER}${GLIB_SCHEME}" "$GLIB_DIR"
sudo glib-compile-schemas "$GLIB_DIR"
