"""
$Id$
"""
from libs import exported
from plugins import BasePlugin

NAME = 'Aardwolf Alerts'
SNAME = 'alerts'
PURPOSE = 'Alert for Aardwolf Events'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(BasePlugin):
  """
  a plugin to handle aardwolf quest events
  """  
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)
    self.dependencies.append('aardu')    
    self.dependencies.append('gq')    
    self.addsetting('email', '', str, 'the email to send the alerts', 
              nocolor=True)    
    self.events['aard_gq_declared'] = {'func':self._gqdeclared}
    self.events['aard_quest_ready'] = {'func':self._quest}
    
  def _gqdeclared(self, args):
    """
    do something when a gq is declared
    """
    msg = '%s:%s - A GQuest has been declared for levels %s to %s.' % (
              exported.PROXY.host, exported.PROXY.port, 
              args['lowlev'], args['highlev'])
    if self.variables['email']:
      exported.mail.send('New GQuest', msg, 
              self.variables['email'])
    else:
      exported.mail.send('New GQuest', msg)
      
  def _quest(self, _=None):
    """
    do something when you can quest
    """
    msg = '%s:%s - Time to quest!' % (
              exported.PROXY.host, exported.PROXY.port)
    if self.variables['email']:
      exported.mail.send('Quest Time', msg, 
              self.variables['email'])
    else:
      exported.mail.send('Quest Time', msg)