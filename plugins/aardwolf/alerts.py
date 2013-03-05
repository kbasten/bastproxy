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
  def __init__(self, name, sname, filename, directory, importloc):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, name, sname, filename, directory, importloc)
    self.dependencies.append('aardu')    
    self.dependencies.append('gq')    
    self.addsetting('email', '', str, 'the email to send the alerts', nocolor=True)    
    self.events['aard_gq_declared'] = {'func':self._gqdeclared}
    
  def _gqdeclared(self, args):
    """
    do something when a gq is declared
    """
    self.msg('sending email for gquest')
    if self.variables['email']:
      exported.mail.send('New GQuest', 'A GQuest has been declared', 
              self.variables['email'])
    else:
      exported.mail.send('New GQuest', 'A GQuest has been declared.')
      
