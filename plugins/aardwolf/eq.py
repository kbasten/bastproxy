"""
This plugin reads and parses invmon data from Aardwolf
"""
import argparse
import re
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin

NAME = 'Aardwolf Eq cmds, parser'
SNAME = 'eq'
PURPOSE = 'Eq Manipulation'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

OPTIONALLOCS = [8, 9, 10, 11, 25, 28, 29, 30, 31, 32]

class Item(object):
  def __init__(self, attributes):
    self._dump_shallow_attrs = ['curcontainer', 'origcontainer']

    self.score = 'Unkn'
    self.wearslot = None

    self.upditem(attributes)

    self.curcontainer = None
    self.origcontainer = None
    self.hasbeenided = False

  def upditem(self, attributes):
    for k, v in attributes.items():
      setattr(self, k, v)

  def checkattr(self, attr):
    if hasattr(self, attr) and self.__dict__[attr]:
      return True

    return False


class EqContainer(object):
  def __init__(self, plugin, cid, cmd=None, cmdregex=None,
                  startregex=None, endregex=None):
    ## cid = container ID "83744667"
    ## cmd = command to send to get data "invdata 83744667"
    ## cmdregex = regex that matches command "^invdata 83744667$"
    ## startregex = the line to match to start collecting data "{invdata 83744667}"
    ## endregex = the line to match to end collecting data "{/invdata}"
    self.cid = cid
    self.cmd = cmd or "invdata %s" % self.cid
    self.cmdregex = cmdregex or "^invdata %s$" % self.cid
    self.startregex = startregex or "{invdata %s}" % self.cid
    self.endregex = endregex or "{/invdata}"
    self.plugin = plugin
    self.api = self.plugin.api
    self.cmdqueue = self.plugin.cmdqueue
    self.itemcache = self.plugin.itemcache
    self.needsrefresh = True
    self.items = []

    self._dump_shallow_attrs = ['plugin', 'api', 'cmdqueue', 'itemcache']

    self.cmdqueue.addcmdtype(self.cid, self.cmd, self.cmdregex,
                       beforef=self.databefore, afterf=self.dataafter)

    self.reset()

  def __str__(self):
    return 'Container: %s' % self.cid

  def count(self):
    """
    return the # of items in container
    """
    return len(self.items)

  def get(self, serial):
    """
    get an item from container
    """
    self.api('send.execute')('get %s %s' % (serial, self.cid))

  def put(self, serial):
    """
    put an item into container
    """
    self.api('send.execute')('put %s %s' % (serial, self.cid))

  def add(self, serial, place=-1):
    """
    add an item into this container
    """
    self.itemcache[serial].curcontainer = self
    if place >= 0:
      self.items.insert(place, serial)
    else:
      self.items.append(serial)

  def remove(self, serial):
    """
    remove an item from this container
    """
    self.itemcache[serial].curcontainer = None
    itemindex = self.items.index(serial)
    del self.items[itemindex]

  def reset(self):
    """
    reset this container
    """
    self.items = []

  def refresh(self):
    """
    refresh data
    """
    self.cmdqueue.addtoqueue(self.cid, '')

  def databefore(self):
    """
    this will be called before the the command
    """
    self.api.get('triggers.add')('%sstart' % self.cid,
      self.startregex,
      enabled=False, group='%sdata' % self.cid, omit=True)

    self.api.get('triggers.add')('%send' % self.cid,
      self.endregex,
      enabled=False, group='%sdata' % self.cid, omit=True)

    self.api.get('events.register')('trigger_%sstart' % self.cid, self.datastart)
    self.api.get('events.register')('trigger_%send' % self.cid, self.dataend)

    self.api.get('send.msg')('enabling %sdata triggers' % self.cid)
    self.api.get('triggers.togglegroup')('%sdata' % self.cid, True)

    if self.api.get('triggers.gett')('dataline'):
      self.api.get('triggers.remove')('dataline', force=True)

    self.api.get('triggers.add')('dataline',
      "^\s*(\d+),(.*),(.+),(.+),(.+),(.+),(.+),(.+)$",
      enabled=True, group='dataline', omit=True)

    self.api.get('events.register')('trigger_dataline', self.dataline,
                                    plugin=self.plugin.sname)

  def dataafter(self):
    """
    this will be called after the command
    """
    self.api.get('send.msg')('disabling %sdata triggers' % self.cid)
    self.api.get('triggers.togglegroup')('%sdata' % self.cid, False)
    self.api.get('events.unregister')('trigger_dataline', self.dataline)
    self.api.get('triggers.remove')('dataline')

    self.api.get('events.unregister')('trigger_%sstart' % self.cid, self.datastart)
    self.api.get('events.unregister')('trigger_%send' % self.cid, self.dataend)

    self.api.get('triggers.remove')('%sstart' % self.cid)
    self.api.get('triggers.remove')('%send' % self.cid)

  def datastart(self, args):
    """
    found beginning of data for this container
    """
    self.api.get('send.msg')('found {invdata}: %s' % args)
    self.reset()

  def dataline(self, args):
    """
    parse a line of data
    """
    line = args['colorline'].strip()
    if line != self.startregex:
      #self.api.get('send.msg')('invdata args: %s' % args)
      try:
        attributes = self.api.get('itemu.dataparse')(line, 'eqdata')
        titem = Item(attributes)
        self.itemcache[titem.serial] = titem
        #self.api.get('send.msg')('invdata parsed item: %s' % titem)
        self.add(titem.serial)
        if titem.itype == 11 and not (titem.serial in self.plugin.containers):
          self.plugin.containers[titem.serial] = EqContainer(self.plugin, titem.serial)
      except (IndexError, ValueError):
        self.api.get('send.msg')('incorrect invdata line: %s' % line)
        self.api('send.traceback')()

  def dataend(self, args):
    """
    found end of data for this container
    """
    self.cmdqueue.cmddone(self.cid)
    self.needsrefresh = False
    for container in self.plugin.containers:
      if self.plugin.containers[container].needsrefresh:
        self.plugin.containers[container].refresh()
        break

  def build_header(self, args):
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

  def build(self, args):
    """
    build a container
    """
    self.api.get('send.msg')('build_container args: %s' % args)

    msg = ['Items in %s:' % self.cid]

    msg.append(self.build_header(args))

    msg.append('@B' + '-' * 80)

    if len(self.items) < 1:
      msg.append('You have nothing in %s' % self.cid)
    else:
      items = []
      numstyles = {}
      foundgroup = {}

      for serial in self.items:
        item = self.itemcache[serial]
        #item = i
        stylekey = item.name + item.shortflags + str(item.level)
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
            numstyles[stylekey]['item'].insert(
                                    numstyles[stylekey]['serialcol'],
                                      "%-12s" % "Many")

        if doit:
          if not args['nogroup']:
            sitem.append(" %3s  " % " ")
            if not (stylekey in numstyles):
              numstyles[stylekey] = {'item':sitem, 'countcol':len(sitem) - 1,
                                     'serial':item.serial}

          if not args['noflags']:
            sitem.append('(')

            count = 0
            flagaardcolors = self.api.get('itemu.itemflagscolors')()
            for flag in self.api.get('itemu.itemflags')():
              aardcolour = flagaardcolors[flag]
              count = count + 1
              if flag in item.shortflags:
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
          sitem.append("@G%3s@w" % (item.level or ""))
          sitem.append(') ')

          if args['serial']:
            sitem.append('(@x136')
            sitem.append("%-12s" % (item.serial))
            if not args['nogroup']:
              if stylekey in numstyles:
                numstyles[stylekey]['serialcol'] = len(sitem) - 1
            sitem.append('@w) ')

          if args['score']:
            sitem.append('(@C')
            sitem.append("%5s" % (item.score))
            sitem.append('@w) ')

          sitem.append(item.cname)
          items.append(sitem)

      for item in items:
        msg.append(''.join(item))

      msg.append('')

    return msg

