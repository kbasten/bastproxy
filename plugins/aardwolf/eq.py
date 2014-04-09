"""
$Id$

This plugin reads and parses invmon data from Aardwolf
"""
import copy
import time
import argparse
import shlex
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin

NAME = 'Aardwolf Eq cmds, parser'
SNAME = 'eq'
PURPOSE = 'Eq Manipulation'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

optionallocs = [8, 9, 10, 11, 25, 28, 29, 30, 31, 32]

class Plugin(AardwolfBasePlugin):
  """
  a plugin to handle equipment related actions
  invmon, eqdata, inv
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    AardwolfBasePlugin.__init__(self, *args, **kwargs)

    self.itemcache = {}
    self.eqdata = {}
    self.invdata = {}
    self.currentcontainer = None
    self.currentcmd = ''

    self.wearall = False
    self.removeall = False
    self.putall = False
    self.getall = False
    self.sellall = False
    self.buyall = False
    self.dropall = False

    self.queue = []

    self.cmdqueue = None

    self.api.get('dependency.add')('aardwolf.itemu')
    self.api.get('dependency.add')('cmdq')

    self.api.get('api.add')('getitem', self.api_getitem)
    self.api.get('api.add')('get', self.api_putininventory)
    self.api.get('api.add')('put', self.api_putincontainer)

  def load(self):
    """
    load the plugin
    """
    AardwolfBasePlugin.load(self)

    self.resetworneq()

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

    parser = argparse.ArgumentParser(add_help=False,
                 description='show some internal variables')
    self.api.get('commands.add')('sv', self.cmd_showinternal,
                                parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='refresh eq')
    self.api.get('commands.add')('refresh', self.cmd_refresh,
                                parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='get an item')
    parser.add_argument('item', help='the item to get', default='', nargs='?')
    parser.add_argument('otherargs', help='the rest of the args', default=[], nargs='*')
    self.api.get('commands.add')('get', self.cmd_get,
                                parser=parser, format=False, preamble=False)

    parser = argparse.ArgumentParser(add_help=False,
                 description='get an item')
    parser.add_argument('item', help='the item to get', default='', nargs='?')
    parser.add_argument('otherargs', help='the rest of the args', default=[], nargs='*')
    self.api.get('commands.add')('put', self.cmd_put,
                                parser=parser, format=False, preamble=False)

    parser = argparse.ArgumentParser(add_help=False,
                 description='get an item')
    parser.add_argument('item', help='the item to get', default='', nargs='?')
    self.api.get('commands.add')('icache', self.cmd_icache,
                                parser=parser)

    self.api.get('triggers.add')('dead',
      "^You die.$",
      enabled=True, group='dead')

    self.api.get('triggers.add')('badinvdata1',
      "^Syntax: invdata                - view all inv data.$",
      enabled=True, group='badinvdata')

    self.api.get('triggers.add')('badinvdata2',
      "^      : invdata <container id> - view all inv data in a container.$",
      enabled=True, group='badinvdata')

    self.api.get('triggers.add')('badinvdata3',
      "^      : invdata ansi           - remove color codes from output.$",
      enabled=True, group='badinvdata')

    self.api.get('triggers.add')('badinvdata4',
      "^      : invdata <container> ansi - remove color codes from output.$",
      enabled=True, group='badinvdata')

    self.api.get('triggers.add')('invmon',
      "^\{invmon\}(?P<action>.*),(?P<serial>.*),(?P<container>.*),(?P<location>.*)$",
      enabled=True, group='invmon')

    self.api.get('triggers.add')('invitem',
      "^\{invitem\}(?P<data>.*)$",
      enabled=True, matchcolor=True)

    self.api.get('triggers.add')('eqdatastart',
      "^\{eqdata\}$",
      enabled=False, group='eqdata', omit=True)

    self.api.get('triggers.add')('eqdataend',
      "^\{/eqdata\}$",
      enabled=False, group='eqdata', omit=True)

    self.api.get('triggers.add')('dataline',
      "^(\d+),(.+),(.+),(.+),(.+),(.+),(.+),(.+)$",
      enabled=False, group='dataline', omit=True)

    self.api.get('triggers.add')('invdatastart',
      "^\{invdata\s*(?P<container>.*)?\}$",
      enabled=False, group='invdata', omit=True)

    self.api.get('triggers.add')('invdataend',
      "^\{/invdata\}$",
      enabled=True, group='invdata', omit=True)

    self.api.get('events.register')('trigger_dead', self.dead)
    self.api.get('events.register')('trigger_invitem', self.trigger_invitem)
    self.api.get('events.register')('trigger_eqdatastart', self.eqdatastart)
    self.api.get('events.register')('trigger_eqdataend', self.eqdataend)
    self.api.get('events.register')('trigger_invdatastart', self.invdatastart)
    self.api.get('events.register')('trigger_invdataend', self.invdataend)
    self.api.get('events.register')('trigger_invmon', self.invmon)

    CmdQueue = self.api.get('cmdq.baseclass')()

    self.cmdqueue = CmdQueue(self)
    self.cmdqueue.addcmdtype('invdata', 'invdata', "^invdata\s*(\d*)$",
                       self.invdatabefore, self.invdataafter)
    self.cmdqueue.addcmdtype('eqdata', 'eqdata', "^eqdata$",
                       self.eqdatabefore, self.eqdataafter)
    self.cmdqueue.addcmdtype('get', 'get', "^get\s*(.*)$")
    self.cmdqueue.addcmdtype('put', 'put', "^get\s*(.*)$")

  def invdatabefore(self):
    """
    """
    self.api.get('send.msg')('enabling invdata triggers')
    self.api.get('triggers.togglegroup')('invdata', True)
    self.api.get('triggers.togglegroup')('dataline', True)
    self.api.get('events.register')('trigger_dataline', self.invdataline)

  def invdataafter(self):
    """
    """
    self.api.get('send.msg')('disabling invdata triggers')
    self.api.get('triggers.togglegroup')('invdata', False)
    self.api.get('triggers.togglegroup')('dataline', False)
    self.api.get('events.unregister')('trigger_dataline', self.invdataline)

  def eqdatabefore(self):
    """
    """
    self.api.get('send.msg')('enabling eqdata triggers')
    self.api.get('triggers.togglegroup')('eqdata', True)
    self.api.get('triggers.togglegroup')('dataline', True)
    self.api.get('events.register')('trigger_dataline', self.eqdataline)

  def eqdataafter(self):
    """
    """
    self.api.get('send.msg')('disabling eqdata triggers')
    self.api.get('triggers.togglegroup')('eqdata', False)
    self.api.get('triggers.togglegroup')('dataline', False)
    self.api.get('events.unregister')('trigger_dataline', self.eqdataline)

  def disconnect(self, args):
    """
    """
    AardwolfBasePlugin.disconnect(self)
    self.itemcache = {}
    self.eqdata = {}
    self.invdata = {}
    self.currentcontainer = None

    self.cmdqueue.resetqueue()

  def cmd_refresh(self, args):
    """
    refresh eq
    """
    self.itemcache = {}
    self.eqdata = {}
    self.invdata = {}
    self.currentcontainer = None

    self.cmdqueue.resetqueue()

    self.getdata('Worn')
    self.getdata('Inventory')

    return True, ['Refreshing EQ']

  # get an item from the cache
  def api_getitem(self, item):
    """
    get an item from the cache
    """
    nitem = self.find_item(item)

    if nitem in self.itemcache:
      return self.itemcache[nitem]
    else:
      return None

  def api_putininventory(self, serial):
    """
    put an item in inventory
    """
    serial = int(serial)
    if serial in self.itemcache:
      container = self.itemcache[serial]['curcontainer']
      if container == 'Worn':
        self.queue.append('remove %s' % serial)
      elif container != 'Inventory':
        self.itemcache[serial]['origcontainer'] = container
        self.api.get('send.execute')('get %s %s' % (serial, container))
      else:
        container = ''
      return True, container
    else:
      return False, ''

  def api_putincontainer(self, serial, container=None):
    """
    put an item in a container
    """
    serial = int(serial)
    if not container:
      if serial in self.itemcache and 'origcontainer' in self.itemcache[serial]:
        container = self.itemcache[serial]['origcontainer']
    try:
      container = int(container)
    except (ValueError, TypeError):
      pass

    self.api_putininventory(serial)

    if serial in self.itemcache and container in self.itemcache:
      self.api.get('send.execute')('put %s %s' % (serial, container))
      return True, container

    return False, ''

  def api_wearitem(self, serial):
    """
    wear an item
    """
    pass

  def api_removeitem(self, serial):
    """
    remove an item
    """
    pass

  def afterfirstactive(self, _=None):
    """
    do something on connect
    """
    print 'firstactive'
    AardwolfBasePlugin.afterfirstactive(self)
    self.getdata('Worn')
    self.getdata('Inventory')

  def getdata(self, etype):
    """
    get container or worn data
    """
    if etype == 'Inventory':
      self.cmdqueue.addtoqueue('invdata', '')
    elif etype == 'Worn':
      self.cmdqueue.addtoqueue('eqdata', '')
    else:
      self.cmdqueue.addtoqueue('invdata', etype)

  def dead(self, _):
    """
    reset stuff on death
    """
    self.invdata = {}
    self.queue = []
    self.resetworneq()

  def cmd_showinternal(self, args):
    """
    show internal stuff
    """
    msg = []
    msg.append('Queue     : %s' % self.cmdqueue.queue)
    msg.append('Cur cmd   : %s' % self.cmdqueue.currentcmd)
    msg.append('invdata   : %s' % self.invdata)
    msg.append('eqdata    : %s' % self.eqdata)
    msg.append('itemcache : %s' % self.itemcache)

    return True, msg

  def cmd_icache(self, args):
    """
    show internal stuff
    """
    msg = []
    item = args['item']
    try:
      item = int(item)
      if item in self.itemcache:
        msg.append('%s' % self.itemcache[item])
      else:
        msg.append('That item is not in the cache')

    except ValueError:
      msg.append('%s is not a serial number' % item)

    return True, msg

  def find_item(self, item):
    """
    find and item by serial or identifier
    """
    try:
      item = int(item)
      if item in self.itemcache:
        return item

    except ValueError:
      #check for identifiers here
      if item == 'tokenbag':
        return 417249394
      else:
        return "'%s'" % item if ' ' in item else item

  def cmd_get(self, args):
    """
    get an item
    """
    item = self.find_item(args['item'])
    if item in self.itemcache:
      retval, container = self.api_putininventory(item)
      return True, []

    tlist = ['%s' % self.find_item(x) for x in args['otherargs']]
    tlist.insert(0, '%s' % self.find_item(args['item']))
    args = ' '.join(tlist)

    # need to parse all items for identifiers
    self.api.get('send.msg')('serial is not a number, sending \'get %s\'' % args)
    self.api.get('send.execute')('get %s' % args)

    return True, []

  def cmd_put(self, args):
    """
    put an item in something
    """
    item = self.find_item(args['item'])
    origcontainer = False
    destination = None
    if len(args['otherargs']) == 0:
      if item in self.itemcache and 'origcontainer' in self.itemcache[item]:
        destination = self.itemcache[item]['origcontainer']
        if destination != self.itemcache[item]['curcontainer']:
          self.api_putincontainer(item, destination)
          return True, []

    if len(args['otherargs']) == 1:
      destination = self.find_item(args['otherargs'][0])

    if item in self.itemcache and destination in self.itemcache and len(args['otherargs']) != 0:
      self.api_putincontainer(item, destination)

    else:
      args = '%s %s' % (item,
              ' '.join(['%s' % self.find_item(x) for x in args['otherargs']]))
      self.api.get('send.msg')('sending \'put %s\'' % args)
      self.api.get('send.execute')('put %s %s' % (item, args))

    return True, []

  def checkvaliditem(self, item):
    if item['serial'] == "" or \
      item['level'] == "" or \
      item['type'] == "" or \
      item['name'] == "" or \
      item['cname'] == "":
        return False

    return True

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

  def resetworneq(self):
    """
    reset worn eq
    """
    wearlocs = self.api.get('itemu.wearlocs')()
    self.eqdata = []
    for i in xrange(0, len(wearlocs)):
      self.eqdata.append(-1)

  def wearitem(self, serial, wearloc):
    """
    wear an item
    """
    del self.eqdata[wearloc]
    self.itemcache[serial]['curcontainer'] = 'Worn'
    self.eqdata.insert(wearloc, serial)

  def takeoffitem(self, serial):
    self.itemcache[serial]['curcontainer'] = 'Inventory'
    try:
      location = self.eqdata.index(serial)
      del self.eqdata[location]
      self.eqdata.insert(location, -1)
    except IndexError:
      self.getdata('Worn')

  def eqdatastart(self, args):
    """
    show that the trigger fired
    """
    #self.api.get('send.msg')('found {eqdata}')
    self.resetworneq()

  def eqdataline(self, args):
    """
    parse a line of eqdata
    """
    line = args['line'].strip()
    if line != '{eqdata}':
      #self.api.get('send.msg')('eqdata args: %s' % args)
      titem = self.api.get('itemu.dataparse')(line, 'eqdata')
      self.itemcache[titem['serial']] = titem
      #self.api.get('send.msg')('eqdata parsed item: %s' % titem)
      self.wearitem(titem['serial'], titem['wearslot'])

  def eqdataend(self, args):
    """
    reset current when seeing a spellheaders ending
    """
    self.cmdqueue.cmddone('eqdata')

  def putitemincontainer(self, container, serial, place=-1):
    """
    add item to a container
    """
    self.itemcache[serial]['curcontainer'] = container
    if container:
      if place >= 0:
        self.invdata[container].insert(place, serial)
      else:
        self.invdata[container].append(serial)

  def removeitemfromcontainer(self, container, serial):
    """
    remove an item from inventory
    """
    self.itemcache[serial]['curcontainer'] = 'Inventory'
    itemindex = self.invdata[container].index(serial)
    del self.invdata[container][itemindex]

  def invdatastart(self, args):
    """
    show that the trigger fired
    """
    self.api.get('send.msg')('found {invdata}: %s' % args)
    if not args['container']:
      container = 'Inventory'
    else:
      container = int(args['container'])
    self.currentcontainer = container
    self.invdata[self.currentcontainer] = []

  def invdataline(self, args):
    """
    parse a line of eqdata
    """
    line = args['line'].strip()
    if line != '{invdata}':
      #self.api.get('send.msg')('invdata args: %s' % args)
      try:
        titem = self.api.get('itemu.dataparse')(line, 'eqdata')
        self.itemcache[titem['serial']] = titem
        #self.api.get('send.msg')('invdata parsed item: %s' % titem)
        self.putitemincontainer(self.currentcontainer, titem['serial'])
        if titem['type'] == 11 and not (titem['serial'] in self.invdata):
          self.cmdqueue.addtoqueue('invdata', titem['serial'])
      except (IndexError, ValueError):
        self.api.get('send.msg')('incorrect invdata line: %s' % line)

  def invdataend(self, args):
    """
    reset current when seeing a spellheaders ending
    """
    self.currentcontainer = None
    #self.api.get('send.msg')('found {/invdata}')
    self.cmdqueue.cmddone('invdata')

  def trigger_invitem(self, args):
    #self.api.get('send.msg')('invitem args: %s' % args)
    titem = self.api.get('itemu.dataparse')(args['data'], 'eqdata')
    self.itemcache[titem['serial']] = titem
    #self.api.get('send.msg')('invitem parsed item: %s' % titem)
    self.itemcache[titem['serial']] = titem

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

  def build_containerheader(self, args):
    """
    build the container header
    """
    header = []

    if not args['nogroup']:
      header.append(' %3s  '% '#')

    if not args['noflags']:
      header.append('(')
      count = 0
      flagaardcolors = self.api.get('itemu.itemflagscolors')()
      for flag in self.api.get('itemu.itemflags')():
        colour = flagaardcolors[flag]
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
      header.append('@w) ')

    if args['score']:
      header.append('(@C')
      header.append("%-5s" % 'Score')
      header.append('@w) ')

    header.append("%s" % 'Item Name')

    return ''.join(header)

  def build_container(self, args):
    """
    build a container
    """
    self.api.get('send.msg')('build_container args: %s' % args)

    try:
      container = int(args['container'])
    except ValueError:
      container = args['container']

    msg = ['Items in %s:' % container]

    msg.append(self.build_containerheader(args))

    msg.append('@B' + '-' * 80)

    if not (container in self.invdata) or not self.invdata[container]:
      msg.append('You have nothing in %s' % container)
    else:
      items = []
      numstyles = {}
      foundgroup = {}

      for serial in self.invdata[container]:
        item = self.itemcache[serial]
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
            flagaardcolors = self.api.get('itemu.itemflagscolors')()
            for flag in self.api.get('itemu.itemflags')():
              aardcolour = flagaardcolors[flag]
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
          sitem.append(') ')

          if args['serial']:
            sitem.append('(@x136')
            sitem.append("%-12s" % (item['serial'] if 'serial' in item else ""))
            if not args['nogroup']:
              if stylekey in numstyles:
                numstyles[stylekey]['serialcol'] = len(sitem) - 1
            sitem.append('@w) ')

          if args['score']:
            sitem.append('(@C')
            sitem.append("%5s" % (item['score'] if 'score' in item else 'Unkn'))
            sitem.append('@w) ')

          sitem.append(item['cname'])
          items.append(sitem)

      for item in items:
        msg.append(''.join(item))

      msg.append('')

    return msg


  def build_wornitem(self, item, wearloc, args):
    """
    build the output of a worn item
    """
    sitem = []

    wearlocs = self.api.get('itemu.wearlocs')()

    sitem.append('@G[@w')

    colour = '@c'
    if wearlocs[wearloc] == 'wielded' or wearlocs[wearloc] == 'second':
      colour = '@R'
    elif wearlocs[wearloc] == 'above' or wearlocs[wearloc] == 'light':
      colour = '@W'
    elif wearlocs[wearloc] == 'portal' or wearlocs[wearloc] == 'sleeping':
      colour = '@C'

    sitem.append(' %s%-8s@x ' % (colour, wearlocs[wearloc]))
    sitem.append('@G]@w ')

    if not args['noflags']:
      sitem.append('(')

      count = 0
      flagaardcolors = self.api.get('itemu.itemflagscolors')()
      for flag in self.api.get('itemu.itemflags')():
        aardcolour = flagaardcolors[flag]
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
    sitem.append(') ')

    if args['serial']:
      sitem.append('(@x136')
      sitem.append("%-12s" % (item['serial'] if 'serial' in item else ""))
      sitem.append('@w) ')

    if args['score']:
      sitem.append('(@C')
      sitem.append("%5s" % (item['score'] if 'score' in item else 'Unkn'))
      sitem.append('@w) ')

    sitem.append(item['cname'])

    return ''.join(sitem)

  def build_worn(self, args):
    """
    build the output of a container
    """
    wearlocs = self.api.get('itemu.wearlocs')()
    self.api.get('send.msg')('build_worn args: %s' % args)
    msg = ['You are using:']
    header = []

    header.append('@G[@w')
    header.append(' %-8s ' % 'Location')
    header.append('@G]@w ')

    if not args['noflags']:
      header.append('(')
      count = 0
      flagaardcolors = self.api.get('itemu.itemflagscolors')()
      for flag in self.api.get('itemu.itemflags')():
        colour = flagaardcolors[flag]
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
      header.append('@w) ')

    if args['score']:
      header.append('(@C')
      header.append("%-5s" % 'Score')
      header.append('@w) ')

    header.append("%s" % 'Item Name')

    header.append('  ')

    msg.append(''.join(header))

    msg.append('@B' + '-' * 80)

    for i in xrange(0, len(wearlocs)):
      if self.eqdata[i] != -1:
        serial = self.eqdata[i]
        item = self.itemcache[serial]
        msg.append(self.build_wornitem(item, i, args))
      else:
        doit = True
        if i in optionallocs:
          doit = False
        if (i == 23 or i == 26) and self.eqdata[25] != -1:
          doit = False
        if doit:
          item = {'cname':"@r< empty >@w", 'shortflags':"", 'level':'',
                  'serial':''}
          msg.append(self.build_wornitem(item, i, args))

    msg.append('')
    return msg

  def invmon(self, args):
    """
    do the appropriate action when seeing an invmon message
    """
    action = int(args['action'])
    serial = int(args['serial'])
    container = int(args['container'])
    location = int(args['location'])
    #self.api.get('send.msg')('action: %s, item: %s' % (action, serial))
    if action == 1:
    # Remove an item
      if serial in self.eqdata:
        self.takeoffitem(serial)
        self.putitemincontainer('Inventory', serial, place=0)
      else:
        self.getdata('Inventory')
        self.getdata('Worn')
    elif action == 2:
    # Wear an item
      if 'Inventory' in self.invdata and serial in self.invdata['Inventory']:
        self.removeitemfromcontainer('Inventory', serial)
        self.wearitem(serial, location)
      else:
        self.getdata('Inventory')
        self.getdata('Worn')
    elif action == 3 or action == 7:
      # 3 = Removed from inventory, 7 = consumed
      if 'Inventory' in self.invdata and serial in self.invdata['Inventory']:
        titem = self.itemcache[serial]
        if titem['type'] == 11:
          for item in self.invdata[serial]:
            del self.itemcache[item]
        self.removeitemfromcontainer('Inventory', serial)
        del self.itemcache[serial]
      else:
        self.getdata('Inventory')
    elif action == 4:
    # Added to inventory
      try:
        self.putitemincontainer('Inventory', serial, place=0)
        titem = self.itemcache[serial]
        if titem['type'] == 11:
          self.getdata(serial)
      except KeyError:
        self.getdata('Inventory')
    elif action == 5:
    # Taken out of container
      try:
        self.removeitemfromcontainer(container, serial)
        self.putitemincontainer('Inventory', serial, place=0)
      except KeyError:
        self.getdata('Inventory')
        self.getdata(container)
    elif action == 6:
    # Put into container
      try:
        self.removeitemfromcontainer('Inventory', serial)
        self.putitemincontainer(container, serial, place=0)
      except KeyError:
        self.getdata('Inventory')
        self.getdata(container)


