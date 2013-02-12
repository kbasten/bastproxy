"""
$Id$
"""
from libs import exported
from plugins import BasePlugin

name = 'Timer Example'
sname = 'timerex'
purpose = 'examples for using timers'
author = 'Bast'
version = 1

autoload = False

class Plugin(BasePlugin):
  def __init__(self, name, sname, filename, directory, importloc):
    BasePlugin.__init__(self, name, sname, filename, directory, importloc) 
    self.timers['test_timer'] = {'func':self.test, 'seconds':30, 'onetime':False}
    self.timers['test_touser_timer'] = {'func':self.test_to_user, 'seconds':10, 'onetime':True}
    
  def test(self):
    exported.sendtouser('@RHere is the timer that fires every 30 seconds!')

  def test_to_user(self):
    exported.sendtouser('@RA onetime timer just fired.')
    
    