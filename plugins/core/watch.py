"""
This plugin will handle watching for commands coming from the client
"""
import re
import argparse
from plugins._baseplugin import BasePlugin

#these 5 are required
NAME = 'Command Watch'
SNAME = 'watch'
PURPOSE = 'watch for specific commands from clients'
AUTHOR = 'Bast'
VERSION = 1
PRIORITY = 25

# This keeps the plugin from being autoloaded if set to False
AUTOLOAD = True

class Plugin(BasePlugin):
  """
  a plugin to watch for commands coming from the client
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)

    self.canreload = False

    self.regexlookup = {}
    self.watchcmds = {}

    self.api.get('api.add')('add', self.api_addwatch)
    self.api.get('api.add')('remove', self.api_removewatch)
    self.api.get('api.add')('removeplugin', self.api_removeplugin)

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

    #self.api.get('commands.add')('detail', self.cmd_detail,
                                 #shelp='details of an event')

    self.api.get('events.register')('from_client_event', self.checkcmd)

    parser = argparse.ArgumentParser(add_help=False,
                 description='list watches')
    parser.add_argument('match',
                    help='list only aliases that have this argument in them',
                    default='', nargs='?')
    self.api.get('commands.add')('list', self.cmd_list,
                                 parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='get details of a watch')
    parser.add_argument('watch', help='the trigger to detail',
                        default=[], nargs='*')
    self.api.get('commands.add')('detail', self.cmd_detail,
                                 parser=parser)

  def cmd_list(self, args):
    """
    list watches
    """
    tmsg = []
    tkeys = self.watchcmds.keys()
    tkeys.sort()
    match = args['match']

    tmsg.append('%-25s : %-13s %s' % ('Name', 'Defined in',
                                            'Hits'))
    tmsg.append('@B' + '-' * 60 + '@w')
    for i in tkeys:
      watch = self.watchcmds[i]
      if not match or match in i or watch['plugin'] == match:
        tmsg.append('%-25s : %-13s %s' % (i, watch['plugin'],
                                        watch['hits']))

    return True, tmsg

  def cmd_detail(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      list the details of a watch
      @CUsage@w: detail watchname
    """
    tmsg = []
    if len(args['watch']) > 0:
      for watch in args['watch']:
        if watch in self.watchcmds:
          eventname = self.watchcmds[watch]['eventname']
          eventstuff = self.api.get('events.detail')(eventname)
          tmsg.append('%-13s : %s' % ('Name', watch))
          tmsg.append('%-13s : %s' % ('Defined in',
                                            self.watchcmds[watch]['plugin']))
          tmsg.append('%-13s : %s' % ('Regex',
                                            self.watchcmds[watch]['regex']))
          tmsg.append('%-13s : %s' % ('Hits', self.watchcmds[watch]['hits']))
          tmsg.extend(eventstuff)
        else:
          tmsg.append('trigger %s does not exist' % trigger)
    else:
      tmsg.append('Please provide a watch name')

    return True, tmsg

  # add a command watch
  def api_addwatch(self, watchname, regex, plugin, **kwargs):
    """  add a command watch
    @Ywatchname@w   = name
    @Yregex@w    = the regular expression that matches this trigger
    @Yplugin@w   = the plugin this comes from, added
          automatically if using the api through BaseClass
    @Ykeyword args@w arguments:
      None as of now

    this function returns no values"""
    if regex in self.regexlookup:
      self.api.get('send.msg')(
          'watch %s tried to add a regex that already existed for %s' % \
                      (watchname, self.regexlookup[regex]), secondary=plugin)
      return
    args = kwargs.copy()
    args['regex'] = regex
    args['plugin'] = plugin
    args['eventname'] = 'watch_' + watchname
    try:
      self.watchcmds[watchname] = args
      self.watchcmds[watchname]['hits'] = 0
      self.watchcmds[watchname]['compiled'] = re.compile(args['regex'])
      self.regexlookup[args['regex']] = watchname
      self.api.get('send.msg')(
          'added watch %s for plugin %s' % \
                      (watchname, plugin), secondary=plugin)
    except:
      self.api.get('send.traceback')(
          'Could not compile regex for cmd watch: %s : %s' % \
                (watchname, regex))

  # remove a command watch
  def api_removewatch(self, watchname, force=False):
    """  remove a command watch
    @Ywatchname@w   = The trigger name

    this function returns no values"""
    if watchname in self.watchcmds:
      event = self.api.get('events.gete')(
                            self.watchcmds[watchname]['eventname'])
      plugin = self.watchcmds[watchname]['plugin']
      if event:
        if len(event['pluginlist']) > 0 and not force:
          self.api.get('send.msg')(
            'removewatch: watch %s for plugin %s has functions registered' % \
                      (watchname, plugin), secondary=plugin)
          return False
      del self.regexlookup[self.watchcmds[watchname]['regex']]
      del self.watchcmds[watchname]
      self.api.get('send.msg')('removed watch %s' % watchname,
                                    secondary=plugin)
    else:
      self.api.get('send.msg')('removewatch: watch %s does not exist' % \
                                            watchname)

  # remove all watches related to a plugin
  def api_removeplugin(self, plugin):
    """  remove all watches related to a plugin
    @Ywatchname@w   = The trigger name

    this function returns no values"""
    self.api.get('send.msg')('removing watches for plugin %s' % plugin,
                               secondary=plugin)
    tkeys = self.watchcmds.keys()
    for i in tkeys:
      if self.watchcmds[i]['plugin'] == plugin:
        self.api.get('watch.remove')(i)

  def checkcmd(self, data):
    """
    check input from the client and see if we are watching for it
    """
    tdat = data['fromdata'].strip()
    for i in self.watchcmds.keys():
      cmdre = self.watchcmds[i]['compiled']
      mat = cmdre.match(tdat)
      if mat:
        self.watchcmds[i]['hits'] = self.watchcmds[i]['hits'] + 1
        targs = mat.groupdict()
        targs['cmdname'] = 'cmd_' + i
        targs['data'] = tdat
        self.api.get('send.msg')('raising %s' % targs['cmdname'])
        tdata = self.api.get('events.eraise')('watch_' + i, targs)
        if 'changed' in tdata:
          data['nfromdata'] = tdata['changed']

    if 'nfromdata' in data:
      data['fromdata'] = data['nfromdata']
    return data

