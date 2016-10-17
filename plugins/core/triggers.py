"""
This plugin handles internal triggers for the proxy
"""
import re
import sys
import argparse
import time
from plugins._baseplugin import BasePlugin
from libs.timing import timeit

#these 5 are required
NAME = 'triggers'
SNAME = 'triggers'
PURPOSE = 'handle triggers'
AUTHOR = 'Bast'
VERSION = 1
PRIORITY = 25

# This keeps the plugin from being autoloaded if set to False
AUTOLOAD = True

class Plugin(BasePlugin):
  """
  a plugin to handle internal triggers
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)

    self.canreload = False

    self.triggers = {}
    self.regexlookup = {}
    self.triggergroups = {}

    self.api.get('api.add')('add', self.api_addtrigger)
    self.api.get('api.add')('remove', self.api_remove)
    self.api.get('api.add')('toggle', self.api_toggle)
    self.api.get('api.add')('gett', self.api_gett)
    self.api.get('api.add')('togglegroup', self.api_togglegroup)
    self.api.get('api.add')('toggleomit', self.api_toggleomit)
    self.api.get('api.add')('removeplugin', self.api_removeplugin)

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

    parser = argparse.ArgumentParser(add_help=False,
                                     description='get details of a trigger')
    parser.add_argument('trigger',
                        help='the trigger to detail',
                        default=[],
                        nargs='*')
    self.api.get('commands.add')('detail',
                                 self.cmd_detail,
                                 parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                                     description='list triggers')
    parser.add_argument('match',
                        help='list only triggers that have this argument in them',
                        default='',
                        nargs='?')
    self.api.get('commands.add')('list',
                                 self.cmd_list,
                                 parser=parser)

    self.api.get('events.register')('from_mud_event',
                                    self.checktrigger, prio=1)

    self.api.get('events.register')('plugin_unloaded', self.pluginunloaded)

  def pluginunloaded(self, args):
    """
    a plugin was unloaded
    """
    self.api('send.msg')('removing triggers for plugin %s' % args['name'],
                         secondary=args['name'])
    self.api('%s.removeplugin' % self.sname)(args['name'])

  # add a trigger
  def api_addtrigger(self, triggername, regex, plugin=None, **kwargs):
    """  add a trigger
    @Ytriggername@w   = The trigger name
    @Yregex@w    = the regular expression that matches this trigger
    @Yplugin@w   = the plugin this comes from, added
          automatically if using the api through BaseClass
    @Ykeyword@w arguments:
      @Yenabled@w  = (optional) whether the trigger is enabled (default: True)
      @Ygroup@w    = (optional) the group the trigger is a member of
      @Yomit@w     = (optional) True to omit the line from the client,
                              False otherwise
      @Yargtypes@w = (optional) a dict of keywords in the regex and their type
      @Ypriority@w = (optional) the priority of the trigger, default is 100
      @Ystopevaluating@w = (optional) True to stop trigger evauluation if this
                              trigger is matched

    this function returns no values"""
    if not plugin:
      plugin = self.api('utils.funccallerplugin')()

    if not plugin:
      print 'could not add a trigger for triggername', triggername
      return False

    if regex in self.regexlookup:
      self.api.get('send.msg')(
          'trigger %s tried to add a regex that already existed for %s' % \
              (triggername, self.regexlookup[regex]))
      return False
    args = kwargs.copy()
    args['regex'] = regex
    if 'enabled' not in args:
      args['enabled'] = True
    if 'group' not in args:
      args['group'] = None
    if 'omit' not in args:
      args['omit'] = False
    if 'priority' not in args:
      args['priority'] = 100
    if 'stopevaluating' not in args:
      args['stopevaluating'] = False
    if 'argtypes' not in args:
      args['argtypes'] = {}
    args['plugin'] = plugin
    args['hits'] = 0
    try:
      self.triggers[triggername] = args
      self.triggers[triggername]['compiled'] = re.compile(args['regex'])
      self.triggers[triggername]['eventname'] = 'trigger_' + triggername
      self.regexlookup[args['regex']] = triggername
      if args['group']:
        if args['group'] not in self.triggergroups:
          self.triggergroups[args['group']] = []
        self.triggergroups[args['group']].append(triggername)
      self.api.get('send.msg')(
          'added trigger %s for plugin %s' % \
              (triggername, plugin), secondary=plugin)
    except Exception:  # pylint: disable=broad-except
      self.api.get('send.traceback')(
          'Could not compile regex for trigger: %s : %s' % \
              (triggername, args['regex']))
      return False

    return True

  # remove a trigger
  def api_remove(self, triggername, force=False):
    """  remove a trigger
    @Ytriggername@w   = The trigger name
    @Yforce@w         = True to remove it even if other functions
                              are registered
       (default: False)

    this function returns True if the trigger was removed,
                              False if it wasn't"""
    if triggername in self.triggers:
      event = self.api.get('events.gete')(
          self.triggers[triggername]['eventname'])
      plugin = self.triggers[triggername]['plugin']
      if event:
        if len(event['pluginlist']) > 0 and not force:
          self.api.get('send.msg')(
              'deletetrigger: trigger %s has functions registered' % triggername,
              secondary=plugin)
          return False
      plugin = self.triggers[triggername]['plugin']
      del self.regexlookup[self.triggers[triggername]['regex']]
      del self.triggers[triggername]
      self.api.get('send.msg')('removed trigger %s' % triggername,
                               secondary=plugin)
      return True
    else:
      self.api.get('send.msg')('deletetrigger: trigger %s does not exist' % \
                        triggername)
      return False

  # get a trigger
  def api_gett(self, triggername):
    """get a trigger
    @Ytriggername@w   = The trigger name
    """
    if triggername in self.triggers:
      return self.triggers[triggername]
    else:
      return None

  # remove all triggers related to a plugin
  def api_removeplugin(self, plugin):
    """  remove all triggers related to a plugin
    @Yplugin@w   = The plugin name

    this function returns no values"""
    self.api.get('send.msg')('removing triggers for plugin %s' % plugin,
                             secondary=plugin)
    tkeys = self.triggers.keys()
    for i in tkeys:
      if self.triggers[i]['plugin'] == plugin:
        self.api.get('triggers.remove')(i)

  # toggle a trigger
  def api_toggle(self, triggername, flag):
    """  toggle a trigger
    @Ytriggername@w = The trigger name
    @Yflag@w        = (optional) True to enable, False otherwise

    this function returns no values"""
    if triggername in self.triggers:
      self.triggers[triggername]['enabled'] = flag
    else:
      self.api.get('send.msg')('toggletrigger: trigger %s does not exist' % \
        triggername)

  # toggle the omit flag for a trigger
  def api_toggleomit(self, triggername, flag):
    """  toggle a trigger
    @Ytriggername@w = The trigger name
    @Yflag@w        = (optional) True to omit the line, False otherwise

    this function returns no values"""
    if triggername in self.triggers:
      self.triggers[triggername]['omit'] = flag
    else:
      self.api.get('send.msg')('toggletriggeromit: trigger %s does not exist' % \
        triggername)

  # toggle a trigger group
  def api_togglegroup(self, triggroup, flag):
    """  toggle a trigger group
    @Ytriggername@w = The triggergroup name
    @Yflag@w        = (optional) True to enable, False otherwise

    this function returns no values"""
    self.api.get('send.msg')('toggletriggergroup: %s to %s' % \
                                                (triggroup, flag))
    if triggroup in self.triggergroups:
      for i in self.triggergroups[triggroup]:
        self.api.get('triggers.toggle')(i, flag)

  def checktrigger(self, args):
    # pylint: disable=too-many-nested-blocks,too-many-branches
    """
    check a line of text from the mud to see if it matches any triggers
    called whenever the from_mud_event is raised
    """
    time1 = time.time()
    self.api.get('send.msg')('checktrigger: %s started' % (args), 'timing')
    data = args['noansi']
    colordata = args['convertansi']

    self.raisetrigger('beall',
                      {'line':data, 'triggername':'all'},
                      args)

    if data == '':
      self.raisetrigger('emptyline',
                        {'line':'', 'triggername':'emptyline'},
                        args)
    else:
      triggers = sorted(self.triggers,
                        key=lambda item: self.triggers[item]['priority'])
      for i in triggers:
        if i in self.triggers:
          if self.triggers[i]['enabled']:
            trigre = self.triggers[i]['compiled']
            if 'matchcolor' in self.triggers[i] \
                and self.triggers[i]['matchcolor']:
              mat = trigre.match(colordata)
            else:
              mat = trigre.match(data)
            if mat:
              targs = mat.groupdict()
              if 'argtypes' in self.triggers[i]:
                for arg in self.triggers[i]['argtypes']:
                  if arg in targs:
                    targs[arg] = self.triggers[i]['argtypes'][arg](targs[arg])
              targs['line'] = data
              targs['colorline'] = colordata
              targs['triggername'] = i
              self.triggers[i]['hits'] = self.triggers[i]['hits'] + 1
              args = self.raisetrigger(i, targs, args)
              if i in self.triggers:
                if self.triggers[i]['stopevaluating']:
                  break

    self.raisetrigger('all', {'line':data, 'triggername':'all'}, args)
    time2 = time.time()
    self.api('send.msg')('%s: %0.3f ms' % \
              ('checktrigger', (time2-time1)*1000.0), 'timing')
    return args

  def raisetrigger(self, triggername, args, origargs):
    """
    raise a trigger event
    """
    time1 = time.time()
    self.api.get('send.msg')('raisetrigger: %s started %s' % (triggername, args), 'timing')
    try:
      eventname = self.triggers[triggername]['eventname']
    except KeyError:
      eventname = 'trigger_' + triggername
    if triggername in self.triggers and self.triggers[triggername]['omit']:
      origargs['omit'] = True

    tdat = self.api.get('events.eraise')(eventname, args)
    self.api.get('send.msg')('trigger raiseevent returned: %s' % tdat)
    if tdat and 'newline' in tdat:
      self.api.get('send.msg')('changing line from trigger')
      origargs['original'] = self.api.get('colors.convertcolors')(tdat['newline'])
    if tdat and 'omit' in tdat and tdat['omit']:
      origargs['omit'] = True
    if triggername in self.triggers and self.triggers[triggername]['omit']:
      origargs['original'] = ''
      origargs['omit'] = True
    time2 = time.time()
    self.api('send.msg')('%s: %0.3f ms' % \
              (triggername, (time2-time1)*1000.0), 'timing')
    return

  def cmd_list(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      list triggers and the plugins they are defined in
      @CUsage@w: list
    """
    tmsg = []
    tkeys = self.triggers.keys()
    tkeys.sort()
    match = args['match']

    tmsg.append('%-25s : %-13s %-9s %s' % ('Name', 'Defined in',
                                           'Enabled', 'Hits'))
    tmsg.append('@B' + '-' * 60 + '@w')
    for i in tkeys:
      trigger = self.triggers[i]
      if not match or match in i or trigger['plugin'] == match:
        tmsg.append('%-25s : %-13s %-9s %s' % \
          (i, trigger['plugin'], trigger['enabled'], trigger['hits']))

    return True, tmsg

  def getstats(self):
    """
    return stats for this plugin
    """
    stats = BasePlugin.getstats(self)

    totalhits = 0
    totalenabled = 0
    totaldisabled = 0
    for trigger in self.triggers:
      totalhits = totalhits + self.triggers[trigger]['hits']
      if self.triggers[trigger]['enabled']:
        totalenabled = totalenabled + 1
      else:
        totaldisabled = totaldisabled + 1

    totaltriggers = len(self.triggers)

    stats['Triggers'] = {}
    stats['Triggers']['showorder'] = ['Total', 'Enabled', 'Disabled',
                                      'Total Hits', 'Memory Usage']
    stats['Triggers']['Total'] = totaltriggers
    stats['Triggers']['Enabled'] = totalenabled
    stats['Triggers']['Disabled'] = totaldisabled
    stats['Triggers']['Total Hits'] = totalhits
    stats['Triggers']['Memory Usage'] = sys.getsizeof(self.triggers)
    return stats

  def cmd_detail(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      list the details of a trigger
      @CUsage@w: detail
    """
    tmsg = []
    if len(args['trigger']) > 0:
      for trigger in args['trigger']:
        if trigger in self.triggers:
          eventname = self.triggers[trigger]['eventname']
          eventstuff = self.api.get('events.detail')(eventname)
          tmsg.append('%-13s : %s' % ('Name', trigger))
          tmsg.append('%-13s : %s' % ('Defined in',
                                      self.triggers[trigger]['plugin']))
          tmsg.append('%-13s : %s' % ('Regex',
                                      self.triggers[trigger]['regex']))
          tmsg.append('%-13s : %s' % ('Group',
                                      self.triggers[trigger]['group']))
          tmsg.append('%-13s : %s' % ('Omit', self.triggers[trigger]['omit']))
          tmsg.append('%-13s : %s' % ('Hits', self.triggers[trigger]['hits']))
          tmsg.append('%-13s : %s' % ('Enabled',
                                      self.triggers[trigger]['enabled']))
          tmsg.extend(eventstuff)
        else:
          tmsg.append('trigger %s does not exist' % trigger)
    else:
      tmsg.append('Please provide a trigger name')

    return True, tmsg

