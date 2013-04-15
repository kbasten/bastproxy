"""
a module that holds a persistent dictionary implementation
it saves the dict to a file
"""
import pickle
import json
import csv
import os
import shutil
from libs.utils import convert

class PersistentDict(dict):
  ''' Persistent dictionary with an API compatible with shelve and anydbm.

  The dict is kept in memory, so the dictionary operations run as fast as
  a regular dictionary.

  Write to disk is delayed until close or sync (similar to gdbm's fast mode).

  Input file format is automatically discovered.
  Output file format is selectable between pickle, json, and csv.
  All three serialization formats are backed by fast C implementations.

  '''
  def __init__(self, filename, flag='c', mode=None, 
                                    format='json', *args, **kwds):
    """
    initialize the instance
    """
    self.flag = flag                    # r=readonly, c=create, or n=new
    self.mode = mode                    # None or an octal triple like 0644
    self.format = format                # 'csv', 'json', or 'pickle'
    self.filename = filename
    self.pload()
    dict.__init__(self, *args, **kwds)

  def sync(self):
    """
    write data to disk
    """
    if self.flag == 'r':
      return
    filename = self.filename
    tempname = filename + '.tmp'
    fileobj = open(tempname, 'wb' if self.format=='pickle' else 'w')
    try:
      self.dump(fileobj)
    except Exception:
      os.remove(tempname)
      raise
    finally:
      fileobj.close()
    shutil.move(tempname, self.filename)    # atomic commit
    if self.mode is not None:
      os.chmod(self.filename, self.mode)

  def close(self):
    """
    close the file
    """
    self.sync()

  def __enter__(self):
    """
    ????
    """
    return self

  def __exit__(self, *exc_info):
    """
    close the file
    """
    self.close()

  def dump(self, fileobj):
    """
    dump the file
    """
    if self.format == 'csv':
      csv.writer(fileobj).writerows(self.items())
    elif self.format == 'json':
      json.dump(self, fileobj, separators=(',', ':'))
    elif self.format == 'pickle':
      pickle.dump(dict(self), fileobj, 2)
    else:
      raise NotImplementedError('Unknown format: ' + repr(self.format))    

  def pload(self):
    """
    load from file
    """
    # try formats from most restrictive to least restrictive
    if self.flag != 'n' and os.access(self.filename, os.R_OK):
      fileobj = open(self.filename, 'rb' if self.format=='pickle' else 'r')
      with fileobj:
        self.load(fileobj)      

  def load(self, fileobj):
    """
    load the dictionary
    """  
    for loader in (pickle.load, json.load, csv.reader):
      fileobj.seek(0)
      try:
        if loader == json.load:                
          return self.update(loader(fileobj, object_hook=convert))
        else:
          return self.update(loader(fileobj))
      except Exception:
        #if not ('log' in self.filename):
          #exported.write_traceback("Error when loading %s" % loader)
        #else:
          #pass
        pass
    raise ValueError('File not in a supported format')
    
  def __setitem__(self, key, val):
    """
    override setitem
    """
    key = convert(key)
    val = convert(val)
    dict.__setitem__(self, key, val)
        
  def update(self, *args, **kwargs):
    """
    override update
    """
    for k, val in dict(*args, **kwargs).iteritems():
      self[k] = val    

