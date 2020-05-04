#!/bin/sh
# Script to generate mo files in a temp locale folder
# Use it only for testing purpose
export PLUGIN_HELLO=True
export PYTHONPATH="$HOME/test/gnome-layout-switcher/bin:$HOME/Data/projects/application-utility"
rm -rf locale
mkdir locale
cd po
for lang in $(ls *.po); do
    lang=${lang::-3}
    mkdir -p ../locale/${lang//_/-}/LC_MESSAGES
    msgfmt -c -o ../locale/${lang//_/-}/LC_MESSAGES/manjaro-hello.mo $lang.po
done
cd ..
python3 src/manjaro_hello.py --dev
