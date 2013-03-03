"""
$Id$
"""
from libs import exported
from plugins import BasePlugin

NAME = 'Timer Example'
SNAME = 'timerex'
PURPOSE = 'examples for using timers'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(BasePlugin):
  """
  a plugin to show how to use timers
  """
  def __init__(self, name, sname, filename, directory, importloc):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, name, sname, filename, directory, importloc) 
    self.timers['test_timer'] = {'func':self.test, 
                                'seconds':600, 'onetime':False}
    self.timers['test_touser_timer'] = {'func':self.test_to_user, 
                                'seconds':10, 'onetime':True}
    
  def test(self):
    """
    send a message to the mud and client
    """
    exported.sendtoclient('@RHere is the timer that fires every 600 seconds!')
    exported.execute('look')

  def test_to_user(self):
    """
    test a onetime timer
    """
    exported.sendtoclient('@RA onetime timer just fired.')
    
    