"""
$Id$
"""
import os
import copy
from libs import exported
from libs.persistentdict import PersistentDict
from plugins import BasePlugin


NAME = 'Aardwolf Whois'
SNAME = 'whois'
PURPOSE = 'Gather whois data'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(BasePlugin):
  """
  a plugin to handle aardwolf cp events
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)
    self.savewhoisfile = os.path.join(self.savedir, 'whois.txt')
    self.whois = PersistentDict(self.savewhoisfile, 'c', format='json')    
    self.dependencies.append('aardu')     
    exported.watch.add('whois', {
                'regex':'^(whoi|whois)$'})
       
    self.triggers['whoisheader'] = {
      'regex':"^\[.*\]\s+.*\s*\((?P<sex>\w+)\s+\w+\)$", 
      'enabled':False, 
      'group':'whois'}
    self.triggers['whoisclasses'] = {
      'regex':"^\[Multiclass Player: (?P<classes>.*) \]$", 
      'enabled':False, 
      'group':'whois'}
    self.triggers['whois1'] = {
      'regex':"^(?P<name1>[\w\s]*)\s*:\s*\[\s*(?P<val1>[\w\d\s]*)\s*\]\s*$", 
      'enabled':False, 
      'group':'whois'}      
    self.triggers['whois2'] = {
      'regex':"^(?P<name1>[\w\s]*)\s*:\s*\[\s*(?P<val1>[\w\d\s]*)\s*\]" \
            "\s*(?P<name2>[\w\s]*)\s*:\s*\[\s*(?P<val2>[\w\d\s]*)\s*\]\s*$", 
      'enabled':False, 
      'group':'whois'}
    self.triggers['whois3'] = {
      'regex':"^(?P<name1>[\w\s]*)\s*:\s*\[\s*(?P<val1>[\w\d\s]*)\s*\]" \
            "\s*(?P<name2>[\w\s]*)\s*:\s*\[\s*(?P<val2>[\w\d\s]*)\s*\]" \
            "\s*(?P<name3>[\w\s]*)\s*:\s*\[\s*(?P<val3>[\w\d\s]*)\s*\]\s*$", 
      'enabled':False, 
      'group':'whois'}  
    self.triggers['whoispowerup'] = {
      'regex':"^(?P<name1>[\w\s]*)\s*:\s*\[\s*(?P<val1>[\w\d\s]*)\s*\]" \
            "\s*([\w\s]*)\s*:\s*\[\s*(?P<pval1>[\w\d\s]*)\s*\]\s*\[\s*" \
            "(?P<pval2>[\w\d\s]*)\s*\]\s*$", 
      'enabled':False, 
      'group':'whois'}        
    self.triggers['whoisend'] = {
      'regex':"^-{74,74}$", 
      'enabled':False}
      
    self.events['cmd_whois'] = {'func':self._whois}
    self.events['trigger_whoisheader'] = {'func':self._whoisheader}
    self.events['trigger_whoisclasses'] = {'func':self._whoisclasses}
    self.events['trigger_whois1'] = {'func':self._whoisstats}
    self.events['trigger_whois2'] = {'func':self._whoisstats}
    self.events['trigger_whois3'] = {'func':self._whoisstats}
    self.events['trigger_whoispowerup'] = {'func':self._whoisstats}
    self.events['trigger_whoisend'] = {'func':self._whoisend}
    
  def _whois(self, args=None):
    """
    reset the whois info when a "whois" command is sent
    """
    self.whois.clear()
    exported.trigger.togglegroup('whois', True)    
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
    self.whois["name"] = exported.GMCP.getv('char.base.name')
    self.whois['level'] = exported.GMCP.getv('char.status.level')
    self.whois['tiers'] = exported.GMCP.getv('char.base.tier')
    self.whois['redos'] = int(exported.GMCP.getv('char.base.redos'))
    self.whois['race'] = exported.GMCP.getv('char.base.race').lower()
    self.whois['sex'] = args['sex'].lower()
    self.whois['subclass'] = exported.GMCP.getv('char.base.subclass').lower()
    self.whois['powerupsall'] = 0
    self.whois['powerupsmort'] = 0
    self.whois['remorts'] = exported.GMCP.getv('char.base.remorts')
    if self.whois['remorts'] == 1:
      classabs = exported.aardu.classabb()
      self.whois['classes'] = []
      self.whois['classes'].append({'remort':1, 
              'class':classabs[exported.GMCP.getv(
                                      'char.base.class').lower()]})
                                      
    exported.trigger.toggle('whoisend', True)
  
  def _whoisclasses(self, args):
    """
    add classes
    """
    classabs = exported.aardu.classabb()
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
    self.whois['totallevels'] = exported.aardu.getactuallevel(
                      self.whois['level'], self.whois['remorts'], 
                      self.whois['tiers'], self.whois['redos'])    
    self.whois.sync()
    exported.trigger.togglegroup('whois', False)
    exported.trigger.toggle('whoisend', False)
    exported.event.eraise('aard_whois', copy.deepcopy(self.whois))    
    self.msg('whois: %s' % self.whois)
    
  def savestate(self):
    """
    save states
    """
    BasePlugin.savestate(self)
    self.whois.sync()
    
    