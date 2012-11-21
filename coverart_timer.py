# -*- Mode: python; coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
##
# Copyright (C) 2012 - fossfreedom
# Copyright (C) 2012 - Agustin Carrasco
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
#
#ttimer: Thread callback timer, it execute your callback function periodically. 
#
#adapted from
#
#Author   : H.K.Ong
#Date     : 27-03-2008
#Website  : http://linux.byexamples.com
#Revision : 1
#

import sys,time
from threading import Thread
import threading


class ttimer(object):
    """Threading callback timer - threading timer will callback your function periodically.
interval - interval callback periodically, in sec
retry    - execute how many times? -1 is infinity
cbfunc   - callback function
cbparam  - parameter in list

i.e t=ttimer(1,10,myfunc,["myparam"])"""

    def __init__(self, interval, retry, cbfunc, cbparam=[]):
        self.is_start=False
        self.is_end=False

        # doing my thread stuff now.
        self.thread = threading.Thread(target = self._callback, args=(interval,retry,cbfunc,cbparam,) )
        self.thread.setDaemon(True)
        self.thread.start()
        #thread.start_new_thread(self._callback,(interval,retry,cbfunc,cbparam,))

    def Start(self):
        #start the thread
        self.mytime=time.time()
        self.is_start=True
        self.is_end=False

    def Stop(self):
        #stop the thread.
        self.mytime=time.time()
        self.is_start=False
        self.is_end=True

    def IsStop(self):
        #Is the thread already end? return True if yes.
        if self.is_end:
            return True
        else:
            return False

    def _callback(self,interval,retry,cbfunc,cbparam=[]):
        """ This is the private thread loop, call start() to start the threading timer."""
        print "callback"
        self.retry=retry
        retry=0

        if self.is_end:
            return None

        while True:
            if not self.is_end:                
                if self.retry==-1:
                    pass
                elif retry>=self.retry:
                    break

                if self.is_start:
                    #check time
                    tmptime=time.time()
                    if tmptime >=(self.mytime + interval):
                        print "before"
                        cbfunc(cbparam) # callback your function
                        print "after"
                        self.mytime=time.time()

                        if not self.retry== -1:
                            retry+=1
                    else:
                        pass
            time.sleep(0.5)

        self.is_end=True
        print "end callback"
        
