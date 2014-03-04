"""
$Id$

This plugin is a variable plugin

"""
import os
import re
import argparse

from string import Template
from plugins._baseplugin import BasePlugin
from libs.persistentdict import PersistentDict

#these 5 are required
NAME = 'Loop'
SNAME = 'loop'
PURPOSE = 'loop a command multiple times'
AUTHOR = 'Bast'
VERSION = 1

# This keeps the plugin from being autoloaded if set to False
AUTOLOAD = True


class Plugin(BasePlugin):
  """
  a plugin to do simple substitution
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)


  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

    parser = argparse.ArgumentParser(add_help=False,
                 description='loop a command')
    parser.add_argument('cmd', help='the variable to remove', default='', nargs='?')
    parser.add_argument('-c', "--count", help="how many times to execute the command", default=1)
    self.api.get('commands.add')('cmd', self.cmd_loop,
                                 parser=parser)

    self.api.get('commands.default')('loop')

  def cmd_loop(self, args):
    """
    loop a command count times
    """
    tmsg = []
    if args['cmd']:
      count = int(args['count'])
      start = 1
      templ = Template(args['cmd'])
      for i in xrange(1, count + 1):
        datan = templ.safe_substitute({'num':i})
        self.api.get('send.msg')('sending cmd: %s' % datan)
        self.api.get('send.execute')(datan)
      return True, ['"%s" was sent %s times' % (args['cmd'], count)]
    else:
      tmsg.append("@RPlease include all arguments@w")
      return False, tmsg

