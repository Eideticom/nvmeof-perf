########################################################################
##
## Copyright 2015 PMC-Sierra, Inc.
## Copyright 2018 Eidetic Communications Inc.
##
## Licensed under the Apache License, Version 2.0 (the "License"); you
## may not use this file except in compliance with the License. You may
## obtain a copy of the License at
## http://www.apache.org/licenses/LICENSE-2.0 Unless required by
## applicable law or agreed to in writing, software distributed under the
## License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
## CONDITIONS OF ANY KIND, either express or implied. See the License for
## the specific language governing permissions and limitations under the
## License.
##
########################################################################

import sys
import time
import curses

class DummyContext(object):
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass

class Timeline(DummyContext):
    def __init__(self, period=1.0, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.period = period
        self.last_time = time.time() - period

    def wait_until_ready(self):
        tm = self.last_time + self.period
        if tm > time.time():
            time.sleep(tm - time.time())

    def next(self):
        self.wait_until_ready()
        self.last_time = time.time()

class CursesContext(object):
    def __enter__(self):
        curses.setupterm()
        self.cmd("smcup")
        return self

    def __exit__(self, type, value, traceback):
        self.cmd("rmcup")

    def cmd(self, name, *args):
        s = curses.tigetstr(name)
        sys.stdout.buffer.write(curses.tparm(s, *args))

    def clear(self):
        self.cmd("clear")
        self.cmd("cup", 0, 0)
