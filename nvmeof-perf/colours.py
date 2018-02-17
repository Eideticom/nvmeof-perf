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
