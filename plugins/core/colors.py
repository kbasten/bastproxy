"""
$Id$

This plugin handles colors

Color Codes:
xterm 256
@x154 - make text color xterm 154
@z154 - make background color xterm 154

regular ansi:
         regular    bold
Red        @r        @R
Green      @g        @G
Yellow     @y        @Y
Blue       @b        @B
Magenta    @m        @M
Cyan       @c        @C
White      @w        @W
Reset      @k        @D

"""
import math
import re
import argparse
from plugins._baseplugin import BasePlugin

NAME = 'Ansi Colors'
SNAME = 'colors'
PURPOSE = 'Ansi color functions'
AUTHOR = 'Bast'
VERSION = 1
PRIORITY = 11

AUTOLOAD = True

# for finding ANSI color sequences
XTERM_COLOR_REGEX = re.compile('^@[xz](?P<num>[\d]{1,3})$')
ANSI_COLOR_REGEX = re.compile(chr(27) + r'\[(?P<arg_1>\d+)(;(?P<arg_2>\d+)(;(?P<arg_3>\d+))?)?m')

CONVERTANSI = {}

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
  'x' : '0',
}


for i in CONVERTCOLORS.keys():
  CONVERTANSI[CONVERTCOLORS[i]] = i

#xterm colors
for i in xrange(0, 256):
  CONVERTANSI['38;5;%d' % i] = 'x%d' % i
  CONVERTANSI['39;5;%d' % i] = 'z%d' % i

#backgrounds
for i in xrange(40, 48):
  CONVERTANSI['%s' % i] = CONVERTANSI['39;5;%d' % (i - 40)]

#foregrounds
for i in xrange(30, 38):
  CONVERTANSI['%s' % i] = CONVERTANSI['0;%d' % i]

def genrepl(match):
  """
  a general replace function
  """
  return match.group(1)

def fixstring(tstr):
  """
  fix a strings invalid colors
  """
  # Thanks to Fiendish from the aardwolf mushclient package, see
  # http://code.google.com/p/aardwolfclientpackage/

  # fix tildes
  tstr = re.sub("@-", "~", tstr)
  # change @@ to \0
  tstr = re.sub("@@", "\0", tstr)
  # strip invalid xterm codes (non-number)
  tstr = re.sub("@[xz]([^\d])", genrepl, tstr)
  # strip invalid xterm codes (300+)
  tstr = re.sub("@[xz][3-9]\d\d", "", tstr)
  # strip invalid xterm codes (260+)
  tstr = re.sub("@[xz]2[6-9]\d", "", tstr)
  # strip invalid xterm codes (256+)
  tstr = re.sub("@[xz]25[6-9]", "", tstr)
  # rip out hidden garbage
  tstr = re.sub("@[^xzcmyrgbwCMYRGBWD]", "", tstr)
  return tstr

