# -*- Mode: python; coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
#
# Copyright (C) 2014 - fossfreedom
# GTK3 port https://github.com/exaile-dev/exaile/blob/master/xlgui/cover.py
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301  USA.

from gi.repository import Gtk
from gi.repository import GdkPixbuf
from coverart_browser_prefs import CoverLocale
from gi.repository import GObject
import rb


class CoverWindow(GObject.Object):
    """Shows the cover in a simple image viewer"""

    # signals
    __gsignals__ = {
        'close-window': (GObject.SIGNAL_RUN_LAST, None, ())
    }

    def __init__(self, plugin, parent, savedir=None):
        """Initializes and shows the cover

        :param plugin: source
        :type plugin: RBSource
        :param parent: Parent window to attach to
        :type parent: Gtk.Window
        :param savedir: Initial directory for the Save As functionality
        :type savedir: basestring
        """

        super(CoverWindow, self).__init__()
        cl = CoverLocale()
        cl.switch_locale(cl.Locale.LOCALE_DOMAIN)
        self.builder = Gtk.Builder()
        self.builder.add_from_file(rb.find_plugin_file(plugin,
                                                       'ui/coverart_window.ui'))
        self.builder.connect_signals(self)

        self.cover_window = self.builder.get_object('CoverWindow')
        self.cover_window.connect('destroy', self.send_destroy_signal)
        self.layout = self.builder.get_object('layout')
        self.toolbar = self.builder.get_object('toolbar')
        self.save_as_button = self.builder.get_object('save_as_button')
        self.zoom_in_button = self.builder.get_object('zoom_in_button')
        self.zoom_out_button = self.builder.get_object('zoom_out_button')
        self.zoom_100_button = self.builder.get_object('zoom_100_button')
        self.zoom_fit_button = self.builder.get_object('zoom_fit_button')
        self.close_button = self.builder.get_object('close_button')
        self.image = self.builder.get_object('image')
        self.statusbar = self.builder.get_object('statusbar')
        self.scrolledwindow = self.builder.get_object('scrolledwindow')
        self.scrolledwindow.set_hadjustment(self.layout.get_hadjustment())
        self.scrolledwindow.set_vadjustment(self.layout.get_vadjustment())

        self.savedir = savedir

        if parent:
            self.cover_window.set_transient_for(parent)
        self.cover_window_width = 500
        self.cover_window_height = 500 + self.toolbar.size_request().height + \
                                   self.statusbar.size_request().height
        self.cover_window.set_default_size(self.cover_window_width, \
                                           self.cover_window_height)

        self.min_percent = 1
        self.max_percent = 500
        self.ratio = 1.5
        self.image_interp = GdkPixbuf.InterpType.BILINEAR
        self.image_fitted = True

    def send_destroy_signal(self, *args):
        self.emit('close-window')

    def show_all(self, title, pixbuf):
        self.image_original_pixbuf = pixbuf
        self.image_pixbuf = self.image_original_pixbuf

        self.cover_window.set_title(title)
        self.cover_window.show_all()
        self.set_ratio_to_fit()
        self.update_widgets()

    def available_image_width(self):
        """Returns the available horizontal space for the image"""
        return self.cover_window.get_size()[0]

    def available_image_height(self):
        """Returns the available vertical space for the image"""
        return self.cover_window.get_size()[1] - \
               self.toolbar.size_request().height - \
               self.statusbar.size_request().height

    def center_image(self):
        """Centers the image in the layout"""
        new_x = max(0, int((self.available_image_width() - \
                            self.image_pixbuf.get_width()) / 2))
        new_y = max(0, int((self.available_image_height() - \
                            self.image_pixbuf.get_height()) / 2))
        self.layout.move(self.image, new_x, new_y)

    def update_widgets(self):
        """Updates image, layout, scrolled window, tool bar and status bar"""
        # if self.cover_window.window:
        #    self.cover_window.window.freeze_updates()
        self.apply_zoom()
        self.layout.set_size(self.image_pixbuf.get_width(), \
                             self.image_pixbuf.get_height())
        if self.image_fitted or \
                (self.image_pixbuf.get_width() == self.available_image_width() and \
                             self.image_pixbuf.get_height() == self.available_image_height()):
            self.scrolledwindow.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        else:
            self.scrolledwindow.set_policy(Gtk.PolicyType.AUTOMATIC,
                                           Gtk.PolicyType.AUTOMATIC)
        percent = int(100 * self.image_ratio)
        message = str(self.image_original_pixbuf.get_width()) + " x " + \
                  str(self.image_original_pixbuf.get_height()) + \
                  " pixels " + str(percent) + '%'
        self.zoom_in_button.set_sensitive(percent < self.max_percent)
        self.zoom_out_button.set_sensitive(percent > self.min_percent)
        self.statusbar.pop(self.statusbar.get_context_id(''))
        self.statusbar.push(self.statusbar.get_context_id(''), message)
        self.image.set_from_pixbuf(self.image_pixbuf)
        self.center_image()
        #if self.cover_window.window:
        #    self.cover_window.window.thaw_updates()

    def apply_zoom(self):
        """Scales the image if needed"""
        new_width = int(self.image_original_pixbuf.get_width() * \
                        self.image_ratio)
        new_height = int(self.image_original_pixbuf.get_height() * \
                         self.image_ratio)
        if new_width != self.image_pixbuf.get_width() or \
                        new_height != self.image_pixbuf.get_height():
            self.image_pixbuf = self.image_original_pixbuf.scale_simple(new_width, \
                                                                        new_height, self.image_interp)

    def set_ratio_to_fit(self):
        """Calculates and sets the needed ratio to show the full image"""
        width_ratio = float(self.image_original_pixbuf.get_width()) / \
                      self.available_image_width()
        height_ratio = float(self.image_original_pixbuf.get_height()) / \
                       self.available_image_height()
        self.image_ratio = 1 / max(1, width_ratio, height_ratio)

    def on_save_as_button_clicked(self, widget):
        """
            Saves image to user-specified location
        """
        dialog = Gtk.FileChooserDialog(_("Save File"), self.cover_window,
                                       Gtk.FileChooserAction.SAVE,
                                       (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT))
        filename = 'cover.png'
        dialog.set_current_name(filename)
        if self.savedir:
            dialog.set_current_folder(self.savedir)
        if dialog.run() == Gtk.ResponseType.ACCEPT:
            filename = dialog.get_filename()
            lowfilename = filename.lower()
            if lowfilename.endswith('.jpg') or lowfilename.endswith('.jpeg'):
                type_ = 'jpeg'
            else:
                type_ = 'png'
            self.image_pixbuf.savev(filename, type_, [None], [None])
        dialog.destroy()

    def on_zoom_in_button_clicked(self, widget):
        """
            Zooms into the image
        """
        self.image_fitted = False
        self.image_ratio *= self.ratio
        self.update_widgets()

    def on_zoom_out_button_clicked(self, widget):
        """
            Zooms out of the image
        """
        self.image_fitted = False
        self.image_ratio *= 1 / self.ratio
        self.update_widgets()

    def on_zoom_100_button_clicked(self, widget):
        """
            Restores the original image zoom
        """
        self.image_fitted = False
        self.image_ratio = 1
        self.update_widgets()

    def on_zoom_fit_button_clicked(self, widget):
        """
            Zooms the image to fit the window width
        """
        self.image_fitted = True
        self.set_ratio_to_fit()
        self.update_widgets()

    def on_close_button_clicked(self, widget):
        """
            Hides the window
        """
        self.cover_window.hide()

    def cover_window_size_allocate(self, widget, allocation):
        if self.cover_window_width != allocation.width or \
                        self.cover_window_height != allocation.height:
            if self.image_fitted:
                self.set_ratio_to_fit()
            self.update_widgets()
            self.cover_window_width = allocation.width
            self.cover_window_height = allocation.height
