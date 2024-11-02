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

# This script assumes a particular directory structure
# namely a top level directory, with each station as a sub-directory

import argparse
import datetime
import os
import sys

sys.path.append("/usr/local/lib/python3.6/site-packages")  # Ubuntu 18.04
sys.path.append("/usr/local/lib/python3.8/site-packages")  # Ubuntu 20.04
sys.path.append("/usr/local/lib/python3.10/site-packages") # Ubuntu 22.04

import ottplib as ottp

AUTHORS = 'Michael Wouters'
VERSION = '2.1.0'

examples = 'Usage examples:\n'
examples += '(1) Difference 7 day files generated using CSRS\n'
examples += '    diffrnxclk.py --csrs --days 7 SYDN PTBB ./sydn ./ptbb ./clkdiffs 60539 60545\n'
examples += '\nFiles are expected to have names like\n'
examples += '  STAyyddd.clk eg SYDN24273.clk\n'
examples += '  PPPyydddSTA.clk eg PPP24273SYDN.clk\n'
examples += 'otherwise, specify the file name as a template,\n'
examples += 'Templates are recognized from patterns in the name like YYDDD,YYYYDDD,DDD\n'
examples += 'eg SYDN24273.clk -> SYDNYYDDD.clk\n'
examples += 'Note that files with multiple stations can also be parsed since sta1 and sta2 can be used to extract a particular station\n'
examples += '(2) Extract two clocks SYDN and USN7 from the IGS CLK file IGS2R03FIN_20191990000_01D_30S_CLK.CLK\n'
examples += 'diffrnxclk.py --sta1match SYDN --sta2match USN7 IGS0OPSRAP_YYYYDDD0000_01D_05M_CLK.CLK IGS0OPSRAP_YYYYDDD0000_01D_05M_CLK.CLK ~/igs/rapid/ ~/igs/rapid/ ./ 60589 60589\n'

parser = argparse.ArgumentParser(description='Differences RINEX clock files',
	formatter_class=argparse.RawDescriptionHelpFormatter,epilog = examples)

parser.add_argument('sta1',help='station 1 name/template' )
parser.add_argument('sta2',help='station 2 name/template')
parser.add_argument('sta1dir',help = 'path to station 1 RINEX CLK files')
parser.add_argument('sta2dir',help = 'path to station 2 RINEX CLK files')
parser.add_argument('outdir',help='output directory')
parser.add_argument('startmjd')
parser.add_argument('stopmjd')
parser.add_argument('--days',help='nominal number of days in the CLK file (used to select the range in a multi-day file and to step through multi-day files when the MJD range spans multiple files)')
parser.add_argument('--csrs','-n',help='use CSRS PPP file name format STAyyddd.clk (default is Bernese PPPyydddSTA.clk)',action='store_true')
parser.add_argument('--debug','-d',help='debug (to stderr)',action='store_true')
parser.add_argument('--version','-v',action='version',version = os.path.basename(sys.argv[0])+ ' ' + VERSION + '\n' + 'Written by ' + AUTHORS)
parser.add_argument('--sta1match',help='station 1 name to match inside the RINEX clk file (otherwise deduced from file name)\n')
parser.add_argument('--sta2match',help='station 2 name to match inside the RINEX clk file (otherwise deduced from file name)\n')

args = parser.parse_args()

ottp.SetDebugging(args.debug)

sta1     = args.sta1
sta2     = args.sta2
startMJD = int(args.startmjd)
stopMJD  = int(args.stopmjd)

nDays = 1 # expected step in file name time tag 
if args.days:
	nDays = int(args.days)

# Set the station name to match
sta1match = sta1
sta2match = sta2

# If using a template, then guess from the template
if ('YYYYDDD' in sta1) or ('YYDDD' in sta1) or ('DDD' in sta1):
	sta1match = sta1[0:4]

if ('YYYYDDD' in sta2) or ('YYDDD' in sta2) or ('DDD' in sta2):
	sta2match = sta2[0:4]

# Finally, option arguments override our guesses
if args.sta1match:
	sta1match = args.sta1match
	
if args.sta2match:
	sta2match = args.sta2match
		
fdiff = os.path.join(args.outdir,'{}.{}.{:d}.{:d}.diff.dat'.format(sta1match,sta2match,startMJD,stopMJD))
fout  = open(fdiff,'w')
cnt = 0