class Plugin(BasePlugin):
  """
  a plugin to handle ansi colors
  """
  def __init__(self, *args, **kwargs):
    BasePlugin.__init__(self, *args, **kwargs)

    self.api.get('api.add')('iscolor', self.api_iscolor)
    self.api.get('api.add')('convertcolors', self.api_convertcolors)
    self.api.get('api.add')('convertansi', self.api_convertansi)
    self.api.get('api.add')('ansicode', self.api_ansicode)
    self.api.get('api.add')('stripansi', self.api_stripansi)
    self.api.get('api.add')('stripcolor', self.api_stripcolor)
    self.api.get('api.add')('lengthdiff', self.api_getlengthdiff)

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

    parser = argparse.ArgumentParser(add_help=False,
                 description='show colors')
    self.api.get('commands.add')('show', self.cmd_show,
                                    parser=parser)
    parser = argparse.ArgumentParser(add_help=False,
                 description='show color examples')
    self.api.get('commands.add')('example', self.cmd_example,
                                    parser=parser)

  def api_getlengthdiff(self, colorstring):
    """
    get the length difference of a colored string and its noncolor equivalent
    """
    lennocolor = len(self.api.get('colors.stripcolor')(colorstring))
    lencolor = len(colorstring)
    return lencolor - lennocolor

  def api_iscolor(self, color):
    """
    check if a string is a @ color, either xterm or ansi
    """
    if re.match('^@[cmyrgbwCMYRGBWD]$', color):
      return True
    else:
      mat = XTERM_COLOR_REGEX.match( color)
      if mat:
        num = int(mat.groupdict()['num'])
        if num >= 0 and num < 257:
          return True

    return False

  def api_convertcolors(self, tstr):
    """
    convert @ colors in a string
    """
    test = False
    if '@' in tstr:
      if tstr[-2:] != '@w':
        tstr = tstr + '@w'
      tstr = fixstring(tstr)
      if test:
        print 'After fixstring', tstr
      tstr2 = ''
      tmat = re.search("@(\w)([^@]+)", tstr)
      if tmat and tmat.start() != 0:
        tstr2 = tstr[0:tmat.start()]
      for tmatch in re.finditer("@(\w)([^@]+)", tstr):
        color, text = tmatch.groups()
        if color == 'x':
          tcolor, newtext = re.findall("^(\d\d?\d?)(.*)$", text)[0]
          color = '38;5;%s' % tcolor
          tstr2 = tstr2 + self.api_ansicode(color, newtext)
        elif color == 'z':
          tcolor, newtext = re.findall("^(\d\d?\d?)(.*)$", text)[0]
          color = '48;5;%s' % tcolor
          tstr2 = tstr2 + self.api_ansicode(color, newtext)
        else:
          tstr2 = tstr2 + self.api_ansicode(CONVERTCOLORS[color], text)

      if tstr2:
        tstr = tstr2 + "%c[0m" % chr(27)
      if test:
        print 'After:', tstr
    else:
      pass
    tstr = re.sub("\0", "@", tstr)    # put @ back in
    return tstr

  def api_convertansi(self, text):
    """
    convert ansi color escape sequences to @colors
    """
    def single_sub(match):
        argsdict = match.groupdict()
        tstr = ''
        tstr = tstr + argsdict['arg_1']
        if argsdict['arg_2']:
          tstr = tstr + ';%d' % int(argsdict['arg_2'])

        if argsdict['arg_3']:
          tstr = tstr + ';%d' % int(argsdict['arg_3'])

        try:
          return '@%s' % CONVERTANSI[tstr]
        except KeyError:
          print 'could not lookup color %s for text %s' % (tstr, repr(text))

    return ANSI_COLOR_REGEX.sub(single_sub, text)

  def api_ansicode(self, color, data):
    """
    return an ansicoded string
    """
    return "%c[%sm%s" % (chr(27), color, data)

  def api_stripansi(self, text):
    """
    strip all ansi from a string
    """
    return ANSI_COLOR_REGEX.sub('', text)

  def api_stripcolor(self, text):
    """
    strip @colors
    """
    return self.api_stripansi(self.api_convertcolors(text))

  def cmd_show(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      Show xterm colors
      @CUsage@w: show @Y"compact"@w
        @Y"compact"@w    = The original string to be replaced
    """
    msg = ['']
    lmsg = []
    compact = False
    joinc = ' '
    if 'compact' in args:
      compact = True
      colors = '@z%s  @w'
      joinc = ''
    else:
      colors = '@B%-3s : @z%s    @w'
    for i in range(0, 16):
      if i % 8 == 0 and i != 0:
        msg.append(joinc.join(lmsg))
        lmsg = []

      if compact:
        lmsg.append(colors % (i))
      else:
        lmsg.append(colors % (i, i))

    lmsg.append('\n')
    msg.append(joinc.join(lmsg))

    lmsg = []

    for i in range(16, 256):
      if (i - 16) % 36 == 0 and ((i - 16) != 0 and not i > 233):
        lmsg.append('\n')

      if (i - 16) % 6 == 0 and (i - 16) != 0:
        msg.append(joinc.join(lmsg))
        lmsg = []

      if compact:
        lmsg.append(colors % (i))
      else:
        lmsg.append(colors % (i, i))

    msg.append(joinc.join(lmsg))
    lmsg = []

    msg.append('')

    return True, msg


  def cmd_example(self, _=None):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      Show examples of how to use colors
      @CUsage@w: example
    """
    msg = ['']
    msg.append('Examples')
    msg.append('Raw   : @@z165Regular text with color 165 Background@@w')
    msg.append('Color : @z165Regular text with color 165 Background@w')
    msg.append('Raw   : @@x165@zcolor 165 text with regular Background@@w')
    msg.append('Color : @x165color 165 text with regular Background@w')
    msg.append('Raw   : @@z255@@x0color 0 text with color 255 Background@@w')
    msg.append('Color : @z255@x0color 0 text with color 255 Background@w')
    msg.append('Note: see the show command to show the table of colors')
    msg.append('')
    return True, msg
