"""
$Id$

This plugin will show information about connections to the proxy
"""
import re
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
  a plugin to show connection information
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
      self.api.get('output.msg')(
          'watch %s tried to add a regex that already existed for %s' % \
                      (watchname, self.regexlookup[regex]), secondary=plugin)
      return
    args = kwargs.copy()
    args['regex'] = regex
    args['plugin'] = plugin
    args['eventname'] = 'watch_' + watchname
    try:
      self.watchcmds[watchname] = args
      self.watchcmds[watchname]['compiled'] = re.compile(args['regex'])
      self.regexlookup[args['regex']] = watchname
      self.api.get('output.msg')(
          'added watch %s for plugin %s' % \
                      (watchname, plugin), secondary=plugin)
    except:
      self.api.get('output.traceback')(
          'Could not compile regex for cmd watch: %s : %s' % \
                (watchname, regex))

  # remove a command watch
  def api_removewatch(self, watchname, force=False):
    """  remove a command watch
    @Ywatchname@w   = The trigger name

    this function returns no values"""
    if watchname in self.watchcmds:
      event = self.api.get('events.gete')(self.watchcmds[watchname]['eventname'])
      plugin = self.watchcmds[watchname]['plugin']
      if event:
        if len(event['pluginlist']) > 0 and not force:
          self.api.get('output.msg')('removewatch: watch %s for plugin has functions registered' % \
                      (watchname, plugin), secondary=plugin)
          return False
      del self.regexlookup[self.watchcmds[watchname]['regex']]
      del self.watchcmds[watchname]
      self.api.get('output.msg')('removed watch %s' % watchname,
                                    secondary=plugin)
    else:
      self.api.get('output.msg')('removewatch: watch %s does not exist' % watchname)

  # remove all watches related to a plugin
  def api_removeplugin(self, plugin):
    """  remove all watches related to a plugin
    @Ywatchname@w   = The trigger name

    this function returns no values"""
    self.api.get('output.msg')('removing watches for plugin %s' % plugin,
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
    for i in self.watchcmds:
      cmdre = self.watchcmds[i]['compiled']
      mat = cmdre.match(tdat)
      if mat:
        targs = mat.groupdict()
        targs['cmdname'] = 'cmd_' + i
        targs['data'] = tdat
        self.api.get('output.msg')('raising %s' % targs['cmdname'])
        tdata = self.api.get('events.eraise')('watch_' + i, targs)
        if 'changed' in tdata:
          data['nfromdata'] = tdata['changed']

    if 'nfromdata' in data:
      data['fromdata'] = data['nfromdata']
    return data

