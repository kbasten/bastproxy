"""
This plugin handles colors

## Color Codes
### Ansi

|| color   ||   regular   ||     bold     ||
|| Red     ||   @r@@r@w   ||     @R@@R@w  ||
|| Green   ||   @g@@g@w   ||     @g@@G@w  ||
|| Yellow  ||   @y@@y@w   ||     @Y@@Y@w  ||
|| Blue    ||   @b@@b@w   ||     @B@@B@w  ||
|| Magenta ||   @m@@m@w   ||     @M@@M@w  ||
|| Cyan    ||   @c@@c@w   ||     @C@@C@w  ||
|| White   ||   @w@@w@w   ||     @W@@W@w  ||

### xterm 256

* @x154@@x154 - make text color xterm 154@w
* @z154@@z154@w - make background color xterm 154@w

"""
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
ANSI_COLOR_REGEX = re.compile(chr(27) + r'\[(?P<arg_1>\d+)(;(?P<arg_2>\d+)' \
                                              '(;(?P<arg_3>\d+))?)?m')

COLORCODE_REGEX = re.compile('(@[cmyrgbwCMYRGBWD|xz[\d{0:3}]])(?P<stuff>.*)')

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

colortable = {}
def build_color_table():
    # colors 0..15: 16 basic colors

    colortable[0] = (0x00, 0x00, 0x00) # 0
    colortable['k'] = colortable[0]
    colortable[1] = (0xcd, 0x00, 0x00) # 1
    colortable['r'] = colortable[1]
    colortable[2] = (0x00, 0xcd, 0x00) # 2
    colortable['g'] = colortable[2]
    colortable[3] = (0xcd, 0xcd, 0x00) # 3
    colortable['y'] = colortable[3]
    colortable[4] = (0x00, 0x00, 0xee) # 4
    colortable['b'] = colortable[4]
    colortable[5] = (0xcd, 0x00, 0xcd) # 5
    colortable['m'] = colortable[5]
    colortable[6] = (0x00, 0xcd, 0xcd) # 6
    colortable['c'] = colortable[6]
    colortable[7] = (0xe5, 0xe5, 0xe5) # 7
    colortable['w'] = colortable[7]
    colortable[8] = (0x7f, 0x7f, 0x7f) # 8
    colortable['D'] = colortable[8]
    colortable[9] = (0xff, 0x00, 0x00) # 9
    colortable['R'] = colortable[9]
    colortable[10] = (0x00, 0xff, 0x00) # 10
    colortable['G'] = colortable[10]
    colortable[11] = (0xff, 0xff, 0x00) # 11
    colortable['Y'] = colortable[11]
    colortable[12] = (0x5c, 0x5c, 0xff) # 12
    colortable['B'] = colortable[12]
    colortable[13] = (0xff, 0x00, 0xff) # 13
    colortable['M'] = colortable[13]
    colortable[14] = (0x00, 0xff, 0xff) # 14
    colortable['C'] = colortable[14]
    colortable[15] = (0xff, 0xff, 0xff) # 15
    colortable['W'] = colortable[15]

    # colors 16..232: the 6x6x6 color cube

    valuerange = (0x00, 0x5f, 0x87, 0xaf, 0xd7, 0xff)

    for i in range(217):
        r = valuerange[(i // 36) % 6]
        g = valuerange[(i // 6) % 6]
        b = valuerange[i % 6]
        colortable[i + 16] = ((r, g, b))

    # colors 233..253: grayscale

    for i in range(1, 22):
        v = 8 + i * 10
        colortable[i + 233] = ((v, v, v))

build_color_table()

def convertcolorcodetohtml(colorcode):
  try:
    colorcode = int(colorcode)
    if colorcode in colortable:
      #print colortable[colorcode]
      return '#%.2x%.2x%.2x' % (colortable[colorcode][0],
                          colortable[colorcode][1],
                          colortable[colorcode][2])
  except ValueError:
    if colorcode in colortable:
      return '#%.2x%.2x%.2x' % (colortable[colorcode][0],
                          colortable[colorcode][1],
                          colortable[colorcode][2])

  return '#000'

def createspan(color, text):
  """
  create an html span

  color = "@g"
  """
  background = False
  if color[0] == '@':
    if color[1] == 'x':
      ncolor = convertcolorcodetohtml(color[2:])
    elif color[1] == 'z':
      ncolor = convertcolorcodetohtml(color[2:])
      background = True
    else:
      ncolor = convertcolorcodetohtml(color[1])
  else:
    ncolor = convertcolorcodetohtml(color)

  if background:
    return '<span style="background-color:%(COLOR)s">%(TEXT)s</span>' % {
                      'COLOR':ncolor,
                      'TEXT':text}
  else:
    return '<span style="color:%(COLOR)s">%(TEXT)s</span>' % {
                      'COLOR':ncolor,
                      'TEXT':text}

for colorc in CONVERTCOLORS.keys():
  CONVERTANSI[CONVERTCOLORS[colorc]] = colorc

#xterm colors
for xtn in xrange(0, 256):
  CONVERTANSI['38;5;%d' % xtn] = 'x%d' % xtn
  CONVERTANSI['48;5;%d' % xtn] = 'z%d' % xtn

#backgrounds
for acn in xrange(40, 48):
  CONVERTANSI['%s' % acn] = CONVERTANSI['48;5;%d' % (acn - 40)]

#foregrounds
for abn in xrange(30, 38):
  CONVERTANSI['%s' % abn] = CONVERTANSI['0;%d' % abn]

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
    self.api.get('api.add')('colortohtml', self.api_colorcodestohtml)

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

  # convert color codes to html
  def api_colorcodestohtml(self, input):
    """
    convert colorcodes to html
    """
    tinput = input.split('\n')

    olist = []
    for line in tinput:
      if line and line[-1] == '\n':
        lastchar = '\n'
      else:
        lastchar = ''

      line = line.rstrip()
      #line = fixstring(line)
      if '@@' in line:
        line = line.replace('@@', '\0')
      tlist = re.split('(@[cmyrgbwCMYRGBWD]|@[xz]\d\d\d|@[xz]\d\d|@[xz]\d)', line)

      nlist = []
      color = 'w'
      tstart = 0
      tend = 0

      for i in xrange(0, len(tlist)):
        #print 'checking %s, i = %s' % (tlist[i], i)
        if tlist[i]:
          if tlist[i][0] == '@' and tlist[i][1] in 'xzcmyrgbwCMYRGBWD':
            #print 'found color'
            words = tlist[tstart:tend]
            if not (color in ['x', 'D', 'w']):
              #print 'would put %s in a %s span' % (words, color)
              nlist.append(createspan(color, ''.join(words)))
            else:
              #print 'would just add %s' % words
              nlist.append(''.join(words))
            if tlist[i][1] in ['x', 'z']:
              color = tlist[i]
            else:
              color = tlist[i]
            tstart = i + 1
            tend = i + 1
          else:
            tend = tend + 1
        else:
          tend = tend + 1
        if i == len(tlist) - 1:
          words = tlist[tstart:]
          if not (color in ['x', 'D', 'w']):
            #print 'would put %s in a %s span' % (words, color)
            nlist.append(createspan(color, ''.join(words)))
          else:
            #print 'would just add %s' % words
            nlist.append(''.join(words))
      tstring = ''.join(nlist)
      if '\0' in tstring:
        tstring = tstring.replace('\0', '@')

      olist.append(tstring + lastchar)

    return '\n'.join(olist) + lastchar

  # get the length difference of a colored string and its noncolor equivalent
  def api_getlengthdiff(self, colorstring):
    """
    get the length difference of a colored string and its noncolor equivalent
    """
    lennocolor = len(self.api.get('colors.stripcolor')(colorstring))
    lencolor = len(colorstring)
    return lencolor - lennocolor

  # check if a string is an @@ color, either xterm or ansi
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

  # convert @@ colors in a string
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

  # convert ansi color escape sequences to @@ colors
  def api_convertansi(self, text):
    """
    convert ansi color escape sequences to @@ colors
    """
    def single_sub(match):
      """
      do a single substitution
      """
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

  # return an ansi coded string
  def api_ansicode(self, color, data):
    """
    return an ansi coded string
    """
    return "%c[%sm%s" % (chr(27), color, data)

  # strip all ansi from a string
  def api_stripansi(self, text):
    """
    strip all ansi from a string
    """
    return ANSI_COLOR_REGEX.sub('', text)

  # strip @@ colors from a string
  def api_stripcolor(self, text):
    """
    strip @@ colors
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
