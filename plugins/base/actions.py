"""
$Id$

This plugin will show information about connections to the proxy
"""
import re
import sys
import argparse
import os
from string import Template

from plugins._baseplugin import BasePlugin
from libs.timing import timeit
from libs.color import convertcolors
from libs.persistentdict import PersistentDict
from libs import utils
from libs.color import strip_ansi

#these 5 are required
NAME = 'Actions'
SNAME = 'actions'
PURPOSE = 'handle user actions'
AUTHOR = 'Bast'
VERSION = 1

# This keeps the plugin from being autoloaded if set to False
AUTOLOAD = True

class Plugin(BasePlugin):
  """
  a plugin for user actions
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)

    self.canreload = True

    self.regexlookup = {}
    self.actiongroups = {}
    self.compiledregex = {}
    self.sessionhits = {}

    self.saveactionsfile = os.path.join(self.savedir, 'actions.txt')
    self.actions = PersistentDict(self.saveactionsfile, 'c', format='json')

    for i in self.actions:
      self.compiledregex[i] = re.compile(self.actions[i]['regex'])

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

    self.api.get('setting.add')('nextnum', 0, int,
                                'the number of the next alias added',
                                readonly=True)

    parser = argparse.ArgumentParser(add_help=False,
                 description='add a action')
    parser.add_argument('regex', help='the regex to match', default='', nargs='?')
    parser.add_argument('action', help='the action to take', default='', nargs='?')
    parser.add_argument('send', help='where to send the action', default='execute', nargs='?',
                        choices=self.api.get('api.getchildren')('send'))
    parser.add_argument('-c', "--color", help="match colors (@@colors)",
              action="store_true")
    parser.add_argument('-d', "--disable", help="disable the action", action="store_true")
    parser.add_argument('-g', "--group", help="the action group", default="")
    self.api.get('commands.add')('add', self.cmd_add,
              parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='list actions')
    parser.add_argument('match', help='list only actions that have this argument in them', default='', nargs='?')
    self.api.get('commands.add')('list', self.cmd_list,
                                 parser=parser)

    #self.api.get('commands.add')('stats', self.cmd_stats,
    #                             shelp='show action stats')

    self.api.get('events.register')('from_mud_event', self.checkactions, prio=5)
#    self.api.get('events.register')('plugin_stats', self.getpluginstats)

  def cmd_add(self, args):
    """
    add user defined actions
    """
    if not args['regex']:
      return False, ['Please include a regex']
    if not args['action']:
      return False, ['Please include an action']

    num = self.api.get('setting.gets')('nextnum')

    self.api.get('setting.change')('nextnum', num + 1)

    self.actions[num] = {
      'regex':args['regex'],
      'action':args['action'],
      'send':args['send'],
      'matchcolor':args['color'],
      'enabled':not args['disable'],
      'group':args['group']
      }

    self.compiledregex[num] = re.compile(args['regex'])

    self.actions.sync()

    return True, ['added action %s' % args['regex']]

  @timeit
  def checkactions(self, args):
    """
    check a line of text from the mud
    the is called whenever the from_mud_event is raised
    """
    data = args['noansi']
    colordata = args['convertansi']

    for i in self.actions:
      if self.actions[i]['enabled']:
        trigre = self.compiledregex[i]
        datatomatch = data
        if 'matchcolor' in self.actions[i] and \
            self.actions[i]['matchcolor']:
          datatomatch = colordata
        mat = trigre.match(datatomatch)
        self.api.get('send.msg')('attempting to match %s' % datatomatch)
        if mat:
          if not (i in self.sessionhits):
            self.sessionhits[i] = 0
          self.sessionhits[i] = self.sessionhits[i] + 1
          if not ('hits' in self.actions[i]):
            self.actions[i]['hits'] = 0
          self.actions[i]['hits'] = self.actions[i]['hits'] + 1
          self.api.get('send.msg')('matched line: %s to action %s' % (data, i))
          templ = Template(self.actions[i]['action'])
          newaction = templ.safe_substitute(mat.groupdict())
          sendtype = 'send.' + self.actions[i]['send']
          self.api.get('send.msg')('sent %s to %s' % (newaction, sendtype))
          self.api.get(sendtype)(newaction)

    return args

  def cmd_list(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      List aliases
      @CUsage@w: list
    """
    tmsg = self.listactions(args['match'])
    return True, tmsg

  def listactions(self, match):
    """
    return a table of strings that list aliases
    """
    tmsg = []
    for s in sorted(self.actions.keys()):
      item = self.actions[s]
      if not match or match in item:
        regex = strip_ansi(item['regex'])
        if len(regex) > 30:
          regex = regex[:27] + '...'
        action = strip_ansi(item['action'])
        if len(action) > 30:
          action = action[:27] + '...'
        tmsg.append("%4s %2s  %-32s : %s@w" % (s,
                      'Y' if item['enabled'] else 'N',
                      regex,
                      action))
    if len(tmsg) == 0:
      tmsg = ['None']
    else:
      tmsg.insert(0, "%4s %2s  %-32s : %s@w" % ('#', 'E', 'Regex', 'Action'))
      tmsg.insert(1, '@B' + '-' * 60 + '@w')

    return tmsg

  def clearactions(self):
    """
    clear all aliases
    """
    self.actions.clear()
    self.actions.sync()

  def reset(self):
    """
    reset the plugin
    """
    BasePlugin.reset(self)
    self.clearactions()

  def savestate(self):
    """
    save states
    """
    BasePlugin.savestate(self)
    self.actions.sync()
