##############################################################################
# 
# Copyright (C) 2015 Atmel Corporation
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
# 
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in
#   the documentation and/or other materials provided with the
#   distribution.
# 
# * Neither the name of the copyright holders nor the names of
#   contributors may be used to endorse or promote products derived
#   from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
##############################################################################

import sys
import xml.etree.ElementTree as ET
import argparse
import os.path

class pdscparser(object):
  #def __init__(self, pdscfile, cmsis_pdscfile):
  def __init__(self, pdscfile):
    try:
      self.logmsg = False
      self._supportedSchemaVersions = ['1.3']
      self._supportedExtensions = {'atmel':'http://www.atmel.com/schemas/pack-device-atmel-extension'}

      # process pdscfile
      if False == os.path.isfile(pdscfile):
        self._err(pdscfile + ' is not a valid file')
      self._pdscfile = os.path.abspath(pdscfile)
      self._packdir = os.path.dirname(self._pdscfile)

      # parse pdscfile
      tree = ET.parse(self._pdscfile)
      self._root = tree.getroot()

      # check supported schema
      schemaVer = self._root.attrib.get('schemaVersion')
      if schemaVer not in self._supportedSchemaVersions:
        self._err('Supports only schema version %s' %(self._supportedSchemaVersions))
      self._log('verified schema version')

      # get list of releases
      self._releases = self._getReleases()

      # parse list of devices
      self._devices = self._getDevices()

    except Exception as inst:
      self._err("initialization: %s:%s" %(type(inst), inst))

  # get list of releases
  def getReleases(self):
    return self._releases

  # worker function to get list of releases
  def _getReleases(self):
    try:
      _releases = []
      lreleases = self._root.findall('releases/release')
      for lrelease in lreleases:
        _releases.append({'version':lrelease.attrib.get('version'),
                          'date':lrelease.attrib.get('date'),
                          'description':lrelease.text.strip()})

      return _releases

    except Exception as inst:
      self._err('get releases: %s:%s' %(type(inst), inst))

  # get list of devices
  def getDevices(self):
    return self._devices

  # worker function to find the list of devices
  def _getDevices(self):
    try:

      devicesTag = self._root.findall('devices/family/device')

      _devices = []

      for devTag in devicesTag:
        devname = devTag.attrib.get('Dname')
        processors = devTag.findall('processor')
        pname = []
        for p in processors:
          pname.append(p.attrib.get('Pname'))

        for pn in pname:
          if pn is not None:
            _devices.append(devname + ':' + pn)
          else:
            _devices.append(devname)

      return _devices

    except Exception as inst:
      self._err("getDevices: %s:%s" %(type(inst), inst))

  def _splitDeviceName(self, ldevicename):
    justdevicename = ldevicename
    pname = ''
    if ldevicename.find(':') != -1:
      justdevicename = ldevicename[:-(len(ldevicename)-(ldevicename.find(':')))]
      pname = ldevicename[-(len(ldevicename)-(ldevicename.find(':'))-1):]
    return {'device':justdevicename,'pname':pname}
     
  def getEnvironments(self, devicename):
    try:
      if devicename not in self.getDevices():
        self._err('Device %s not found' %(devicename))

      device_split = self._splitDeviceName(devicename)
      deviceTag = self._root.find('devices/family/device[@Dname="%s"]' %(device_split['device']))

      envs = deviceTag.findall('environment')
      _environments = []
      for env in envs:
        _environments.append(env.attrib.get('name'))

      return _environments

    except Exception as inst:
      self._err("getEnvironments: %s:%s" %(type(inst), inst))

  def _getDeviceTag(self, ldevicename):
    try:
      if ldevicename not in self.getDevices():
        self._err('Device "%s" not found' %(ldevicename))
      device_split = self._splitDeviceName(ldevicename)
      self._log('Device: %s Pname: %s' %(device_split['device'], device_split['pname']))

      ldeviceTag = self._root.find('devices/family/device[@Dname="%s"]' %(device_split['device']))
      assert(ldeviceTag is not None)
      return ldeviceTag

    except Exception as inst:
      self._err("getDeviceTag: %s:%s" %(type(inst), inst))

  def getDeviceSpecifics(self, ldevicename):
    try:
      deviceTag = _getDeviceTag(ldevicename)
      device_split = self._splitDeviceName(ldevicename)
      just_device_name = device_split['device']
      pname = device_split['pname']
      self._log('Device: %s Pname: %s' %(just_device_name, pname))
      device_specifics = {}
      if pname != '':
        compileTags = deviceTag.findall('compile[@Pname="%s"]' %(pname))
        debugTags = deviceTag.findall('debug[@Pname="%s"]' %(pname))
      else:
        compileTags = deviceTag.findall('compile')
        debugTags = deviceTag.findall('debug')

      if compileTags is not None:
        for compileTag in compileTags:
          device_specifics['header'] = compileTag.attrib.get('header')
          device_specifics['define'] = compileTag.attrib.get('define')

      if debugTags is not None:
        for debugTag in debugTags:
          device_specifics['svd'] = debugTag.attrib.get('svd')
            
      return device_specifics

    except Exception as inst:
      self._err("getDeviceSpecifics: %s:%s" %(type(inst), inst))

  def _getEnvExtension(self, devTag, lextn):
    try:
      env = devTag.find('environment[@name="%s"]' %(lextn))
      if env is None:
        self._err('Environment extension "%s" is not found.' %(lextn))
      return env

    except Exception as inst:
      self._err("getEnvExtension: %s:%s" %(type(inst), inst))

  def getGCCProjectDependencies(self, devicename, lang, exe, eextn):
    try:
      self._log('Find GCC project dependencies')
      deviceTag = self._getDeviceTag(devicename)
      lang = lang.lower()
      exe = exe.lower()
      if exe not in ('exe', 'lib'):
        self._warn('Incorrect project configuration "%s"' %(exe))
        return None

      self._log('device: %s lang: %s exe: %s' %(devicename, lang, exe))

      if eextn in self._supportedExtensions:
        namespace = {'at':self._supportedExtensions[eextn]}
      else:
        self._warn('Extension "%s" is not supported by the parser' %(eextn))
        return None

      assert namespace != ''
      envextn = self._getEnvExtension(deviceTag, eextn)

      device_split = self._splitDeviceName(devicename)
      just_device_name = device_split['device']
      pname = device_split['pname']
      if pname == '':
        projs = envextn.findall('at:extension/at:project', namespace)
      else:
        projs = envextn.findall('at:extension/at:project[@Pname="%s"]' %(pname), namespace)
      if projs is None:
        self._warn('Project not found for device %s' %(devicename))
        return None
      langstr = ' '+lang+' '
      found = False
      for proj in projs:
        if langstr not in proj.attrib.get('name').lower():
          continue
        found = True
        break

      if found == False:
        self._warn('Could not find \'%s\' project in pdsc file.' %(lang))
        return None

      dependencies = {}

      dependencies['mode'] = 'thumb'
      dependencies['other'] = []

      if pname == '':
        dependencies['define'] = deviceTag.find('compile').attrib.get('define')
        dependencies['cpu'] = deviceTag.find('processor').attrib.get('Dcore').replace('+', 'plus')
      else:
        dependencies['define'] = deviceTag.find('compile[@Pname="%s"]' %(pname)).attrib.get('define')
        dependencies['cpu'] = deviceTag.find('processor[@Pname="%s"]' %(pname)).attrib.get('Dcore').replace('+', 'plus')

      prcompTag = proj.findall('at:component', namespace)
      for prcomp in prcompTag:
        files_dict = {}
        component = self._root.find('components/component[@Cvendor="%s"][@Cclass="%s"][@Cgroup="%s"][@condition="%s"]' 
                   %(prcomp.attrib.get('Cvendor'), prcomp.attrib.get('Cclass'), prcomp.attrib.get('Cgroup'), devicename))

        if component is None:
          continue

        filesTag = component.findall('files/file')
        for f in filesTag:
          condition = f.attrib.get('condition').lower()
          category = f.attrib.get('category').lower()
          name = f.attrib.get('name')
          name_abspath = self._packdir + '/' + name
          #print ('%s:%s:%s' %(condition, category, name))

          if condition == 'c' and category == 'include':
            if False == os.path.isdir(name_abspath):
              self._err('Could not find include directory "%s"' %(name_abspath))
            dependencies['include'] = name_abspath

          elif condition == 'c' and category == 'header':
            if False == os.path.isfile(name_abspath):
              self._err('Could not find header file "%s"' %(name_abspath))
            dependencies['header'] = name_abspath

          elif condition == 'c exe' and lang == 'c' and exe == 'exe' and name.rstrip().endswith('main.c'):
            if False == os.path.isfile(name_abspath):
              self._err('Could not find template file "%s"' %(name_abspath))
            dependencies['template'] = name_abspath

          elif condition == 'c exe' and lang == 'cpp' and exe == 'exe' and name.rstrip().endswith('main.cpp'):
            if False == os.path.isfile(name_abspath):
              self._err('Could not find template file "%s"' %(name_abspath))
            dependencies['template'] = name_abspath

          elif condition == 'c lib' and lang == 'c' and exe == 'lib' and name.rstrip().endswith('library.c'):
            if False == os.path.isfile(name_abspath):
              self._err('Could not find template file "%s"' %(name_abspath))
            dependencies['template'] = name_abspath

          elif condition == 'c lib' and lang == 'cpp' and exe == 'lib' and name.rstrip().endswith('library.cpp'):
            if False == os.path.isfile(name_abspath):
              self._err('Could not find template file "%s"' %(name_abspath))
            dependencies['template'] = name_abspath

          elif condition == 'gcc exe' and category == 'linkerscript':
            if False == os.path.isfile(name_abspath):
              self._err('Could not find linker script "%s"' %(name_abspath))
            dependencies['linkerscript'] = name_abspath

          elif condition == 'gcc exe' and category == 'source' and ('system_' in name):
            if False == os.path.isfile(name_abspath):
              self._err('Could not find system file "%s"' %(name_abspath))
            dependencies['system'] = name_abspath

          elif condition == 'gcc exe' and category == 'source' and ('startup_' in name):
            if False == os.path.isfile(name_abspath):
              self._err('Could not find startup file "%s"' %(name_abspath))
            dependencies['startup'] = name_abspath

          # dual core devices uses nested linker scripts that is listed in other category
          elif condition == 'gcc exe' and category == 'other':
            if False == os.path.isfile(name_abspath):
              self._err('Could not find other config file "%s"' %(name_abspath))
            dependencies['other'].append(name_abspath)

      return dependencies

    except Exception as inst:
      self._err("getGCCProjectDependencies: %s:%s" %(type(inst), inst))

  def _log(self, lmsg):
    if self.logmsg == False:
      return
    print ('==> %s' %(lmsg))

  def _msg(self, message):
    print (message)

  def _err(self, emsg):
    print ("Error: %s" %(emsg))
    sys.exit(2)

  def _warn(self, wmsg):
    print ("Warning: %s" %(wmsg))

