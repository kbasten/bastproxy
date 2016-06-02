"""
This is the base plugin for aardwolf plugins
it adds some dependencies
"""
from plugins._baseplugin import BasePlugin

NAME = 'Aardwolf Base Plugin'
SNAME = 'abase'
PURPOSE = 'The Aardwolf BasePlugin'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class AardwolfBasePlugin(BasePlugin):
  """
  base plugin for aardwolf
  """
  def __init__(self, *args, **kwargs):
    BasePlugin.__init__(self, *args, **kwargs)

    self.api.get('dependency.add')('aardwolf.connect')
    self.api.get('dependency.add')('aardwolf.aardu')
    self.api.get('dependency.add')('aardwolf.agmcp')

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)
