#!/usr/bin/python3

#
# The MIT License (MIT)
#
# Copyright (c) 2024 Michael J. Wouters
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

# [2024 280] [2024 10 6]
# ./runginan.py -d --config  ./runginan.yaml 60589

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import time
import yaml

# This is where ottplib is installed
sys.path.append("/usr/local/lib/python3.8/site-packages")  # Ubuntu 20.04
sys.path.append("/usr/local/lib/python3.10/site-packages") # Ubuntu 22.04

try: 
	import ottplib as ottp
except ImportError:
	sys.exit('ERROR: Must install ottplib\n eg openttp/software/system/installsys.py -i ottplib')

try: 
	import rinexlib as rinex
except ImportError:
	sys.exit('ERROR: Must install rinexlib\n eg openttp/software/system/installsys.py -i rinexlib')
	
VERSION = '0.1.0'
AUTHORS = 'Michael Wouters'
RAPID_LATENCY = 2    # Latency of rapid orbit products 
PEA = '/usr/local/bin/pea'
PPP_TEMPLATE = 'ppp_template.yaml'
EDITRNXOBS = '/usr/local/bin/editrnxobs.py'

# ------------------------------------------
def ErrorExit(msg):
	sys.stderr.write('Error! '+ msg+'\n')
	sys.exit(1)

# ------------------------------------------
def MJDtoIGSProductName(mjd,template):
	
	fname = ''
	t    = (mjd-40587)*86400.0
	tod  = time.gmtime(t)
	yyyy = tod.tm_year
	yy   = tod.tm_year - int(tod.tm_year/100)*100
	doy  = tod.tm_yday
	
	# See the format spec!
	m = re.match('(\w{10})_YYYYDDD(\d{4})_(\w{3})_(\w{3})_(\w{3})\.(sp3|SP3|BIA|bia|CLK|clk)',template)
	if m:
		fname='{}_{:04d}{:03d}{}_{}_{}_{}.{}'.format(m.group(1),yyyy,doy,m.group(2),m.group(3),m.group(4),m.group(5),m.group(6))
		return fname

	return fname

# ------------------------------------------
def PrependPeaRoot(peaRoot,path):
	ret = path
	if re.match('<ROOT>/',path):
		return os.path.join(peaRoot,path.replace('<ROOT>/','',1))# note that the '/' is needed otherwise the result is treated as an absolute path
	elif re.match('<ROOT>',path):
		return os.path.join(peaRoot,path.replace('<ROOT>','',1))
	return path

# ------------------------------------------
def EditCfgData(cfg):
	if type(cfg)==str:
		cfg = PrependPeaRoot(peaRoot,cfg)
		if '<STATION>' in cfg:
			cfg = cfg.replace('<STATION>',station,1)
		if '<RUNDIR>' in cfg:
			cfg = cfg.replace('<RUNDIR>',runDir,1)
	elif type(cfg)==list:
		for i in range(0,len(cfg)):
			if type(cfg[i]) == str:
				cfg[i]=PrependPeaRoot(peaRoot,cfg[i])
				if '<STATION>' in cfg[i]:
					cfg[i] = cfg[i].replace('<STATION>',station,1)
				if '<RUNDIR>' in cfg[i]:
					cfg[i] = cfg[i].replace('<RUNDIR>',runDir,1)
	return cfg

# ------------------------------------------
def EditCfg(cfg):
	for c in cfg:
		if type(cfg[c]) == dict:
			cfg[c] = EditCfg(cfg[c]) # ooh recursion
		else:
			cfg[c] = EditCfgData(cfg[c])
	return cfg

# ------------------------------------------
def ScrubDir(theDir):
	if not(args.debug):
		ottp.Debug(f'Cleaning {theDir}')
		files = glob.glob(os.path.join(theDir,'*'))
		for f in files:
			if os.path.isfile(f):
				os.unlink(f)
		
# --------------------------------------------------------------------------------------------------------

home = os.environ['HOME'] 
root = home 
configFile = os.path.join(root,'etc','runginan.yaml')

peaRoot = './'
peaExec = 'pea'

pppTemplate = PPP_TEMPLATE

station = 'AU00'
editRnxObs = EDITRNXOBS
exclusions = 'CREIJS' # GNSS to remove from RINEX before processing

parser = argparse.ArgumentParser(description='')

examples =  'Usage examples\n'

parser = argparse.ArgumentParser(description='Generate a station clock solution using Ginan PPP',
	formatter_class=argparse.RawDescriptionHelpFormatter,epilog=examples)

