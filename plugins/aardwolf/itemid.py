"""
$Id$

This plugin reads and parses id and invdetails from Aardwolf
"""
import copy
import time
import argparse
import shlex
import re
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin

NAME = 'Item Identification'
SNAME = 'itemid'
PURPOSE = 'Parse invdetails and id'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

DETAILS_RE = '^\{(?P<header>.*)\}(?P<data>.*)$'
DETAILS_REC = re.compile(DETAILS_RE)

class Plugin(AardwolfBasePlugin):
  """
  a plugin to handle equipment identification, id and invdetails
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    AardwolfBasePlugin.__init__(self, *args, **kwargs)

    self.waitingforid = {}
    self.showid = {}
    self.itemcache = {}
    self.pastkeywords = False
    self.dividercount = 0

    self.currentitem = {}

    self.api.get('dependency.add')('aardu')

  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)

    self.api.get('setting.add')('idcmd', True, str,
                      'identify')

    parser = argparse.ArgumentParser(add_help=False,
                 description='show inventory or a container')
    parser.add_argument('serial', help='the item to id', default='', nargs='?')
    self.api.get('commands.add')('id', self.cmd_id,
                                parser=parser, format=False, preamble=False)

    parser = argparse.ArgumentParser(add_help=False,
                 description='show some internal variables')
    self.api.get('commands.add')('sv', self.cmd_showinternal,
                                parser=parser)

    self.api.get('triggers.add')('invdetailsstart',
      "^\{invdetails\}$",
      enabled=True)

    self.api.get('triggers.add')('invdetailsend',
      "^\{/invdetails\}$",
      enabled=True, group='invdetails')

    self.api.get('triggers.add')('identifyon',
      "\+-*\+",
      enabled=False, group='identify', omit=True)

    self.api.get('triggers.add')('identify1',
      '^\|\s*(?P<data>.*)\s*\|$', group='identifydata',
      enabled=False, omit=True)

    self.api.get('events.register')('trigger_invdetailsstart', self.invdetailsstart)
    self.api.get('events.register')('trigger_invdetailsend', self.invdetailsend)
    self.api.get('events.register')('trigger_identifyon', self.identifyon)
    self.api.get('events.register')('trigger_identify1', self.identifyline)

  def cmd_showinternal(self, args):
    """
    show internal stuff
    """
    msg = []
    msg.append('waitingforid: %s' % self.waitingforid)
    msg.append('showid: %s' % self.showid)
    msg.append('currentitem: %s' % self.currentitem)

    return True, msg

  def sendcmd(self, cmd):
    self.api.get('send.msg')('sending cmd: %s' % cmd)
    self.api.get('send.execute')(cmd)

  def addmod(self, ltype, mod):
    if not (ltype in self.currentitem):
      self.currentitem[ltype] = {}

    self.currentitem[ltype][mod['name']] = int(mod['value'])

  def invdetailsstart(self, args):
    """
    show that the trigger fired
    """
    self.currentitem = {}
    self.api.get('send.msg')('found {invdetails}')
    self.api.get('triggers.togglegroup')('invdetails', True)
    self.api.get('events.register')('trigger_all', self.invdetailsline)

  def invdetailsline(self, args):
    """
    parse a line of invdetails
    """
    line = args['line'].strip()
    self.api.get('send.msg')('invdetails args: %s' % args)
    if line != '{invdetails}':
      mat = DETAILS_REC.match(line)
      if mat:
        matd = mat.groupdict()
        header = matd['header']
        data = matd['data']
        self.api.get('send.msg')('match: %s - %s' % (header,
                                                     data))
        titem = self.api.get('itemu.dataparse')(matd['data'],
                                                matd['header'])
        if header == 'invheader':
          self.currentitem = titem
        elif header in ['statmod', 'resistmod', 'skillmod']:
          self.addmod(header, titem)
        else:
          self.currentitem[header] = titem
        self.api.get('send.msg')('invdetails parsed item: %s' % titem)
      else:
        self.api.get('send.msg')('bad invdetails line: %s' % line)

  def invdetailsend(self, args):
    """
    reset current when seeing a spellheaders ending
    """
    titem = self.api.get('eq.getitem')(self.currentitem['serial'])
    if titem:
      self.currentitem.update(titem)
    self.itemcache[self.currentitem['serial']] = self.currentitem
    #self.waiting['Worn'] = False
    #add the current item to something
    self.api.get('send.msg')('found {/invdetails}')
    self.api.get('events.unregister')('trigger_all', self.invdetailsline)

  def identifyon(self, args):
    """
    """
    self.dividercount = self.dividercount + 1
    if self.dividercount == 1:
      self.api.get('send.msg')('found identify')
      self.api.get('triggers.togglegroup')('identifydata', True)
      #self.api.get('events.register')('trigger_all', self.identifyline)
      self.api.get('events.register')('trigger_emptyline', self.identifyend)
    elif self.dividercount == 2:
      self.pastkeywords = True

  def identifyline(self, args):
    """
    """
    print args
    data = args['data']
    if 'Keywords' in data:
      keywords = data.split(' : ')[1].strip()
      self.currentitem['keywords'] = keywords
    elif 'Found at' in data:
      foundat = data.split(' : ')[1].strip()
      self.currentitem['foundat'] = foundat
    elif self.pastkeywords:
      if args['line'][2] != ' ':
        if 'Mods' in data:
          pass
        else:
          if not ('notes' in self.currentitem):
            self.currentitem['notes'] = []
          self.currentitem['notes'].append(data.strip())

  def identifyend(self, args):
    """
    """
    self.api.get('events.unregister')('trigger_emptyline', self.identifyend)
    self.api.get('triggers.togglegroup')('identify', False)
    self.api.get('triggers.togglegroup')('identifydata', False)
    self.pastkeywords = False
    self.dividercount = 0
    if self.waitingforid[self.currentitem['serial']]:
      del self.waitingforid[self.currentitem['serial']]
      self.showitem(self.currentitem['serial'])

  def cmd_id(self, args):
    """
    do an id
    """
    msg = []
    if args['serial']:
      try:
        serial = int(args['serial'])
        titem = self.api.get('eq.getitem')(serial)
        if not titem:
          msg.append('Could not find %s' % serial)
        else:
          serial = titem['serial']
          if titem['serial'] in self.itemcache:
            self.showitem(serial)
          else:
            msg.append('We have item %s' % args['serial'])
            self.waitingforid[serial] = True
            if titem['container'] != 'Inventory':
              self.api.get('eq.get')(serial)
            self.sendcmd('invdetails %s' % serial)
            self.api.get('triggers.togglegroup')('invdetails', False)
            self.api.get('triggers.togglegroup')('identify', True)
            self.sendcmd('identify %s' % serial)
            if titem['container'] != 'Inventory':
              self.api.get('eq.put')(serial)
      except ValueError:
        msg.append('%s is not a serial number' % args['serial'])
    else:
      msg.append('Please supply a serial #')

    return True, msg

  def showitem(self, serial):
    """
    """
    serial = int(serial)
    nitem = self.api.get('eq.getitem')(serial)
    if nitem:
      self.itemcache[serial].update(nitem)
    self.api.get('send.client')('%s' % self.itemcache[serial])