for m in range(startMJD,stopMJD+1,nDays):
	
	dclk1 = []
	dclk2 = []

	yyyy,doy,mon = ottp.MJDtoYYYYDOY(m)
	yy = yyyy % 100
	
	if ('YYYYDDD' in sta1): # a template has been given. Test for this pattern first because YYDDD will also match
		sta1tmp = sta1.replace('YYYYDDD',f'{yyyy:04d}{doy:03d}',1)
		fclk1 = os.path.join(args.sta1dir,f'{sta1tmp}') 
	elif ('YYDDD' in sta1): # and then this pattern
		sta1tmp = sta1.replace('YYDDD',f'{yy:02d}{doy:03d}',1)
		fclk1 = os.path.join(args.sta1dir,f'{sta1tmp}') 
	elif ('DDD' in sta1): # and then this pattern
		sta1tmp = sta1.replace('DDD',f'{doy:03d}',1)
		fclk1 = os.path.join(args.sta1dir,f'{sta1tmp}')
	elif (args.csrs): # CSRS style
		fclk1 = os.path.join(args.sta1dir,'{}{:02d}{:03d}.clk'.format(sta1,yy,doy)) # hmm depends on what the input file was called 
	else: # Bernese style
		fclk1 = os.path.join(args.sta1dir,'PPP{:02d}{:03d}{}.CLK'.format(yy,doy, sta1))
	
	if (not(os.path.exists(fclk1)) or (os.path.getsize(fclk1) == 0)):
		ottp.Debug('{} is  missing/empty'.format(fclk1))
		continue
	
	if ('YYYYDDD' in sta2): 
		sta2tmp = sta2.replace('YYYYDDD',f'{yyyy:04d}{doy:03d}',1)
		fclk2 = os.path.join(args.sta2dir,f'{sta2tmp}') 
	elif ('YYDDD' in sta2):
		sta2tmp = sta2.replace('YYDDD',f'{yy:02d}{doy:03d}',1)
		fclk2 = os.path.join(args.sta2dir,f'{sta2tmp}')
	elif ('DDD' in sta2):
		sta2tmp = sta2.replace('DDD',f'{doy:03d}',1)
		fclk2 = os.path.join(args.sta2dir,f'{sta2tmp}')
	elif (args.csrs):
		fclk2 = os.path.join(args.sta2dir,'{}{:02d}{:03d}.clk'.format(sta2,yy,doy)) 
	else:
		fclk2 = os.path.join(args.sta2dir,'PPP{:02d}{:03d}{}.CLK'.format(yy,doy, sta2))

	if (not(os.path.exists(fclk2)) or (os.path.getsize(fclk2) == 0)):
		ottp.Debug('{} is  missing/empty'.format(fclk2))
		continue
	
	# Read the first station 
	
	fin = open(fclk1,'r')
	stastr = 'AR '+ sta1match
	for l in fin:
		if stastr in l:
			data = l.split()
			tod = int(data[5])*3600 + int(data[6])*60 + int(float(data[7])) 
			dt = datetime.datetime(int(data[2]), int(data[3]), int(data[4]))
			mjd = int(dt.timestamp()/86400) + 40587;
			dclk1.append([mjd,tod,data[9]])
	fin.close()
	ottp.Debug('--->{} has {} points'.format(fclk1,len(dclk1)))
	
	# Read the second station
	
	fin = open(fclk2,'r')
	stastr = 'AR '+ sta2match
	for l in fin:
		if stastr in l:
			data = l.split()
			tod = int(data[5])*3600 + int(data[6])*60 + int(float(data[7])) 
			dt = datetime.datetime(int(data[2]), int(data[3]), int(data[4]))
			mjd = int(dt.timestamp()/86400) + 40587;
			dclk2.append([mjd,tod,data[9]])
	fin.close()
	ottp.Debug('--->{} has {} points'.format(fclk2,len(dclk2)))
	
	# Difference the two clocks, lining up the time stamps
	
	i = 0
	j = 0
	lenclk1 = len(dclk1)
	lenclk2 = len(dclk2)
	
	while i < lenclk1 and j < lenclk2:
		
		mjd1 = dclk1[i][0]
		tod1 = dclk1[i][1]
		mjd2 = dclk2[j][0]
		tod2 = dclk2[j][1]
		
		if (mjd1 == mjd2 and tod1 == tod2): # ding! ding! It's a Perfect Match!!
			fout.write('{:d} {:d} {} {} {:.12e}\n'.format(dclk1[i][0],dclk1[i][1],dclk1[i][2],dclk2[j][2],float(dclk1[i][2])-float(dclk2[j][2])))
			cnt += 1
			i += 1
			j += 1
			continue
		
		# Timestamps do not match
		# So test MJD first    
		if (mjd2 > mjd1):
			i += 1
			continue
		elif (mjd2 < mjd1):
			j += 1
			continue
		
		# MJDs must match so test TOD
		if (tod2 > tod1):
			i += 1
			continue
		elif (tod2 < tod1):
			j += 1
			continue

ottp.Debug('--->{:d} matched points in {}'.format(cnt,fdiff))

fout.close()
