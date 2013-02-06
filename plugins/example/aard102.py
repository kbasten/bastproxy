"""
$Id$
"""

from libs import exported
from plugins import BasePlugin

name = 'Aard102 Example'
sname = 'a102exam'
autoload = False

class Plugin(BasePlugin):
  def __init__(self, name, sname, filename, directory, importloc):
    BasePlugin.__init__(self, name, sname, filename, directory, importloc) 
    
  def test(self, args):
    exported.sendtouser(exported.colors('Got A102: %s' % args, 'red',bold=True))

  def testchar(self, args):
    exported.sendtouser(exported.colors('Got A102:101: %s' % args, 'red',bold=True))

  def load(self):
    exported.registerevent('A102', self.test)
    exported.registerevent('A102:101', self.testchar)

  def unload(self):
    exported.unregisterevent('A102', self.test)
    exported.unregisterevent('A102:101', self.testchar)
  