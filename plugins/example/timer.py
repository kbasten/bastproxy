"""
$Id$
"""
from libs import exported
from plugins import BasePlugin

name = 'Timer Example'
sname = 'timexam'
autoload = False

class Plugin(BasePlugin):
  def __init__(self, name, sname, filename, directory, importloc):
    BasePlugin.__init__(self, name, sname, filename, directory, importloc) 
    
  def test(self):
    exported.sendtouser(exported.colors('Here is the timer that fires every 30 seconds!', 'red',bold=True))

  def test_to_user(self):
    exported.sendtouser('A timer just fired.')

  def load(self):
    exported.addtimer('test_timer', self.test, 30)
    exported.addtimer('test_touser_timer', self.test_to_user, 10, True)

  def unload(self):
    exported.deletetimer('test_timer')
    exported.deletetimer('test_touser_timer')
    
    