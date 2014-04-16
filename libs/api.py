"""
$Id$

this module handles the api for all other modules
"""
import inspect

class API(object):
  """
  A class that exports an api for plugins and modules to use
  """
  api = {} # where the main api resides
  BASEPATH = ''
  MANAGERS = {}

  def __init__(self):
    """
    initialize the class
    """
    self.overloadedapi = {}
    self.timestring = '%a %b %d %Y %H:%M:%S'
    self.splitre = '(?<=[^\|])\|(?=[^\|])'
    self.overload('managers', 'add', self.addmanager)
    self.overload('managers', 'getm', self.getmanager)
    self.overload('api', 'add', self.add)
    self.overload('api', 'remove', self.remove)
    self.overload('api', 'getchildren', self.api_getchildren)
    self.overload('api', 'has', self.api_has)
    self.overload('api', 'detail', self.api_detail)
    self.overload('api', 'list', self.api_list)

  # add a function to the api
  def add(self, ptype, name, function):
    """  add a function to the api
    @Yptype@w  = the base that the api should be under
    @Yname@w  = the name of the api
    @Yfunction@w  = the function

    the function is added as ptype.name into the api

    this function returns no values"""
    if not (ptype in API.api):
      API.api[ptype] = {}

    if not (name in API.api[ptype]):
      API.api[ptype][name] = function

  # overload a function in the api
  def overload(self, ptype, name, function):
    """  overload a function in the api
    @Yptype@w  = the base that the api should be under
    @Yname@w  = the name of the api
    @Yfunction@w  = the function

    the function is added as ptype.name into the overloaded api

    this function returns no values"""
    try:
      ofunc = self.get(ptype + '.' + name)
      function.__doc__ = ofunc.__doc__
    except AttributeError:
      pass

    if not (ptype in self.overloadedapi):
      self.overloadedapi[ptype] = {}

    self.overloadedapi[ptype][name] = function

  # get a manager
  def getmanager(self, name):
    """  get a manager
    @Yname@w  = the name of the manager to get

    this function returns the manager instance"""
    if name in self.MANAGERS:
      return self.MANAGERS[name]
    else:
      return None

  # add a manager
  def addmanager(self, name, manager):
    """  add a manager
    @Yname@w  = the name of the manager
    @Ymanager@w  = the manager instance

    this function returns no values"""
    self.MANAGERS[name] = manager

  # remove a toplevel api
  def remove(self, ptype):
    """  remove a toplevel api
    @Yptype@w  = the base of the api to remove

    this function returns no values"""
    if ptype in API.api:
      del API.api[ptype]

  def get(self, apiname, baseapi=False):
    """
    get an api
    """
    ptype, name = apiname.split('.')
    if not baseapi:
      try:
        return self.overloadedapi[ptype][name]
      except KeyError:
        pass

    try:
      return self.api[ptype][name]
    except KeyError:
      pass

    raise AttributeError('%s is not in the api' % apiname)

  # return a list of api functions in a toplevel api
  def api_getchildren(self, toplevel):
    """
    return a list of apis in a toplevel api
    """
    apilist = []
    if toplevel in self.api:
      apilist.extend(self.api[toplevel].keys())

    if toplevel in self.overloadedapi:
      apilist.extend(self.overloadedapi[toplevel].keys())

    return list(set(apilist))

  # check to see if something exists in the api
  def api_has(self, apiname):
    """
    see if something exists in the api
    """
    try:
      self.get(apiname)
      return True
    except AttributeError:
      return False

  # get the details for an api function
  def api_detail(self, api):
    """
    return the detail of an api function
    """
    tmsg = []
    apia = None
    apio = None
    apiapath = None
    apiopath = None
    if api:
      apiname = api
      name, cmdname = apiname.split('.')
      tdict = {'name':name, 'cmdname':cmdname, 'apiname':apiname}
      try:
        apia = self.get(apiname, True)
      except AttributeError:
        pass

      try:
        apio = self.get(apiname)
      except AttributeError:
        pass

      if not apia and not apio:
        tmsg.append('%s is not in the api' % apiname)
      else:
        if apia and not apio:
          apif = apia
          apiapath = inspect.getsourcefile(apia)
          apiapath = apiapath[len(self.BASEPATH)+1:]

        elif apio and not apia:
          apif = apio
          apiopath = inspect.getsourcefile(apio)
          apiopath = apiopath[len(self.BASEPATH)+1:]

        elif not (apio == apia) and apia and apio:
          apif = apia
          apiapath = inspect.getsourcefile(apia)
          apiopath = inspect.getsourcefile(apio)
          apiapath = apiapath[len(self.BASEPATH)+1:]
          apiopath = apiopath[len(self.BASEPATH)+1:]

        else:
          apif = apia
          apiapath = inspect.getsourcefile(apia)
          apiapath = apiapath[len(self.BASEPATH)+1:]

        src = inspect.getsource(apif)
        dec = src.split('\n')[0]
        args = dec.split('(')[-1].strip()
        args = args.split(')')[0]
        argsl = args.split(',')
        argn = []
        for i in argsl:
          if i == 'self':
            continue
          argn.append('@Y%s@w' % i.strip())

        args = ', '.join(argn)
        tmsg.append('@G%s@w(%s)' % (apiname, args))
        tmsg.append(apif.__doc__ % tdict)

        tmsg.append('')
        if apiapath:
          tmsg.append('original defined in %s' % apiapath)
        if apiopath and apiapath:
          tmsg.append('overloaded in %s' % apiopath)
        elif apiopath:
          tmsg.append('original defined in %s' % apiopath)

    return tmsg

  # return a formatted list of functions in an api
  def api_list(self, toplevel=None):
    """
    return a formatted list of functions in an api
    """
    apilist = {}
    tmsg = []
    if toplevel:
      if toplevel in self.api:
        apilist[toplevel] = {}
        for k in self.api[toplevel]:
          apilist[toplevel][k] = True
      if toplevel in self.overloadedapi:
        if not (toplevel in apilist):
          apilist[toplevel] = {}
        for k in self.overloadedapi[toplevel]:
          apilist[toplevel][k] = True
    else:
      for i in self.api:
        if not (i in apilist):
          apilist[i] = {}
        for k in self.api[i]:
          apilist[i][k] = True

      for i in self.overloadedapi:
        if not (i in apilist):
          apilist[i] = {}
        for k in self.overloadedapi[i]:
          apilist[i][k] = True

    tkeys = apilist.keys()
    tkeys.sort()
    for i in tkeys:
      tmsg.append('@G%-10s@w' % i)
      tkeys2 = apilist[i].keys()
      tkeys2.sort()
      for k in tkeys2:
        apif = self.get('%s.%s' % (i, k))
        comments = inspect.getcomments(apif)
        if comments:
          comments = comments.strip()
        tmsg.append('  @G%-15s@w : %s' % (k, comments))

    return tmsg


