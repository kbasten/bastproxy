"""
$Id$

This plugin holds a afk plugin
"""
from libs import utils
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin
import time
import re
import copy

NAME = 'AFK plugin'
SNAME = 'afk'
PURPOSE = 'do actions when no clients are connected'
AUTHOR = 'Bast'
VERSION = 1

# This keeps the plugin from being autoloaded if set to False
AUTOLOAD = False

titlematch = '^Your title is: (?P<title>.*)\.$'
titlere = re.compile(titlematch)

titlesetmatch = 'Title now set to: (?P<title>.*)$'
titleset = re.compile(titlesetmatch)

class Plugin(AardwolfBasePlugin):
  """
  a plugin to show connection information
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    AardwolfBasePlugin.__init__(self, *args, **kwargs)

    self.temptitle = ''

  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)

    self.api.get('setting.add')('afktitle', 'is AFK.', str,
                        'the title when afk mode is enabled')
    self.api.get('setting.add')('lasttitle', '', str,
                        'the title before afk mode is enabled')
    self.api.get('setting.add')('queue', [], list, 'the tell queue', readonly=True)
    self.api.get('setting.add')('isafk', False, bool, 'AFK flag', readonly=True)

    self.api.get('commands.add')('show', self.cmd_show,
                                  shelp='Show the afk comm queue')
    self.api.get('commands.add')('clear', self.cmd_clear,
                                  shelp='Clear the afk comm queue')
    self.api.get('commands.add')('toggle', self.cmd_toggle,
                                  shelp='toggle afk')

    self.api.get('watch.add')('titleset', '^(tit|titl|title) (?P<title>.*)$')

    self.api.get('events.register')('client_connected', self.clientconnected)
    self.api.get('events.register')('client_disconnected', self.clientdisconnected)
    self.api.get('events.register')('firstactive', self.afkfirstactive)
    self.api.get('events.register')('watch_titleset', self._titlesetevent)

  def afkfirstactive(self, args):
    """
    set the title when we first connect
    """
    if self.api.get('setting.gets')('lasttitle'):
      title = self.api.get('setting.gets')('lasttitle')
      self.api.get('input.execute')('title %s' % title)

  def _titlesetevent(self, args):
    """
    check for stuff when the title command is seen
    """
    self.api.get('output.msg')('saw title set command %s' % args)
    self.temptitle = args['title']
    self.api.get('events.register')('trigger_all', self.titlesetline)

  def titlesetline(self, args):
    """
    get the titleline
    """
    line = args['line'].strip()
    tmatch = titleset.match(line)
    if line:
      if tmatch:
        newtitle = tmatch.groupdict()['title']
        if newtitle != self.api.get('setting.gets')('afktitle'):
          self.api.get('setting.change')('lasttitle', self.temptitle)
          self.api.get('output.msg')('lasttitle is "%s"' % self.temptitle)
      else:
        self.api.get('output.msg')('unregistering trigger_all from titlesetline')
        self.api.get('events.unregister')('trigger_all', self.titlesetline)

  def cmd_show(self, _=None):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      show the tell queue
      @CUsage@w: show
    """
    msg = []
    queue = self.api.get('setting.gets')('queue')
    if len(queue) == 0:
      msg.append('The queue is empty')
    else:
      msg.append('Tells received while afk')
      for i in queue:
        msg.append('%25s - %s' % (i['timestamp'], i['msg']))

    return True, msg

  def cmd_clear(self, _=None):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      Show examples of how to use colors
      @CUsage@w: example
    """
    msg = []
    msg.append('AFK comm queue cleared')
    self.api.get('setting.change')('queue', [])
    self.savestate()
    return True, msg

  def cmd_toggle(self, _=None):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      toggle afk mode
      @CUsage@w: toggle
    """
    msg = []
    newafk = not self.api.get('setting.gets')('isafk')
    self.api.get('setting.change')('isafk', newafk)
    if newafk:
      self.enableafk()
      msg.append('AFK mode is enabled')
    else:
      self.disableafk()
      msg.append('AFK mode is disabled')

    return True, msg

  def checkfortell(self, args):
    """
    check for tells
    """
    if args['data']['chan'] == 'tell':
      tdata = copy.deepcopy(args['data'])
      tdata['timestamp'] = \
              time.strftime('%a %b %d %Y %H:%M:%S', time.localtime())
      queue = self.api.get('setting.gets')('queue')
      queue.append(tdata)
      self.savestate()

  def enableafk(self):
    """
    enable afk mode
    """
    afktitle = self.api.get('setting.gets')('afktitle')
    self.api.get('setting.change')('isafk', True)
    self.api.get('events.register')('GMCP:comm.channel', self.checkfortell)
    self.api.get('input.execute')('title %s' % afktitle)

  def disableafk(self):
    """
    disable afk mode
    """
    self.api.get('setting.change')('isafk', False)
    lasttitle = self.api.get('setting.gets')('lasttitle')
    self.api.get('input.execute')('title %s' % lasttitle)
    try:
      self.api.get('events.unregister')('GMCP:comm.channel', self.checkfortell)
    except KeyError:
      pass

    queue = self.api.get('setting.gets')('queue')

    if len(queue) > 0:
      self.api.get('output.client')("@BAFK Queue")
      self.api.get('output.client')("@BYou have %s tells in the queue" % \
                len(queue))


  def clientconnected(self, _):
    """
    if we have enabled triggers when there were no clients, disable them
    """
    proxy = self.api.get('managers.getm')('proxy')
    if len(proxy.clients) == 1:
      self.api.get('output.msg')('disabling afk mode')
      self.disableafk()


  def clientdisconnected(self, _):
    """
    if this is the last client, enable afk triggers
    """
    proxy = self.api.get('managers.getm')('proxy')
    if len(proxy.clients) == 0:
      self.api.get('output.msg')('enabling afk mode')
      self.enableafk()

