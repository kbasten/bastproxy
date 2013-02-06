"""
$Id$
"""

from libs import exported
from plugins import BasePlugin

name = 'GMCP Test'
sname = 'gmcpt'
autoload = True

class Plugin(BasePlugin):
  def __init__(self, name, sname, filename, directory, importloc):
    BasePlugin.__init__(self, name, sname, filename, directory, importloc)    
    self._substitutes = {}
    self.cmds = {}
    self.cmds['test'] = self.cmd_test

  def cmd_test(self, args):
    print(args)

  def test(self, args):
    exported.sendtouser('@x52@z192 Event @w- @GGMCP@w: @B%s@w : %s' % (args['module'], args['data']))

  def testchar(self, args):
    print('testchar --------------------------')
    tchar = exported.gmcp.getv('char')
    print(tchar)
    if tchar and tchar.status:
      print('char.status.state from tchar')
      print(tchar.status.state)
    else:
      print('Do not have status')
    print('char.status.state with getting full')
    cstate = exported.gmcp.getv('char.status.state')
    if cstate:
      print('Got state: %s' % cstate)
    else:
      print('did not get state')
    print('getting a module that doesn\'t exist')
    print(exported.gmcp.getv('char.test'))
    print('getting a variable that doesn\'t exist')
    print(exported.gmcp.getv('char.status.test'))
    
    exported.sendtouser('@CEvent@w - @GGMCP:char@w: %s' % args['module'])

  def testcharstatus(self, args):
    exported.sendtouser('@CEvent@w - @GGMCP:char.status@w')

  def load(self):
    exported.registerevent('GMCP', self.test)
    exported.registerevent('GMCP:char', self.testchar)
    exported.registerevent('GMCP:char.status', self.testcharstatus)

  def unload(self):
    exported.unregisterevent('GMCP', self.test)
    exported.unregisterevent('GMCP:char', self.testchar)
    exported.unregisterevent('GMCP:char.status', self.testcharstatus)

  