if __name__ == '__main__':
  def testapi():
    """
    a test api
    """
    print 'testapi'

  def testover():
    """
    a test overloaded api
    """
    print 'testover'

  api = API()
  api.add('test', 'api', testapi)
  api.add('test', 'over', testapi)
  print 'test.api', api.get('test.api')()
  print 'test.over', api.get('test.over')()
  print 'dict api.api', api.api
  api.overload('over', 'api', testover)
  print 'dict api.overloadedapi', api.overloadedapi
  print 'over.api', api.get('over.api')()
  api.overload('test', 'over', testover)
  print 'test.over', api.get('test.over')()
  print 'test.api', api.get('test.api')()
  print 'api.has', api.get('api.has')('test.over')
  print 'api.has', api.get('api.has')('test.over2')
  print 'dict api.api', api.api
  print 'dict api.overloadapi', api.overloadedapi
  #print 'test.three', api.test.three()

  api2 = API()
  print 'api2 test.api', api2.get('test.api')()
  print 'api2 test.over', api2.get('test.over')()
  print 'api2 dict api.api', api2.api
  api2.overload('over', 'api', testover)
  print 'api2 dict api.overloadedapi', api2.overloadedapi
  print 'api2 over.api', api2.get('over.api')()
  api2.overload('test', 'over', testover)
  print 'api2 dict api.api', api2.api
  print 'api2 dict api.overloadapi', api2.overloadedapi
  print 'api2 test.over', api2.get('test.over')()
  print 'api2 test.api', api2.get('test.api')()
  print 'api_has', api2.api_has('test.three')
  print 'test.three', api2.get('test.three')()


