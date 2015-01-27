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

import array, struct, re
# To get proper ADS error messages, put a dictionary return_codes with return codes in the file return_codes.
# Such a list can be found at:
# http://infosys.beckhoff.com/index.php?content=../content/1031/tcadsnetref/html/twincat.ads.adserrorcode.html
try:
    from return_codes import return_codes
except: 
    pass

ads_cmd_codes= {'read_dev_info':1, 'read':2, 'write':3,  'read_state':4, 'write_control':5, 'add_dev_notification':6, \
                'del_dev_notification':7,  'dev_notification':8, 'read_write':9}

ads_state_flags= {'command_request':0x04}
    
class _ads_packet:
    '''This class provides common packet assembly functionality for the more specific packet assembly classes'''
    def __init__(self):
        self.payload=array.array('c')

    def get_packet(self, invoke_id, ads_connection):
        '''Returns the fully assembled ads packet ready to be send'''
        # *** Assemble header
        # Length for TCP AMS header 32 byte AMS header plus payload
        lenght= self.payload.buffer_info()[1] + 32
        #Connection details from socket data 
        header=array.array('c')
        header.extend(struct.pack('<HL', 0, lenght))
        header.extend(self.__get_bin_id(ads_connection.ams_netid_target))
        header.extend(struct.pack('<H', ads_connection.ams_port_target))
        header.extend(self.__get_bin_id(ads_connection.ams_netid_source))
        header.extend(struct.pack('<H', ads_connection.ams_port_source))
        #Check the size of the header. 
        if not header.buffer_info()[1] == 22:
            print 'Header size: %f'  %(header.buffer_info()[1])
            raise RuntimeError('Wrong ADS header size detected during header assembly. Please check the provided connection setting.')
        # Command code, state flag, payload size (Dangerous protocol :))
        # Length for AMS header- lenght of payload
        lenght= self.payload.buffer_info()[1]
        header.extend(struct.pack('<HHL', self.command_id, self.state_flag, lenght))
        #Error code (Always 0 in our case) and invoke id
        header.extend(struct.pack('<LL', 0, invoke_id))
        #Check the size of the header. 
        if not header.buffer_info()[1] == 38:
            print 'Header size: %f'  %(header.buffer_info()[1])
            raise RuntimeError('Wrong ADS header size detected. This is a bug, please fix it.')        
        # *** Add payload
        self.packet=header
        if not self.payload == None:
            self.packet.extend(self.payload)
        return self.packet
    
    def decode_header(self, response):
        '''Decodes the header of the provided (partial) response. Returns a dictionary with header data and the remaining payload'''
        try:
            ams_tcp_header=struct.unpack('<HL', response[0:6]) # ams_tcp header
            tartget_id=struct.unpack('<6B', response[6:12])
            target_port=struct.unpack('<H', response[12:14]) # ams header
            source_id=struct.unpack('<6B', response[14:20])
            source_port=struct.unpack('<H', response[20:22])
            dec_header=struct.unpack('<HHLLL', response[22:38])
        except:
            print "Decoding of header failed"
            print self._print_data(response[0:32])
            raise
        result={'target_id': '%d.%d.%d.%d.%d.%d' %(tartget_id[0], tartget_id[1], tartget_id[2], tartget_id[3], tartget_id[4], tartget_id[5]), \
                'target_port':      target_port[0], \
                'source_id': '%d.%d.%d.%d.%d.%d' %(source_id[0], source_id[1], source_id[2], source_id[3], source_id[4], source_id[5]), \
                'source_port':          source_port[0], \
                'command_id':           dec_header[0],\
                'state_flags':          dec_header[1], \
                'ams_tcp_reserved':     ams_tcp_header[0], \
                'ams_packet_lenght':   ams_tcp_header[1], \
                'payload_lenght':          dec_header[2], \
                'error_code':           dec_header[3], \
                'invoke_id':            dec_header[4]}
        return result, response[38:]
    
    def _print_data(self, data):
        '''Prints binary data for debugging purposes'''
        print ":".join("{:02x}".format(ord(c)) for c in data)
        try:
            print "Length: %d" %(data.buffer_info()[1])
        except:
            try:
                print "Length: %d" %(len(data))
            except:
                pass
    
    def _print_decoded_header(self, data):
        '''Decodes the provided header and prints it for debugging purposes'''
        print self.decode_header(data)
          
    def __get_bin_id(self, ads_id):
        '''Converts an ams id string into a binary form'''
        pattern = re.compile('(\d+)\.(\d+)\.(\d+)\.(\d+)\.(\d+)\.(\d+)')
        result=array.array('c')
        #print result
        for num in pattern.match(ads_id).groups():
            result.append(struct.pack('!B', int(num)))
        return result

    def _check_ret_err_code(self, err_code, rec_header):
        '''Checks the returned ADS error codes and provides appropriate debugging information''' 
        if not err_code == 0:
            try:
                errmesg= 'PLC returned non zero error code: %d, %s.' %(err_code, return_codes[err_code])
            except KeyError:
                errmesg= 'PLC returned non zero error code: %d ' %(err_code)
            print errmesg
            print 'The header of the transmitted package was:'
            self._print_decoded_header(self.packet)
            print 'The sent payload was:'
            self._print_data(self.payload)
            print 'The header of the received package was:'
            print rec_header
            raise RuntimeError(errmesg)