parser.add_argument('mjd',nargs = '*',help='first MJD [last MJD]')
parser.add_argument('--daily',help='generate daily files',action='store_true')
parser.add_argument('--config','-c',help='use an alternate configuration file',default=configFile)
parser.add_argument('--debug','-d',help='debug (to stderr)',action='store_true')
parser.add_argument('--version','-v',action='version',version = os.path.basename(sys.argv[0])+ ' ' + VERSION + '\n' + 'Written by ' + AUTHORS)

args = parser.parse_args()

debug = args.debug
ottp.SetDebugging(debug)
rinex.SetDebugging(debug)
rinex.SetHatanakaTools('crx2rnx','rnx2crx')

ottp.Debug('Using ottplib v{}'.format(ottp.LibVersion()))
ottp.Debug('Using rinexlib v{}'.format(rinex.LibVersion()))

configFile = args.config

try:
	fin = open(configFile, 'r')
except:
	ErrorExit('Unable to open ' + configFile)
cfg = yaml.safe_load(fin) # only need to load the template once
fin.close()

if 'exec' in cfg['pea']:
	peaExec = cfg['pea']['exec']

if 'root' in cfg['pea']:
	peaRoot = cfg['pea']['root'] # need this for replacements
	
if 'station' in cfg['pea']:
	station = cfg['pea']['station'] # need this for replacements
	
cfg = EditCfg(cfg) # make substitutions

runDir = cfg['pea']['run_dir']
if not os.path.isdir(runDir):
	os.mkdir(runDir)
tmpDir = os.path.join(runDir,'tmp') # give each run its own temporary directory
if not os.path.isdir(tmpDir):
	os.mkdir(tmpDir)
	
satDataSrcDir  = cfg['inputs']['satellite_data']['src_dir']
outputClockDir = cfg['outputs']['clocks']['directory']
srcDir = cfg['inputs']['gnss_observations']['rnx_src_dir']
pppTemplate = cfg['pea']['ppp_template']

# Automatic calculation 
mjdToday = ottp.MJD(time.time())
startMJD = mjdToday - RAPID_LATENCY
stopMJD  = startMJD
# startMJD = weeklyStart + int((mjdToday - weeklyStart)/7 - 1 )*7 - RAPID_LATENCY
# stopMJD  = startMJD + 6 # maximum of 7 days data
ottp.Debug('Default  MJD range: {} {}'.format(startMJD,stopMJD))

if (args.mjd): # specifying MJD overrides the automatic calculation
	
	if 1 == len(args.mjd): # one day only
		startMJD = int(args.mjd[0])
		stopMJD  = startMJD
	elif ( 2 == len(args.mjd)): # a range
		startMJD = int(args.mjd[0])
		stopMJD  = int(args.mjd[1])
		if (stopMJD < startMJD):
			ottp.ErrorExit('Stop MJD is before start MJD')
	else:
		ottp.ErrorExit('Too many MJDs')
ottp.Debug('Processing  MJD range: {} {}'.format(startMJD,stopMJD))

rnxStation = cfg['inputs']['gnss_observations']['rnx_station']
rnxStation4Letter = rnxStation[0:4]

clkTemplate = cfg['inputs']['satellite_data']['clk_template']
bsxTemplate = cfg['inputs']['satellite_data']['bsx_template']
sp3Template = cfg['inputs']['satellite_data']['sp3_template']

try:
	ottp.Debug('Loading ' + pppTemplate)
	fin = open(pppTemplate, 'r')
except:
	ErrorExit('Unable to open ' + pppTemplate)
	
gCfg = yaml.safe_load(fin) # only need to load the template once
fin.close()

gCfg = EditCfg(gCfg)

gCfg['receiver_options'][rnxStation4Letter] = {}
gCfg['receiver_options'][rnxStation4Letter]['receiver_type']    = cfg['receiver_options']['receiver_type']
gCfg['receiver_options'][rnxStation4Letter]['antenna_type']     = cfg['receiver_options']['antenna_type']
gCfg['receiver_options'][rnxStation4Letter]['apriori_position'] = cfg['receiver_options']['apriori_position']
	
dstDir = gCfg['inputs']['gnss_observations']['gnss_observations_root']
if not os.path.isdir(dstDir): # will just be runDir anyway
	os.mkdir(dstDir)
	
stationID = cfg['pea']['station']
clkFileTemplate = gCfg['outputs']['clocks']['filename'] # save this, because it will be repeatedly modified

satData = [['clk_files',clkTemplate,''],['bsx_files',bsxTemplate,''],['sp3_files',sp3Template,'']]

