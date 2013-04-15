"""
$Id$
"""
from plugins import BasePlugin

#these 5 are required
NAME = 'Color Example'
SNAME = 'colorex'
PURPOSE = 'show colors'
AUTHOR = 'Bast'
VERSION = 1

# This keeps the plugin from being autoloaded when set to False
AUTOLOAD = False


class Plugin(BasePlugin):
  """
  a plugins to show colors
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)
    self.cmds['show'] = {'func':self.show, 'shelp':'Show colors'}
    self.cmds['example'] = {'func':self.example, 'shelp':'Show colors'}
    
  def show(self, args):
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


  def example(self, _=None):
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
    