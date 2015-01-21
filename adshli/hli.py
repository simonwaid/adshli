#adshli
#Authors:
# - Simon Waid (simon_waid@gmx.net)
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 3.0 of the License, or (at your option) any later version.
#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#Lesser General Public License for more details.
#You should have received a copy of the GNU Lesser General Public
#License along with this library.

import protocol

idx_grp={'SYMTAB': 0xF000, \
         'SYMNAME': 0xF001 , \
         'SYMVAL': 0xF002 , \
         'SYM_HNDBYNAME': 0xF003, \
         'SYM_VALBYNAME': 0xF004 , \
         'SYM_VALBYHND': 0xF005 , \
         'SYM_RELEASEHND': 0xF006, \
         'SYM_INFOBYNAME': 0xF007, \
         'SYM_VERSION': 0xF008, \
         'SYM_INFOBYNAMEEX': 0xF009, \
         'SYM_DOWNLOAD': 0xF00A, \
         'SYM_UPLOAD': 0xF00B, \
         'SYM_UPLOADINFO': 0xF00C, \
         'SYMNOTE': 0xF010 , \
         'IOIMAGE_RWIB': 0xF020, \
         'IOIMAGE_RWIX': 0xF021 , \
         'IOIMAGE_RISIZE': 0xF025, \
         'IOIMAGE_RWOB': 0x030 , \
         'IOIMAGE_RWOX': 0x031 , \
         'IOIMAGE_RWOSIZE': 0x035 , \
         'IOIMAGE_CLEARI': 0x040 , \
         'IOIMAGE_CLEARO': 0x050 , \
         'IOIMAGE_RWIOB': 0x060 , \
         'DEVICE_DATA': 0x100 , \
         'ADSIOFFS_DEVDATA_ADSSTATE': 0x0000, \
         'ADSIOFFS_DEVDATA_DEVSTATE': 0x0002}

class ads_device:
    '''Provides a high level interface for accessing device information and state'''
    def __init__(self, ads_connection):
        self.ads_connection=ads_connection
        self.update_info()
        
    def update_info(self):
        #Read device information
        cmd=protocol.ads_cmd_read_dev_info()
        retval=self.ads_connection.execute_cmd(cmd)
        self.device_name=retval['dev_name']
        self.major_version=retval['major_ver']
        self.minor_version=retval['minor_ver']
        self.version_build=retval['build_ver']
        #Read the ads state
        cmd=protocol.ads_cmd_read_state()
        retval=self.ads_connection.execute_cmd(cmd)
        self.ads_state=retval['ads_state']
        self.device_state=retval['dev_state']
        
class ads_variable:
    '''Provides a high level interface for accessing PLC variables via ADS'''    
    def __init__(self, ads_connection, var_name, var_type):
        '''Save variable details and get a handle in the PLC'''
        self._ads_connection=ads_connection
        self._var_name=var_name
        self._var_type=var_type
        self._get_handle()
        
    def _get_handle(self):
        '''Get a handle for the variable'''
        cmd=protocol.ads_cmd_read_write(idx_grp['SYM_HNDBYNAME'], 0x0, 'L',  self._var_name)
        self._handle=self._ads_connection.execute_cmd(cmd)['data'][0]
    
    def read(self):
        '''Read the variable content from the PLC memory'''
        cmd=protocol.ads_cmd_read(idx_grp['SYM_VALBYHND'], self._handle, self._var_type)
        var_content=self._ads_connection.execute_cmd(cmd)['data'][0]
        return var_content
    
    def write(self, data):
        '''Write the provided data to the PLC'''
        cmd=protocol.ads_cmd_write(idx_grp['SYM_VALBYHND'], self._handle, self._var_type, data)
        self._ads_connection.execute_cmd(cmd)
        
    def _release_handle(self):
        '''Releases the handle in the PLC'''
        cmd=protocol.ads_cmd_write(idx_grp['SYM_RELEASEHND'], 0x0, 'L', self._handle)
        self._ads_connection.execute_cmd(cmd)
        self._handle=None
    
    def __del__(self):
        pass
        #self._release_handle()