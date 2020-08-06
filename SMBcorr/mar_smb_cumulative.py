#!/usr/bin/env python
u"""
mar_smb_cumulative.py
Written by Tyler Sutterley (11/2019)
Calculates cumulative anomalies of MAR surface mass balance products

COMMAND LINE OPTIONS:
    --help: list the command line options
    --directory=X: set the full path to the MAR data directory
    --version=X: MAR version to run
        v3.5.2
        v3.9
        v3.10
        v3.11
    --downscaled: run downscaled MAR
    --product: MAR product to calculate
        SMB: Surface Mass Balance
        PRECIP: Precipitation
        SNOWFALL: Snowfall
        RAINFALL: Rainfall
        RUNOFF: Melt Water Runoff
        SNOWMELT: Snowmelt
        REFREEZE: Melt Water Refreeze
        SUBLIM = Sublimation
    --mean: Start and end year of mean (separated by commas)
    -M X, --mode=X: Permission mode of directories and files created
    -V, --verbose: Verbose output of netCDF4 variables

PROGRAM DEPENDENCIES:
    convert_calendar_decimal.py: converts from calendar dates to decimal years

UPDATE HISTORY:
    Written 11/2019
"""
from __future__ import print_function

import sys
import os
import re
import getopt
import pyproj
import netCDF4
import builtins
import traceback
import numpy as np
from SMBcorr.convert_calendar_decimal import convert_calendar_decimal

#-- data product longnames
longname = {}
longname['SMB'] = 'Surface_Mass_Balance'
longname['PRECIP'] = 'Precipitation'
longname['SNOWFALL'] = 'Snowfall'
longname['RAINFALL'] = 'Rainfall'
longname['RUNOFF'] = 'Melt_Water_Runoff'
longname['SNOWMELT'] = 'Snowmelt'
longname['REFREEZE'] = 'Melt_Water_Refreeze'
longname['SUBLIM'] = 'Sublimation'

#-- PURPOSE: sort input files by year
def sort_files(regex, input_files):
    sort_indices = np.argsort([regex.match(f).group(2) for f in input_files])
    return np.array(input_files)[sort_indices]

#-- PURPOSE: get the dimensions for the input data matrices
def get_dimensions(directory,input_files,XNAME,YNAME):
    #-- get grid dimensions from first file and 12*number of files
    #-- Open the NetCDF file for reading
    fileID = netCDF4.Dataset(os.path.join(directory,input_files[0]), 'r')
    nx, = fileID[XNAME].shape
    ny, = fileID[YNAME].shape
    fileID.close()
    return ny,nx

#-- PURPOSE: create an output netCDF4 file for the output data fields
def create_netCDF4(OUTPUT, FILENAME=None, UNITS=None, LONGNAME=None,
    VARNAME=None, LONNAME=None, LATNAME=None, XNAME=None, YNAME=None,
    TIMENAME=None, MASKNAME=None, PROJECTION=None, TITLE=None, VERBOSE=False):
    #-- output netCDF4 file
    fileID = netCDF4.Dataset(FILENAME,'w',format="NETCDF4")
    nc = {}
    #-- Defining the netCDF dimensions
    #-- create each netCDF4 dimension variable
    for key in (XNAME,YNAME):
        fileID.createDimension(key, len(OUTPUT[key]))
        nc[key] = fileID.createVariable(key, 'f', (key,), zlib=True)
    fileID.createDimension(TIMENAME, 1)
    nc[TIMENAME] = fileID.createVariable(TIMENAME, 'f', (TIMENAME,), zlib=True)
    #-- create each netCDF4 variable
    for key,type in zip([LONNAME,LATNAME,MASKNAME],['f','f','b']):
        nc[key] = fileID.createVariable(key, type, ('y','x',), zlib=True)
    nc[VARNAME] = fileID.createVariable(VARNAME, 'f', ('y','x',),
        fill_value=OUTPUT[VARNAME].fill_value, zlib=True)
    #-- fill each output netCDF4 variable
    for key in (XNAME,YNAME,TIMENAME,LONNAME,LATNAME,MASKNAME,VARNAME):
        nc[key][:] = OUTPUT[key]
    #-- Defining attributes for each netCDF4 variable
    nc[XNAME].units = 'm'
    nc[YNAME].units = 'm'
    nc[TIMENAME].units = 'years'
    nc[TIMENAME].long_name = 'Date_in_Decimal_Years'
    nc[LONNAME].long_name = 'longitude'
    nc[LONNAME].units = 'degrees_east'
    nc[LATNAME].long_name = 'latitude'
    nc[LATNAME].units = 'degrees_north'
    nc[VARNAME].long_name = LONGNAME
    nc[VARNAME].units = UNITS
    #-- global variables of netCDF file
    fileID.projection = PROJECTION
    fileID.TITLE = TITLE
    #-- Output NetCDF structure information
    if VERBOSE:
        print(FILENAME)
        print(list(fileID.variables.keys()))
    #-- Closing the netCDF file
    fileID.close()

