"""
$Id$
"""

from libs import exported
from plugins import BasePlugin

name = 'Aard102 Example'
sname = 'a102ex'
purpose = 'examples for using the a102 plugin'
author = 'Bast'
version = 1

autoload = False

class Plugin(BasePlugin):
  def __init__(self, name, sname, filename, directory, importloc):
    BasePlugin.__init__(self, name, sname, filename, directory, importloc) 
    self.events.append({'event':'A102', 'func':self.test})
    self.events.append({'event':'A102:101', 'func':self.test101})    
    
  def test(self, args):
    exported.sendtouser(exported.colors('Got A102: %s' % args, 'red',bold=True))

  def test101(self, args):
    exported.sendtouser(exported.colors('Got A102:101: %s' % args, 'red',bold=True))

  