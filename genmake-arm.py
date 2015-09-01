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

import argparse
import pdscparser as PP
import sys
import tempfile as TMP
import os.path
import shutil

aparser = argparse.ArgumentParser(description='Generate Makefile fragment for Atmel Devices.')
aparser.add_argument('-f', metavar='<pdsc file>', help="PDSC file", required="True")
aparser.add_argument('-d', metavar='<devicename>', help="Device name E.g. ATSAMD20E14 or ATSAM4C4C:0 (for special device names refer Pname attribute of processor tag in pdsc file)", required="True")
aparser.add_argument('-c', metavar='<cmsis pack dir>', help="CMSIS pack directory", required="True")
aparser.add_argument('--copy-config-files', help="Copy config files (startup_*.c, system_*.c and linker script)", action='store_true')

makefileHeaderText = """
#
# Makefile for %s project of Atmel %s device
#

ifdef SystemRoot
      SHELL = cmd.exe
      MKDIR = mkdir
else
   ifeq ($(shell uname), Linux)
    MKDIR = mkdir -p
   endif
endif

CC=arm-none-eabi-gcc
CXX=arm-none-eabi-g++
OBJCOPY=arm-none-eabi-objcopy
OBJDUMP=arm-none-eabi-objdump
SIZE=arm-none-eabi-size

OUTPUT_FILE=%s
OUTPUT_FILE_NAME=$(basename $(OUTPUT_FILE))

"""

asflags="""ASFLAGS=-m%s -mcpu=%s -D%s -O1 -ffunction-sections -Wall
"""
cflags="""CFLAGS=-x c -m%s -mcpu=%s -D%s -O1 -ffunction-sections -Wall -c -std=gnu99
"""
cxxflags="""CXXFLAGS=-x c++ -m%s -mcpu=%s -D%s -O1 -ffunction-sections -Wall -c -std=g++99
"""
ldflags="""LDFLAGS=-Wl,--start-group -lm  -Wl,--end-group -Wl,--gc-sections -m%s -mcpu=%s %s %s
"""
incpaths="""INCLUDE_PATHS=%s
"""
srcfileTemplate="""
SRCS = %s
"""
objfileTemplate="""
OBJS = %s
"""
bldTemplate="""
# All target
all: $(OUTPUT_FILE)

# Link target
$(OUTPUT_FILE): $(OBJS)
\t$(CC) -o $(OUTPUT_FILE) $(LDFLAGS) $(OBJS)
\t$(OBJCOPY) -O binary $(OUTPUT_FILE_NAME).elf $(OUTPUT_FILE_NAME).bin
\t$(OBJCOPY) -O ihex -R .eeprom -R .fuse -R .lock -R .signature  $(OUTPUT_FILE_NAME).elf $(OUTPUT_FILE_NAME).hex
\t$(OBJDUMP) -h -S $(OUTPUT_FILE_NAME).elf > $(OUTPUT_FILE_NAME).lss
\t$(SIZE) $(OUTPUT_FILE_NAME).elf

# Compile target(s)
./%.o: ./%.cpp
\t$(CXX) $(CXXFLAGS) $(INCLUDE_PATHS) -o $@ $<

./%.o: ./%.c
\t$(CC) $(CFLAGS) $(INCLUDE_PATHS) -o $@ $<

startup/%.o: startup/%.c
\t$(CC) $(CFLAGS) $(INCLUDE_PATHS) -o $@ $<

clean:
\trm -f $(OBJS)
\trm -f $(OUTPUT_FILE_NAME).elf $(OUTPUT_FILE_NAME).bin $(OUTPUT_FILE_NAME).hex $(OUTPUT_FILE_NAME).lss

"""

