# -*- Mode: python; coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
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

import sys

PYVER = sys.version_info[0]

if PYVER >= 3:
    import urllib.request, urllib.parse, urllib.error
else:
    import urllib
    from urlparse import urlparse as rb2urlparse


def unicodestr(param, charset):
    if PYVER >=3:
        return str(param, charset)
    else:
        return unicode(param, charset)
    
def urlparse(uri):
    if PYVER >=3:
        return urllib.parse.urlparse(uri)
    else:
        return rb2urlparse(uri)
        
def url2pathname(url):
    if PYVER >=3:
        return urllib.request.url2pathname(url)
    else:
        return urllib.url2pathname(url)

def pathname2url(filename):
    if PYVER >=3:
        return urllib.request.pathname2url(filename)
    else:
        return urllib.pathname2url(filename)

def unquote(uri):
    if PYVER >=3:
        return urllib.parse.unquote(uri)
    else:
        return urllib.unquote(uri)
