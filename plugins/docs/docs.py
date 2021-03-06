"""
This module creates the documentation

it requires the markdown2 and lxml libraries
"""
import argparse
import sys
import os
import copy
import distutils.dir_util as dir_util

from cgi import escape

from plugins._baseplugin import BasePlugin

#these 5 are required
NAME = 'Documentation'
SNAME = 'docs'
PURPOSE = 'create bastproxy documentation'
AUTHOR = 'Bast'
VERSION = 1

# This keeps the plugin from being autoloaded if set to False
AUTOLOAD = False

class Plugin(BasePlugin):
  """
  a plugin to create documentation
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)

    global markdown2
    import markdown2

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

    parser = argparse.ArgumentParser(add_help=False,
                 description='create documentation')
    self.api.get('commands.add')('build', self.cmd_build,
                                 parser=parser, group='Documentation')

  def buildtoc(self, toc):
    """
    convert a toc from markdown
    """
    tocl = []
    tocl.append('<ul class="nav sidebar-fixed">')
    firstlev = toc[0][0]
    tocn = {}
    lastlev = firstlev
    topparent = tocn
    secparent = None
    for i in xrange(0, len(toc)):
      level = toc[i][0]
      id = toc[i][1]
      text = toc[i][2]
      if level == firstlev:
        itemn = len(tocn) + 1
        tocn[itemn] = {}
        tocn[itemn]['id'] = id
        tocn[itemn]['text'] = text
        tocn[itemn]['parent'] = None
        tocn[itemn]['children'] = {}
        topparent = tocn[itemn]
      elif level == firstlev + 1:
        childn = len(topparent['children']) + 1
        topparent['children'][childn] = {}
        topparent['children'][childn]['id'] = id
        topparent['children'][childn]['text'] = text
        topparent['children'][childn]['parent'] = topparent
        topparent['children'][childn]['children'] = {}
        secparent = topparent['children'][childn]
      elif level == firstlev + 2:
        childn = len(secparent['children']) + 1
        secparent['children'][childn] = {}
        secparent['children'][childn]['id'] = id
        secparent['children'][childn]['text'] = text
        secparent['children'][childn]['parent'] = secparent
        secparent['children'][childn]['children'] = {}


    tocl.extend(self.tocitem(tocn))
    return '\n'.join(tocl)

  def tocitem(self, nitem):
    tocl = []
    for i in sorted(nitem.keys()):
      item = nitem[i]
      data_target = item['id'] + 'Menu'
      if len(item['children']) > 0:
        tocl.append(
    """  <li><a href="#" data-toggle="collapse" data-target="#%(data_target)s">
           %(text)s <i class="glyphicon glyphicon-chevron-right"></i>
           <ul class="list-unstyled collapse" id="%(data_target)s">""" % \
           {'data_target':data_target, 'text':item['text']})
        tocl.extend(self.tocitem(item['children']))
        tocl.append('</ul></li>')
      else:
        tocl.append('  <li><a href="#%(id)s">%(text)s</a></li>' % \
          {'id':item['id'], 'text':item['text']})

    return tocl

  def checknodocs(self, plugin):
    """
    check for no docs setting
    """
    ppack = 'plugins.%s' % plugin.package

    if not ('NODOCS' in sys.modules[ppack].__dict__):
      return False
    elif 'NODOCS' in sys.modules[ppack].__dict__:
      if sys.modules[ppack].__dict__['NODOCS']:
        return True
      else:
        return False

    return False


  def buildpluginmenu(self, plugininfo):
    """
    build the plugin menu
    """
    pmenu = []

    ptree = {}
    for i in plugininfo.keys():
      pmod = self.api.get('plugins.getp')(plugininfo[i]['modpath'])

      try:
        testdoc = sys.modules[pmod.fullimploc].__doc__
      except AttributeError:
        self.api.get('send.msg')('Plugin %s is not loaded' % \
                                                plugininfo[i]['modpath'])
        continue

      moddir = os.path.basename(os.path.split(i)[0])
      name = os.path.splitext(os.path.basename(i))[0]

      if not self.checknodocs(pmod):
        if not (moddir in ptree):
          ptree[moddir] = {}

        ptree[moddir][name] = {'location':i}

    for i in sorted(ptree.keys()):
      pmenu.append("""<li class="dropdown-submenu">
            <a href="#" class="dropdown-toggle" data-toggle="dropdown">%s</a>
                  <ul class="dropdown-menu">""" % (i.capitalize()))
      for j in sorted(ptree[i].keys()):
        item = plugininfo[ptree[i][j]['location']]
        pmenu.append('<li><a href="%(link)s">%(name)s</a></li>' % {
                  'name':item['sname'],
                  'link':'/bastproxy/plugins/%s/%s.html' % (i, item['sname'])})
      pmenu.append('</ul>')
      pmenu.append('</li>')

    return '\n'.join(pmenu)

  def build_index(self, title, pluginmenu, plugininfo, template):
    """
    build the index page
    """
    #testdoc = __doc__

    testdoc = sys.modules['__main__'].__doc__

    about = markdown2.markdown(testdoc,
                               extras=['header-ids', 'fenced-code-blocks',
                                       'wiki-tables'])

    nbody = self.adddivstodoc(about)

    nbody = self.addhclasses(nbody)

    body = self.addtableclasses(nbody)

    ttoc = self.buildtoc(
                    self.gettoc('<body>\n' + '\n'.join(body) + '\n</body>'))

    html = template % {'BODY':'\n'.join(body), 'TOC':ttoc, 'TITLE':title,
                       'PLUGINMENU':pluginmenu, 'PNAME':'Bastproxy'}

    tfile = open(os.path.join(self.api.BASEPATH, 'docsout', 'index.html'), 'w')

    tfile.write(html)

    tfile.close()

  def addelementclass(self, html, element, eclass):
    """
    add a class to an element

    eclass can include the tagname as %(tag)s
    """
    from lxml import etree

    if type(html) == type([]):
      html = '\n'.join(html)

    doc = etree.fromstring('<body>\n' + html + '\n</body>\n')
    for node in doc.xpath(element):
      attrib = node.attrib
      nclass = eclass % {'tag':node.tag}
      if attrib.get('class'):
        attrib['class'] = attrib.get('class') + ' ' + nclass
      else:
        attrib['class'] = nclass

    htmlout = etree.tostring(doc, pretty_print=True)

    htmlout = htmlout.strip()

    html = htmlout.split('\n')

    html.remove('<body>')
    html.remove('</body>')

    return html

  def addhclasses(self, html):
    """
    add classes to headers
    """
    return self.addelementclass(html, '//h1|//h2|//h3|//h4|//h5', 'bp%(tag)s')

  def addtableclasses(self, html):
    """
    add classes to tables
    """
    return self.addelementclass(html, '//table', 'table')

  def gettoc(self, html):
    """
    get the toc from the html headers
    """
    from lxml import etree

    toc = []
    try:
      doc = etree.fromstring(html)
      for node in doc.xpath('//h1|//h2|//h3|//h4|//h5'):
        toc.append((int(node.tag[-1]), node.attrib.get('id'), node.text))
    except:
      self.api.get('send.traceback')('error parsing html')
      print html

    return toc

  def adddivstodoc(self, thtml):
    """
    put divs around headers
    """
    from lxml import etree, html

    oldbody = html.fromstring('<body>\n' + thtml + '\n</body>')
    newbody = html.fromstring('<html>\n</html>')
    activediv = None
    for child in oldbody.iter():
      if child.getparent() == oldbody:
        if child.tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
          if activediv != None:
            newbody.append(activediv)
            activediv = None

          activediv = etree.fromstring('<div class="indent%s"></div>' \
                                                  % child.tag)
          activediv.append(copy.deepcopy(child))

        elif activediv != None:
          activediv.append(copy.deepcopy(child))
        else:
          newbody.append(copy.deepcopy(child))

    if activediv != None:
      newbody.append(activediv)

    htmlout = etree.tostring(newbody, pretty_print=True)

    html = htmlout.split('\n')

    if '<html>' == html[0]:
      html.pop(0)
    while html[-1] == '':
      html.pop()
    lastelem = html.pop()
    lastelem = lastelem.replace('</html>', '')
    if lastelem:
      html.append(lastelem)

    return '\n'.join(html)

  def build_plugin(self, plugin, title, pluginmenu, template):
    """
    build a plugin page
    """

    tlist = plugin['fullimploc'].split('.')
    pdir = tlist[1]

    pmod = self.api.get('plugins.getp')(plugin['modpath'])

    if pmod and self.checknodocs(pmod):
      self.api.get('send.msg')(
                        'skipping %s' % plugin['fullimploc'])
      return

    self.api.get('send.msg')('building %s' % plugin['fullimploc'])

    try:
      testdoc = sys.modules[pmod.fullimploc].__doc__
    except AttributeError:
      self.api.get('send.msg')('Plugin %s is not loaded' % plugin['modpath'])
      return

    wplugin = plugin['fullimploc'].split('.')

    wpluginname = '.'.join(wplugin[1:])

    #testdoc = __doc__

    #testdoc = self.api.get('colors.colortohtml')(testdoc)

    aboutb = markdown2.markdown(testdoc,
                                  extras=['header-ids', 'fenced-code-blocks',
                                          'wiki-tables'])

    aboutb = self.api.get('colors.colortohtml')(aboutb)

    aboutl = []

    aboutl.append('<h2 id="about">About</h2>\n')
    aboutl.append(aboutb)

    about = '\n'.join(aboutl)

    nbody = self.adddivstodoc(about)

    nbody = self.addhclasses(nbody)

    body = self.addtableclasses(nbody)

    cmds = self.api.get('commands.list')(pmod.sname, format=False)

    groups = {}
    for i in sorted(cmds.keys()):
      if i != 'default':
        if not (cmds[i]['group'] in groups):
          groups[cmds[i]['group']] = []

        groups[cmds[i]['group']].append(i)

    cmds = ['<h2 id="commands" class="bph2">Commands</h2>']

    for group in sorted(groups.keys()):
      if group != 'Base':
        cmds.append('<div class="indenth3">')
        cmds.append('<h3 id="cmdgroup%(NAME)s" class="bph3">%(NAME)s</h3>' % {
                    'NAME':group})
        cmds.append('</div>')
        cmds.append('<div class="indenth4">')
        for i in groups[group]:
          cmds.append('<h4 id="cmd%(NAME)s" class="bph4">%(NAME)s</h4>' % {
                    'NAME':i})
          cmds.append('<pre><code>')
          chelp = self.api.get('commands.cmdhelp')(pmod.sname, i)
          chelp = self.api.get('colors.colortohtml')(escape(chelp))
          cmds.extend(chelp.split('\n'))
          cmds.append('</code></pre>')
        cmds.append('</div>')

    cmds.append('<div class="indenth3">')
    cmds.append('<h3 id="cmdgroup%(NAME)s" class="bph3">%(NAME)s</h3>' % {
                'NAME':'Base'})
    cmds.append('</div>')
    cmds.append('<div class="indenth4">')
    for i in groups['Base']:
        cmds.append('<h4 id="cmd%(NAME)s" class="bph4">%(NAME)s</h4>' % {
                  'NAME':i})
        cmds.append('<pre><code>')
        chelp = self.api.get('commands.cmdhelp')(pmod.sname, i)
        chelp = self.api.get('colors.colortohtml')(escape(chelp))
        cmds.extend(chelp.split('\n'))
        cmds.append('</code></pre>')
    cmds.append('</div>')

    body.extend(cmds)

    if len(pmod.settings) > 0:
      settings = ['<h2 id="settings" class="bph2">Settings</h2>']
      settings.append('<div class="indenth4">')
      for i in pmod.settings:
        settings.append('<h3 id="set%(NAME)s" class="bph4">%(NAME)s</h3>' % {
                          'NAME':i})
        settings.append('<pre><code>')
        settings.append('%s' % self.api.get('colors.colortohtml')(
          escape(pmod.settings[i]['help'])))
        settings.append('</code></pre>')

      settings.append('</div>')

      body.extend(settings)

    papis = self.api.get('api.getchildren')(pmod.sname)

    if len(papis) > 0:
      apis = ['<h2 id="api" class="bph2">API</h2>']
      apis.append('<div class="indenth4">')

      for i in papis:
        apis.append('<h3 id="set%(NAME)s" class="bph4">%(NAME)s</h3>' % {
                          'NAME':i})
        apis.append('<pre><code>')
        tapi = '\n'.join(self.api.get('api.detail')('%s.%s' % (pmod.sname, i)))
        tapi = self.api.get('colors.colortohtml')(escape(tapi))
        apis.extend(tapi.split('\n'))
        apis.append('</code></pre>')

      apis.append('</div>')

      body.extend(apis)

    testt = self.gettoc('<body>\n' + '\n'.join(body) + '\n</body>')

    ttoc = self.buildtoc(testt)

    html = template % {'BODY':'\n'.join(body), 'TOC':ttoc, 'TITLE':title,
                       'PLUGINMENU':pluginmenu, 'PNAME':wpluginname}

    outdir = os.path.join(self.api.BASEPATH, 'docsout', 'plugins', pdir)

    try:
      os.makedirs(outdir)
    except OSError:
      pass

    tfile = open(os.path.join(self.api.BASEPATH,
                              outdir, '%s.html'% pmod.sname),
                              'w')

    tfile.write(html)

    tfile.close()

  def copy_css(self):
    """
    copy the css files into the output directory
    """
    outpath = os.path.join(self.api.BASEPATH, 'docsout')

    csssrc = os.path.join(self.pluginlocation, 'css')
    cssdst = os.path.join(outpath, 'css')

    dir_util.copy_tree(csssrc, cssdst)

  def copy_favicon(self):
    """
    copy the favicon files into the output directory
    """
    outpath = os.path.join(self.api.BASEPATH, 'docsout')

    favsrc = os.path.join(self.pluginlocation, 'favicon')
    favdst = os.path.join(outpath, 'favicon')

    dir_util.copy_tree(favsrc, favdst)

  def cmd_build(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
    detail a function in the api
      @CUsage@w: detail @Y<api>@w
      @Yapi@w = (optional) the api to detail
    """
    import linecache
    linecache.clearcache()

    temppath = os.path.join(self.pluginlocation, 'templates',
                                          'template-dark.html')
    plugininfo = self.api.get('plugins.allplugininfo')()

    with open(temppath, 'r') as content_file:
      template = content_file.read()

    pmenu = self.buildpluginmenu(plugininfo)

    title = 'Bastproxy'

    self.build_index(title, pmenu, plugininfo, template)

    for i in plugininfo:
      self.build_plugin(plugininfo[i], title, pmenu, template)

    outpath = os.path.join(self.api.BASEPATH, 'docsout')

    self.copy_css()
    self.copy_favicon()

    return True, ['Docs built', 'Directory: %s' % outpath]

