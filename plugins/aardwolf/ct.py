"""
$Id$

This plugin includes a combat tracker for aardwolf
"""
import math
from libs import utils
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin

NAME = 'CombatTracker'
SNAME = 'ct'
PURPOSE = 'Show combat stats'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(AardwolfBasePlugin):
  """
  a plugin to show combat stats after a mob kill
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    AardwolfBasePlugin.__init__(self, *args, **kwargs)

    self.msgs = []

    self.api.get('dependency.add')('mobk')

  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)

    self.api.get('setting.add')('statcolor', '@W', 'color', 'the stat color')
    self.api.get('setting.add')('infocolor', '@x33', 'color', 'the info color')

    self.api.get('events.register')('aard_mobkill', self.mobkill)

  def mobkill(self, args=None):
    """
    handle a mob kill
    """
    linelen = 72
    msg = []
    infocolor = self.api.get('setting.gets')('infocolor')
    statcolor = self.api.get('setting.gets')('statcolor')
    msg.append(infocolor + '-' * linelen)
    timestr = ''
    damages = args['damage']
    totald = sum(damages[d]['damage'] for d in damages)
    if args['finishtime'] and args['starttime']:
      timestr = '%s' % utils.timedeltatostring(args['starttime'],
              args['finishtime'],
              colorn=statcolor,
              colors=infocolor)

    xpstr = '%s%s%sxp' % (statcolor, args['totalxp'], infocolor)

    namestr = "{statcolor}{name}{infocolor} : {time}{infocolor} - {xp}".format(
            infocolor = infocolor,
            statcolor = statcolor,
            name = args['name'],
            time=timestr,
            xp=xpstr
            )
    tstr = infocolor + utils.center(namestr, '-', linelen)

    msg.append(tstr)
    msg.append(infocolor + '-' * linelen)

    bstringt = "{statcolor}{dtype:<20} {infocolor}: {statcolor}{hits:^10} " \
                "{damage:^10} ({percent:4.0%}) {misses:^10} {average:^10}"

    msg.append(bstringt.format(
           statcolor=infocolor,
           infocolor=infocolor,
           dtype='Dam Type',
           hits='Hits',
           percent=0,
           damage='Damage',
           misses='Misses',
           average='Average'))
    msg.append(infocolor + '-' * linelen)
    #totald = 0
    totalm = 0
    totalh = 0
    tkeys = damages.keys()
    tkeys.sort()
    for i in tkeys:
      if i != 'enemy' and i != 'starttime' and i != 'finishtime':
        vdict = args['damage'][i]
        #totald = totald + vdict['damage']
        totalm = totalm + vdict['misses']
        totalh = totalh + vdict['hits']
        damt = i
        if i == 'backstab' and 'incombat' in vdict:
          damt = i + " (in)"

        if vdict['hits'] == 0:
          avedamage =  0
        else:
          avedamage = vdict['damage'] / vdict['hits']

        tperc = vdict['damage'] / float(totald)

        msg.append(bstringt.format(
           statcolor=statcolor,
           infocolor=infocolor,
           dtype=damt,
           hits=vdict['hits'],
           percent=tperc,
           damage=vdict['damage'],
           misses=vdict['misses'],
           average=avedamage))

    msg.append(infocolor + '-' * linelen)
    msg.append(bstringt.format(
           statcolor=statcolor,
           infocolor=infocolor,
           dtype='Total',
           hits=totalh,
           percent=1,
           damage=totald,
           misses=totalm,
           average=totald/(totalh or 1)))
    msg.append(infocolor + '-' * linelen)
    self.addmessage('\n'.join(msg))

  def addmessage(self, msg):
    """
    add a message to the out queue
    """
    self.msgs.append(msg)

    self.api.get('events.register')('trigger_emptyline', self.showmessages)

  def showmessages(self, _=None):
    """
    show a message
    """

    self.api.get('events.unregister')('trigger_emptyline', self.showmessages)
    for i in self.msgs:
      self.api.get('send.client')(i, preamble=False)

    self.msgs = []