#-- PURPOSE: calculates cumulative anomalies in MAR products
def mar_smb_cumulative(input_dir, VERSION, PRODUCT, RANGE=[1961,1990],
    DOWNSCALED=False, VERBOSE=False, MODE=0o775):

    #-- regular expression pattern for MAR dataset
    rx = re.compile('MAR{0}-monthly-(.*?)-(\d+).nc$'.format(VERSION))
    #-- netCDF4 variable names (for both direct and derived products)
    input_products = {}
    #-- SMB from downscaled product
    if DOWNSCALED:
        #-- variable coordinates
        XNAME,YNAME,TIMENAME = ('x','y','time')
        #-- SMBcorr is topography corrected SMB for the ice covered area
        #-- SMB2 is the SMB for the tundra covered area
        input_products['SMB'] = ['SMBcorr','SMB2']
        #-- RU from downscaled product
        #-- RUcorr is topography corrected runoff for the ice covered area
        #-- RU2corr is topography corrected runoff for the tundra covered area
        input_products['RUNOFF'] = ['RUcorr','RU2corr']
        input_products['PRECIP'] = ['RF','SF']
        input_products['SNOWFALL'] = 'SF'
        #-- ME from downscaled product
        #-- MEcorr is topography corrected melt
        input_products['SNOWMELT'] = 'MEcorr'
        input_products['SUBLIM'] = 'SU'
        input_products['REFREEZE'] = ['MEcorr','RUcorr','RU2corr']
        input_products['RAINFALL'] = 'RF'
        #-- downscaled projection: WGS84/NSIDC Sea Ice Polar Stereographic North
        proj4_params = "+init=EPSG:{0:d}".format(3413)
    else:
        #-- variable coordinates
        XNAME,YNAME,TIMENAME = ('X10_105','Y21_199','TIME')
        #-- SMB is SMB for the ice covered area
        input_products['SMB'] = 'SMB'
        #-- RU is runoff for the ice covered area
        #-- RU2 is runoff for the tundra covered area
        input_products['RUNOFF'] = ['RU','RU2']
        input_products['PRECIP'] = ['RF','SF']
        input_products['SNOWFALL'] = 'SF'
        input_products['SNOWMELT'] = 'ME'
        input_products['SUBLIM'] = 'SU'
        input_products['REFREEZE'] = 'RZ'
        input_products['RAINFALL'] = 'RF'
        #-- MAR model projection: Polar Stereographic (Oblique)
        #-- Earth Radius: 6371229 m
        #-- True Latitude: 0
        #-- Center Longitude: -40
        #-- Center Latitude: 70.5
        proj4_params = ("+proj=sterea +lat_0=+70.5 +lat_ts=0 +lon_0=-40.0 "
            "+a=6371229 +no_defs")

    #-- create flag to differentiate between direct and directed products
    if (np.ndim(input_products[PRODUCT]) == 0):
        #-- direct products
        derived_product = False
    else:
        #-- derived products
        derived_product = True

    #-- Open the NetCDF4 file for reading
    mean_filename = 'MAR_{0}_{1}_mean_{2:4.0f}-{3:4.0f}.nc'
    MEAN_FILE = mean_filename.format(VERSION,PRODUCT,RANGE[0],RANGE[1])
    with netCDF4.Dataset(os.path.join(input_dir,MEAN_FILE), 'r') as fileID:
        MEAN = fileID.variables[PRODUCT][:,:].copy()

    #-- output subdirectory
    output_sub = 'MAR_{0}_{1}_cumul'
    output_dir = os.path.join(input_dir,output_sub.format(VERSION,PRODUCT))
    os.makedirs(output_dir,MODE) if not os.access(output_dir,os.F_OK) else None
    #-- output netCDF4 title format
    TITLE = 'Cumulative_anomalies_relative_to_{0:4d}-{1:4d}_Mean'

    #-- find input files
    input_files=sort_files(rx,[f for f in os.listdir(input_dir) if rx.match(f)])
    #-- input dimensions and counter variable
    #-- get dimensions for input dataset
    ny,nx = get_dimensions(input_dir,input_files,XNAME,YNAME)
    #-- allocate for all data
    CUMUL = {}
    CUMUL['LON'] = np.zeros((ny,nx))
    CUMUL['LAT'] = np.zeros((ny,nx))
    CUMUL['VALID'] = np.zeros((ny,nx),dtype=np.bool)
    CUMUL['x'] = np.zeros((nx))
    CUMUL['y'] = np.zeros((ny))
    #-- calculate cumulative anomalies
    CUMUL[PRODUCT] = np.ma.zeros((ny,nx),fill_value=-9999.0)
    CUMUL[PRODUCT].mask = np.ones((ny,nx),dtype=np.bool)
    #-- input monthly data
    MONTH = {}
    MONTH['MASK'] = np.zeros((ny,nx))

    #-- for each file
    for t,input_file in enumerate(input_files):
        #-- Open the NetCDF file for reading
        fileID = netCDF4.Dataset(os.path.join(input_dir,input_file), 'r')
        #-- Getting the data from each netCDF variable
        #-- latitude and longitude
        CUMUL['LON'][:,:] = fileID.variables['LON'][:,:].copy()
        CUMUL['LAT'][:,:] = fileID.variables['LAT'][:,:].copy()
        #-- extract model x and y
        CUMUL['x'][:] = fileID.variables[XNAME][:].copy()
        CUMUL['y'][:] = fileID.variables[YNAME][:].copy()
        #-- get reanalysis and year from file
        reanalysis,year = rx.findall(input_file).pop()
        #-- convert from months since year start to calendar month
        months = fileID.variables[TIMENAME][:].copy() + 1.0
        #-- read land/ice mask
        LAND_MASK = fileID.variables['MSK'][:,:].copy()
        #-- finding valid points only from land mask
        iy,ix = np.nonzero(LAND_MASK > 1)
        CUMUL['VALID'][iy,ix] = True
        CUMUL[PRODUCT].mask[iy,ix] = False
        #-- read downscaled masks
        if DOWNSCALED:
            #-- read glacier and ice sheet mask (tundra=1, permanent ice=2)
            MASK_MAR = fileID.variables['MSK_MAR'][:,:].copy()
            SURF_MAR = fileID.variables['SRF_MAR'][:,:].copy()
            iy,ix = np.nonzero((SURF_MAR >= 0.0) & (LAND_MASK > 1))
            MONTH['MASK'][iy,ix] = MASK_MAR[iy,ix]
        else:
            MONTH['MASK'][iy,ix] = 2.0

        #-- invalid value from MAR product
        FILL_VALUE = fileID.variables['SMB']._FillValue

        #-- for each month
        for m,mon in enumerate(months):
            #-- calculate time in decimal format (m+1 to convert from indice)
            #-- convert to decimal format (uses matrix algebra for speed)
            CUMUL['TIME'] = convert_calendar_decimal(np.float(year),mon)
            #-- read each product of interest contained within the dataset
            #-- read variables for both direct and derived products
            if derived_product:
                for p in input_products[PRODUCT]:
                    MONTH[p] = fileID.variables[p][m,:,:].copy()
            else:
                p = input_products[PRODUCT]
                MONTH[PRODUCT] = fileID.variables[p][m,:,:].copy()

            #-- calculate derived products
            if (PRODUCT == 'PRECIP'):
                #-- PRECIP = SNOWFALL + RAINFALL
                MONTH['PRECIP'] = MONTH['SF'] + MONTH['RF']
            elif (PRODUCT == 'REFREEZE') and DOWNSCALED:
                #-- runoff from permanent ice covered regions and tundra regions
                RU1,RU2 = input_products['RUNOFF']
                ME = input_products['SNOWMELT']
                MONTH['RUNOFF'] = (MONTH['MASK'] - 1.0)*MONTH[RU1] + \
                    (2.0 - MONTH['MASK'])*MONTH[RU2]
                #-- REFREEZE = (total) SNOWMELT - RUNOFF
                MONTH['REFREEZE'] = MONTH[ME] - MONTH['RUNOFF']
            elif (PRODUCT == 'RUNOFF'):
                #-- runoff from permanent ice covered regions and tundra regions
                RU1,RU2 = input_products['RUNOFF']
                MONTH['RUNOFF'] = (MONTH['MASK'] - 1.0)*MONTH[RU1] + \
                    (2.0 - MONTH['MASK'])*MONTH[RU2]
            elif (PRODUCT == 'SMB'):
                #-- SMB from permanent ice covered regions and tundra regions
                SMB1,SMB2 = input_products['SMB']
                MONTH['SMB'] = (MONTH['MASK'] - 1.0)*MONTH[SMB1] + \
                    (2.0 - MONTH['MASK'])*MONTH[SMB2]

            #-- calculate cumulative for each time step
            CUMUL[PRODUCT].data[iy,ix] += MONTH[PRODUCT][iy,ix] - MEAN[iy,ix]
            #-- replace masked values with fill value
            CUMUL[PRODUCT].data[CUMUL[PRODUCT].mask] = CUMUL[PRODUCT].fill_value
            #-- output netCDF4 filename
            args = (VERSION, PRODUCT, year, mon)
            cumul_file = 'MAR_{0}_{1}_cumul_{2}_{3:02.0f}.nc'.format(*args)
            create_netCDF4(CUMUL, FILENAME=os.path.join(output_dir,cumul_file),
                UNITS='mmWE', LONGNAME=longname[PRODUCT], VARNAME=PRODUCT,
                LONNAME='LON', LATNAME='LAT', XNAME='x', YNAME='y',
                TIMENAME='TIME', MASKNAME='VALID', VERBOSE=VERBOSE,
                PROJECTION=proj4_params, TITLE=TITLE.format(RANGE[0],RANGE[1]))
            #-- change the permissions mode
            os.chmod(os.path.join(output_dir,cumul_file),MODE)

        #-- close the netcdf file
        fileID.close()