class Inventory(EqContainer):
  def __init__(self, plugin):
    EqContainer.__init__(self, plugin, 'Inventory', cmd='invdata',
                         cmdregex='^invdata$', startregex="{invdata}")

  def build(self, args):
    msg = EqContainer.build(self, args)

    if 'Keyring' in self.plugin.containers and \
        self.plugin.containers['Keyring'].count() > 0:
      msg.append("@C(%2d)@W ** Item(s) on Keyring **@w" % \
                                  self.plugin.containers['Keyring'].count())
      msg.append("")

    return msg

class Worn(EqContainer):
  def __init__(self, plugin):
    EqContainer.__init__(self, plugin, 'Worn', cmd='eqdata',
                         cmdregex='^eqdata$', startregex="{eqdata}",
                         endregex="{/eqdata}")

    self.lastworn = {}

  def reset(self):
    """
    reset worn eq
    """
    wearlocs = self.api.get('itemu.wearlocs')()
    self.items = []
    for i in xrange(0, len(wearlocs)):
      self.items.append(-1)

  def get(self, serial):
    """
    get an item from container
    """
    self.api('send.execute')('remove %s' % (serial))

  def put(self, serial, location=None):
    """
    put an item into container
    """
    cmd = 'wear %s' % serial
    if location:
      if location == 'lastworn' and serial in self.lastworn:
        cmd = cmd + ' ' + self.lastworn[serial]
      else:
        cmd = cmd + ' ' + location
    self.api('send.execute')(cmd)

  def add(self, serial, wearloc):
    """
    wear an item
    """
    if wearloc:
      del self.items[wearloc]
    self.itemcache[serial].curcontainer = self
    self.items.insert(wearloc, serial)
    self.lastworn[serial] = wearloc
    self.itemcache[serial].wearslot = wearloc

  def remove(self, serial):
    """
    take off an item
    """
    self.itemcache[serial].curcontainer = 'Inventory'
    self.itemcache[serial].wearslot = None
    try:
      location = self.items.index(serial)
      del self.items[location]
      self.items.insert(location, -1)
    except IndexError:
      self.refresh()

  def dataline(self, args):
    """
    parse a line of data
    """
    line = args['colorline'].strip()
    if line != self.startregex:
      #self.api.get('send.msg')('invdata args: %s' % args)
      try:
        attributes = self.api.get('itemu.dataparse')(line, 'eqdata')
        titem = Item(attributes)
        self.itemcache[titem.serial] = titem
        #self.api.get('send.msg')('invdata parsed item: %s' % titem)
        self.add(titem.serial, titem.wearslot)
        if titem.itype == 11 and not (titem.serial in self.plugin.containers):
          self.plugin.containers[titem.serial] = EqContainer(self.plugin, titem.serial)
      except (IndexError, ValueError):
        self.api.get('send.msg')('incorrect invdata line: %s' % line)
        self.api('send.traceback')()

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
        if item.checkattr('shortflags') and flag in item.shortflags:
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
    try:
      sitem.append("@G%3s@w" % item.level)
    except:
      print(item)
    sitem.append(') ')

    if args['serial']:
      sitem.append('(@x136')
      sitem.append("%-12s" % item.serial)
      sitem.append('@w) ')

    if args['score']:
      sitem.append('(@C')
      sitem.append("%5s" % item.score)
      sitem.append('@w) ')

    sitem.append(item.cname)

    return ''.join(sitem)

  def build(self, args):
    """
    build the output of a container
    """
    emptyitem = Item({'cname':"@r< empty >@w", 'shortflags':"", 'level':'',
                  'serial':''})

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
      if self.items[i] != -1:
        serial = self.items[i]
        item = self.itemcache[serial]
        msg.append(self.build_wornitem(item, i, args))
      else:
        doit = True
        if i in OPTIONALLOCS:
          doit = False
        if (i == 23 or i == 26) and self.items[25] != -1:
          doit = False
        if doit:
          msg.append(self.build_wornitem(emptyitem, i, args))

    msg.append('')
    return msg

