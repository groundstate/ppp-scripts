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
VERSION = '2.0.2'

examples = 'Usage examples\n'
examples += 

parser = argparse.ArgumentParser(description='Differences RINEX clock files',
	formatter_class=argparse.RawDescriptionHelpFormatter,epilog = examples)

parser.add_argument('sta1',help='station 1 name')
parser.add_argument('sta2',help='station 2 name')
parser.add_argument('sta1dir',help = 'path to station 1 RINEX CLK files')
parser.add_argument('sta2dir',help = 'path to station 2 RINEX CLK files')
parser.add_argument('outdir',help='output directory')
parser.add_argument('startmjd')
parser.add_argument('stopmjd')
parser.add_argument('--days',help='nominal number of days in the CLK file (used to select the range in a multi-day file and to step through multi-day files when the MJD range spans multiple files)')
parser.add_argument('--csrs','-n',help='use CSRS PPP file name format STAyyddd.clk(default is Bernese PPPyydddSTA.clk)',action='store_true')
parser.add_argument('--debug','-d',help='debug (to stderr)',action='store_true')
parser.add_argument('--version','-v',action='version',version = os.path.basename(sys.argv[0])+ ' ' + VERSION + '\n' + 'Written by ' + AUTHORS)

args = parser.parse_args()

ottp.SetDebugging(args.debug)

sta1     = args.sta1
sta2     = args.sta2
startMJD = int(args.startmjd)
stopMJD  = int(args.stopmjd)

nDays = 1 # expected step in file name time tag 
if args.days:
	nDays = int(args.days)

fdiff = os.path.join(args.outdir,'{}.{}.{:d}.{:d}.diff.dat'.format(sta1,sta2,startMJD,stopMJD))
fout  = open(fdiff,'w')
cnt = 0

for m in range(startMJD,stopMJD+1,nDays):
	
	dclk1 = []
	dclk2 = []

	yyyy,doy,mon = ottp.MJDtoYYYYDOY(m)
	
	if (args.csrs):
		fclk1 = os.path.join(args.sta1dir,'{}{:02d}{:03d}.clk'.format(sta1,yyyy % 100,doy)) # hmm depends on what input file was called 
	else:
		fclk1 = os.path.join(args.sta1dir,'PPP{:02d}{:03d}{}.CLK'.format(yyyy % 100,doy, sta1))
	
	if (not(os.path.exists(fclk1)) or (os.path.getsize(fclk1) == 0)):
		ottp.Debug('{} is  missing/empty'.format(fclk1))
		continue
	
	
	if (args.csrs):
		fclk2 = os.path.join(args.sta2dir,'{}{:02d}{:03d}.clk'.format(sta2,yyyy % 100,doy)) # hmm depends on what input file was called 
	else:
		fclk2 = os.path.join(args.sta2dir,'PPP{:02d}{:03d}{}.CLK'.format(yyyy % 100,doy, sta2))

	if (not(os.path.exists(fclk2)) or (os.path.getsize(fclk2) == 0)):
		ottp.Debug('{} is  missing/empty'.format(fclk2))
		continue
	
	# Read the first station 
	
	fin = open(fclk1,'r')
	stastr = 'AR '+ sta1
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
	stastr = 'AR '+ sta2
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
