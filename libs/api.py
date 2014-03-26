"""
$Id$

this module handles the api for all other modules
"""
import sys
import time
#from decorator import decorator
try:
  from libs import color
except ImportError:
  pass


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

  def api_has(self, api):
    """
    see if something exists in the api
    """
    try:
      self.api.get(api)
      return True
    except AttributeError:
      return False


if __name__ == '__main__':
  def testapi():
    print 'testapi'

  def testover():
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
  print 'dict api.api', api.api
  print 'dict api.overloadapi', api.overloadedapi
  print 'test.over', api.get('test.over')()
  print 'test.api', api.get('test.api')()
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
  print 'test.three', api2.get('test.three')()