#-- PURPOSE: help module to describe the optional input parameters
def usage():
    print('\nHelp: {0}'.format(os.path.basename(sys.argv[0])))
    print(' -D X, --directory=X\tSet the base data directory')
    print(' --version=X\t\tMAR version to run')
    print('\tv3.5.2\n\tv3.9\n\tv3.10\n\tv3.11')
    print(' --downscaled\t\tRun downscaled MAR')
    print(' --product:\t\tMAR product to calculate')
    print('\tSMB: Surface Mass Balance')
    print('\tPRECIP: Precipitation')
    print('\tRUNOFF: Melt Water Runoff')
    print('\tSNOWMELT: Snowmelt')
    print('\tREFREEZE: Melt Water Refreeze')
    print(' --mean:\t\tStart and end year of mean (separated by commas)')
    print(' -M X, --mode=X\t\tPermission mode of directories and files created')
    print(' -V, --verbose\t\tVerbose output of netCDF4 variables\n')

#-- This is the main part of the program that calls the individual modules
def main():
    #-- Read the system arguments listed after the program and run the analyses
    #-- with the specific parameters.
    long_options = ['help','directory=','version=''downscaled','product=',
        'mean=','verbose','mode=']
    optlist,arglist = getopt.getopt(sys.argv[1:],'hD:VM:',long_options)

    #-- command line parameters
    input_dir = os.getcwd()
    #-- MAR model version
    VERSION = 'v3.11'
    DOWNSCALED = False
    #-- Products to calculate cumulative
    PRODUCTS = ['SMB']
    #-- mean range
    RANGE = [1961,1990]
    VERBOSE = False
    MODE = 0o775
    for opt, arg in optlist:
        if opt in ('-h','--help'):
            usage()
            sys.exit()
        elif opt in ("-D","--directory"):
            input_dir = os.path.expanduser(arg)
        elif opt in ("--version"):
            VERSION = arg
        elif opt in ("--downscaled"):
            DOWNSCALED = True
        elif opt in ("--product"):
            PRODUCTS = arg.split(',')
        elif opt in ("--mean"):
            RANGE = np.array(arg.split(','),dtype=np.int)
        elif opt in ("-V","--verbose"):
            VERBOSE = True
        elif opt in ("-M","--mode"):
            MODE = int(arg,8)

    #-- for each product
    for p in PRODUCTS:
        #-- check that product was entered correctly
        if p not in longname.keys():
            raise IOError('{0} not in valid MAR products'.format(p))
        #-- run cumulative program with parameters
        mar_smb_cumulative(input_dir, VERSION, p, RANGE=RANGE,
            DOWNSCALED=DOWNSCALED, VERBOSE=VERBOSE, MODE=MODE)

#-- run main program
if __name__ == '__main__':
    main()