class ads_cmd_read_dev_info(_ads_packet):
    '''Provides a packet and decoder functionality for the "ADS Read Device Info" command'''
    def __init__(self):
        '''Generate the request packet'''
        _ads_packet.__init__(self)
        self.command_id=ads_cmd_codes['read_dev_info']
        self.state_flag=ads_state_flags['command_request']
        
    def decode_response(self, response):
        '''Decode the returned response '''
        result, payload=self.decode_header(response)
        dec_payload=struct.unpack('<LBBH16s', payload)
        result['result']= dec_payload[0]
        result['major_ver']= dec_payload[1]
        result['minor_ver']= dec_payload[2]
        result['build_ver']= dec_payload[3]
        result['dev_name']= dec_payload[4]
        return result
   
class ads_cmd_read(_ads_packet):
    '''Provides a packet and decoder functionality for the "ADS Read" command'''
    #Usage: Instanciate, get assembled packet, call decode response to decode PLC response'''
    def __init__(self, idx_grp, idx_offset, data_type):
        '''Generate the request packet'''
        _ads_packet.__init__(self)
        self.command_id=ads_cmd_codes['read']
        self.state_flag=ads_state_flags['command_request']
        self.add_var(idx_grp, idx_offset, data_type)
        
    def add_var(self, idx_grp, idx_offset, data_type):
        '''Generate ads payload data and decoder information for a given variable'''
        # TODO: Test if multiple variables may be read in on packet
        lenght=struct.calcsize('<'+data_type) # Compute the size of the data to read in PLC memory
        payload=struct.pack('<LLL',idx_grp, idx_offset,  lenght) # Assemble the payload to be send to the plc
        self.payload.extend(payload) # Save the payload 
        self.decoderstring=data_type # Save the decoder string for the return value

    def decode_response(self, response):
        '''Decode the returned response '''
        result, payload=self.decode_header(response)
        dec_payload=struct.unpack('<LL' + self.decoderstring, payload)
        result['result']=dec_payload[0]
        result['data_length']=dec_payload[1]
        result['data']=dec_payload[2:]
        return result

class ads_cmd_write(_ads_packet):
    '''Provides a packet and decoder functionality for the "ADS Write" command'''
    def __init__(self, idx_grp, idx_offset, data_type, data):
        '''Generate the request packet'''
        _ads_packet.__init__(self)
        self.command_id=ads_cmd_codes['write']
        self.state_flag=ads_state_flags['command_request']
        self.add_var(idx_grp, idx_offset, data_type, data)
        
    def add_var(self, idx_grp, idx_offset, data_type, data):
        '''Generate ads payload data and decoder information for a given variable'''
        # TODO: Test if multiple variables may be read in on packet
        lenght=struct.calcsize('<'+data_type) # Compute the size of the data to read in PLC memory
        payload=struct.pack('<LLL',idx_grp, idx_offset,  lenght) # Assemble the payload to be send to the plc
        self.payload.extend(payload) # Save the payload 
        try:
            self.payload.extend(struct.pack('<'+data_type, data))
        except:
            self.payload.extend(struct.pack('<'+data_type, *data))
        
    def decode_response(self, response):
        '''Decode the returned response '''
        result, payload=self.decode_header(response)
        dec_payload=struct.unpack('<L', payload)
        result['result']= dec_payload[0]
        return result

