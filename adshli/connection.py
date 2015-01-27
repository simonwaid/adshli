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

import socket

class ads_connection:
    def __init__(self, ams_netid_target, ams_port_target, ams_netid_source, ams_port_source):
        '''Saves all ams connection data for use in the packet assembly'''
        self.ams_netid_target=ams_netid_target
        self.ams_port_target=ams_port_target
        self.ams_netid_source=ams_netid_source
        self.ams_port_source=ams_port_source        
        self.invoke_id=0
    
    def open(self, plc_ip, plc_port, timeout):
        '''Opens tcp connection to communication partner'''
        self.socket = socket.create_connection((plc_ip, plc_port), timeout=timeout)

    def close(self):
        del self.socket

    def execute_cmd(self, ads_cmd):
        '''Sends the provided packet to the plc and evaluates the result'''
        #Send command to plc
        packet=ads_cmd.get_packet(self.invoke_id, self)
        #print packet
        self.socket.send(packet)
        # Read first part of response (heasder + some data)
        packet_size=1024
        try:
            response=self.socket.recv(packet_size)
        except:
            print 'No response received from PLC'
            raise
        # Decode header
        header_data, payload=ads_cmd.decode_header(response)
        # Fetch residual data
        while header_data['ams_packet_lenght']+6 > len(response):
            #read_lenght+=packet_size
            response+=self.socket.recv(packet_size)
        # Increase invoke id. Note: Currently this is not used.  
        self.invoke_id+=1
        if self.invoke_id > 2**30:
            self.invoke_id
        # Decode packet 
        result=ads_cmd.decode_response(response)
        return result
        