if args.daily:
	for mjd in range(startMJD,stopMJD+1):
		
		ScrubDir(runDir)
		ScrubDir(tmpDir)
		
		(yyyy,doy,mon) = ottp.MJDtoYYYYDOY(mjd)
		yy = yyyy % 100
		
		ottp.Debug(f'Processing MJD={mjd} yyyy={yyyy} doy={doy}')
		
		# Do any necessary preprocessing of the station observation files, including decompression
		# First, find the file
		
		(baseObsPath, compressionExt) = rinex.FindObservationFile(srcDir,rnxStation,yyyy,doy,3,True)
		obsPath = baseObsPath + compressionExt # note that compression extensions are .gz and .Z, not .crx 
		obsBaseName = os.path.basename(obsPath)
		
		# editrnxobs.py will decompress for us but then helpfully (and unnecessarily) recompress it
		# So give it a decompressed file, which it will leave as is
		#
		# Copy the RINEX file to the temporary directory
		# This is because we might be using files from another user's directory where
		# we don't have permission to decompress in place 
		# (and this use case is not supported by editrnxobs.py at present either)
			
		shutil.copy(obsPath,tmpDir)
		obsDecompressedPath,algo = rinex.Decompress(os.path.join(tmpDir,obsBaseName)) # this will be deleted so no need to save details for recompression
		obsDecompressedBaseName = os.path.basename(obsDecompressedPath)
		
		ottp.Debug('Running ' + editRnxObs)
		try:
			cmdargs = [editRnxObs,'--tmpdir',tmpDir,'--excludegnss',exclusions,'--output',dstDir,obsDecompressedPath]
			# print(cmdargs) # FIXME useful when debugging
			x = subprocess.check_output(cmdargs) 
		except Exception as e:
			print(e)
			ottp.ErrorExit('Failed to run ' + editRnxObs)
		
		ginanInputRINEX = os.path.join(dstDir,obsDecompressedBaseName)
		if not(os.path.exists(ginanInputRINEX)): # hmmm no output
			ottp.Debug(f'Expected {ginanInputRINEX} - not found!')
			continue # not fatal
		
		# Customize the Ginan config after finding the file because we need the decompressed base name
		# and write it out
		gCfg['inputs']['gnss_observations']['rnx_inputs'] = [obsDecompressedBaseName] # pea grumbles if this is not a list, so give it a list
		
		for sd in satData:
			dstDir = os.path.dirname(gCfg['inputs']['satellite_data'][sd[0]][0]) # destination directory
			fileName = MJDtoIGSProductName(mjd,sd[1])
			gCfg['inputs']['satellite_data'][sd[0]] = [os.path.join(dstDir,fileName)]
			# lazy find
			files = glob.glob(os.path.join(satDataSrcDir,fileName)+'*')
			if files:
				shutil.copy(files[0],dstDir)
				rinex.Decompress(os.path.join(dstDir,os.path.basename(files[0])))
			else:
				pass # FIXME what do we do

		clkFile = clkFileTemplate
		if 'YYDDD' in clkFile:
			clkFile = clkFile.replace('YYDDD',f'{yy:02d}{doy:03d}',1)
			gCfg['outputs']['clocks']['filename']  =  clkFile
		elif 'DDD0.YY' in clkFile:
			clkFile = clkFile.replace('DDD0.YY',f'{doy:03d}{yy:02d}',1)
			gCfg['outputs']['clocks']['filename']  =  clkFile
		
		# FIXME unlink this always ?
		gCfgOut = os.path.join(runDir,'pppclk.yaml')
		try:
			fout = open(gCfgOut, 'w')
		except:
			ErrorExit('Unable to open ' + gCfgOut)
			
		yaml.safe_dump(gCfg, fout, sort_keys = False) # We preserve the input order. Note that comments are stripped
		
		# Run 'pea'
		ottp.Debug('Running pea')
		tstart = time.time()
		try:
			cmdargs = [peaExec,'-y',gCfgOut]
			subprocess.check_output(cmdargs) 
		except Exception as e:
			print(e)
			ottp.ErrorExit('Failed to run ' + peaExec)
		tstop = time.time()
		ottp.Debug('..done')
		ottp.Debug('Job run time = {:g} s'.format(tstop-tstart))
		
		# Collect the output, namely the smoothed clock file
		# Ginan appears to put _smoothed before the extension
		base,ext = os.path.splitext(clkFile)
		clkPath = os.path.join(gCfg['outputs']['clocks']['directory'],f'{base}_smoothed{ext}')
		shutil.copy(clkPath,os.path.join(outputClockDir,clkFile))
		ottp.Debug(f'CLK file in {outputClockDir}/{clkFile}')
				
