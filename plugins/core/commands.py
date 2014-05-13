"""
This module handles commands and parsing input
"""
import shlex
import argparse

from plugins._baseplugin import BasePlugin

NAME = 'Commands'
SNAME = 'commands'
PURPOSE = 'Parse commands, e.g. #bp.commands.list'
AUTHOR = 'Bast'
VERSION = 1
PRIORITY = 10

# This keeps the plugin from being autoloaded if set to False
AUTOLOAD = True

class Plugin(BasePlugin):
  """
  a class to manage internal commands
  """
  def __init__(self, *args, **kwargs):
    """
    init the class
    """
    BasePlugin.__init__(self, *args, **kwargs)

    self.canreload = False

    self.cmds = {}
    self.nomultiplecmds = {}
    self.regexlookup = {}
    self.lastcmd = ''

    self.api.get('api.add')('add', self.api_addcmd)
    self.api.get('api.add')('remove', self.api_removecmd)
    self.api.get('api.add')('default', self.api_setdefault)
    self.api.get('api.add')('removeplugin', self.api_removeplugin)
    self.api.get('api.add')('list', self.api_listcmds)
    self.api.get('api.add')('run', self.api_run)
    self.api.get('api.add')('cmdhelp', self.api_cmdhelp)


  def load(self):
    """
    load external stuff
    """
    BasePlugin.load(self)
    self.api.get('managers.add')(self.sname, self)
    self.api.get('log.adddtype')(self.sname)
    self.api.get('log.console')(self.sname)

    self.api.get('setting.add')('spamcount', 20, int,
            'the # of times a command can be run before an antispam command')
    self.api.get('setting.add')('antispamcommand', 'look', str,
                      'the antispam command to send')
    self.api.get('setting.add')('cmdcount', 0, int,
            'the # of times the current command has been run', readonly=True)

    parser = argparse.ArgumentParser(add_help=False,
                 description='list commands in a category')
    parser.add_argument('category', help='the category to see help for',
                        default='', nargs='?')
    parser.add_argument('cmd',
                        help='the command in the category (can be left out)',
                        default='', nargs='?')
    self.api.get('commands.add')('list', self.cmd_list, shelp='list commands',
                                 parser=parser)

    self.api.get('commands.default')('list')
    self.api.get('events.register')('from_client_event', self.chkcmd, prio=2)
    self.api.get('events.eraise')('plugin_cmdman_loaded', {})

  def formatretmsg(self, msg, sname, cmd):
    """
    format a return message
    """
    msg.insert(0, '')
    msg.insert(1, '#bp.%s.%s' % (sname, cmd))
    msg.insert(2, '@G' + '-' * 60 + '@w')
    msg.append('@G' + '-' * 60 + '@w')
    msg.append('')
    return msg

  def api_cmdhelp(self, plugin, cmd):
    """
    get the help for a command
    """
    if plugin in self.cmds and cmd in self.cmds[plugin]:
      return self.cmds[plugin][cmd]['parser'].format_help()
    else:
      return ''

  # return a formatted list of commands for a plugin
  def api_listcmds(self, plugin, format=True):
    """
    list commands for a plugin
    """
    if format:
      return self.listcmds(plugin)
    else:
      if plugin in self.cmds:
        return self.cmds[plugin]
      else:
        return {}

  def api_run(self, plugin, cmdname, argstring):
    """
    run a command and return the output
    """
    tmsg = []
    if plugin in self.cmds and cmdname in self.cmds[plugin]:
      cmd = self.cmds[plugin][cmdname]
      args, other_args = cmd['parser'].parse_known_args(argstring)

      if args['help']:
        return cmd['parser'].format_help().split('\n')
      else:
        return cmd['func'](args)

  def runcmd(self, cmd, targs, fullargs):
    """
    run a command that has an ArgParser
    """
    retval = False

    args, other_args = cmd['parser'].parse_known_args(targs)

    args = vars(args)
    args['fullargs'] = fullargs
    if args['help']:
      msg = cmd['parser'].format_help().split('\n')
      self.api.get('send.client')('\n'.join(self.formatretmsg(
                                                  msg, cmd['sname'],
                                                  cmd['commandname'])))

    else:
      retvalue = cmd['func'](args)
      if isinstance(retvalue, tuple):
        retval = retvalue[0]
        msg = retvalue[1]
      else:
        retval = retvalue
        msg = []

      if retval == False:
        msg.append('')
        msg.extend(cmd['parser'].format_help().split('\n'))
        self.api.get('send.client')('\n'.join(self.formatretmsg(
                                                  msg, cmd['sname'],
                                                  cmd['commandname'])))
      else:
        if not cmd['format']:
          self.api.get('send.client')(msg, preamble=cmd['preamble'])
        else:
          self.api.get('send.client')('\n'.join(self.formatretmsg(
                                                  msg, cmd['sname'],
                                                  cmd['commandname'])),
                                        preamble=cmd['preamble'])

    return retval

  def chkcmd(self, data):
    """
    check a line from a client for a command
    """
    tdat = data['fromdata']
    if tdat[0:3] == '#bp':
      targs = shlex.split(tdat.strip())
      try:
        tmpind = tdat.index(' ')
        fullargs = tdat[tmpind+1:]
      except ValueError:
        fullargs = ''
      cmd = targs.pop(0)
      cmdsplit = cmd.split('.')
      sname = ''
      if len(cmdsplit) >= 2:
        sname = cmdsplit[1].strip()

      scmd = ''
      if len(cmdsplit) >= 3:
        scmd = cmdsplit[2].strip()

      if 'help' in targs:
        try:
          del targs[targs.index('help')]
        except ValueError:
          pass
        cmd = self.cmds[self.sname]['list']
        self.runcmd(cmd, [sname, scmd], fullargs)

      elif sname:
        if not (sname in self.cmds):
          self.api.get('send.client')("@R%s.%s@W is not a command." % \
                                                  (sname, scmd))
        else:
          if scmd:
            cmd = None
            if scmd in self.cmds[sname]:
              cmd = self.cmds[sname][scmd]
            if cmd:
              try:
                self.runcmd(cmd, targs, fullargs)
              except:
                self.api.get('send.traceback')('Error when calling command %s.%s' % (sname, scmd))
                return {'fromdata':''}
            else:
              self.api.get('send.client')("@R%s.%s@W is not a command" % \
                                                    (sname, scmd))
          else:
            if 'default' in self.cmds[sname]:
              cmd = self.cmds[sname]['default']
              try:
                self.runcmd(cmd, targs, fullargs)
              except:
                self.api.get('send.traceback')('Error when calling command %s.%s' % (sname, scmd))
                return {'fromdata':''}
            else:
              cmd = self.cmds[self.sname]['list']
              try:
                self.runcmd(cmd, [sname, scmd], '')
              except:
                self.api.get('send.traceback')('Error when calling command %s.%s' % (sname, scmd))
                return {'fromdata':''}
      else:
        try:
          del targs[targs.index('help')]
        except ValueError:
          pass
        cmd = self.cmds[self.sname]['list']
        try:
          self.runcmd(cmd, [sname, scmd], '')
        except:
          self.api.get('send.traceback')('Error when calling command %s.%s' % (sname, scmd))
          return {'fromdata':''}

      return {'fromdata':''}
    else:
      if tdat.strip() == self.lastcmd:
        self.api.get('setting.change')('cmdcount',
                            self.api.get('setting.gets')('cmdcount') + 1)
        if self.api.get('setting.gets')('cmdcount') == \
                              self.api.get('setting.gets')('spamcount'):
          data['fromdata'] = self.api.get('setting.gets')('antispamcommand') \
                                      + '|' + tdat
          self.api.get('send.msg')('adding look for 20 commands')
          self.api.get('setting.change')('cmdcount', 0)
        if tdat in self.nomultiplecmds:
          data['fromdata'] = ''
      else:
        self.api.get('setting.change')('cmdcount', 0)
        self.api.get('send.msg')('resetting command to %s' % tdat.strip())
        self.lastcmd = tdat.strip()

      return data

  # add a command
  def api_addcmd(self, cmdname, func, **kwargs):
    """  add a command
    @Ycmdname@w  = the base that the api should be under
    @Yfunc@w   = the function that should be run when this command is executed
    @Ykeyword arguments@w
      @Yshelp@w    = the short help, a brief description of what the
                                          command does
      @Ylhelp@w    = a longer description of what the command does
      @Ypreamble@w = show the preamble for this command (default: True)
      @Yformat@w   = format this command (default: True)
      @Ygroup@w    = the group this command is in

    The command will be added as sname.cmdname

    sname is gotten from the class the function belongs to or the sname key
      in args

    this function returns no values"""

    args = kwargs.copy()

    lname = None
    if not func:
      self.api.get('send.msg')('cmd %s has no function, not adding' % \
                                                (cmdname))
      return
    try:
      sname = func.im_self.sname
    except AttributeError:
      if 'sname' in args:
        sname = args['sname']
      else:
        self.api.get('send.msg')('Function is not part of a plugin class: %s' \
                                                      % cmdname)
        return

    if 'parser' in args:
      tparser = args['parser']
    else:
      self.api.get('send.msg')('adding default parser to command %s.%s' % \
                                      (sname, cmdname))
      if not ('shelp' in args):
        args['shelp'] = 'there is no help for this command'
      tparser = argparse.ArgumentParser(add_help=False,
                 description=args['shelp'])
      args['parser'] = tparser

    tparser.add_argument("-h", "--help", help="show help",
                  action="store_true")

    tparser.prog = '@B#bp.%s.%s@w' % (sname, cmdname)

    if not ('group' in args):
      args['group'] = 'Base'

    try:
      lname = func.im_self.name
      args['lname'] = lname
    except AttributeError:
      pass

    if not ('lname' in args):
      self.api.get('send.msg')('cmd %s.%s has no long name, not adding' % \
                                            (sname, cmdname),
                                            secondary=sname)
      return

    self.api.get('send.msg')('added cmd %s.%s' % \
                                            (sname, cmdname),
                                            secondary=sname)

    if not (sname in self.cmds):
      self.cmds[sname] = {}
    args['func'] = func
    args['sname'] = sname
    args['lname'] = lname
    args['commandname'] = cmdname
    if not ('preamble' in args):
      args['preamble'] = True
    if not ('format' in args):
      args['format'] = True
    self.cmds[sname][cmdname] = args

  # remove a command
  def api_removecmd(self, sname, cmdname):
    """  remove a command
    @Ysname@w    = the top level of the command
    @Ycmdname@w  = the name of the command

    this function returns no values"""
    if sname in self.cmds and cmdname in self.cmds[sname]:
      del self.cmds[sname][cmdname]
    else:
      self.api.get('send.msg')('remove cmd: cmd %s.%s does not exist' % \
                                                (sname, cmdname),
                                            secondary=sname)

    self.api.get('send.msg')('removed cmd %s.%s' % \
                                                (sname, cmdname),
                                            secondary=sname)

  # set the default command for a plugin
  def api_setdefault(self, sname, cmd):
    """  set the default command for a plugin
    @Ysname@w    = the plugin of the command
    @Ycmdname@w  = the name of the command

    this function returns True if the command exists, False if it doesn't"""
    if sname in self.cmds and cmd in self.cmds[sname]:
      self.cmds[sname]['default'] = self.cmds[sname][cmd]
      return True

    return False

  # remove all commands for a plugin
  def api_removeplugin(self, plugin):
    """  remove all commands for a plugin
    @Ysname@w    = the plugin to remove commands for

    this function returns no values"""
    if plugin in self.cmds:
      del self.cmds[plugin]
    else:
      self.api.get('send.msg')('removeplugin: plugin %s does not exist' % \
                                                        plugin)

  def format_cmdlist(self, category, cmdlist):
    """
    format a list of commands
    """
    tmsg = []
    for i in cmdlist:
      if i != 'default':
        tlist = self.cmds[category][i]['parser'].description.split('\n')
        if not tlist[0]:
          tlist.pop(0)
        tmsg.append('  @B%-10s@w : %s' % (i, tlist[0]))

    return tmsg

  def listcmds(self, category, cmd=None):
    """
    build a table of commands for a category
    """
    tmsg = []
    if category:
      if category in self.cmds:
        tmsg.append('Commands in %s:' % category)
        tmsg.append('@G' + '-' * 60 + '@w')
        groups = {}
        for i in sorted(self.cmds[category].keys()):
          if i != 'default':
            if not (self.cmds[category][i]['group'] in groups):
              groups[self.cmds[category][i]['group']] = []

            groups[self.cmds[category][i]['group']].append(i)

        if len(groups) == 1:
          tmsg.extend(self.format_cmdlist(category, self.cmds[category].keys()))
        else:
          for group in sorted(groups.keys()):
            if group != 'Base':
              tmsg.append('@M' + '-' * 5 + ' ' +  group + ' ' + '-' * 5)
              tmsg.extend(self.format_cmdlist(category, groups[group]))
              tmsg.append('')

          tmsg.append('@M' + '-' * 5 + ' ' +  'Base' + ' ' + '-' * 5)
          tmsg.extend(self.format_cmdlist(category, groups['Base']))
        #tmsg.append('@G' + '-' * 60 + '@w')
    return tmsg

  def cmd_list(self, args):
    """
    list commands
    """
    tmsg = []
    category = args['category']
    cmd = args['cmd']
    if category:
      if category in self.cmds:
        if cmd and cmd in self.cmds[category]:
          msg = self.cmds[category][cmd]['parser'].format_help().split('\n')
          tmsg.extend(msg)
        else:
          tmsg.extend(self.listcmds(category, cmd))
      else:
        tmsg.append('There is no category %s' % category)
    else:
      tmsg.append('Categories:')
      tkeys = self.cmds.keys()
      tkeys.sort()
      for i in tkeys:
        tmsg.append('  %s' % i)
    return True, tmsg