def createMakefile(device, lang, dep):
  try:
    pdir = TMP.gettempdir()
    makefile = pdir+'/Makefile'
    mfo = open(makefile,'w+')
    if mfo is None:
      print ('Could not open make file %s' %(makefile))
      sys.exit(2)

    output_filename = device.replace(':','_')
    mfo.write(makefileHeaderText %(lang, device, output_filename.lower()+'-application.elf'))

    templatefile = dep['template'] if 'template' in dep else ''
    systemfile = dep['system'] if 'system' in dep else ''
    startupfile = dep['startup'] if 'startup' in dep else ''
    ldscript = dep['linkerscript'] if 'linkerscript' in dep else ''
    other_configs = dep['other'] if 'other' in dep else ''

    srcfiles = ''
    objfiles = ''
    if copycfg and templatefile != '':
      shutil.copy2(templatefile, './')
      templatefile = os.path.basename(templatefile)
      srcfiles = srcfiles + ' ' + templatefile + ' '
      objfiles = objfiles + ' ' + os.path.basename(templatefile).replace(lang, 'o') + ' '

    if copycfg and systemfile != '':
      shutil.copy2(systemfile, './')
      systemfile = os.path.basename(systemfile)
      srcfiles = srcfiles + ' ' + systemfile + ' '
      objfiles = objfiles + ' ' + os.path.basename(systemfile).replace('.c', '.o') + ' '

    if copycfg and startupfile != '':
      shutil.copy2(startupfile, './')
      startupfile = os.path.basename(startupfile)
      srcfiles = srcfiles + ' ' + startupfile + ' '
      objfiles = objfiles + ' ' + os.path.basename(startupfile).replace('.c', '.o') + ' '

    ldscript_option = ''
    if copycfg and ldscript != '':
      shutil.copy2(ldscript, './')
      ldscript_option = '-T'+os.path.basename(ldscript)

      for f in other_configs:
        shutil.copy2(f, './')

    inc_options = "-I"+dep['include']
    if 'cmsis_include' in dep:
      inc_options = inc_options + " -I"+dep['cmsis_include']
    mfo.write(incpaths %(inc_options))

    mfo.write(asflags %(dep['mode'], dep['cpu'], dep['define']))
    mfo.write(cflags %(dep['mode'], dep['cpu'], dep['define']))
    mfo.write(cxxflags %(dep['mode'], dep['cpu'], dep['define']))

    lib_options = ""
    if 'cmsis_lib' in dep:
      lib_options = "-L %s" %(dep['cmsis_lib'])

    mfo.write(ldflags %(dep['mode'], dep['cpu'], ldscript_option, lib_options))
    mfo.write(srcfileTemplate %(srcfiles.strip()))
    mfo.write(objfileTemplate %(objfiles.strip()))
    mfo.write(bldTemplate)
    mfo.close()
    mkname = output_filename.lower() + '_Makefile'
    shutil.move(makefile, './' + mkname)
    print ('Makefile generated (%s).' %(os.path.abspath(mkname)))

  except Exception as inst:
    print ("create makefile: %s:%s" %(type(inst), inst))
    sys.exit(2)

#args = vars(aparser.parse_args())
#print (args)
pargs = aparser.parse_args()
pdscfile = pargs.f
devicename = pargs.d
cmsis_packdir = pargs.c
copycfg = False
if pargs.copy_config_files:
  copycfg = True

# process cmsis_packdir
if False == os.path.exists(cmsis_packdir):
  print ('cmsis pack directory \'%s\' doesn\'t exist' %(cmsis_packdir))
  sys.exit(2)

cmsis_packdir = os.path.abspath(cmsis_packdir)


print ("#pdscfile: %s ## cmsis_packdir: %s" %(pdscfile, cmsis_packdir))

pparser = PP.pdscparser (pdscfile)
pparser.logmsg = True

#Test 1
devices = pparser.getDevices()
print ('~~~~~~~~~~~~~~~~~~~~~')
print ('List of devices: %s' %(devices))
print ('~~~~~~~~~~~~~~~~~~~~~')
#Test 2
#print (pparser.getEnvironments(devicename))

#Test 3
#print (pparser.getDeviceSpecifics(devicename))

#Test 4
#for l in ('c', 'cpp', 'java'):
#  for e in ('exe', 'lib', 'nop'):
#    print ('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
#    dependencies = pparser.getGCCProjectDependencies(devicename, l, e, 'atmel')
#    print ('Dependencies: ')
#    if dependencies is None:
#      continue
#    for f,value in dependencies.items():
#      print ('==> %s : %s' %(f, value))
#
#print ('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
#print (pparser.getGCCProjectDependencies(devicename, 'java', 'exe', 'atmel'))
#print ('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
#print (pparser.getGCCProjectDependencies(devicename, 'C', 'lib', 'atmel'))
#print ('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
#print (pparser.getGCCProjectDependencies(devicename, 'C', 'exe', 'atme'))
#print ('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')

dependencies = pparser.getGCCProjectDependencies(devicename, 'c', 'exe', 'atmel')

#cmsis_pack_dir = os.path.dirname(os.path.abspath(self._cmsis_pdscfile))
#self._log('cmsis pack dir: %s' %(cmsis_pack_dir))
assert(True == os.path.isdir(cmsis_packdir))
cmsis_inc_dir = cmsis_packdir+'/CMSIS/Include'
cmsis_lib_dir = cmsis_packdir+'/CMSIS/Lib/GCC'

if False == os.path.isdir(cmsis_inc_dir):
  print ('Warning: CMSIS include directory "%s" not found.' %(cmsis_inc_dir))
else:
  dependencies['cmsis_include'] = cmsis_inc_dir

if False == os.path.isdir(cmsis_lib_dir):
  print ('Warning: CMSIS lib directory "%s" not found.' %(cmsis_lib_dir))
else:
  dependencies['cmsis_lib'] = cmsis_lib_dir

createMakefile (devicename, 'c', dependencies)

