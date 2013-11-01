"""
$Id$

This plugin is a utility plugin for aardwolf functions
It adds functions to exported.aardu
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
  a plugin to handle aardwolf cp events
  """
  def __init__(self, *args, **kwargs):
    BasePlugin.__init__(self, *args, **kwargs)

    self.api.get('dependency.add')('aardwolf.connect')
    self.api.get('dependency.add')('aardwolf.aardu')

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)