class ads_cmd_read_state(_ads_packet):
    def __init__(self):
        _ads_packet.__init__(self)
        self.command_id=ads_cmd_codes['read_state']
        self.state_flag=ads_state_flags['command_request']
         
    def decode_response(self, response):
        '''Decode the returned response '''
        result, payload=self.decode_header(response)
        dec_payload=struct.unpack('<LHH', payload)
        result['result']=dec_payload[0]
        result['ads_state']= dec_payload[1]
        result['dev_state']=dec_payload[2]
        return result

class ads_cmd_write_ctrl(_ads_packet):
    #TODO: Test this
    def __init__(self, ads_socket, ads_state, dev_state, data):
        '''Performs the write control command (whatever that is) Data must be provided as array('c')'''
        _ads_packet.__init__(self, ads_socket)
        self.command_id=ads_cmd_codes['write_control']
        self.state_flag=ads_state_flags['command_request']
        lenght=data.itemsize        
        payload=struct.pack('<HHL',ads_state, dev_state, lenght) # Assemble the payload to be send to the plc
        self.payload.extend(payload) # Save the payload 
        self.payload.extend(data)
        
    def decode_response(self, response):
        '''Decode the returned response '''
        result, payload=self.decode_header(response)
        dec_payload=struct.unpack('<L', payload)
        result['result']=dec_payload[0]
        return result

class ads_cmd_add_dev_notif(_ads_packet):
    #TODO: Test this
    def __init__(self, ads_socket, idx_group, idx_offset, lenght, transm_mode, max_delay, cycle_time):
        '''Performs the write control command (whatever that is) Data must be provided as array('c')'''
        _ads_packet.__init__(self, ads_socket)
        self.command_id=ads_cmd_codes['add_dev_notification']
        self.state_flag=ads_state_flags['command_request']
        self.payload=struct.pack('<LLLLLL',idx_group, idx_offset, lenght, transm_mode, max_delay, cycle_time) # Assemble the payload to be send to the plc
        self.payload.extend('<LLLL', 0, 0, 0, 0) # pad reserved with 0. 
        
    def decode_response(self, response):
        '''Decode the returned response '''
        result, payload=self.decode_header(response)
        result['result']=struct.unpack('<L', payload[0:4])
        self._check_ret_err_code(result['result'], result)
        result['notif_handle']=struct.unpack('<L', payload[4:8])
        return result   

class ads_cmd_del_dev_notif(_ads_packet):
    #TODO: Test this
    def __init__(self, ads_socket, notif_handle):
        '''Performs the write control command (whatever that is) Data must be provided as array('c')'''
        _ads_packet.__init__(self, ads_socket)
        self.command_id=ads_cmd_codes['del_dev_notification']
        self.state_flag=ads_state_flags['command_request']
        self.payload=struct.pack('<L',notif_handle) # Assemble the payload to be send to the plc
        
    def decode_response(self, response):
        '''Decode the returned response '''
        result, payload=self.decode_header(response)
        dec_payload=struct.unpack('<L', payload)
        self._check_ret_err_code(result['result'], result)
        result['result']=dec_payload[0]
        return result

class ads_cmd_dev_notif(_ads_packet):
    # TODO: Implement this!
    def __init__(self):
        _ads_packet.__init__(self)
        pass

class ads_cmd_read_write(_ads_packet):
    def __init__(self, idx_group, idx_offset, read_datatype, write_data):
        _ads_packet.__init__(self)
        self.command_id=ads_cmd_codes['read_write']
        self.state_flag=ads_state_flags['command_request']
        write_buf=array.array('c')
        write_buf.extend(write_data)
        write_size=write_buf.buffer_info()[1]
        self.payload=array.array('c')
        self.payload.extend(struct.pack('<LLLL',idx_group, idx_offset, struct.calcsize(read_datatype), write_size)) # Assemble the payload to be send to the plc
        self.payload.extend(write_buf)  
        self.decoderstring=read_datatype
        
    def decode_response(self, response):
        '''Decode the returned response '''
        result, payload=self.decode_header(response)
        dec_payload=struct.unpack('<LL', payload[0:8])
        result['result']=dec_payload[0]
        result['data_lenght']=dec_payload[1]
        self._check_ret_err_code(result['result'], result)
        result['data']=struct.unpack('<'+self.decoderstring, payload[8:])
        return result
