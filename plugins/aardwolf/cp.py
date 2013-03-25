"""
$Id$
"""
import time, os, copy, re
from libs import exported, utils
from libs.persistentdict import PersistentDict
from plugins import BasePlugin



NAME = 'Aardwolf CP Events'
SNAME = 'cp'
PURPOSE = 'Events for Aardwolf CPs'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False


class Plugin(BasePlugin):
  """
  a plugin to handle aardwolf cp events
  """
  def __init__(self, name, sname, filename, directory, importloc):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, name, sname, filename, directory, importloc)
    self.savecpfile = os.path.join(self.savedir, 'cp.txt')
    self.cp = PersistentDict(self.savecpfile, 'c', format='json')    
    self.dependencies.append('aardu')    
    self.mobsleft = []
    self.cptimer = {}
    exported.watch.add('cp_check', {
      'regex':'^(cp|campa|campai|campaig|campaign) (c|ch|che|chec|check)$'})
    self.triggers['cpnew'] = {
      'regex':"^Commander Barcett tells you " \
                        "'Type 'campaign info' to see what you must kill.'$"}
    self.triggers['cpnone'] = {
      'regex':"^You are not currently on a campaign.$", 
      'enabled':False, 
      'group':'cpcheck'}
    self.triggers['cptime'] = {
      'regex':"^You have (?P<time>.*) to finish this campaign.$", 
      'enabled':False, 
      'group':'cpcheck'}
    self.triggers['cpmob'] = {
      'regex':"^You still have to kill \* (?P<mob>.*) " \
            "\((?P<location>.*?)(?P<dead> - Dead|)\)$", 
      'enabled':False, 
      'group':'cpcheck'}    
    self.triggers['cpneedtolevel'] = {
      'regex':"^You will have to level before you" \
                " can go on another campaign.$", 
      'enabled':False, 
      'group':'cpin'}
    self.triggers['cpcantake'] = {
      'regex':"^You may take a campaign at this level.$", 
      'enabled':False, 
      'group':'cpin'}
    self.triggers['cpshnext'] = {
      'regex':"^You cannot take another campaign for (?P<time>.*).$", 
      'enabled':False, 
      'group':'cpin'}
    self.triggers['cpmobdead'] = {
      'regex':"^Congratulations, that was one of your CAMPAIGN mobs!$", 
      'enabled':False, 
      'group':'cpin'}
    self.triggers['cpcomplete'] = {
      'regex':"^CONGRATULATIONS! You have completed your campaign.$", 
      'enabled':False, 
      'group':'cpin'}
    self.triggers['cpclear'] = {
      'regex':"^Campaign cleared.$", 
      'enabled':False, 
      'group':'cpin'}    
    self.triggers['cpreward'] = {
      'regex':"^\s*Reward of (?P<amount>\d+) (?P<type>.+) .+ added.$", 
      'enabled':False, 
      'group':'cprew',
      'argtypes':{'amount':int}} 
    self.triggers['cpcompdone'] = {
      'regex':"^--------------------------" \
                    "------------------------------------$", 
      'enabled':False, 
      'group':'cpdone'}
      
    self.events['trigger_cpnew'] = {'func':self._cpnew}
    self.events['trigger_cpnone'] = {'func':self._cpnone}
    self.events['trigger_cptime'] = {'func':self._cptime}
    self.events['cmd_cp_check'] = {'func':self._cpcheckcmd}    
    self.events['trigger_cpmob'] = {'func':self._cpmob}
    self.events['trigger_cpneedtolevel'] = {'func':self._cpneedtolevel}
    self.events['trigger_cpcantake'] = {'func':self._cpcantake}
    self.events['trigger_cpshnext'] = {'func':self._cpshnext}
    self.events['trigger_cpmobdead'] = {'func':self._cpmobdead}
    self.events['trigger_cpcomplete'] = {'func':self._cpcomplete}
    self.events['trigger_cpclear'] = {'func':self._cpclear}
    self.events['trigger_cpreward'] = {'func':self._cpreward}
    self.events['trigger_cpcompdone'] = {'func':self._cpcompdone}
    
  def _cpreset(self):
    """
    reset the cp
    """
    self.cp.clear()
    self.cp['mobs'] = {}
    self.cp['trains'] = 0
    self.cp['pracs'] = 0
    self.cp['gold'] = 0
    self.cp['tp'] = 0
    self.cp['qp'] = 0
    self.cp['bonusqp'] = 0
    self.cp['failed'] = 0
    self.cp['level'] = exported.aardu.getactuallevel(
                        exported.GMCP.getv('char.status.level'))
    self.cp['starttime'] = time.time()
    self.cp['finishtime'] = 0
    self.cp['oncp'] = True
    self.cp['cantake'] = False
    self.cp['shtime'] = None
    self.savestate()
    
  def _cpnew(self, args=None):
    """
    handle a new cp
    """
    exported.sendtoclient('cpnew: %s' % args)
    self._cpreset()
  
  def _cpnone(self, _=None):
    """
    handle a none cp
    """
    self.cp['oncp'] = False
    self.savestate()
    exported.trigger.togglegroup('cpcheck', False) 
    exported.trigger.togglegroup('cpin', False) 
    exported.trigger.togglegroup('cprew', False) 
    exported.trigger.togglegroup('cpdone', False)     
    #check(EnableTimer("cp_timer", false))
    self.cptimer = {}    
    exported.sendtoclient('cpnone')

  def _cptime(self, args=None):
    """
    handle cp time
    """
    if not self.cp['mobs']:
      self.cp['mobs'] = self.mobsleft[:]
      self.savestate()
    exported.trigger.togglegroup("cpcheck", False)        
    exported.trigger.togglegroup("cpin", True)      
    
  def _cpneedtolevel(self, _=None):
    """
    handle cpneedtolevel
    """
    self.cp['cantake'] = False
    self.savestate()
    
  def _cpcantake(self, _=None):
    """
    handle cpcantake
    """
    self.cp['cantake'] = True    
    self.savestate()
    
  def _cpshnext(self, args=None):
    """
    handle cpshnext
    """
    self.cp['shtime'] = args['time']    
    self.savestate()
    
  def _cpmob(self, args=None):
    """
    handle cpmob
    """
    name = args['mob']
    mobdead = utils.verify(args['dead'], bool)
    location = args['location']
    if mobdead:
      pass
      #if GetTimerInfo("mob_timer", 6) == false then
        #check(EnableTimer("mob_timer", true))
      #end
    if not name or not location:
      exported.sendtoclient("error parsing line: %s" % args['line'])
    else:
      #self.mobsleft.append({'name':name, 'location':location, 
      #'clean':cleanname(name), 'mobdead':mobdead})
      self.mobsleft.append({'name':name, 
            'location':location, 'mobdead':mobdead})

  def _cpmobdead(self, _=None):
    """
    handle cpmobdead
    """
    exported.execute("cp check")    
    
  def _cpcomplete(self, _=None):
    """
    handle cpcomplete
    """
    exported.trigger.togglegroup('cprew', True)     
    self.cp['finishtime'] = time.time()
    self.cp['oncp'] = False
    self.savestate()

  def _cpreward(self, args=None):
    """
    handle cpreward
    """
    rtype = args['type']
    ramount = args['amount']
    rewardt = exported.aardu.rewardtable()
    self.cp[rewardt[rtype]] = ramount
    self.savestate()
    exported.trigger.togglegroup('cpdone', True) 
    
  def _cpcompdone(self, _=None):
    """
    handle cpcompdone
    """
    exported.event.register('trigger_all', self._triggerall)    
  
  def _triggerall(self, args=None):
    """
    check to see if we have the bonus qp message
    """
    exported.event.unregister('trigger_all', self._triggerall)
    if 'first campaign completed today' in args['data']:
      mat = re.match('^You receive (?P<bonus>\d*) quest points bonus " \
                  "for your first campaign completed today.$', args['data'])
      self.cp['bonusqp'] = int(mat.groupdict()['bonus'])
    exported.event.eraise('aard_cp_comp', copy.deepcopy(self.cp))
  
  def _cpclear(self, _=None):
    """
    handle cpclear
    """
    self.cp['failed'] = 1
    exported.event.eraise('aard_cp_failed', copy.deepcopy(self.cp))
    self._cpnone()    
    
  def _cpcheckcmd(self, args=None):
    """
    handle when we get a cp check
    """
    self.mobsleft = []
    self.cptimer = {}
    exported.trigger.togglegroup('cpcheck', True)    
    return args
  
  def savestate(self):
    """
    save states
    """
    BasePlugin.savestate(self)
    self.cp.sync()
    