import fnmatch
import os
import datetime

def find_files(directory, filematch):
  matches = []
  for root, dirnames, filenames in os.walk(directory):
    for filename in fnmatch.filter(filenames, filematch):
        matches.append(os.path.join(root, filename))
        
  return matches

  
def timedeltatostring(stime, etime):
    delay = datetime.timedelta(seconds=abs(etime - stime))
    if (delay.days > 0):
        tstr = str(delay)
        tstr = tstr.replace(" day, ", ":")
        out  = tstr.replace(" days, ", ":")
    else:
        out = "0:" + str(delay)
    outAr = out.split(':')
    outAr = [(int(float(x))) for x in outAr]
    tmsg = []
    days, hours, minutes = False, False, False
    if outAr[0] != 0:
      days = True
      tmsg.append('%dd' % outAr[0])
    if outAr[1] != 0 or days:
      hours = True
      tmsg.append('%dh' % outAr[1])
    if outAr[2] != 0 or days or hours:
      tmsg.append('%dm' % outAr[2])
    tmsg.append('%ds' % outAr[3])
      
    out   = ":".join(tmsg)
    return out

  
def verify_bool(val):
  if val == 0 or val == '0':
    return False
  elif val == 1 or val == '1':
    return True
  elif isinstance(val, basestring):
    val = val.lower()
    if val  == 'false' or val == 'no':
      return False
    elif val == 'true' or val == 'yes':
      return True
  
  return bool(val)

  
def verify(val, vtype):
  vtab = {}
  vtab[bool] = verify_bool
  
  if vtype in vtab:
    return vtab[vtype](val)
  else:
    return vtype(val)
  
def convert(input):
  """converts input to ascii"""  
  if isinstance(input, dict):
      return {convert(key): convert(value) for key, value in input.iteritems()}
  elif isinstance(input, list):
      return [convert(element) for element in input]
  elif isinstance(input, unicode):
      return input.encode('utf-8')
  else:
      return input
    
  