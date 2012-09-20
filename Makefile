DESTDIR=
SUBDIR=/usr/lib/rhythmbox/plugins/coverart_browser/
DATADIR=/usr/share/rhythmbox/plugins/coverart_browser/
LOCALEDIR=/usr/share/locale/

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
	cd po;./lang.sh $(DESTDIR)$(LOCALEDIR)
