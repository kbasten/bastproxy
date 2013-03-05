"""
$Id$
"""
import time, copy
from libs import exported
from plugins import BasePlugin

NAME = 'Aardwolf GQ Events'
SNAME = 'gq'
PURPOSE = 'Events for Aardwolf GQuests'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(BasePlugin):
  """
  a plugin to handle aardwolf quest events
  """  
  def __init__(self, name, sname, filename, directory, importloc):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, name, sname, filename, directory, importloc) 
    self.dependencies.append('aardu')    
    self.triggers['gqdeclared'] = {
      'regex':"^Global Quest: Global quest \# (?P<gqnum>.*) has been declared for levels (?P<lowlev>.*) to (?P<highlev>.*)\.$"}
    self.events['trigger_gqdeclared'] = {'func':self._gqdeclared}
    
  def _gqdeclared(self, args):
    """
    do something when a gq is declared
    """
    exported.event.eraise('aard_gq_declared', args)
