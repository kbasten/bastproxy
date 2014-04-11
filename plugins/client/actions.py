"""
$Id$

This plugin adds the ability to do user defined actions when text is
seen from the mud
"""
import re
import argparse
import os
from string import Template

from plugins._baseplugin import BasePlugin
from libs.timing import timeit
from libs.persistentdict import PersistentDict

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
    self.actions = PersistentDict(self.saveactionsfile, 'c')

    for i in self.actions:
      self.compiledregex[i] = re.compile(self.actions[i]['regex'])

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

    self.api.get('setting.add')('nextnum', 0, int,
                                'the number of the next action added',
                                readonly=True)

    parser = argparse.ArgumentParser(add_help=False,
                 description='add a action')
    parser.add_argument('regex', help='the regex to match',
                        default='', nargs='?')
    parser.add_argument('action', help='the action to take',
                        default='', nargs='?')
    parser.add_argument('send', help='where to send the action',
                        default='execute', nargs='?',
                        choices=self.api.get('api.getchildren')('send'))
    parser.add_argument('-c', "--color", help="match colors (@@colors)",
                        action="store_true")
    parser.add_argument('-d', "--disable",
                        help="disable the action", action="store_true")
    parser.add_argument('-g', "--group", help="the action group", default="")
    parser.add_argument('-o', "--overwrite",
                        help="overwrite an action if it already exists",
                        action="store_true")
    self.api.get('commands.add')('add', self.cmd_add,
              parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='list actions')
    parser.add_argument('match',
                      help='list only actions that have this argument in them',
                      default='', nargs='?')
    self.api.get('commands.add')('list', self.cmd_list,
                                 parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='remove an action')
    parser.add_argument('action', help='the action to remove',
                        default='', nargs='?')
    self.api.get('commands.add')('remove', self.cmd_remove,
                                 parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='toggle enabled flag')
    parser.add_argument('action', help='the action to toggle',
                        default='', nargs='?')
    self.api.get('commands.add')('toggle', self.cmd_toggle,
                                 parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='get detail for an action')
    parser.add_argument('action', help='the action to get details for',
                        default='', nargs='?')
    self.api.get('commands.add')('detail', self.cmd_detail,
                                 parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='toggle all actions in a group')
    parser.add_argument('group', help='the group to toggle',
                        default='', nargs='?')
    parser.add_argument('-d', "--disable", help="disable the group",
                        action="store_true")
    self.api.get('commands.add')('groupt', self.cmd_grouptoggle,
                                 parser=parser)

    #self.api.get('commands.add')('stats', self.cmd_stats,
    #                             shelp='show action stats')

    self.api.get('events.register')('from_mud_event',
                                    self.checkactions, prio=5)
