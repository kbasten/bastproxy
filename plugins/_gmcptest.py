"""
$Id$
"""

from libs import exported

name = 'GMCP Test'

def test(args):
  exported.sendtouser(exported.color('Got %s from GMCP: %s' % (args['module'], args['data']), 'red',bold=True))

def testchar(args):
  print('testchar --------------------------')
  tchar = exported.gmcp.get('char')
  print(tchar.status.state)
  if tchar and tchar.status:
    print('char.status.state from tchar')
    print(tchar.status.state)
  else:
    print('Do not have status')
  print('char.status.state with getting full')
  cstate = exported.gmcp.get('char.status.state')
  if cstate:
    print('Got state: %s' % cstate)
  else:
    print('did not get state')
  print('getting a module that doesn\'t exist')
  print(exported.gmcp.get('char.test'))
  print('getting a variable that doesn\'t exist')
  print(exported.gmcp.get('char.status.test'))
  
  exported.sendtouser(exported.color('Got %s from GMCP' % args['module'], 'blue',bold=True))

def testcharstatus(args):
  exported.sendtouser(exported.color('Got %s from GMCP' % args['module'], 'green',bold=True))


def load():
  exported.registerevent('GMCP', test)
  exported.registerevent('GMCP:char', testchar)
  exported.registerevent('GMCP:char.status', testcharstatus)

def unload():
  exported.unregisterevent('GMCP', test)
  exported.unregisterevent('GMCP:char', testchar)
  exported.unregisterevent('GMCP:char.status', testcharstatus)
  