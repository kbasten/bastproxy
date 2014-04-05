"""
$Id$

This plugin reads and parses id and invdetails from Aardwolf
"""
import copy
import time
import argparse
import shlex
import re
import textwrap
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
    self.affectmods = False
    self.nonotes = False

    self.currentitem = {}

    self.api.get('dependency.add')('aardu')

    self.api.get('api.add')('identify', self.api_identify)
    self.api.get('api.add')('format', self.api_formatitem)
    self.api.get('api.add')('show', self.api_showitem)

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
                                parser=parser, format=False, preable=False)

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

    self.api.get('events.register')('trigger_invdetailsstart',
                                      self.invdetailsstart)
    self.api.get('events.register')('trigger_invdetailsend',
                                      self.invdetailsend)
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
      self.api.get('events.register')('trigger_emptyline', self.identifyend)
    elif self.dividercount == 2:
      self.pastkeywords = True
    if self.affectmods:
      self.affectmods = False
    self.nonotes = False

  def identifyline(self, args):
    """
    """
    print args
    data = args['data']
    if 'Keywords' in data:
      item = data.split(' : ')[1]
      item = item.replace('@W', '')
      item = item.replace('@w', '')
      self.currentitem['keywords'] = item.strip()
    elif 'Found at' in data:
      item = data.split(' : ')[1]
      item = item.replace('@W', '')
      item = item.replace('@w', '')
      self.currentitem['foundat'] = item.strip()
    elif 'Material' in data:
      item = data.split(' : ')[1]
      item = item.replace('@W', '')
      item = item.replace('@w', '')
      self.currentitem['material'] = item.strip()
    elif 'Leads to' in data:
      item = data.split(' : ')[1]
      item = item.replace('@W', '')
      item = item.replace('@w', '')
      self.currentitem['leadsto'] = item.strip()
    elif 'Affect Mods' in data:
      self.affectmods = True
      print 'Affect Mods', data
      item = data.split(':')[1]
      item = item.replace('@W', '')
      item = item.replace('@w', '')
      item = item.strip()
      tlist = item.split(',')
      self.currentitem['affectmod'] = []
      for i in tlist:
        if i:
          self.currentitem['affectmod'].append(i.strip())
    elif self.affectmods:
      item = data.split(':')[1]
      item = item.replace('@W', '')
      item = item.replace('@w', '')
      item = item.strip()
      tlist = item.split(',')
      for i in tlist:
        if i:
          self.currentitem['affectmod'].append(i.strip())
    elif 'Mods' in data or 'Portal' in data or 'Capacity' in data or \
         'Weapon Type' in data or 'Spells' in data or \
           'Food' in data or 'Drink' in data or 'Heal Rate' in data:
      self.nonotes = True
    elif self.pastkeywords and not self.nonotes:
      if args['line'][2] != ' ':
        if not ('notes' in self.currentitem):
          self.currentitem['notes'] = []
        tdat = args['colorline'][1:-1]
        self.currentitem['notes'].append(tdat.strip())

  def identifyend(self, args):
    """
    """
    self.api.get('events.unregister')('trigger_emptyline', self.identifyend)
    self.api.get('triggers.togglegroup')('identify', False)
    self.api.get('triggers.togglegroup')('identifydata', False)
    self.pastkeywords = False
    self.dividercount = 0
    if self.currentitem['serial'] in self.waitingforid:
      del self.waitingforid[self.currentitem['serial']]
    self.api.get('events.eraise')('itemid_%s' % self.currentitem['serial'],
                            self.currentitem)

  def api_identify(self, serial):
    """
    """
    titem = self.api.get('eq.getitem')(serial)
    if titem['serial'] in self.itemcache:
      return self.itemcache[titem['serial']]
    else:
      self.waitingforid[serial] = True
      if titem['curcontainer'] != 'Inventory':
        self.api.get('eq.get')(serial)
      self.sendcmd('invdetails %s' % serial)
      self.api.get('triggers.togglegroup')('invdetails', False)
      self.api.get('triggers.togglegroup')('identify', True)
      self.sendcmd('identify %s' % serial)
      if titem['curcontainer'] != 'Inventory':
        self.api.get('eq.put')(serial)

  def event_showitem(self, args):
    """
    """
    self.api.get('events.unregister')(args['eventname'], self.event_showitem)
    self.api.get('itemid.show')(args['serial'])

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
            self.api.get('itemid.showitem')(serial)
          else:
            msg.append('We have item %s' % args['serial'])
            self.api.get('events.register')('itemid_%s' % serial,
                                            self.event_showitem)
            self.api.get('itemid.identify')(serial)
      except ValueError:
        msg.append('%s is not a serial number' % args['serial'])
    else:
      msg.append('Please supply a serial #')

    return True, msg

  def formatsingleline(self, linename, linecolour, data, datacolor=None):
    if not datacolor:
      datacolor = '@W'

    data = str(data)

    printstring = '| %s%-11s@w: %s%s'
    ttext = printstring % (linecolour, linename, datacolor, data)
    newnum = 66 - len(self.api.get('colors.stripcolor')(ttext))
    tstring = "%" + str(newnum) + "s@w|"
    ttext = ttext + tstring % ""

    return ttext

  def formatdoubleline(self, linename, linecolour, data, linename2, data2):
    if not linecolour:
      linecolour = '@W'

    data = str(data)
    data2 = str(data2)

    adddata = 24 + self.api.get('colors.lengthdiff')(data)
    adddata2 = 17 + self.api.get('colors.lengthdiff')(data2)

    printstring = '| %s%-11s@w: @W%-' + str(adddata) + 's %s%-7s@w: @W%-' + \
            str(adddata2) + 's@w|'

    return printstring % (linecolour, linename, data,
                          linecolour, linename2, data2)

  def formatspecialline(self, linename, linecolour, data, linename2='', data2=''):
    if not linecolour:
      linecolour = '@W'

    data = str(data)
    data2 = str(data2)

    adddata = 20 + self.api.get('colors.lengthdiff')(data)

    printstring = '| %s%-11s@w: @W%-' + str(adddata) + 's'

    ttext = printstring % (linecolour, linename, data)

    if linename2:
      adddata2 = 14 + self.api.get('colors.lengthdiff')(data2)
      printstring2 = ' %s%-13s:  @W%-' + str(adddata2) + 's@w|'
      ttext = ttext + printstring2 % (linecolour, linename2, data2)
    else:
      newnum = 66 - len(self.api.get('colors.stripcolor')(ttext))
      tstring = "%" + str(newnum) + "s@w|"
      ttext = ttext + tstring % ""

    return ttext

  def formatstatsheader(self):
    return '|     @w%-4s %-4s  %-3s %-3s %-3s %-3s %-3s %-3s   %-3s   %-4s %-4s %-4s   |' % (
                            'DR', 'HR', 'Str', 'Int', 'Wis',
                            'Dex', 'Con', 'Luc', 'Sav', 'HP', 'MN', 'MV')

  def formatstats(self, stats):
    colors = {}
    for i in stats:
      if int(stats[i]) > 0:
        colors[i] = '@G'
      else:
        colors[i] = '@R'

    allstats = ['Damage roll', 'Hit roll', 'Strength', 'Intelligence', 'Wisdom',
             'Dexterity', 'Constitution', 'Luck', 'Saves', 'Hit points',
             'Mana', 'Moves']

    for i in allstats:
      if i in stats:
        if int(stats[i]) > 0:
          colors[i] = '@G'
        else:
          colors[i] = '@R'

      else:
        stats[i] = '-'
        colors[i] = '@w'

    return '|     %s%-4s@w %s%-4s@w  %s%-3s@w %s%-3s@w %s%-3s@w %s%-3s@w %s%-3s@w %s%-3s@w   %s%-3s@w   %s%-4s@w %s%-4s@w %s%-4s@w   |' % (
                colors['Damage roll'], stats['Damage roll'],
                colors['Hit roll'], stats['Hit roll'],
                colors['Strength'], stats['Strength'],
                colors['Intelligence'], stats['Intelligence'],
                colors['Wisdom'], stats['Wisdom'],
                colors['Dexterity'], stats['Dexterity'],
                colors['Constitution'], stats['Constitution'],
                colors['Luck'], stats['Luck'],
                colors['Saves'], stats['Saves'],
                colors['Hit points'], stats['Hit points'],
                colors['Mana'], stats['Mana'],
                colors['Moves'], stats['Moves'])

  def formatresist(self, resists, divider):
    colors = {}
    ttext = []
    foundfirst = False
    foundsecond = False

    firstline = ['Bash', 'Pierce', 'Slash', 'All Physical', 'All magic', 'Disease',
              'Poison']

    secondline = ['Acid', 'Air', 'Cold', 'Earth', 'Electric', 'Energy',
              'Fire', 'Holy', 'Light', 'Magic', 'Mental', 'Negative', 'Shadow',
              'Sonic', 'Water']

    allresists = firstline + secondline

    for i in allresists:
      if i in resists:
        if not foundfirst and i in firstline:
          foundfirst = True
        if not foundsecond and i in secondline:
          foundsecond = True

        if int(resists[i]) > 0:
          colors[i] = '@G'
        else:
          colors[i] = '@R'
      else:
          resists[i] = '-'
          colors[i] = '@w'

    if foundfirst:
      ttext.append('|%5s@w%-5s %-7s %-7s  %-8s  %-8s  %-5s %-5s %5s|' % (
                              '', 'Bash', 'Pierce', 'Slash', 'All Phys', 'All Mag', 'Diss', 'Poisn', ''))
      ttext.append('|%6s%s%-5s  %s%-7s %s%-7s   %s%-8s %s%-8s %s%-5s %s%-5s @w%4s|' % (
                              '',
                              colors['Bash'], resists['Bash'],
                              colors['Pierce'], resists['Pierce'],
                              colors['Slash'], resists['Slash'],
                              colors['All physical'], resists['All physical'],
                              colors['All magic'], resists['All magic'],
                              colors['Disease'], resists['Disease'],
                              colors['Poison'], resists['Poison'],
                              ''))

    if foundsecond:
      ttext.append(divider)
      ttext.append('|%5s%-5s  %-5s %-5s %-5s   %-5s   %-5s   %-5s   %-5s@w %3s|' % (
                            '', 'Acid', 'Air', 'Cold', 'Earth', 'Eltrc', 'Enrgy', 'Fire', 'Holy', ''))

      ttext.append('|%5s%s%-5s  %s%-5s %s%-5s %s%-5s   %s%-5s   %s%-5s   %s%-5s   %s%-5s@w %3s|' % (
                            '',
                            colors['Acid'], resists['Acid'],
                            colors['Air'], resists['Air'],
                            colors['Cold'], resists['Cold'],
                            colors['Earth'], resists['Earth'],
                            colors['Electric'], resists['Electric'],
                            colors['Energy'], resists['Energy'],
                            colors['Fire'], resists['Fire'],
                            colors['Holy'], resists['Holy'],
                            ''))

      ttext.append('|%4s %-5s  %-5s %-5s %-5s   %-5s   %-5s   %-5s @w %10s|' % (
                            '', 'Light', 'Magic', 'Mntl', 'Ngtv', 'Shdw', 'Sonic', 'Water', ''))

      ttext.append('|%4s %s%-5s  %s%-5s %s%-5s %s%-5s   %s%-5s   %s%-5s   %s%-5s@w %11s|' % (
                            '',
                            colors['Light'], resists['Light'],
                            colors['Magic'], resists['Magic'],
                            colors['Mental'], resists['Mental'],
                            colors['Negative'], resists['Negative'],
                            colors['Shadow'], resists['Shadow'],
                            colors['Sonic'], resists['Sonic'],
                            colors['Water'], resists['Water'],
                            ''))

    return ttext

  def api_formatitem(self, serial):
    """
    """
    divider = '+' + '-' * 65 + '+'
    linelen = 50

    serial = int(serial)
    nitem = self.api.get('eq.getitem')(serial)
    if nitem:
      self.itemcache[serial].update(nitem)
    self.api.get('send.client')('%s' % self.itemcache[serial])

    iteml = [divider]
    item = self.itemcache[serial]

    if 'keywords' in item and item['keywords']:
      tstuff = textwrap.wrap(item['keywords'], linelen)
      header = 'Keywords'
      for i in tstuff:
        iteml.append(self.formatsingleline(header, '@R', i))
        header = ''

    # do identifiers here

    if 'cname' in item and item['cname']:
      iteml.append(self.formatsingleline('Name', '@R', '@w' + item['cname']))

    iteml.append(self.formatsingleline('Id', '@R', item['serial']))

    if 'type' in item and item['type'] and 'level' in item:
      objtypes = self.api.get('itemu.objecttypes')()
      ntype = objtypes[item['type']].capitalize()
      iteml.append(self.formatdoubleline('Type', '@c', ntype,
                                         'Level', item['level']))
    else:
      iteml.append(self.formatsingleline('Level', '@c', item['level']))

    if 'worth' in item and 'weight' in item:
      iteml.append(self.formatdoubleline('Worth', '@c', item['worth'],
                                         'Weight', item['weight']))

    if 'wearable' in item and item['wearable']:
      iteml.append(self.formatsingleline('Wearable', '@c', item['wearable']))

    if 'score' in item:
      iteml.append(self.formatsingleline('Score', '@c', item['score'],
                                         datacolor='@Y'))

    if 'material' in item and item['material']:
      iteml.append(self.formatsingleline('Material', '@c', item['material']))

    if 'flags' in item and item['flags']:
      tlist = textwrap.wrap(item['flags'], linelen)
      header = 'Flags'
      for i in tlist:
        i = i.replace('precious', '@Yprecious@w')
        iteml.append(self.formatsingleline(header, '@c', i.rstrip()))
        header = ''

    if 'owner' in item and item['owner']:
      iteml.append(self.formatsingleline('Owned by', '@c', item['owner']))

    if 'fromclan' in item and item['fromclan']:
      iteml.append(self.formatsingleline('Clan Item', '@G', item['fromclan'],
                                         datacolor='@M'))

    if 'foundat' in item and item['foundat']:
      iteml.append(self.formatsingleline('Found at', '@G', item['foundat'],
                                         datacolor='@M'))

    if 'leadsto' in item and item['leadsto']:
      iteml.append(self.formatsingleline('Leads to', '@G', item['leadsto'],
                                         datacolor='@M'))

    if 'notes' in item and item['notes']:
      iteml.append(divider)
      tlist = textwrap.wrap(' '.join(item['notes']), linelen)
      header = 'Notes'
      for i in tlist:
        iteml.append(self.formatsingleline(header, '@W', i, '@w'))
        header = ''

    if 'affectmod' in item and item['affectmod']:
      iteml.append(divider)
      tlist = textwrap.wrap(', '.join(item['affectmod']), linelen)
      header = 'Affects'
      for i in tlist:
        iteml.append(self.formatsingleline(header, '@W', i, '@w'))
        header = ''

    if 'container' in item and item['container']:
      iteml.append(divider)
      iteml.append(self.formatspecialline('Capacity', '@c',
                          item['container']['capacity'], 'Heaviest Item',
                          item['container']['heaviestitem']))
      iteml.append(self.formatspecialline('Holding', '@c',
                            item['container']['holding'], 'Items Inside',
                            item['container']['itemsinside']))
      iteml.append(self.formatspecialline('Tot Weight', '@c',
                            item['container']['totalweight'], 'Item Burden',
                            item['container']['itemburden']))
      iteml.append(self.formatspecialline('', '@c',
                  '@wItems inside weigh @Y%d@w%%@w of their usual weight' % \
                          item['container']['itemweightpercent']))

    if 'weapon' in item and item['weapon']:
      iteml.append(divider)
      iteml.append(self.formatspecialline('Weapon Type', '@c',
                                  item['weapon']['wtype'], 'Average Dam',
                                  item['weapon']['avedam']))
      iteml.append(self.formatspecialline('Inflicts', '@c',
                                  item['weapon']['inflicts'], 'Damage Type',
                                  item['weapon']['damtype']))
      if 'special' in item['weapon'] and item['weapon']['special']:
        iteml.append(self.formatspecialline('Specials', '@c',
                                            item['weapon']['special']))

    if item['type'] == 20:
      if 'portal' in item and item['portal']:
        iteml.append(divider)
        iteml.append(self.formatsingleline('Portal', '@R',
                  '@Y%s@w uses remaining.' % item['portal']['uses']))

    if 'statmod' in item and item['statmod']:
      iteml.append(divider)
      iteml.append(self.formatstatsheader())
      iteml.append(self.formatstats(item['statmod']))

    if 'resistmod' in item and item['resistmod']:
      item.append(divider)
      for i in self.formatresist(item['resistmod'], divider):
        item.append(i)

    if 'skillmod' in item and item['skillmod']:
      iteml.append(divider)
      header = 'Skill Mods'
      for i in item['skillmod']:
        spell = self.api.get('skills.gets')(i)
        color = '@R'
        if int(item['skillmod'][i]) > 0:
          color = '@G'
        iteml.append(self.formatspecialline(header, '@c',
               'Modifies @g%s@w by %s%+d@w' % (str(spell['name']).capitalize(),
               color, int(item['skillmod'][i]))))
        header = ''

    if 'spells' in item and item['spells']:
      iteml.append(divider)

      header = 'Spells'
      for i in xrange(1, 5):
        key = 'sn%s' % i
        if item['spells'][key] and item['spells'][key] != 0:
          spell = self.api.get('skills.gets')(item['spells'][key])
          plural = ''
          if int(item['spells']['uses']) > 1:
            plural = 's'
          iteml.append(self.formatspecialline(header, '@c',
                    "%d use%s of level %d '@g%s@w'" % (
                            item['spells']['uses'], plural,
                            item['spells']['level'],
                            spell['name'].lower())))
          header = ''

    if 'food' in item and item['food']:
      iteml.append(divider)
      header = 'Food'
      iteml.append(self.formatspecialline(header, '@c',
          "Will replenish hunger by %d%%" % (item['food']['percent'])))

    if 'drink' in item and item['drink']:
      iteml.append(divider)
      iteml.append(self.formatspecialline('Drink', '@c',
                  "%d servings of %s. Max: %d" % (item['drink']['servings'],
                                    item['drink']['liquid'],
                                    item['drink']['liquidmax']/20)))
      iteml.append(self.formatspecialline('', '@c',
                  "Each serving replenishes thirst by %d%%" % \
                    item['drink']['thirstpercent']))
      iteml.append(self.formatspecialline('', '@c',
                  "Each serving replenishes hunger by %d%%" % \
                    item['drink']['hungerpercent']))

    if 'furniture' in item and item['furniture']:
      iteml.append(divider)
      iteml.append(self.formatspecialline('Heal Rate', '@c',
              "Health [@Y%d@w]    Magic [@Y%d@w]" % (
                    item['furniture']['hpregen'],
                    item['furniture']['manaregen'])))

    iteml.append(divider)

    return iteml

  def api_showitem(self, serial):
    tstuff = self.api.get('itemid.format')(serial)

    self.api.get('send.client')('\n'.join(tstuff), preamble=False)



