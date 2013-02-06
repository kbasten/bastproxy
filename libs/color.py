"""
$Id$

"""
import re

# for finding ANSI color sequences
ANSI_COLOR_REGEXP = re.compile(chr(27) + '\[[0-9;]*[m]')

STYLE_NORMAL = 0
STYLE_BOLD = 1
STYLE_UNDERLINE = 4
STYLE_BLINK = 5
STYLE_REVERSE = 7

# enums for placement in the color list
PLACE_BOLD = 0
PLACE_UNDERLINE = 1
PLACE_BLINK = 2
PLACE_REVERSE = 3
PLACE_FG = 4
PLACE_BG = 5

# the default color
DEFAULT_COLOR = [0, 0, 0, 0, -1, -1]

# used for converting text descriptions to ANSI color sequences
STYLEMAP = {
             "default": "0",
             "bold": "1",
             "underline": "4",
             "blink": "5",
             "reverse": "7",
             "black": "30",
             "red": "31",
             "green": "32",
             "yellow": "33",
             "blue": "34",
             "magenta": "35",
             "cyan": "36",
             "white": "37",
             "grey": "1;30",
             "light red": "1;31",
             "light green": "1;32",
             "light yellow": "1;33",
             "light blue": "1;34",
             "light magenta": "1;35",
             "light cyan": "1;36",
             "light white": "1;37",
             "b black": "40",
             "b red": "41",
             "b green": "42",
             "b yellow": "43",
             "b blue": "44",
             "b magenta": "45",
             "b cyan": "46",
             "b white": "47"
           }
      

      
CONVERTCOLORS = {
  'k' : '0;30',
  'r' : '0;31',
  'g' : '0;32',
  'y' : '0;33', 
  'b' : '0;34', 
  'm' : '0;35',
  'c' : '0;36',
  'w' : '0;37',
  'D' : '1;30',
  'R' : '1;31',
  'G' : '1;32',
  'Y' : '1;33',
  'B' : '1;34',
  'M' : '1;35',
  'C' : '1;36',
  'W' : '1;37', 
}


def genrepl(m):
  return m.group(1)


def fixstring(tstr):
  # Thanks to Fiendish from the aardwolf mushclient package, see 
  # http://code.google.com/p/aardwolfclientpackage/
  
  tstr = re.sub("@-", "~", tstr)                   # fix tildes
  tstr = re.sub("@@", "\0", tstr)                  # change @@ to \0
  tstr = re.sub("@x([^\d])", genrepl, tstr)        # strip invalid xterm codes (non-number)
  tstr = re.sub("@x[3-9]\d\d", "", tstr)           # strip invalid xterm codes (300+)
  tstr = re.sub("@x2[6-9]\d", "", tstr)            # strip invalid xterm codes (260+)
  tstr = re.sub("@x25[6-9]", "", tstr)             # strip invalid xterm codes (256+)
  tstr = re.sub("@z([^\d])", genrepl, tstr)        # strip invalid xterm codes (non-number)
  tstr = re.sub("@z[3-9]\d\d", "", tstr)           # strip invalid xterm codes (300+)
  tstr = re.sub("@z2[6-9]\d", "", tstr)            # strip invalid xterm codes (260+)
  tstr = re.sub("@z25[6-9]", "", tstr)             # strip invalid xterm codes (256+)  
  tstr = re.sub("@[^xzcmyrgbwCMYRGBWD]", "", tstr)  # rip out hidden garbage  
  return tstr


def convertcodes(tstr):
  if '@' in tstr:
    if tstr[-2:] != '@w':
      tstr = tstr + '@w'
    tstr = fixstring(tstr)
    tstr2 = ''
    for tmatch in re.finditer("@(\w)([^@]+)", tstr):
      color, text = tmatch.groups()
      if color == 'x':
        tcolor, newtext = re.findall("^(\d\d?\d?)(.*)$", text)[0]
        color = '38;5;%s' % tcolor
        tstr2 = tstr2 + ansicode(color, newtext)
      elif color == 'z':
        tcolor, newtext = re.findall("^(\d\d?\d?)(.*)$", text)[0]
        color = '48;5;%s' % tcolor
        tstr2 = tstr2 + ansicode(color, newtext)
      else:
        tstr2 = tstr2 + ansicode(CONVERTCOLORS[color], text)
        
    if tstr2:
      tstr = tstr2 + "%c[0m" % chr(27)
  else:
    pass
  tstr = re.sub("\0", "@", tstr)    # put @ back in 
  return tstr

      
def ansicode(color, data):
  return "%c[%sm%s" % (chr(27), color, data)


def color(data, fc=37, bc=40, bold=False):
  if fc in STYLEMAP:
    fc = STYLEMAP[fc]
  if bc in STYLEMAP:
    bc = STYLEMAP[bc]

  if bold:
    return "%c[1;%s;%sm%s%c[0m" % (chr(27), str(fc), str(bc), data, chr(27))
  else:
    return "%c[%s;%sm%s%c[0m" % (chr(27), str(fc), str(bc), data, chr(27))


def strip_ansi(text):
  """
  Takes in text and filters out the ANSI color codes.

  @returns: text without ANSI color codes
  @rtype: string
  """
  return ANSI_COLOR_REGEXP.sub('', text)