class Keyring(EqContainer):
  def __init__(self, plugin):
    EqContainer.__init__(self, plugin, 'Keyring', cmd='keyring data',
                         cmdregex='^keyring data$', startregex="{keyring}",
                         endregex="{/keyring}")

  def get(self, serial):
    """
    get an item from the keyring
    """
    self.api('send.execute')('keyring get %s' % serial)

  def put(self, serial):
    """
    put an item into the keyring
    """
    self.api('send.execute')('keyring put %s' % serial)

class Vault(EqContainer):
  def __init__(self, plugin):
    EqContainer.__init__(self, plugin, 'Vault', cmd='vault data',
                         cmdregex='^vault data$', startregex="{vault}",
                         endregex="{/vault}")
    self.itemcount = 0
    self.itemtotal = 0
    self.itemmax = 0

  def refresh(self):
    if 'bank' in self.api('GMCP.getv')('room.info')['details']:
      EqContainer.refresh(self)

  def get(self, serial):
    """
    get an item from the keyring
    """
    self.api('send.execute')('vault get %s' % serial)

  def put(self, serial):
    """
    put an item into the keyring
    """
    self.api('send.execute')('vault put %s' % serial)

  def databefore(self):
    """
    account for vaultcounts
    """
    EqContainer.databefore(self)

    self.api.get('triggers.add')('%scount' % self.cid,
      "^{vaultcounts}(?P<items>.*),(?P<totalitems>.*),(?P<maxitems>.*){/vaultcounts}$",
      omit=True)

    self.api.get('events.register')('trigger_%scount' % self.cid, self.vaultcount)

  def vaultcount(self, args):
    """
    get the vaultcount line
    """
    self.itemcount = args['items']
    self.itemtotal = args['totalitems']
    self.itemmax = args['maxitems']

    self.api.get('events.unregister')('trigger_%scount' % self.cid, self.vaultcount)

    self.api.get('triggers.remove')('%scount' % self.cid, force=True)

  def build(self, args):
    msg = EqContainer.build(self, args)

    msg.append("@wYou have @Y%s@w of @Y%s@w items stored in your vault." % \
                                (len(self.items), self.itemmax))

    #if self.itemcount != self.itemtotal:
      #msg.append("@wIncluding keep flagged items, you have @Y%s@w item in your vault.@w" % \
        #self.itemtotal)

    return msg

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
    self.containers = {}
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

    self._dump_shallow_attrs.append('itemcache')

    self.api.get('dependency.add')('aardwolf.itemu')
    self.api.get('dependency.add')('cmdq')

    self.api.get('api.add')('getitem', self.api_getitem)
    self.api.get('api.add')('getcontainer', self.api_getcontainer)
    self.api.get('api.add')('get', self.api_putininventory)
    self.api.get('api.add')('put', self.api_putincontainer)
    self.api.get('api.add')('findname', self.api_findname)
    self.api.get('api.add')('getworn', self.api_getworn)
    self.api.get('api.add')('equip', self.api_equipitem)
    self.api.get('api.add')('unequip', self.api_unequipitem)
    self.api.get('api.add')('addidentify', self.api_addidentify)


  def load(self):
    """
    load the plugin
    """
    AardwolfBasePlugin.load(self)

    parser = argparse.ArgumentParser(add_help=False,
                 description='show equipment worn')
    parser.add_argument('-n', "--noflags",
                        help="don't show flags, default False",
                        action="store_true")
    parser.add_argument('-c', "--score", help="show score, default False",
              action="store_true")
    parser.add_argument('-s', "--serial", help="show serial, default False",
              action="store_true")
    self.api.get('commands.add')('eq', self.cmd_eq,
                                parser=parser, format=False, preamble=False)

    parser = argparse.ArgumentParser(add_help=False,
                 description='show inventory or a container')
    parser.add_argument('container', help='the container to see',
                        default='Inventory', nargs='?')
    parser.add_argument('-n', "--noflags",
                        help="don't show flags, default False",
                        action="store_true")
    parser.add_argument('-c', "--score", help="show score, default False",
              action="store_true")
    parser.add_argument('-s', "--serial", help="show serial, default False",
              action="store_true")
    parser.add_argument('-g', "--nogroup",
                        help="don't group items, default False",
                        action="store_true")
    self.api.get('commands.add')('inv', self.cmd_inv,
                                parser=parser, format=False, preamble=False)

    parser = argparse.ArgumentParser(add_help=False,
                 description='refresh eq')
    self.api.get('commands.add')('refresh', self.cmd_refresh,
                                parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='get an item')
    parser.add_argument('item', help='the item to get', default='', nargs='?')
    parser.add_argument('otherargs', help='the rest of the args',
                        default=[], nargs='*')
    self.api.get('commands.add')('get', self.cmd_get,
                                parser=parser, format=False, preamble=False)

    parser = argparse.ArgumentParser(add_help=False,
                 description='get an item')
    parser.add_argument('item', help='the item to get', default='', nargs='?')
    parser.add_argument('otherargs', help='the rest of the args',
                        default=[], nargs='*')
    self.api.get('commands.add')('put', self.cmd_put,
                                parser=parser, format=False, preamble=False)

    parser = argparse.ArgumentParser(add_help=False,
                 description='show an item from the cache')
    parser.add_argument('item', help='the item to show', default='', nargs='?')
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
      "^\{invmon\}(?P<action>.*),(?P<serial>.*)," \
        "(?P<container>.*),(?P<location>.*)$",
      enabled=True, group='invmon')

    self.api.get('triggers.add')('invitem',
      "^\{invitem\}(?P<data>.*)$",
      enabled=True, matchcolor=True)


    self.api.get('events.register')('trigger_dead', self.dead)
    self.api.get('events.register')('trigger_invitem', self.trigger_invitem)
    self.api.get('events.register')('trigger_invmon', self.invmon)

    self.cmdqueue = self.api.get('cmdq.baseclass')()(self)

    self.containers['Inventory'] = Inventory(self)
    self.containers['Worn'] = Worn(self)
    self.containers['Keyring'] = Keyring(self)
    self.containers['Vault'] = Vault(self)

  # add identify information to an item
  def api_addidentify(self, serial, attributes):
    """
    add identify information to an item
    """
    if serial in self.itemcache:
      self.itemcache[serial].upditem(attributes)
      self.itemcache[serial].hasbeenided = True

  # return the item worn at a specified location
  def api_getworn(self, location):
    """
    get the item that is worn at location
    """
    try:
      int(location)
      try:
        return self.itemcache[self.containers['Worn'].items[location]]
      except KeyError:
        return None
    except ValueError:
      wearlocsrev = self.api.get('itemu.wearlocs')(True)
      if location in wearlocsrev:
        container = self.containers['Worn']
        return self.itemcache[container.items[wearlocsrev[location]]]
    return None

  # find an item with name in it
  def api_findname(self, name, exact=False):
    """
    find an item with name in it
    """
    results = []
    for i in self.itemcache:
      if name in self.itemcache[i].name:
        results.append(self.itemcache[i])

    return results

  def disconnect(self, args=None):
    """
    called when the mud disconnects
    """
    AardwolfBasePlugin.disconnect(self, args)
    #self.itemcache = {}

    self.cmdqueue.resetqueue()

  def cmd_refresh(self, args):
    """
    refresh eq
    """
    #self.itemcache = {}

    self.cmdqueue.resetqueue()

    for container in self.containers:
      self.containers[container].refresh()

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

  # get a container
  def api_getcontainer(self, container):
    """
    get an item from the cache
    """
    try:
      container = int(container)
    except ValueError:
      pass

    if container in self.containers:
      return self.containers[container]

    return None

  # put an item into inventory
  def api_putininventory(self, serial):
    """
    put an item into inventory
    """
    serial = int(serial)
    if serial in self.itemcache:
      container = self.itemcache[serial].curcontainer
      if container.cid != 'Inventory':
        self.itemcache[serial].origcontainer = container
        container.get(serial)
      else:
        container = ''
      return True, container
    else:
      return False, ''

  # put an item into a container
  def api_putincontainer(self, serial, container=None, location=None):
    """
    put an item into a container
    """
    serial = int(serial)
    oldcontainer = None

    serial = int(serial)

    if serial in self.itemcache:
      item = self.itemcache[serial]
    else:
      item = None

    if not item:
      return

    if not container:
      if serial in self.itemcache:
        if self.itemcache[serial].checkattr('origcontainer'):
          container = self.itemcache[serial].origcontainer

    if serial in self.itemcache:
      if self.itemcache[serial].checkattr('curcontainer') and \
          self.itemcache[serial].curcontainer.cid != 'Inventory' and \
          self.itemcache[serial].curcontainer != container:
        oldcontainer = self.itemcache[serial].curcontainer

    if container:
      if oldcontainer:
        oldcontainer.get(serial)

      if container.cid == 'Worn' and location:
        container.put(serial, location)
      else:
        container.put(serial)
      return True, container

    return False, ''

  # equip an item
  def api_equipitem(self, serial, location=None):
    """
    wear an item
    """
    self.containers['Worn'].put(serial, location)

  # unequip an item
  def api_unequipitem(self, serial):
    """
    remove an item
    """
    self.containers['Worn'].get(serial)

  def afterfirstactive(self, _=None):
    """
    do something on connect
    """
    AardwolfBasePlugin.afterfirstactive(self)
    for container in self.containers:
      print 'refreshing %s' % container
      self.containers[container].refresh()

  def dead(self, _):
    """
    reset stuff on death
    """
    self.queue = []
    for container in self.containers:
      self.containers[container].reset()

  def cmd_icache(self, args):
    """
    show what's in the cache for an item
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
    if type(item) == Item:
      return item

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

    return None

  def cmd_get(self, args):
    """
    get an item
    """
    item = self.find_item(args['item'])
    if item in self.itemcache:
      self.api_putininventory(item)
      return True, []

    tlist = ['%s' % self.find_item(x) for x in args['otherargs']]
    tlist.insert(0, '%s' % self.find_item(args['item']))
    args = ' '.join(tlist)

    # need to parse all items for identifiers
    self.api.get('send.msg')('serial is not a number, sending \'get %s\'' % \
                                                      args)
    self.api.get('send.execute')('get %s' % args)

    return True, []

  def cmd_put(self, args):
    """
    put an item in something
    """
    item = self.find_item(args['item'])

    destination = None
    if len(args['otherargs']) == 0:
      if item in self.itemcache and self.itemcache[item].checkattr('origcontainer'):
        destination = self.itemcache[item].origcontainer
        if destination != self.itemcache[item].curcontainer:
          self.api_putincontainer(item, destination)
          return True, []

    if len(args['otherargs']) == 1:
      destination = self.find_item(args['otherargs'][0])

    if item in self.itemcache and destination in self.itemcache and \
            len(args['otherargs']) != 0:
      self.api_putincontainer(item, destination)

    else:
      args = '%s %s' % (item,
              ' '.join(['%s' % self.find_item(x) for x in args['otherargs']]))
      self.api.get('send.msg')('sending \'put %s\'' % args)
      self.api.get('send.execute')('put %s %s' % (item, args))

    return True, []

  def checkvaliditem(self, item):
    """
    check to see if an item is valid
    """
    if item.serial == "" or \
        item.level == "" or \
        item.itype == "" or \
        item.name == "" or \
        item.cname == "":
      return False

    return True

  def trigger_invitem(self, args):
    """
    run when an invitem is seen
    """
    #self.api.get('send.msg')('invitem args: %s' % args)
    data = self.api.get('itemu.dataparse')(args['data'], 'eqdata')
    if data['serial'] in self.itemcache:
      self.itemcache[data['serial']].upditem(data)
    else:
      titem = Item(data)
      self.itemcache[titem.serial] = titem
    #self.api.get('send.msg')('invitem parsed item: %s' % titem)

  def cmd_eq(self, args):
    """
    show eq
    """
    self.api.get('send.msg')('cmd_eq args: %s' % args)

    return True, self.containers['Worn'].build(args)

  def cmd_inv(self, args):
    """
    show inventory
    """
    self.api.get('send.msg')('cmd_inv args: %s' % args)

    container = args['container']

    try:
      container = int(container)
    except ValueError:
      pass

    if container in self.containers:
      return True, self.containers[container].build(args)
    else:
      return True, ["container %s does not exist" % container]

  def invmon(self, args):
    """
    do the appropriate action when seeing an invmon message
    """
    try:
      action = int(args['action'])
      serial = int(args['serial'])
      container = int(args['container'])
      location = int(args['location'])
    except ValueError:
      self.api('send.error')('the invmon line has bad data: %s' % args['line'])
    #self.api.get('send.msg')('action: %s, item: %s' % (action, serial))
    if action == 1:
    # Remove an item
      if serial in self.containers['Worn'].items:
        self.containers['Worn'].remove(serial)
        self.containers['Inventory'].add(serial, place=0)
        self.api.get('events.eraise')('eq_removed',
                                      {'item':self.itemcache[serial]})
      else:
        self.containers['Worn'].refresh()
        self.containers['Inventory'].refresh()
    elif action == 2:
    # Wear an item
      if serial in self.containers['Inventory'].items:
        self.containers['Inventory'].remove(serial)
        self.containers['Worn'].add(serial, location)
        self.api.get('events.eraise')('eq_worn',
                                      {'item':self.itemcache[serial],
                                       'location':location})
      else:
        self.containers['Inventory'].refresh()
        self.containers['Worn'].refresh()
    elif action == 3 or action == 7:
      # 3 = Removed from inventory, 7 = consumed
      if serial in self.containers['Inventory'].items:
        titem = self.itemcache[serial]
        #if titem.itype == 11:
          #for item in self.containers[serial].items:
            #del self.itemcache[item]
        self.containers['Inventory'].remove(serial)
        self.api.get('events.eraise')('inventory_removed', {'item':titem})
        #del self.itemcache[serial]
      else:
        self.containers['Inventory'].refresh()
    elif action == 4:
    # Added to inventory
      try:
        self.containers['Inventory'].add(serial, place=0)
        titem = self.itemcache[serial]
        if titem.itype == 11:
          self.containers[serial].refresh()
        self.api.get('events.eraise')('inventory_added', {'item':titem})
      except KeyError:
        self.containers['Inventory'].refresh()
    elif action == 5:
    # Taken out of container
      try:
        self.containers[container].remove(serial)
        self.containers['Inventory'].add(serial)
      except KeyError:
        self.containers[container].refresh()
        self.containers['Inventory'].refresh()
    elif action == 6:
    # Put into container
      try:
        self.containers['Inventory'].remove(serial)
        self.containers[container].add(serial, place=0)
      except KeyError:
        self.containers['Inventory'].refresh()
        self.containers[container].refresh()
    elif action == 9:
    # put into vault
      self.containers['Vault'].add(serial)
      pass
    elif action == 10:
    # take from vault
      self.containers['Vault'].remove(serial)
    elif action == 11:
    # put into keyring
      try:
        self.containers['Inventory'].remove(serial)
        self.containers['Keyring'].add(serial, place=0)
      except KeyError:
        self.containers['Inventory'].refresh()
        self.containers['Keyring'].refresh()
    elif action == 12:
    # take from keyring
      try:
        self.containers['Keyring'].remove(serial)
        self.containers['Inventory'].add(serial, place=0)
      except KeyError:
        self.containers['Keyring'].refresh()
        self.containers['Inventory'].refresh()
