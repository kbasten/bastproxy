"""
$Id$

This module holds the class BasePlugin, which all plugins should have as
their base class.
"""
import os
import sys
import argparse
import textwrap
from libs.persistentdict import PersistentDictEvent
from libs.api import API

class BasePlugin(object):
  """
  a base class for plugins
  """
  def __init__(self, name, sname, modpath, basepath, fullimploc):
    """
    initialize the instance
    The following things should not be done in __init__ in a plugin
      Interacting with anything in the api except api.add, api.overload
          or dependency.add
    """
    self.author = ''
    self.purpose = ''
    self.version = 0
    self.priority = 100
    self.name = name
    self.sname = sname
    self.dependencies = []
    self.reloaddependents = False
    self.canreload = True
    self.resetflag = True
    self.api = API()
    self.savedir = os.path.join(self.api.BASEPATH, 'data',
                                      'plugins', self.sname)
    try:
      os.makedirs(self.savedir)
    except OSError:
      pass
    self.savefile = os.path.join(self.api.BASEPATH, 'data',
                                    'plugins', self.sname, 'settingvalues.txt')
    self.modpath = modpath
    self.basepath = basepath
    self.fullimploc = fullimploc
    self.package = fullimploc.split('.')[1]

    self.settings = {}
    self.settingvalues = PersistentDictEvent(self, self.savefile, 'c')

    self.api.overload('send', 'msg', self.api_outputmsg)
    self.api.overload('commands', 'default', self.api_commandsdefault)
    self.api.overload('dependency', 'add', self.api_dependencyadd)
    self.api.overload('setting', 'add', self.api_settingadd)
    self.api.overload('setting', 'gets', self.api_settinggets)
    self.api.overload('setting', 'change', self.api_settingchange)
    self.api.overload('api', 'add', self.api_add)
    self.api.overload('triggers', 'add', self.api_triggersadd)
    self.api.overload('watch', 'add', self.api_watchadd)

  def load(self):
    """
    load stuff, do most things here
    """
    self.settingvalues.pload()

    self.api.get('log.adddtype')(self.sname)
    setparser = argparse.ArgumentParser(add_help=False,
                formatter_class=argparse.RawDescriptionHelpFormatter,
                description=textwrap.dedent("""
          change a setting in the plugin

          if there are no arguments or 'list' is the first argument then
          it will list the settings for the plugin"""))
    setparser.add_argument('name', help='the setting name',
                           default='list', nargs='?')
    setparser.add_argument('value', help='the new value of the setting',
                           default='', nargs='?')
    self.api.get('commands.add')('set', self.cmd_set, parser=setparser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='reset the plugin')
    self.api.get('commands.add')('reset', self.cmd_reset,
                                 parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='save the plugin state')
    self.api.get('commands.add')('save', self.cmd_save,
                                 parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='show plugin stats')
    self.api.get('commands.add')('stats', self.cmd_stats,
                                 parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='show help info for this plugin')
    parser.add_argument('-a', "--api",
          help="show functions this plugin has in the api",
              action="store_true")
    parser.add_argument('-c', "--commands",
          help="show commands in this plugin",
              action="store_true")
    self.api.get('commands.add')('help', self.cmd_help,
                                 parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='list functions in the api')
    parser.add_argument('api',
                        help='api to get details of',
                        default='', nargs='?')
    self.api.get('commands.add')('api', self.cmd_api,
                                 parser=parser)

    self.api.get('events.register')('%s_plugin_loaded' % self.sname,
                                                self.afterload)

    self.api.get('events.register')('shutdown', self.unload)
    self.api.get('events.register')('muddisconnect', self.disconnect)

    self.resetflag = False

  def cmd_api(self, args):
    """
    list functions in the api for a plugin
    """
    tmsg = []
    if args['api']:
      tmsg.extend(self.api.get('api.detail')("%s.%s" % (self.sname,
                                                          args['api'])))
    else:
      apilist = self.api.get('api.list')(self.sname)
      if not apilist:
        tmsg.append('nothing in the api')
      else:
        tmsg.extend(apilist)

    return True, tmsg

  def afterload(self, args):
    """
    do something after the load function is run
    """
    proxy = self.api.get('managers.getm')('proxy')

    if proxy and proxy.connected:
      if self.api.get('api.has')('connect.firstactive'):
        if self.api.get('connect.firstactive')():
          self.afterfirstactive()
      else:
        self.api.get('events.register')('firstactive', self.afterfirstactive)
    else:
      self.api.get('events.register')('firstactive', self.afterfirstactive)

  def disconnect(self, args=None):
    """
    re-register to firstactive on disconnect
    """
    self.api.get('send.msg')('baseplugin, disconnect')
    self.api.get('events.register')('firstactive', self.afterfirstactive)

  # get the vaule of a setting
  def api_settinggets(self, setting):
    """  get the value of a setting
    @Ysetting@w = the setting value to get

    this function returns the value of the setting, None if not found"""
    try:
      return self.api.get('utils.verify')(self.settingvalues[setting],
                                          self.settings[setting]['stype'])
    except KeyError:
      return None

  # add a plugin dependency
  def api_dependencyadd(self, dependency):
    """  add a depencency
    @Ydependency@w    = the name of the plugin that will be a dependency

    this function returns no values"""
    if not (dependency in self.dependencies):
      self.dependencies.append(dependency)

  # change the value of a setting
  def api_settingchange(self, setting, value):
    """  change a setting
    @Ysetting@w    = the name of the setting to change
    @Yvalue@w      = the value to set it as

    this function returns True if the value was changed, False otherwise"""
    if value == 'default':
      value = self.settings[setting]['default']
    if setting in self.settings:
      self.settingvalues[setting] = self.api.get('utils.verify')(value,
                                          self.settings[setting]['stype'])
      self.settingvalues.sync()
      return True

    return False

  def getstats(self):
    """
    get the stats for the plugin
    """
    stats = {}
    stats['Base Sizes'] = {}
    stats['Base Sizes']['showorder'] = ['Class', 'Variables', 'Api']
    stats['Base Sizes']['Variables'] = '%s bytes' % \
                                      sys.getsizeof(self.settingvalues)
    stats['Base Sizes']['Class'] = '%s bytes' % sys.getsizeof(self)
    stats['Base Sizes']['Api'] = '%s bytes' % sys.getsizeof(self.api)

    return stats

  def cmd_stats(self, args=None):
    """
    @G%(name)s@w - @B%(cmdname)s@w
    show stats, memory, profile, etc.. for this plugin
    @CUsage@w: stats
    """
    stats = self.getstats()
    tmsg = []
    for header in stats:
      tmsg.append(self.api.get('utils.center')(header, '=', 60))
      for subtype in stats[header]['showorder']:
        tmsg.append('%-20s : %s' % (subtype, stats[header][subtype]))

    return True, tmsg

  def unload(self, _=None):
    """
    unload stuff
    """
    self.api.get('send.msg')('unloading %s' % self.name)

    # remove anything out of the api
    self.api.get('api.remove')(self.sname)

    #clear all commands for this plugin
    self.api.get('commands.removeplugin')(self.sname)

    #remove all events
    self.api.get('events.removeplugin')(self.sname)

    # delete all timers
    self.api.get('timers.removeplugin')(self.sname)

    # delete all triggers
    self.api.get('triggers.removeplugin')(self.sname)

    # delete all watches
    self.api.get('watch.removeplugin')(self.sname)

    #save the state
    self.savestate()

  # handle a message
  def api_outputmsg(self, msg, secondary='None'):
    """
    an internal function to send msgs
    """
    self.api.get('send.msg', True)(msg, self.sname, secondary)

  def api_triggersadd(self, triggername, regex, **kwargs):
    """
    add triggers
    """
    self.api.get('triggers.add', True)(triggername, regex,
                                       self.sname, **kwargs)

  def api_watchadd(self, triggername, regex, **kwargs):
    """
    add triggers
    """
    self.api.get('watch.add', True)(triggername, regex, self.sname, **kwargs)

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
    msg = []
    if args['name'] == 'list':
      return True, self.listvars()
    elif args['name'] and args['value']:
      var = args['name']
      val = args['value']
      if var in self.settings:
        if 'readonly' in self.settings[var] \
              and self.settings[var]['readonly']:
          return True, ['%s is a readonly setting' % var]
        else:
          try:
            self.api.get('setting.change')(var, val)
            tvar = self.settingvalues[var]
            if self.settings[var]['nocolor']:
              tvar = tvar.replace('@', '@@')
            elif self.settings[var]['stype'] == 'color':
              tvar = '%s%s@w' % (val, val.replace('@', '@@'))
            elif self.settings[var]['stype'] == 'timelength':
              tvar = self.api.get('utils.formattime')(
                          self.api.get('utils.verify')(val, 'timelength'))
            return True, ['%s is now set to %s' % (var, tvar)]
          except ValueError:
            msg = ['Cannot convert %s to %s' % \
                                    (val, self.settings[var]['stype'])]
            return True, msg
        return True, self.listvars()
      else:
        msg = ['plugin setting %s does not exist' % var]
    return False, msg

  def cmd_save(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
    save plugin state
    @CUsage@w: save
    """
    self.savestate()
    return True, ['Plugin settings saved']

  def cmd_help(self, args):
    """
    test command
    """
    msg = []

    msg.extend(__doc__.split('\n'))
    if args['commands']:
      cmdlist = self.api.get('commands.list')(self.sname)
      if cmdlist:
        msg.extend(self.api.get('commands.list')(self.sname))
        msg.append('@G' + '-' * 60 + '@w')
        msg.append('')
    if args['api']:
      apilist = self.api.get('api.list')(self.sname)
      if apilist:
        msg.append('API functions in %s' % self.sname)
        msg.append('@G' + '-' * 60 + '@w')
        msg.extend(self.api.get('api.list')(self.sname))
    return True, msg

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
        elif self.settings[i]['stype'] == 'timelength':
          val = self.api.get('utils.formattime')(
                          self.api.get('utils.verify')(val, 'timelength'))
        tmsg.append(tform % (i, val, self.settings[i]['help']))
    return tmsg

  # add a setting to the plugin
  def api_settingadd(self, name, default, stype, shelp, **kwargs):
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
    self.api.get('send.msg')('baseplugin, firstactive')
    self.api.get('events.unregister')('firstactive', self.afterfirstactive)

  # set the default command
  def api_commandsdefault(self, cmd):
    """
    set a command as default
    """
    # we call the non overloaded versions
    self.api.get('commands.default', True)(self.sname, cmd)

  # add a function to the api
  def api_add(self, name, func):
    """
    add a command to the api
    """
    # we call the non overloaded versions
    self.api.add(self.sname, name, func)
