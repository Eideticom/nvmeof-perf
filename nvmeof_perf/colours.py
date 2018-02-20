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

import curses

curses.setupterm()

bold = curses.tigetstr("bold") or b""
setaf = curses.tigetstr("setaf") or b""
rst = curses.tigetstr("sgr0") or b""

if setaf:
    green = curses.tparm(setaf, curses.COLOR_GREEN) or b""
    magenta = curses.tparm(setaf, curses.COLOR_MAGENTA) or b""
    yellow = curses.tparm(setaf, curses.COLOR_YELLOW) or b""
    cyan = curses.tparm(setaf, curses.COLOR_CYAN) or b""
    red = curses.tparm(setaf,  curses.COLOR_RED) or b""
    blue = curses.tparm(setaf, curses.COLOR_BLUE) or b""
else:
    green = b""
    magenta = b""
    yellow = b""
    cyan = b""
    red = b""
    blue = b""


bold = bold.decode()
setaf = setaf.decode()
rst = rst.decode()
green = green.decode()
magenta = magenta.decode()
yellow = yellow.decode()
cyan = cyan.decode()
red = red.decode()
blue = blue.decode()
