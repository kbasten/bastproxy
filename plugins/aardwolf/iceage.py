"""
This plugin adds events for Aardwolf Ice Ages.
"""
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin

NAME = 'Aardwolf Ice Age'
SNAME = 'iceage'
PURPOSE = 'Send ice age events'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(AardwolfBasePlugin):
  """
  a plugin to handle aardwolf quest events
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

    self.api.get('triggers.add')('iceage',
      "[[ WARNING: An Ice Age Approaches - 1 minute - See 'help ice age' ]]")

    self.api.get('events.register')('iceage',
                                    self.iceage)

  def iceage(self, args):
    """
    raise an iceage event
    """
    self.api.get('events.eraise')('aard_iceage', {})
