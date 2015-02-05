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
from protocol import idx_grp
#Numpy is only needed for arrays so 
try:
    import numpy as np
except:
    pass


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

class ads_var():
    '''Class to store information on '''
    def __init__(self, var_name, var_type, shape=None):
        '''Save variable details and get a handle in the PLC. In case of an array you have to provide its shape for correct interpretation of the data'''
        self.shape=shape
        self.var_name=var_name
        self.var_type=var_type
        self.value=None
        self.handle=None

    def _expand_array(self, value):
        '''Checks if the data is an array and reshapes it'''
        if not self.shape==None:
            value=np.reshape(value, self.shape, order='C')
        return value
    
    def _linearize_array(self, data):
        '''Linearizes an array to fit into the memory of the PLC'''
        if not self.shape==None:
            data=np.reshape(data, -1, order='C')
        return data
    
class ads_var_single(ads_var):
    '''Provides a high level interface for accessing PLC variables via ADS'''    
    def __init__(self, ads_connection, var_name, var_type, shape=None):
        '''Save variable details and get a handle in the PLC. In case of an array you have to provide its shape for correct interpretation of the data'''
        ads_var.__init__(self, var_name, var_type, shape)
        if not ads_connection==None:
            self.connect(ads_connection)
        
    def connect(self,ads_connection):
        '''Sets the connection to the plc'''
        # If we have a handle release it
        try:
            self._release_handle()
        except:
            pass
        self.ads_connection=ads_connection
        self._get_handle()
    
    def _get_handle(self):
        '''Get a handle for the variable'''
        try:
            cmd=protocol.ads_cmd_read_write(idx_grp['SYM_HNDBYNAME'], 0x0, 'L',  self.var_name)
            self.handle=self.ads_connection.execute_cmd(cmd)['data'][0]
        except:
            print 'Getting handle failed'
            print 'Variable name: ', self.var_name
            raise
        
    def read(self):
        '''Read the variable content from the PLC memory'''
        cmd=protocol.ads_cmd_read(idx_grp['SYM_VALBYHND'], self.handle, self.var_type)
        var_content=self.ads_connection.execute_cmd(cmd)['data']
        if len(var_content)==1:
            self.value=self._expand_array(var_content)[0]
        else:
            self.value=self._expand_array(var_content)
        return self.value
    
    def write(self, data):
        '''Write the provided data to the PLC'''
        data=self._linearize_array(data)
        cmd=protocol.ads_cmd_write(idx_grp['SYM_VALBYHND'], self.handle, self.var_type, data)
        self.ads_connection.execute_cmd(cmd)
        
    def _release_handle(self):
        '''Releases the handle in the PLC'''
        cmd=protocol.ads_cmd_write(idx_grp['SYM_RELEASEHND'], 0x0, 'L', self.handle)
        self.ads_connection.execute_cmd(cmd)
        self.handle=None

class ads_var_group:
    '''Groups multiple variables for collective reading and writing'''
    # TODO: Implement multicommand ads access
    def __init__(self):
        self.plc_variables=[]
        self.ads_connection=None
        
    def add_variable(self, var_name, var_type, shape=None):
        '''Add a variable to the group. Returns an object to allow reading/writing the variable value'''
        variable=ads_var_single(self.ads_connection, var_name, var_type, shape=shape)
        self.plc_variables.append(variable)
        return variable
    
    def connect(self, ads_connection):
        '''Call this after all variables have been added'''
        try:
            self._release_handle()
        except:
            pass
        for variable in self.plc_variables:
            variable.ads_connection=ads_connection
        self.ads_connection=ads_connection
        self._get_handle()
        
    def _get_handle(self):
        '''Get a handles for all variables'''
        cmd=protocol.ads_sum_cmd_rw()
        for variable in self.plc_variables:
            if variable.handle!=None:
                variable._release_handle()
            cmd.add_var(idx_grp['SYM_HNDBYNAME'], 0x0, 'L', variable.var_name)
        #try:
        results=self.ads_connection.execute_cmd(cmd)
        #except:
        #    for variable in self.plc_variables:
        #        print 'Variable name', variable.var_name
        #    raise
        for i in range(len(self.plc_variables)):
            self.plc_variables[i].handle=results[i]['data'][0]
        
    def read(self):
        '''Reads all variables in the group. Returns True in case of success'''
        cmd=protocol.ads_sum_cmd_read()
        for variable in self.plc_variables:
            if variable.handle == None:
                raise RuntimeError('found no handle for variable')
            cmd.add_var(idx_grp['SYM_VALBYHND'], variable.handle, variable.var_type)
        results=self.ads_connection.execute_cmd(cmd)
        # If we get a misguided packet (or similar in the future) the result is none.
        # In that case we ignore the result and return false to let
        # the user application do the error handling
        if results!= None:
            for i in range(len(self.plc_variables)):
                var_content=results[i]['data']
                if len(var_content)==1:
                    self.plc_variables[i].value=var_content[0]
                else:
                    self.plc_variables[i].value=var_content
        else:
            return False
        return True
    
    def write(self):
        '''Writes all variables in the group'''
        cmd=protocol.ads_sum_cmd_write()
        for variable in self.plc_variables:
            if variable.handle == None:
                raise RuntimeError('found no handle for variable')
            cmd.add_var(idx_grp['SYM_VALBYHND'], variable.handle, variable.var_type, variable.value)
        results=self.ads_connection.execute_cmd(cmd)

    def _release_handle(self):
        '''Releases the handle in the PLC'''
        cmd=protocol.ads_sum_cmd_rw()
        for variable in self.plc_variables:
            cmd.add_var(idx_grp['SYM_RELEASEHND'], 0x0, 'L', variable.handle)
        self.ads_connection.execute_cmd(cmd)
        for variable in self.plc_variables:
            variable.handle=None
        
