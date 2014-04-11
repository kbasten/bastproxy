"""
$Id$

This plugin runs gmcp commands after connecting to aardwolf
"""
import time
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin

NAME = 'Aardwolf Repop'
SNAME = 'repop'
PURPOSE = 'Send repop messages to a channel'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = True

class Plugin(AardwolfBasePlugin):
  """
  a plugin to show gmcp usage
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    AardwolfBasePlugin.__init__(self, *args, **kwargs)

  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)

    self.api.get('setting.add')('channel', 'gt', str,
                        'the channel to send the repop message')

    self.api.get('events.register')('GMCP:comm.repop', self.repop)

  def repop(self, args):
    """
    do something on repop
    """
    zone = args['data']['zone']

    ttime = time.strftime('%X', time.localtime())

    tformat = "@r[@RRepop@r]@w %s @R@@ @w%s" % (zone, ttime)

    chan = self.api.get('setting.gets')('channel')

    self.api.get('send.execute')(chan + ' ' + tformat)
