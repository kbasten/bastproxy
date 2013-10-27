"""
$Id$

#TODO: make initialized events use the same syntax as runtime added events
  make an addevent function to the plugin baseclass
  same with commands and all other items that can be added at runtime

make all functions that add things use kwargs instead of a table
"""
import os
from libs.utils import verify, convert
from libs.persistentdict import PersistentDict
from libs.api import API


class PersistentDictEvent(PersistentDict):
  """
  a class to send events when a dictionary object is set
  """
  def __init__(self, plugin, filename, *args, **kwds):
    """
    init the class
    """
    self.plugin = plugin
    self.api = API()
    PersistentDict.__init__(self, filename, *args, **kwds)

  def __setitem__(self, key, val):
    """
    override setitem
    """
    key = convert(key)
    val = convert(val)
    dict.__setitem__(self, key, val)
    eventname = '%s_%s' % (self.plugin.sname, key)
    if not self.plugin.resetflag:
      self.api.get('events.eraise')(eventname, {'var':key,
                                        'newvalue':val})


class BasePlugin(object):
  """
  a base class for plugins
  """
  def __init__(self, name, sname, fullname, basepath, fullimploc):
    """
    initialize the instance
    """
    self.author = ''
    self.purpose = ''
    self.version = 0
    self.name = name
    self.sname = sname
    self.dependencies = []
    self.canreload = True
    self.resetflag = False
    self.api = API()
    self.savedir = os.path.join(self.api.BASEPATH, 'data',
                                      'plugins', self.sname)
    try:
      os.makedirs(self.savedir)
    except OSError:
      pass
    self.savefile = os.path.join(self.api.BASEPATH, 'data',
                                    'plugins', self.sname, 'settingvalues.txt')
    self.fullname = fullname
    self.basepath = basepath
    self.fullimploc = fullimploc

    self.cmds = {}
    self.settingvalues = PersistentDictEvent(self, self.savefile,
                            'c', format='json')
    self.settings = {}
    self.api.overload('output', 'msg', self.msg)
    self.api.overload('commands', 'default', self.defaultcmd)
    self.api.overload('dependency', 'add', self.adddependency)
    self.api.overload('setting', 'add', self.addsetting)
    self.api.overload('setting', 'gets', self.getsetting)
    self.api.overload('api', 'add', self.addapi)
    self.timers = {}
    self.triggers = {}
    self.cmdwatch = {}

    self.api.get('logger.adddtype')(self.sname)
    self.api.get('commands.add')('set', {'func':self.cmd_set, 'shelp':'Show/Set Settings'})
    self.api.get('commands.add')('reset', {'func':self.cmd_reset, 'shelp':'reset the plugin'})
    self.api.get('commands.add')('save', {'func':self.cmd_save, 'shelp':'save plugin state'})
    self.api.get('events.register')('firstactive', self.afterfirstactive)

  # get the vaule of a setting
  def getsetting(self, setting):
    """  get the value of a setting
    @Ysetting@w = the setting value to get

    this function returns the value of the setting, None if not found"""
    try:
      return self.settingvalues[setting]
    except KeyError:
      return None

  # add a plugin dependency
  def adddependency(self, dependency):
    """  add a depencency
    @Ydependency@w    = the name of the plugin that will be a dependency

    this function returns no values"""
    if not (dependency in self.dependencies):
      self.dependencies.append(dependency)

  def load(self):
    """
    load stuff
    """
    # load all commands
    proxy = self.api.get('managers.getm')('proxy')

    self.settingvalues.pload()

    # register all timers
    for i in self.timers:
      tim = self.timers[i]
      self.api.get('timers.add')(i, tim)

    for i in self.triggers:
      self.api.get('triggers.add')(i, self.triggers[i])

    for i in self.cmdwatch:
      self.api.get('cmdwatch.add')(i, self.watch[i])

    #if len(self.exported) > 0:
      #for i in self.exported:
        #self.api.add(self.sname, i, self.exported[i]['func'])

    if proxy and proxy.connected:
      try:
        if self.api.get('connect.firstactive'):
          self.api.get('events.unregister')('firstactive', self.afterfirstactive)
          self.afterfirstactive()
      except AttributeError:
        pass

    self.api.get('events.eraise')('event_plugin_load', {'plugin':self.sname})

  def unload(self):
    """
    unload stuff
    """
    self.api.get('output.msg')('unloading %s' % self.name)

    #clear all commands for this plugin
    self.api.get('commands.removeplugin')(self.sname)

    #remove all events
    self.api.get('events.removeplugin')(self.sname)

    # delete all timers
    for i in self.timers:
      self.api.get('timers.remove')(i)

    for i in self.triggers:
      self.api.get('triggers.remove')(i)

    for i in self.cmdwatch:
      self.api.get('cmdwatch.remove')(i, self.watch[i])

    #save the state
    self.savestate()

    # remove anything out of the api
    self.api.get('api.remove')(self.sname)

    self.api.get('events.eraise')('event_plugin_unload', {'plugin':self.sname})

  # handle a message
  def msg(self, msg):
    """
    an internal function to send msgs
    """
    self.api.get('output.msg', True)(msg, self.sname)

  def savestate(self):
    """
    save the state
    """
    self.settingvalues.sync()

  def cmd_set(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
    List or set vars
    @CUsage@w: var @Y<varname>@w @Y<varvalue>@w
      @Ysettingname@w    = The setting to set
      @Ysettingvalue@w   = The value to set it to
      if there are no arguments or 'list' is the first argument then
      it will list the settings for the plugin
    """
    if len(args) == 0 or args[0] == 'list':
      return True, self.listvars()
    elif len(args) == 2:
      var = args[0]
      val = args[1]
      if var in self.settings:
        if 'readonly' in self.settings[var] \
              and self.settings[var]['readonly']:
          return True, ['%s is a readonly setting' % var]
        else:
          if val == 'default':
            val = self.settings[var]['default']
          try:
            val = verify(val, self.settings[var]['stype'])
            self.settingvalues[var] = val
            self.settingvalues.sync()
            tvar = self.settingvalues[var]
            if self.settings[var]['nocolor']:
              tvar = tvar.replace('@', '@@')
            elif self.settings[var]['stype'] == 'color':
              tvar = '%s%s@w' % (val, val.replace('@', '@@'))
            return True, ['set %s to %s' % (var, tvar)]
          except ValueError:
            msg = ['Cannot convert %s to %s' % \
                                    (val, self.settings[var]['stype'])]
            return True, msg
        return True, self.listvars()
    return False, {}

  def cmd_save(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
    save plugin state
    @CUsage@w: save
    """
    self.savestate()
    return True, ['Plugin settings saved']

  def listvars(self):
    """
    return a list of strings that list all settings
    """
    tmsg = []
    if len(self.settingvalues) == 0:
      tmsg.append('There are no settings defined')
    else:
      tform = '%-15s : %-15s - %s'
      for i in self.settings:
        val = self.settingvalues[i]
        if 'nocolor' in self.settings[i] and self.settings[i]['nocolor']:
          val = val.replace('@', '@@')
        elif self.settings[i]['stype'] == 'color':
          val = '%s%s@w' % (val, val.replace('@', '@@'))
        tmsg.append(tform % (i, val, self.settings[i]['help']))
    return tmsg

  # add a setting to the plugin
  def addsetting(self, name, default, stype, shelp, **kwargs):
    """  remove a command
    @Yname@w     = the name of the setting
    @Ydefault@w  = the default value of the setting
    @Ystype@w    = the type of the setting
    @Yshelp@w    = the help associated with the setting
    Keyword Arguments
      @Ynocolor@w    = if True, don't parse colors when showing value
      @Yreadonly@w   = if True, can't be changed by a client

    this function returns no values"""

    if 'nocolor' in kwargs:
      nocolor = kwargs['nocolor']
    else:
      nocolor = False
    if 'readonly' in kwargs:
      readonly = kwargs['readonly']
    else:
      readonly = False
    if not (name in self.settingvalues):
      self.settingvalues[name] = default
    self.settings[name] = {'default':default, 'help':shelp,
                  'stype':stype, 'nocolor':nocolor, 'readonly':readonly}

  def cmd_reset(self, _=None):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      reset the plugin
      @CUsage@w: reset
    """
    self.reset()
    return True, ['Plugin reset']

  def reset(self):
    """
    internal function to reset data
    """
    self.resetflag = True
    self.settingvalues.clear()
    for i in self.settings:
      self.settingvalues[i] = self.settings[i]['default']
    self.settingvalues.sync()
    self.resetflag = False

  def afterfirstactive(self, _=None):
    """
    if we are connected do
    """
    self.api.get('events.unregister')('firstactive', self.afterfirstactive)

  # set the default command
  def defaultcmd(self, cmd):
    """
    set a command as default
    """
    # we call the non overloaded versions
    self.api.get('commands.default', True)(self.sname, cmd)

  # add a function to the api
  def addapi(self, name, func):
    """
    set a command as default
    """
    # we call the non overloaded versions
    self.api.add(self.sname, name, func)
