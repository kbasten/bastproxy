"""
This plugin parses whois data from Aardwolf
"""
import os
import copy
from libs.persistentdict import PersistentDict
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin


NAME = 'Aardwolf Whois'
SNAME = 'whois'
PURPOSE = 'Gather whois data'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(AardwolfBasePlugin):
  """
  a plugin to handle aardwolf cp events
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    AardwolfBasePlugin.__init__(self, *args, **kwargs)
    self.savewhoisfile = os.path.join(self.savedir, 'whois.txt')
    self.whois = PersistentDict(self.savewhoisfile, 'c')

  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)

    self.api.get('watch.add')('whois', '^(whoi|whois)$')

    self.api.get('triggers.add')('whoisheader',
      "^\[.*\]\s+.*\s*\((?P<sex>\w+)\s+\w+\)$",
      enabled=False,
      group='whois')
    self.api.get('triggers.add')('whoisclasses',
      "^\[Multiclass Player: (?P<classes>.*) \]$",
      enabled=False,
      group='whois')
    self.api.get('triggers.add')('whois1',
      "^(?P<name1>[\w\s]*)\s*:\s*\[\s*(?P<val1>[\w\d\s]*)\s*\]\s*$",
      enabled=False,
      group='whois')
    self.api.get('triggers.add')('whois2',
      "^(?P<name1>[\w\s]*)\s*:\s*\[\s*(?P<val1>[\w\d\s]*)\s*\]" \
        "\s*(?P<name2>[\w\s]*)\s*:\s*\[\s*(?P<val2>[\w\d\s]*)\s*\]\s*$",
      enabled=False,
      group='whois')
    self.api.get('triggers.add')('whois3',
      "^(?P<name1>[\w\s]*)\s*:\s*\[\s*(?P<val1>[\w\d\s]*)\s*\]" \
        "\s*(?P<name2>[\w\s]*)\s*:\s*\[\s*(?P<val2>[\w\d\s]*)\s*\]" \
        "\s*(?P<name3>[\w\s]*)\s*:\s*\[\s*(?P<val3>[\w\d\s]*)\s*\]\s*$",
      enabled=False,
      group='whois')
    self.api.get('triggers.add')('whoispowerup',
      "^(?P<name1>[\w\s]*)\s*:\s*\[\s*(?P<val1>[\w\d\s]*)\s*\]" \
        "\s*([\w\s]*)\s*:\s*\[\s*(?P<pval1>[\w\d\s]*)\s*\]\s*\[\s*" \
        "(?P<pval2>[\w\d\s]*)\s*\]\s*$",
      enabled=False,
      group='whois')
    self.api.get('triggers.add')('whoisend',
      "^-{74,74}$",
      enabled=False)

    self.api.get('events.register')('watch_whois', self._whois)
    self.api.get('events.register')('trigger_whoisheader', self._whoisheader)
    self.api.get('events.register')('trigger_whoisclasses', self._whoisclasses)
    self.api.get('events.register')('trigger_whois1', self._whoisstats)
    self.api.get('events.register')('trigger_whois2', self._whoisstats)
    self.api.get('events.register')('trigger_whois3', self._whoisstats)
    self.api.get('events.register')('trigger_whoispowerup', self._whoisstats)
    self.api.get('events.register')('trigger_whoisend', self._whoisend)

  def _whois(self, args=None):
    """
    reset the whois info when a "whois" command is sent
    """
    self.whois.clear()
    self.api.get('triggers.togglegroup')('whois', True)
    return args

  def _whoisstats(self, args=None):
    """
    parse a whois line
    """
    for i in range(1, 4):
      akey = 'name%s' % i
      aval = 'val%s' % i

      if akey in args:
        kname = args[akey].lower().strip()
        kname = kname.replace(' ', '')
        kval = args[aval].strip()

        self.whois[kname] = kval

    if 'pval1' in args:
      self.whois['powerupsall'] = args['pval1']
    if 'pval2' in args:
      self.whois['powerupsmort'] = args['pval2']

  def _whoisheader(self, args=None):
    """
    do stuff when we see the whois header
    """
    self.whois["name"] = self.api.get('GMCP.getv')('char.base.name')
    self.whois['level'] = self.api.get('GMCP.getv')('char.status.level')
    self.whois['tiers'] = self.api.get('GMCP.getv')('char.base.tier')
    self.whois['redos'] = int(self.api.get('GMCP.getv')('char.base.redos'))
    self.whois['race'] = self.api.get('GMCP.getv')('char.base.race').lower()
    self.whois['sex'] = args['sex'].lower()
    self.whois['subclass'] = self.api.get('GMCP.getv')(
                                            'char.base.subclass').lower()
    self.whois['powerupsall'] = 0
    self.whois['powerupsmort'] = 0
    self.whois['remorts'] = self.api.get('GMCP.getv')('char.base.remorts')
    if self.whois['remorts'] == 1:
      classabs = self.api.get('aardu.classabb')()
      self.whois['classes'] = []
      self.whois['classes'].append({'remort':1,
              'class':classabs[self.api.get('GMCP.getv')(
                                      'char.base.class').lower()]})

    self.api.get('triggers.toggle')('whoisend', True)

  def _whoisclasses(self, args):
    """
    add classes
    """
    classabs = self.api.get('aardu.classabb')()
    tlist = args['classes'].split("/")
    remorts = len(tlist)
    self.whois['classes'] = []
    for i in range(remorts):
      tclass = tlist[i].strip().lower()
      self.whois['classes'].append({'remort':i + 1,
                'class':classabs[tclass.lower()]})

    self.whois['remorts'] = remorts

  def _whoisend(self, _=None):
    """
    send a whois
    """
    self.whois['totallevels'] = self.api.get('aardu.getactuallevel')(
                      self.whois['level'], self.whois['remorts'],
                      self.whois['tiers'], self.whois['redos'])
    self.whois.sync()
    self.api.get('triggers.togglegroup')('whois', False)
    self.api.get('triggers.toggle')('whoisend', False)
    self.api.get('events.eraise')('aard_whois', copy.deepcopy(self.whois))
    self.api.get('send.msg')('whois: %s' % self.whois)

  def savestate(self):
    """
    save states
    """
    AardwolfBasePlugin.savestate(self)
    self.whois.sync()

