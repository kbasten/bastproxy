"""
$Id$

This plugin will show information about connections to the proxy
"""
import re
from plugins._baseplugin import BasePlugin
from libs.timing import timeit
from libs.color import convertcolors
from libs import utils

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
  a plugin to show connection information
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
    self.api.get('api.add')('togglegroup', self.api_togglegroup)
    self.api.get('api.add')('toggleomit', self.api_toggleomit)
    self.api.get('api.add')('removeplugin', self.api_removeplugin)

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

    self.api.get('commands.add')('detail', self.cmd_detail,
                                 shelp='details of a trigger')
    self.api.get('commands.add')('list', self.cmd_list,
                                 shelp='list triggers')
    self.api.get('commands.add')('stats', self.cmd_stats,
                                 shelp='show trigger stats')

    self.api.get('events.register')('from_mud_event', self.checktrigger, prio=1)

  # add a trigger
  def api_addtrigger(self, triggername, regex, plugin, **kwargs):
    """  add a trigger
    @Ytriggername@w   = The trigger name
    @Yregex@w    = the regular expression that matches this trigger
    @Yplugin@w   = the plugin this comes from, added
          automatically if using the api through BaseClass
    @Ykeyword args@w arguments:
      @Yenabled@w  = (optional) whether the trigger is enabled (default: True)
      @Ygroup@w    = (optional) the group the trigger is a member of
      @Yomit@w     = (optional) True to omit the line from the client, False otherwise
      @Yargtypes@w = (optional) a dict of keywords in the regex and their type

    this function returns no values"""
    if regex in self.regexlookup:
      self.api.get('output.msg')(
            'trigger %s tried to add a regex that already existed for %s' % \
                    (triggername, self.regexlookup[regex]))
      return
    args = kwargs.copy()
    args['regex'] = regex
    if not ('enabled' in args):
      args['enabled'] = True
    if not ('group' in args):
      args['group'] = None
    if not ('omit' in args):
      args['omit'] = False
    if not ('argtypes' in args):
      args['argtypes'] = {}
    args['plugin'] = plugin
    args['hits'] = 0
    try:
      self.triggers[triggername] = args
      self.triggers[triggername]['compiled'] = re.compile(args['regex'])
      self.triggers[triggername]['eventname'] = 'trigger_' + triggername
      self.regexlookup[args['regex']] = triggername
      if args['group']:
        if not (args['group'] in self.triggergroups):
          self.triggergroups[args['group']] = []
        self.triggergroups[args['group']].append(triggername)
      self.api.get('output.msg')(
            'added trigger %s for plugin %s' % \
                    (triggername, plugin), secondary=plugin)
    except:
      self.api.get('output.traceback')(
              'Could not compile regex for trigger: %s : %s' % \
                      (triggername, args['regex']))

  # remove a trigger
  def api_remove(self, triggername, force=False):
    """  remove a trigger
    @Ytriggername@w   = The trigger name
    @Yforce@w         = True to remove it even if other functions are registered
       (default: False)

    this function returns True if the trigger was removed, False if it wasn't"""
    if triggername in self.triggers:
      event = self.api.get('events.gete')(self.triggers[triggername]['eventname'])
      plugin = self.triggers[triggername]['plugin']
      if event:
        if len(event['pluginlist']) > 0 and not force:
          self.api.get('output.msg')('deletetrigger: trigger %s has functions registered' % \
                      triggername, secondary=plugin)
          return False
      plugin = self.triggers[triggername]['plugin']
      del self.regexlookup[self.triggers[triggername]['regex']]
      del self.triggers[triggername]
      self.api.get('output.msg')('removed trigger %s' % triggername,
                                 secondary=plugin)
      return True
    else:
      self.api.get('output.msg')('deletetrigger: trigger %s does not exist' % \
                        triggername)
      return False

  # remove all triggers related to a plugin
  def api_removeplugin(self, plugin):
    """  remove all triggers related to a plugin
    @Yplugin@w   = The plugin name

    this function returns no values"""
    self.api.get('output.msg')('removing triggers for plugin %s' % plugin,
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
      self.api.get('output.msg')('toggletrigger: trigger %s does not exist' % \
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
      self.api.get('output.msg')('toggletriggeromit: trigger %s does not exist' % \
                        triggername)

  # toggle a trigger group
  def api_togglegroup(self, triggroup, flag):
    """  toggle a trigger group
    @Ytriggername@w = The triggergroup name
    @Yflag@w        = (optional) True to enable, False otherwise

    this function returns no values"""
    self.api.get('output.msg')('toggletriggergroup: %s to %s' % (triggroup, flag))
    if triggroup in self.triggergroups:
      for i in self.triggergroups[triggroup]:
        self.api.get('triggers.toggle')(i, flag)

  @timeit
  def checktrigger(self, args):
    """
    check a line of text from the mud
    the is called whenever the from_mud_event is raised
    """
    data = args['nocolordata']

    self.raisetrigger('beall', {'line':data, 'triggername':'all'}, args)

    if data == '':
      self.raisetrigger('emptyline',
                        {'line':'', 'triggername':'emptyline'}, args)
    else:
      for i in self.triggers:
        if self.triggers[i]['enabled']:
          trigre = self.triggers[i]['compiled']
          mat = trigre.match(data)
          if mat:
            targs = mat.groupdict()
            if 'argtypes' in self.triggers[i]:
              for arg in self.triggers[i]['argtypes']:
                if arg in targs:
                  targs[arg] = self.triggers[i]['argtypes'][arg](targs[arg])
            targs['line'] = data
            targs['triggername'] = i
            self.triggers[i]['hits'] = self.triggers[i]['hits'] + 1
            args = self.raisetrigger(i, targs, args)

    self.raisetrigger('all', {'line':data, 'triggername':'all'}, args)

    return args

  def raisetrigger(self, triggername, args, origargs):
    """
    raise a trigger event
    """
    try:
      eventname = self.triggers[triggername]['eventname']
    except KeyError:
      eventname = 'trigger_' + triggername
    tdat = self.api.get('events.eraise')(eventname, args)
    self.api.get('output.msg')('trigger raiseevent returned: %s' % tdat)
    if tdat and 'newline' in tdat:
      self.api.get('output.msg')('changing line from trigger')
      origargs['fromdata'] = convertcolors(tdat['newline'])
    if triggername in self.triggers and self.triggers[triggername]['omit']:
      origargs['fromdata'] = ''
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
    tmsg.append('%-25s : %-13s %-9s %s' % ('Name', 'Defined in', 'Enabled', 'Hits'))
    tmsg.append('@B' + '-' * 60 + '@w')
    for i in tkeys:
      trigger = self.triggers[i]
      tmsg.append('%-25s : %-13s %-9s %s' % (i, trigger['plugin'], trigger['enabled'], trigger['hits']))

    return True, tmsg

  def cmd_stats(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      get stats for the # of triggers, hits, etc
      @CUsage@w: stats
    """
    tmsg = []
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

    tmsg.append('%-20s : %s' % ('Total Triggers', totaltriggers))
    tmsg.append('%-20s : %s' % ('Enabled', totalenabled))
    tmsg.append('%-20s : %s' % ('Disabled', totaldisabled))
    tmsg.append('%-20s : %s' % ('Total Hits', totalhits))

    return True, tmsg


  def cmd_detail(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      list triggers and the plugins registered with them
      @CUsage@w: list
    """
    tmsg = []
    if len(args) > 0:
      for trigger in args:
        if trigger in self.triggers:
          eventname = self.triggers[trigger]['eventname']
          eventstuff = self.api.get('events.detail')(eventname)
          tmsg.append('%-13s : %s' % ('Name', trigger))
          tmsg.append('%-13s : %s' % ('Defined in', self.triggers[trigger]['plugin']))
          tmsg.append('%-13s : %s' % ('Regex', self.triggers[trigger]['regex']))
          tmsg.append('%-13s : %s' % ('Group', self.triggers[trigger]['group']))
          tmsg.append('%-13s : %s' % ('Omit', self.triggers[trigger]['omit']))
          tmsg.append('%-13s : %s' % ('Hits', self.triggers[trigger]['hits']))
          tmsg.append('%-13s : %s' % ('Enabled', self.triggers[trigger]['enabled']))
          tmsg.extend(eventstuff)
        else:
          tmsg.append('trigger %s does not exist' % trigger)
    else:
      tmsg.append('Please provide a trigger name')

    return True, tmsg

