"""
$Id$

This plugin will show information about connections to the proxy
"""
import re
from plugins._baseplugin import BasePlugin
from libs.timing import timeit
from libs.color import convertcolors

#these 5 are required
NAME = 'triggers'
SNAME = 'triggers'
PURPOSE = 'handle triggers'
AUTHOR = 'Bast'
VERSION = 1

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

    self.api.get('events.register')('from_mud_event', self.checktrigger, prio=1)

  # add a trigger
  def api_addtrigger(self, triggername, args):
    """  add a trigger
    @Ytriggername@w   = The trigger name
    @Yargs@w arguments:
      @Yregex@w    = the regular expression that matches this trigger
      @Yenabled@w  = (optional) whether the trigger is enabled (default: True)
      @Ygroup@w    = (optional) the group the trigger is a member of
      @Yomit@w     = (optional) True to omit the line from the client, False otherwise

    this function returns no values"""
    if not ('regex' in args):
      self.api.get('output.msg')('trigger %s has no regex, not adding' % triggername)
      return
    if args['regex'] in self.regexlookup:
      self.api.get('output.msg')(
            'trigger %s tried to add a regex that already existed for %s' % \
                    (triggername, self.regexlookup[args['regex']]))
      return
    if not ('enabled' in args):
      args['enabled'] = True
    if not ('group' in args):
      args['group'] = None
    if not ('omit' in args):
      args['omit'] = False
    if not ('argtypes' in args):
      args['argtypes'] = {}
    try:
      self.triggers[triggername] = args
      self.triggers[triggername]['compiled'] = re.compile(args['regex'])
      self.regexlookup[args['regex']] = triggername
      if args['group']:
        if not (args['group'] in self.triggergroups):
          self.triggergroups[args['group']] = []
        self.triggergroups[args['group']].append(triggername)
    except:
      self.api.get('output.traceback')(
              'Could not compile regex for trigger: %s : %s' % \
                      (triggername, args['regex']))

  # remove a trigger
  def api_remove(self, triggername):
    """  remove a trigger
    @Ytriggername@w   = The trigger name

    this function returns no values"""
    if triggername in self.triggers:
      del self.regexlookup[self.triggers[triggername]['regex']]
      del self.triggers[triggername]
    else:
      self.api.get('output.msg')('deletetrigger: trigger %s does not exist' % \
                        triggername)

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
            args = self.raisetrigger(i, targs, args)

    self.raisetrigger('all', {'line':data, 'triggername':'all'}, args)

    return args

  def raisetrigger(self, triggername, args, origargs):
    """
    raise a trigger event
    """
    tdat = self.api.get('events.eraise')('trigger_' + triggername, args)
    self.api.get('output.msg')('trigger raiseevent returned: %s' % tdat)
    if tdat and 'newline' in tdat:
      self.api.get('output.msg')('changing line from trigger')
      origargs['fromdata'] = convertcolors(tdat['newline'])
    if triggername in self.triggers and self.triggers[triggername]['omit']:
      origargs['fromdata'] = ''
    return

