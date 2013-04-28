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
	install -d $(DESTDIR)$(DATADIR)img
	install -m 644 img/*.png $(DESTDIR)$(DATADIR)img/
	install -m 644 img/*.svg $(DESTDIR)$(DATADIR)img/
	install -m 644 img/*.xml $(DESTDIR)$(DATADIR)img/
	install -d $(DESTDIR)$(DATADIR)img/dark
	install -m 644 img/dark/*.png $(DESTDIR)$(DATADIR)img/dark
	install -d $(DESTDIR)$(DATADIR)img/light
	install -m 644 img/light/*.png $(DESTDIR)$(DATADIR)img/light
	install -d $(DESTDIR)$(DATADIR)img/standard
	install -m 644 img/standard/*.png $(DESTDIR)$(DATADIR)img/standard
	install -d $(DESTDIR)$(DATADIR)template
	install -m 644 template/*.xml $(DESTDIR)$(DATADIR)template
	install -d $(DESTDIR)$(DATADIR)ui
	install -m 644 ui/*.ui $(DESTDIR)$(DATADIR)ui/
	install -m 644 ui/*.xml $(DESTDIR)$(DATADIR)ui/
	install -m 644 coverart_browser.plugin $(DESTDIR)$(SUBDIR)
	install -d $(DESTDIR)$(DATADIR)tmpl
	install -m 644 tmpl/* $(DESTDIR)$(DATADIR)tmpl/
	install -d $(DESTDIR)$(GLIB_DIR)
	install -m 644 schema/$(GLIB_SCHEME) $(DESTDIR)$(GLIB_DIR) 
	cd po;./lang.sh $(DESTDIR)$(LOCALEDIR)