#    self.api.get('events.register')('plugin_stats', self.getpluginstats)

  def lookup_action(self, action):
    """
    lookup an action by number or name
    """
    nitem = None
    try:
      num = int(action)
      nitem = None
      for titem in self.actions.keys():
        if num == self.actions[titem]['num']:
          nitem = titem
          break

    except ValueError:
      if action in self.actions:
        nitem = action

    return nitem

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

  def cmd_add(self, args):
    """
    add user defined actions
    """
    if not args['regex']:
      return False, ['Please include a regex']
    if not args['action']:
      return False, ['Please include an action']

    if not args['overwrite'] and args['regex'] in self.actions:
      return True, ['Action: %s already exists.' % args['regex']]
    else:
      num = 0

      if args['regex'] in self.actions:
        num = self.actions[args['regex']]['num']
      else:
        num = self.api.get('setting.gets')('nextnum')
        self.api.get('setting.change')('nextnum', num + 1)

      self.actions[args['regex']] = {
        'num': num,
        'regex':args['regex'],
        'action':args['action'],
        'send':args['send'],
        'matchcolor':args['color'],
        'enabled':not args['disable'],
        'group':args['group']
        }
      self.actions.sync()

      self.compiledregex[args['regex']] = re.compile(args['regex'])

      return True, ['added action %s - regex: %s' % (num, args['regex'])]

    return False, ['You should never see this']

  def cmd_remove(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      Remove an action
      @CUsage@w: rem @Y<originalstring>@w
        @Yoriginalstring@w    = The original string
    """
    tmsg = []
    if args['action']:
      retval = self.removeaction(args['action'])
      if retval:
        tmsg.append("@GRemoving action@w : '%s'" % (retval))
      else:
        tmsg.append("@GCould not remove action@w : '%s'" % (args['action']))

      return True, tmsg
    else:
      return False, ['@RPlease include an action to remove@w']

  def cmd_list(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      List actiones
      @CUsage@w: list
    """
    tmsg = self.listactions(args['match'])
    return True, tmsg

  def cmd_toggle(self, args):
    """
    toggle the enabled flag
    """
    tmsg = []
    if args['action']:
      retval = self.toggleaction(args['action'])
      if retval:
        if self.actions[retval]['enabled']:
          tmsg.append("@GEnabled action@w : '%s'" % (retval))
        else:
          tmsg.append("@GDisabled action@w : '%s'" % (retval))
      else:
        tmsg.append("@GDoes not exist@w : '%s'" % (args['action']))
      return True, tmsg

    else:
      return False, ['@RPlease include an action to toggle@w']

  def cmd_grouptoggle(self, args):
    """
    toggle all actions in a group
    """
    tmsg = []
    togglea = []
    state = not args['disable']
    if args['group']:
      for i in self.actions:
        if self.actions[i]['group'] == args['group']:
          self.actions[i]['enabled'] = state
          togglea.append('%s' % self.actions[i]['num'])

      if togglea:
        tmsg.append('The following actions were %s: %s' % (
                        'enabled' if state else 'disabled',
                        ','.join(togglea)))
      else:
        tmsg.append('No actions were modified')

      return True, tmsg
    else:
      return False, ['@RPlease include a group to toggle@w']

  def cmd_detail(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      Add a action
      @CUsage@w: add @Y<originalstring>@w @M<replacementstring>@w
        @Yoriginalstring@w    = The original string to be replaced
        @Mreplacementstring@w = The new string
    """
    tmsg = []
    if args['action']:
      action = self.lookup_action(args['action'])
      if action:
        if not ('hits' in self.actions[action]):
          self.actions[action]['hits'] = 0
        if not (action in self.sessionhits):
          self.sessionhits[action] = 0
        tmsg.append('%-12s : %d' % ('Num', self.actions[action]['num']))
        tmsg.append('%-12s : %s' % ('Enabled',
                            'Y' if self.actions[action]['enabled'] else 'N'))
        tmsg.append('%-12s : %d' % ('Total Hits',
                            self.actions[action]['hits']))
        tmsg.append('%-12s : %d' % ('Session Hits', self.sessionhits[action]))
        tmsg.append('%-12s : %s' % ('Regex', self.actions[action]['regex']))
        tmsg.append('%-12s : %s' % ('Action', self.actions[action]['action']))
        tmsg.append('%-12s : %s' % ('Group', self.actions[action]['group']))
        tmsg.append('%-12s : %s' % ('Match Color',
                            self.actions[action]['matchcolor']))
      else:
        return True, ['@RAction does not exits@w : \'%s\'' % (args['action'])]

      return True, tmsg
    else:
      return False, ['@RPlease include all arguments@w']

  def listactions(self, match):
    """
    return a table of strings that list actiones
    """
    tmsg = []
    for action in sorted(self.actions.keys()):
      item = self.actions[action]
      if not match or match in item:
        regex = self.api.get('colors.stripansi')(item['regex'])
        if len(regex) > 30:
          regex = regex[:27] + '...'
        action = self.api.get('colors.stripansi')(item['action'])
        if len(action) > 30:
          action = action[:27] + '...'
        tmsg.append("%4s %2s  %-10s %-32s : %s@w" % (item['num'],
                      'Y' if item['enabled'] else 'N',
                      item['group'],
                      regex,
                      action))
    if len(tmsg) == 0:
      tmsg = ['None']
    else:
      tmsg.insert(0, "%4s %2s  %-10s %-32s : %s@w" % ('#', 'E', 'Group',
                                                      'Regex', 'Action'))
      tmsg.insert(1, '@B' + '-' * 60 + '@w')

    return tmsg

  def removeaction(self, item):
    """
    internally remove a action
    """
    action = self.lookup_action(item)
    print 'lookup_action', item, 'returned', action
    if action >= 0:
      del self.actions[action]
      self.actions.sync()

    return action

  def toggleaction(self, item):
    """
    toggle an action
    """
    action = self.lookup_action(item)
    if action:
      self.actions[action]['enabled'] = not self.actions[action]['enabled']

    return action

  def clearactions(self):
    """
    clear all actiones
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
