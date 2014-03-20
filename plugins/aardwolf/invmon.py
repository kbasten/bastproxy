"""
$Id: statdb.py 272 2013-12-29 18:41:16Z endavis $

This plugin reads and parses invmon data from Aardwolf

{invitem}1183386700,KMH,Jade Elixir,60,8,1,-1,-1
{invmon}4,1183386700,-1,-1

"""
import copy
import time
import argparse
import shlex
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin
from libs.color import strip_ansi

NAME = 'invmon'
SNAME = 'invmon'
PURPOSE = 'Parse invmon'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

flags = ['K', 'G', 'H', 'I', 'M']

flagaardcolours = {
 'K':'R',
 'M':'B',
 'G':'W',
 'H':'C',
 'I':'w',
}

class Plugin(AardwolfBasePlugin):
  """
  a plugin to monitor aardwolf events
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    AardwolfBasePlugin.__init__(self, *args, **kwargs)

    self.invitemcache = {}
    self.eqdata = {}
    self.invdata = {}

    self.currentcontainer = None

    self.wearall = False
    self.removeall = False
    self.putall = False
    self.getall = False
    self.sellall = False
    self.buyall = False
    self.dropall = False

    self.waiting = {}
    self.waitingforid = {}

    self.layout = {}
    self.layout['invheader'] = ["serial", "level", "type", "worth",
                                "weight", "wearable", "flags", "owner",
                                "fromclan", "timer", "u1", "u2", "u3",
                                "score"]
    self.layout['container'] = ["capacity", "heaviestitem", "holding",
                                "itemsinside", "totalweight", "itemburden",
                                "itemweightpercent"]
    self.layout['statmod'] = ['stat', 'value']
    self.layout['resistmod'] = ['resist', 'value']
    self.layout['weapon'] = ["wtype", "avedam", "inflicts", "damtype",
                             "special"]
    self.layout['skillmod'] = ['skillnum', 'value']
    self.layout['spells'] = ["uses", "level", "sn1", "sn2", "sn3", "sn4",
                             "u1"]
    self.layout['food'] = ['percent']
    self.layout['drink'] = ["servings", "liquid", "liquidmax", "liquidleft",
                            "thirstpercent", "hungerpercent", "u1"]
    self.layout['furniture'] = ["hpregen", "manaregen", "u1"]
    self.layout['eqdata'] = ["serial", "shortflags", "cname", "level",
                             "type", "unique", "wearslot", "timer"]
    self.layout['light'] = ['duration']
    self.layout['portal'] = ['uses']

    self.api.get('dependency.add')('aardu')

  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)

    #self.api.get('watch.add')('sell',
      #'^(se|sel|sell) (?P<stuff>.*)$')

    #self.api.get('watch.add')('buy',
      #'^(b|bu|buy) (?P<stuff>.*)$')

    #self.api.get('setting.add')('backupstart', '0000', 'miltime',
                      #'the time for a db backup, like 1200 or 2000')
    #self.api.get('setting.add')('backupinterval', 60*60*4, int,
                      #'the interval to backup the db, default every 4 hours')

    parser = argparse.ArgumentParser(add_help=False,
                 description='show equipment worn')
    parser.add_argument('-n', "--noflags", help="don't show flags, default False",
              action="store_true")
    parser.add_argument('-c', "--score", help="show score, default False",
              action="store_true")
    parser.add_argument('-s', "--serial", help="show serial, default False",
              action="store_true")
    self.api.get('commands.add')('eq', self.cmd_eq,
                                parser=parser, format=False, preamble=False)

    parser = argparse.ArgumentParser(add_help=False,
                 description='show inventory or a container')
    parser.add_argument('container', help='the container to see', default='Inventory', nargs='?')
    parser.add_argument('-n', "--noflags", help="don't show flags, default False",
              action="store_true")
    parser.add_argument('-c', "--score", help="show score, default False",
              action="store_true")
    parser.add_argument('-s', "--serial", help="show serial, default False",
              action="store_true")
    parser.add_argument('-g', "--nogroup", help="don't group items, default False",
              action="store_true")
    self.api.get('commands.add')('inv', self.cmd_inv,
                                parser=parser, format=False, preamble=False)

    #self.api.get('triggers.add')('dead',
      #"^You die.$",
      #enabled=True, group='dead')

    self.api.get('triggers.add')('badinvdata1',
      "^Syntax: invdata                - view all inv data.$",
      enabled=True, group='badinvdata')

    self.api.get('triggers.add')('badinvdata2',
      "^      : invdata <container id> - view all inv data in a container.$",
      enabled=True, group='badinvdata')

    self.api.get('triggers.add')('badinvdata3',
      "^      : invdata ansi           - remove color codes from output.$",
      enabled=True, group='badinvdata')

    self.api.get('triggers.add')('invmon',
      "^\{invmon\}(?P<action>.*),(?P<serial>.*),(?P<container>.*),(?P<location>.*)$",
      enabled=True, group='invmon')

    self.api.get('triggers.add')('invitem',
      "^\{invitem\}(?P<data>.*)$",
      enabled=True, matchcolor=True)

    self.api.get('triggers.add')('eqdatastart',
      "^\{eqdata\}$",
      enabled=True)

    self.api.get('triggers.add')('eqdataend',
      "^\{/eqdata\}$",
      enabled=False, group='eqdata')

    self.api.get('triggers.add')('invdatastart',
      "^\{invdata\s*(?P<container>.*)?\}$",
      enabled=True)

    self.api.get('triggers.add')('invdataend',
      "^\{/invdata\}$",
      enabled=True, group='invdata')

    self.api.get('triggers.add')('invdetailsstart',
      "^\{invdetails\}$",
      enabled=True)

    self.api.get('triggers.add')('invdetailsend',
      "^\{/invdetails\}$",
      enabled=True, group='invdetails')

    self.api.get('triggers.add')('identityon',
      "\+-----------------------------------------------------------------\+",
      enabled=False, group='identify')

    #self.api.get('events.register')('watch_sell', self.cmd_sell)
    #self.api.get('events.register')('trigger_dead', self.dead)
    self.api.get('events.register')('trigger_invitem', self.trigger_invitem)
    self.api.get('events.register')('trigger_eqdatastart', self.eqdatastart)
    self.api.get('events.register')('trigger_eqdataend', self.eqdataend)
    self.api.get('events.register')('trigger_invdatastart', self.invdatastart)

    #self.api.get('api.add')('runselect', self.api_runselect)

  #def dead(self, _):
    #"""
    #add to timeskilled when dead
    #"""
    #self.statdb.addtostat('timeskilled', 1)

  def sendcmd(self, cmd):
    self.api.get('send.msg')('sending cmd: %s' % cmd)
    self.api.get('send.execute')(cmd)

  def checkvaliditem(self, item):
    if item['serial'] == "" or \
      item['level'] == "" or \
      item['type'] == "" or \
      item['name'] == "" or \
      item['cname'] == "":
        return False

    return True

  def getdata(self, etype):
    if etype in self.waiting and self.waiting[etype]:
      return

    if etype == 'Inventory':
      self.sendcmd('invdata')
      self.waiting[etype] = True
    elif etype == 'Worn':
      self.sendcmd('eqdata')
      self.waiting[etype] = True
    else:
      self.sendcmd('invdata ' + str(etype))
      self.waiting[etype] = True

  def addmod(self, ltype, mod):
    if not (ltype in self.invdetails):
      self.invdetails[ltype] = []

    self.invdetails[ltype][mod[0]] = int(mod[1])

  def cmd_sell(self, args):
    self.api.get('send.msg')('got sell with args: %s' % args)
    pline = shlex.split(args['data'])
    self.api.get('send.msg')('shlex returned %s' % pline)
    if pline[1] == 'all':
      self.api.get('send.msg')('setting sellall')
      self.sellall = True
    elif 'all.' in pline[1]:
      self.api.get('send.msg')('setting sellall')
      self.sellall = True

  def cmd_buy(self, args):
    self.api.get('send.msg')('got buy with args: %s' % args)
    pline = shlex.split(args['data'])
    self.api.get('send.msg')('shlex returned %s' % pline)
    try:
      num = int(pline[1])
      if num > 20:
        self.api.get('send.msg')('setting buyall')
        self.buyall = True

    except ValueError:
      pass

  def eqdatastart(self, args):
    """
    show that the trigger fired
    """
    self.api.get('send.msg')('found {eqdata}')
    self.api.get('triggers.togglegroup')('eqdata', True)
    self.api.get('events.register')('trigger_all', self.eqdataline)
    self.eqdata = {}

  def eqdataline(self, args):
    """
    parse a line of eqdata
    """
    line = args['line'].strip()
    if line != '{eqdata}':
      self.api.get('send.msg')('eqdata args: %s' % args)
      titem = self.dataparse(line, 'eqdata')
      self.api.get('send.msg')('eqdata parsed item: %s' % titem)
      titem['name'] = strip_ansi(titem['cname'])
      self.eqdata[titem['serial']] = titem

  def eqdataend(self, args):
    """
    reset current when seeing a spellheaders ending
    """
    self.waiting['eqdata'] = False
    self.api.get('send.msg')('found {/eqdata}')
    self.api.get('events.unregister')('trigger_all', self.eqdataline)
    self.api.get('triggers.togglegroup')('eqdata', False)

  def invdatastart(self, args):
    """
    show that the trigger fired
    """
    self.api.get('send.msg')('found {invdata}: %s' % args)
    if not args['container']:
      args['container'] = 'Inventory'
    self.currentcontainer = args['container']
    self.api.get('triggers.togglegroup')('invdata', True)
    self.api.get('events.register')('trigger_all', self.invdataline)
    self.invdata[self.currentcontainer] = []

  def invdataline(self, args):
    """
    parse a line of eqdata
    """
    line = args['line'].strip()
    if line != '{invdata}':
      self.api.get('send.msg')('invdata args: %s' % args)
      try:
        titem = self.dataparse(line, 'eqdata')
        self.api.get('send.msg')('invdata parsed item: %s' % titem)
        titem['name'] = strip_ansi(titem['cname'])
        self.invdata[self.currentcontainer].append(titem)
      except IndexError:
        self.api.get('send.msg')('incorrect invdata line: %s' % line)


  def invdataend(self, args):
    """
    reset current when seeing a spellheaders ending
    """
    self.waiting[self.currentcontainer] = False
    self.currentcontainer = None
    self.api.get('send.msg')('found {/invdata}')
    self.api.get('events.unregister')('trigger_all', self.invdataline)
    self.api.get('triggers.togglegroup')('invdata', False)

  def trigger_invitem(self, args):
    self.api.get('send.msg')('invitem args: %s' % args)
    titem = self.dataparse(args['data'], 'eqdata')
    self.api.get('send.msg')('invitem parsed item: %s' % titem)
    self.invitemcache[titem['serial']] = titem

  def dataparse(self, line, layoutname):
    tlist = line.split(',')
    titem = {}
    for i in xrange(len(self.layout[layoutname])):
      v = self.layout[layoutname][i]
      value = tlist[i]
      if v == 'wearslot' or v == 'itemtype' or v == 'level':
        value = int(value)

      titem[v] = value

    return titem

  def cmd_eq(self, args):
    """
    show eq
    """
    self.api.get('send.msg')('cmd_eq args: %s' % args)

    return True, self.build_worn(args)

  def cmd_inv(self, args):
    """
    show inventory
    """
    self.api.get('send.msg')('cmd_inv args: %s' % args)

    return True, self.build_container(args)

  def build_container(self, args):
    """
    build a container
    """
    self.api.get('send.msg')('build_container args: %s' % args)

    container = args['container']

    msg = ['Items in %s:' % container]
    header = []

    if not args['nogroup']:
      header.append(' %3s  '% '#')

    if not args['noflags']:
      header.append('(')
      count = 0
      for flag in flags:
        colour = flagaardcolours[flag]
        count = count + 1
        if count == 1:
          header.append(' @' + colour + flag + '@x ')
        else:
          header.append('@' + colour + flag + '@x ')

      header.append('@w) ')

    header.append('(')
    header.append("@G%3s@w" % 'Lvl')
    header.append(')  ')

    if args['serial']:
      header.append('(@x136')
      header.append("%-12s" % "Serial")
      header.append('@w)  ')

    if args['score']:
      header.append('(@C')
      header.append("%-5s" % 'Score')
      header.append('@w)  ')

    header.append("%s" % 'Item Name')

    header.append('  ')

    msg.append(''.join(header))
    msg.append('@B' + '-' * 80)

    if not (container in self.invdata) or not self.invdata[container]:
      msg.append('You have nothing in %s' % container)
    else:
      items = []
      numstyles = {}
      foundgroup = {}

      for item in self.invdata[container]:
        print item
        #item = i
        stylekey = item['name'] + item['shortflags'] + str(item['level'])
        doit = True
        sitem = []
        if not args['nogroup'] and stylekey in numstyles:
          if not (stylekey) in foundgroup:
            foundgroup[stylekey] = 1
          foundgroup[stylekey] = foundgroup[stylekey] + 1
          doit = False
          numstyles[stylekey]['item'].pop(numstyles[stylekey]['countcol'])
          numstyles[stylekey]['item'].insert(numstyles[stylekey]['countcol'],
                                    "(%3d) " % foundgroup[stylekey])
          if args['serial'] and foundgroup[stylekey] == 2:
            numstyles[stylekey]['item'].pop(numstyles[stylekey]['serialcol'])
            numstyles[stylekey]['item'].insert(numstyles[stylekey]['serialcol'],
                                      "%-12s" % "Many")

        if doit:
          if not args['nogroup']:
            sitem.append(" %3s  " % " ")
            if not (stylekey in numstyles):
              numstyles[stylekey] = {'item':sitem, 'countcol':len(sitem) - 1,
                                     'serial':item['serial']}

          if not args['noflags']:
            sitem.append('(')

            count = 0
            for flag in flags:
              aardcolour = flagaardcolours[flag]
              count = count + 1
              if flag in item['shortflags']:
                if count == 1:
                  sitem.append(' @' + aardcolour + flag + ' ')
                else:
                  sitem.append('@' + aardcolour + flag + ' ')
              else:
                if count == 1:
                  sitem.append('   ')
                else:
                  sitem.append('  ')
            sitem.append('@w)')

            sitem.append(' ')

          sitem.append('(')
          sitem.append("@G%3s@w" % (item['level'] or ""))
          sitem.append(')  ')

          if args['serial']:
            sitem.append('(@x136')
            sitem.append("%-12s" % (item['serial'] if 'serial' in item else ""))
            if not args['nogroup']:
              if stylekey in numstyles:
                numstyles[stylekey]['serialcol'] = len(sitem) - 1
            sitem.append('@w)  ')

          if args['score']:
            sitem.append('(@C')
            sitem.append("%5s" % (item['score'] if 'score' in item else 'Unkn'))
            sitem.append('@w)  ')

          sitem.append(item['cname'])
          items.append(sitem)

      for item in items:
        msg.append(''.join(item))

      msg.append('')

    return msg


  def build_wornitem(self, item, args):
    """
    build the output of a worn item
    """
    self.api.get('send.msg')('build_wornitem args: %s' % args)

    sitem = []

    wearlocs = self.api.get('aardu.wearlocs')()

    sitem.append('@G[@w')

    colour = '@c'
    if wearlocs[item['wearslot']] == 'wielded' or wearlocs[item['wearslot']] == 'second':
      colour = '@R'
    elif wearlocs[item['wearslot']] == 'above' or wearlocs[item['wearslot']] == 'light':
      colour = '@W'
    elif wearlocs[item['wearslot']] == 'portal' or wearlocs[item['wearslot']] == 'sleeping':
      colour = '@C'

    sitem.append(' %s%-8s@x ' % (colour, wearlocs[item['wearslot']]))
    sitem.append('@G]@w ')

    if not args['noflags']:
      sitem.append('(')

      count = 0
      for flag in flags:
        aardcolour = flagaardcolours[flag]
        count = count + 1
        if flag in item['shortflags']:
          if count == 1:
            sitem.append(' @' + aardcolour + flag + ' ')
          else:
            sitem.append('@' + aardcolour + flag + ' ')
        else:
          if count == 1:
            sitem.append('   ')
          else:
            sitem.append('  ')
      sitem.append('@w)')

      sitem.append(' ')

    sitem.append('(')
    sitem.append("@G%3s@w" % (item['level'] or ""))
    sitem.append(')  ')

    if args['serial']:
      sitem.append('(@x136')
      sitem.append("%-12s" % (item['serial'] if 'serial' in item else ""))
      sitem.append('@w)  ')

    if args['score']:
      sitem.append('(@C')
      sitem.append("%5s" % (item['score'] if 'score' in item else 'Unkn'))
      sitem.append('@w)  ')

    sitem.append(item['cname'])

    return ''.join(sitem)

  def build_worn(self, args):
    """
    build the output of a container
    """
    self.api.get('send.msg')('build_worn args: %s' % args)
    msg = ['You are using:']
    header = []

    header.append('@G[@w')
    header.append(' %-8s ' % 'Location')
    header.append('@G]@w ')

    if not args['noflags']:
      header.append('(')
      count = 0
      for flag in flags:
        colour = flagaardcolours[flag]
        count = count + 1
        if count == 1:
          header.append(' @' + colour + flag + '@x ')
        else:
          header.append('@' + colour + flag + '@x ')

      header.append('@w) ')

    header.append('(')
    header.append("@G%3s@w" % 'Lvl')
    header.append(') ')

    if args['serial']:
      header.append('(@x136')
      header.append("%-12s" % "Serial")
      header.append('@w)  ')

    if args['score']:
      header.append('(@C')
      header.append("%-5s" % 'Score')
      header.append('@w)  ')

    header.append("%s" % 'Item Name')

    header.append('  ')

    msg.append(''.join(header))

    msg.append('@B' + '-' * 80)

    for s in sorted(self.eqdata.iteritems(), key=lambda (x, y): y['wearslot']):
      msg.append(self.build_wornitem(s[1], args))

    msg.append('')
    return msg

  #def checkaction(self, action, item, afterwait):
    #if action == 1:
      #if self.eqdata[int(item.wearloc)] != None:
        #self.eqdata[int(item.wearloc)] = None
        #self.invdata[item.objectid] = self.eqdata_cache[item.objectid]

    #elif action == 2:
      #self.eqdata[int(item.wearloc)] = self.eqdata_cache[item.objectid]
      #if self.invdata:
        #self.invdata[item.objectid] = None

