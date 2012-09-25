DESTDIR=
SUBDIR=/usr/lib/rhythmbox/plugins/coverart_browser/
DATADIR=/usr/share/rhythmbox/plugins/coverart_browser/
LOCALEDIR=/usr/share/locale/
GLIB_SCHEME=org.gnome.rhythmbox.plugins.coverart_browser.gschema.xml
GLIB_DIR=/usr/share/glib-2.0/schemas/


all:
clean:
	- rm *.pyc

install:
	install -d $(DESTDIR)$(SUBDIR)
	install -m 644 *.py $(DESTDIR)$(SUBDIR)
	install -d $(DESTDIR)$(DATADIR)
	install -m 644 *.png $(DESTDIR)$(DATADIR)
	install -m 644 *.svg $(DESTDIR)$(DATADIR)
	install -m 644 *.ui $(DESTDIR)$(DATADIR)
	install -m 644 coverart_browser.plugin $(DESTDIR)$(SUBDIR)
	install -d $(DESTDIR)$(GLIB_DIR)
	install -m 644 $(GLIB_SCHEME) $(DESTDIR)$(GLIB_DIR) 
	cd po;./lang.sh $(DESTDIR)$(LOCALEDIR)