else: # output a single CLK file
	
	# This all could be done inside the loop for 'daily', but it's easier to followif we don't do that
	ScrubDir(runDir)
	ScrubDir(tmpDir)
	
	gCfg['inputs']['gnss_observations']['rnx_inputs'] = []
	
	for i in range(0,len(satData)):
		satData[i][2] = os.path.dirname(gCfg['inputs']['satellite_data'][satData[i][0]][0]) # save the directory name 
		gCfg['inputs']['satellite_data'][satData[i][0]]=[] # and then zero it out
	
	for mjd in range(startMJD,stopMJD+1):
		
		(yyyy,doy,mon) = ottp.MJDtoYYYYDOY(mjd)
		yy = yyyy % 100
		
		(baseObsPath, compressionExt) = rinex.FindObservationFile(srcDir,rnxStation,yyyy,doy,3,True)
		obsPath = baseObsPath + compressionExt # note that compression extensions are .gz and .Z, not .crx 
		obsBaseName = os.path.basename(obsPath)
		
		shutil.copy(obsPath,tmpDir)
		obsDecompressedPath,algo = rinex.Decompress(os.path.join(tmpDir,obsBaseName)) # this will be deleted so no need to save details for recompression
		obsDecompressedBaseName = os.path.basename(obsDecompressedPath)
		if (mjd==startMJD):
			firstFile = obsDecompressedPath
			dstRnx = obsDecompressedBaseName
		if (mjd==stopMJD):
			lastFile  = obsDecompressedPath
			
		for sd in satData:
			dstDir = sd[2] # destination directory, wot we saved
			fileName = MJDtoIGSProductName(mjd,sd[1])
			gCfg['inputs']['satellite_data'][sd[0]].append(os.path.join(dstDir,fileName))
			# lazy find
			files = glob.glob(os.path.join(satDataSrcDir,fileName)+'*')
			if files:
				shutil.copy(files[0],dstDir)
				rinex.Decompress(os.path.join(dstDir,os.path.basename(files[0])))
			else:
				pass # FIXME what do we do

	ottp.Debug('Running ' + editRnxObs)
	ginanInputRINEX = os.path.join(dstDir,dstRnx)
	try:
		cmdargs = [editRnxObs,'--catenate','--tmpdir',tmpDir,'--excludegnss',exclusions,'--output',ginanInputRINEX,firstFile,lastFile]
		x = subprocess.check_output(cmdargs) 
	except Exception as e:
		print(e)
		ottp.ErrorExit('Failed to run ' + editRnxObs)
	
	if not(os.path.exists(ginanInputRINEX)): # hmmm no output
		ottp.ErrorExit(f'Expected {ginanInputRINEX} - not found!')
		
	gCfg['inputs']['gnss_observations']['rnx_inputs'] = [ginanInputRINEX] # pea grumbles if this is not a list, so give it a list
		
	(yyyy,doy,mon) = ottp.MJDtoYYYYDOY(startMJD)
	yy = yyyy % 100
	clkFile = clkFileTemplate
	if 'YYDDD' in clkFile:
		clkFile = clkFile.replace('YYDDD',f'{yy:02d}{doy:03d}',1)
		gCfg['outputs']['clocks']['filename']  =  clkFile
	elif 'DDD0.YY' in clkFile:
		clkFile = clkFile.replace('DDD0.YY',f'{doy:03d}{yy:02d}',1)
		gCfg['outputs']['clocks']['filename']  =  clkFile
	
	# FIXME unlink this always ?
	gCfgOut = os.path.join(runDir,'pppclk.yaml')
	try:
		fout = open(gCfgOut, 'w')
	except:
		ErrorExit('Unable to open ' + gCfgOut)
		
	yaml.safe_dump(gCfg, fout, sort_keys = False) 
	ottp.Debug(f'Wrote {gCfgOut}')
	
	# Run 'pea'
	ottp.Debug('Running pea')
	tstart = time.time()
	try:
		cmdargs = [peaExec,'-y',gCfgOut]
		subprocess.check_output(cmdargs) 
	except Exception as e:
		print(e)
		ottp.ErrorExit('Failed to run ' + peaExec)
	tstop = time.time()
	ottp.Debug('..done')
	ottp.Debug('Job run time = {:g} s'.format(tstop-tstart))
	
	# Collect the output, namely the smoothed clock file
	# Ginan appears to put _smoothed before the extension
	base,ext = os.path.splitext(clkFile)
	clkPath = os.path.join(gCfg['outputs']['clocks']['directory'],f'{base}_smoothed{ext}')
	shutil.copy(clkPath,os.path.join(outputClockDir,clkFile))
	ottp.Debug(f'CLK file in {outputClockDir}/{clkFile}')
