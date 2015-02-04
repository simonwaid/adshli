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

cmd_codes= {'read_dev_info':1, 'read':2, 'write':3,  'read_state':4, 'write_control':5, 'add_dev_notification':6, \
                'del_dev_notification':7,  'dev_notification':8, 'read_write':9}

state_flags= {'command_request':0x04}

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
         'ADSIOFFS_DEVDATA_DEVSTATE': 0x0002, \
         'SUM_CMD_READ': 0xf080, \
         'SUM_CMD_WRITE':0xf081, \
         'SUM_CMD_RW': 0xf082}



class _ads_packet:
    '''This class provides common packet assembly functionality for the more specific packet assembly classes'''
    def __init__(self):
        pass
    
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
        print data
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
          
    def _get_bin_id(self, ads_id):
        '''Converts an ams id string into a binary form'''
        pattern = re.compile('(\d+)\.(\d+)\.(\d+)\.(\d+)\.(\d+)\.(\d+)')
        result=array.array('c')
        #print result
        for num in pattern.match(ads_id).groups():
            result.append(struct.pack('!B', int(num)))
        return result

    def _check_ret_err_code(self, err_code, rec_header, cmd):
        '''Checks the returned ADS error codes and provides appropriate debugging information''' 
        if not err_code == 0:
            try:
                errmesg= 'PLC returned non zero error code: %d, %s.' %(err_code, return_codes[err_code])
            except:
                errmesg= 'PLC returned non zero error code: %d ' %(err_code)
            print '\n', errmesg
            print 'The header of the transmitted package was:'
            self._print_decoded_header(self.packet)
            print 'The command header was:'
            self._print_data(cmd.cmd_header)
            print 'The command payload was:'
            self._print_data(cmd.cmd_payload)
            
            print 'The header of the received package was:'
            print rec_header
            raise RuntimeError(errmesg)

class _single_cmd_packet(_ads_packet):
    def __init__(self):
        _ads_packet.__init__(self)
        # Saves the command header
        self.cmd_header=array.array('c')
        # Saves the payload of the command
        self.cmd_payload=array.array('c')
        
    def get_packet(self, invoke_id, ads_connection):
        '''Returns the fully assembled ads packet ready to be send'''
        # Assemble the payload so we know its size
        payload=array.array('c')
        payload.extend(self.cmd_header)
        payload.extend(self.cmd_payload)
        # *** Assemble header
        # Length for TCP AMS header 32 byte AMS header plus payload
        lenght= payload.buffer_info()[1] + 32
        #Connection details from socket data 
        header=array.array('c')
        header.extend(struct.pack('<HL', 0, lenght))
        header.extend(self._get_bin_id(ads_connection.ams_netid_target))
        header.extend(struct.pack('<H', ads_connection.ams_port_target))
        header.extend(self._get_bin_id(ads_connection.ams_netid_source))
        header.extend(struct.pack('<H', ads_connection.ams_port_source))
        #Check the size of the header. 
        if not header.buffer_info()[1] == 22:
            print 'Header size: %f'  %(header.buffer_info()[1])
            raise RuntimeError('Wrong ADS header size detected during header assembly. Please check the provided connection setting.')
        # Command code, state flag, payload size (Dangerous protocol :))
        # Length for AMS header- lenght of payload
        lenght= payload.buffer_info()[1]
        header.extend(struct.pack('<HHL', self.command_id, self.state_flag, lenght))
        #Error code (Always 0 in our case) and invoke id
        header.extend(struct.pack('<LL', 0, invoke_id))
        #Check the size of the header. 
        if not header.buffer_info()[1] == 38:
            print 'Header size: %f'  %(header.buffer_info()[1])
            raise RuntimeError('Wrong ADS header size detected. This is a bug, please fix it.')        
        # *** Add payload
        self.packet=header
        self.packet.extend(payload)
        return self.packet
    
class _sum_cmd_packet(_ads_packet):
    '''Generate one sum command packet from a series of single command'''
    def __init__(self):
        _ads_packet.__init__(self)
        self.cmdlist=[]

    def get_packet(self, invoke_id, ads_connection):
        '''Returns the packet'''
        # The sum command is issued by calling readwrite consists of a header and a payload.
        # Lets assemble the payload for readwrite and use readwrite to compose the packet.
        
        # The payload consitst of the headers of the individual commands.
        payload=array.array('c')
        for cmd in self.cmdlist:
            payload.extend(cmd.cmd_header)
        # Now we can add the payload of the individual commands
        for cmd in self.cmdlist:
            payload.extend(cmd.cmd_payload)
        # We have the payload now we need a decoder for readwrite
        self.dec_header=''
        self.dec_payload='' 
        for cmd in self.cmdlist:
            self.dec_header+=self.decoderheader
            self.dec_payload+=cmd.decoderstring
        self.decoder=self.dec_header+self.dec_payload
        # Now assemble the packet using readwrite. The index offset conatins the number of commands sent
        # Note: the decoder supplied to the readwrite command will only be used to compute the readlenght
        # We have our onwn decoderfunction as we have to handle ADS errors        
        self.cmd=ads_cmd_read_write(self.idx_grp, len(self.cmdlist), self.decoder, payload)
        self.packet=self.cmd.get_packet(invoke_id, ads_connection)
        #result, payload=self.cmd.decode_header(self.packet)
        return self.packet
    
    def decode_response(self, response):
        # Let readwrite decode the response first so we get the response to the sum command
        result, payload=self.cmd._decode_cmd_header(response)
        # Decode the headers and check for errors
        results=[]
        offset=0
        lenght_header=struct.calcsize(self.decoderheader)
        for cmd in self.cmdlist:
            dec_payload=struct.unpack('<'+self.decoderheader, payload[offset:offset+lenght_header])
            result={}
            result['result']=dec_payload[0]
            try:
                result['data_lenght']=dec_payload[1]
            except:
                pass
            self._check_ret_err_code(result['result'], result, cmd)
            results.append(result)
            offset+=lenght_header
        # Decode the payload:
        i=0
        for cmd in self.cmdlist:
            # Size of the data to decode
            lenght=struct.calcsize('<'+ cmd.decoderstring)
            # Decode
            dec_payload=struct.unpack('<'+cmd.decoderstring, payload[offset:offset+lenght])
            results[i]['data']=dec_payload
            i+=1
            offset+=lenght
        return results
        
class ads_sum_cmd_rw(_sum_cmd_packet):
    def __init__(self):
        _sum_cmd_packet.__init__(self)
        self.idx_grp=idx_grp['SUM_CMD_RW']
        self.decoderheader='LL'

    def add_var(self, idx_group, idx_offset, read_datatype, write_data):
        '''Append a variable to the current command list'''
        # We collect all commands first.
        cmd=ads_cmd_read_write(idx_group, idx_offset, read_datatype, write_data)
        self.cmdlist.append(cmd)
        
class ads_sum_cmd_read(_sum_cmd_packet):
    def __init__(self):
        _sum_cmd_packet.__init__(self)
        self.idx_grp=idx_grp['SUM_CMD_READ']
        self.decoderheader='L'

    def add_var(self, idx_grp, idx_offset, data_type):
        '''Append a variable to the current command list'''
        # We collect all commands first.
        cmd=ads_cmd_read(idx_grp, idx_offset, data_type)
        self.cmdlist.append(cmd)

class ads_sum_cmd_write(_sum_cmd_packet):
    def __init__(self):
        _sum_cmd_packet.__init__(self)
        self.idx_grp=idx_grp['SUM_CMD_WRITE']
        self.decoderheader='L'
        
    def add_var(self, idx_grp, idx_offset, data_type, data):
        '''Append a variable to the current command list'''
        # We collect all commands first.
        cmd=ads_cmd_write(idx_grp, idx_offset, data_type, data)
        self.cmdlist.append(cmd)


class ads_cmd_read_dev_info(_single_cmd_packet):
    '''Provides a packet and decoder functionality for the "ADS Read Device Info" command'''
    def __init__(self):
        '''Generate the request packet'''
        _single_cmd_packet.__init__(self)
        self.command_id=cmd_codes['read_dev_info']
        self.state_flag=state_flags['command_request']
        
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
   
class ads_cmd_read(_single_cmd_packet):
    '''Provides a packet and decoder functionality for the "ADS Read" command'''
    #Usage: Instanciate, get assembled packet, call decode response to decode PLC response'''
    def __init__(self, idx_grp, idx_offset, data_type):
        '''Generate the request packet'''
        _single_cmd_packet.__init__(self)
        self.command_id=cmd_codes['read']
        self.state_flag=state_flags['command_request']
        self.add_var(idx_grp, idx_offset, data_type)
        
    def add_var(self, idx_grp, idx_offset, data_type):
        '''Generate ads payload data and decoder information for a given variable'''
        # TODO: Test if multiple variables may be read in on packet
        lenght=struct.calcsize('<'+data_type) # Compute the size of the data to read in PLC memory
        cmd_header=struct.pack('<LLL',idx_grp, idx_offset,  lenght) # Assemble the payload to be send to the plc
        self.cmd_header.extend(cmd_header) # Save the payload 
        self.decoderstring=data_type # Save the decoder string for the return value

    def decode_response(self, response):
        '''Decode the returned response '''
        result, payload=self.decode_header(response)
        dec_payload=struct.unpack('<LL' + self.decoderstring, payload)
        result['result']=dec_payload[0]
        result['data_length']=dec_payload[1]
        result['data']=dec_payload[2:]
        return result

class ads_cmd_write(_single_cmd_packet):
    '''Provides a packet and decoder functionality for the "ADS Write" command'''
    def __init__(self, idx_grp, idx_offset, data_type, data):
        '''Generate the request packet'''
        _single_cmd_packet.__init__(self)
        self.command_id=cmd_codes['write']
        self.state_flag=state_flags['command_request']
        self.add_var(idx_grp, idx_offset, data_type, data)
        self.decoderstring=''
        
    def add_var(self, idx_grp, idx_offset, data_type, data):
        '''Generate ads payload data and decoder information for a given variable'''
        # TODO: Test if multiple variables may be read in on packet
        lenght=struct.calcsize('<'+data_type) # Compute the size of the data to read in PLC memory
        cmd_header=struct.pack('<LLL',idx_grp, idx_offset,  lenght) # Assemble the payload to be send to the plc
        self.cmd_header.extend(cmd_header) # Save the payload 
        try:
            self.cmd_payload.extend(struct.pack('<'+data_type, data))
        except:
            self.cmd_payload.extend(struct.pack('<'+data_type, *data))
        
    def decode_response(self, response):
        '''Decode the returned response '''
        result, payload=self.decode_header(response)
        dec_payload=struct.unpack('<L', payload)
        result['result']= dec_payload[0]
        return result

class ads_cmd_read_state(_single_cmd_packet):
    def __init__(self):
        _single_cmd_packet.__init__(self)
        self.command_id=cmd_codes['read_state']
        self.state_flag=state_flags['command_request']
         
    def decode_response(self, response):
        '''Decode the returned response '''
        result, payload=self.decode_header(response)
        dec_payload=struct.unpack('<LHH', payload)
        result['result']=dec_payload[0]
        result['ads_state']= dec_payload[1]
        result['dev_state']=dec_payload[2]
        return result

class ads_cmd_write_ctrl(_single_cmd_packet):
    #TODO: Test this
    def __init__(self, ads_socket, ads_state, dev_state, data):
        '''Performs the write control command (whatever that is) Data must be provided as array('c')'''
        _single_cmd_packet.__init__(self, ads_socket)
        self.command_id=cmd_codes['write_control']
        self.state_flag=state_flags['command_request']
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

class ads_cmd_add_dev_notif(_single_cmd_packet):
    #TODO: Test this
    def __init__(self, ads_socket, idx_group, idx_offset, lenght, transm_mode, max_delay, cycle_time):
        '''Performs the write control command (whatever that is) Data must be provided as array('c')'''
        _single_cmd_packet.__init__(self, ads_socket)
        self.command_id=cmd_codes['add_dev_notification']
        self.state_flag=state_flags['command_request']
        self.payload=struct.pack('<LLLLLL',idx_group, idx_offset, lenght, transm_mode, max_delay, cycle_time) # Assemble the payload to be send to the plc
        self.payload.extend('<LLLL', 0, 0, 0, 0) # pad reserved with 0. 
        
    def decode_response(self, response):
        '''Decode the returned response '''
        result, payload=self.decode_header(response)
        result['result']=struct.unpack('<L', payload[0:4])
        self._check_ret_err_code(result['result'], result)
        result['notif_handle']=struct.unpack('<L', payload[4:8])
        return result   

class ads_cmd_del_dev_notif(_single_cmd_packet):
    #TODO: Test this
    def __init__(self, ads_socket, notif_handle):
        '''Performs the write control command (whatever that is) Data must be provided as array('c')'''
        _single_cmd_packet.__init__(self, ads_socket)
        self.command_id=cmd_codes['del_dev_notification']
        self.state_flag=state_flags['command_request']
        self.payload=struct.pack('<L',notif_handle) # Assemble the payload to be send to the plc
        
    def decode_response(self, response):
        '''Decode the returned response '''
        result, payload=self.decode_header(response)
        dec_payload=struct.unpack('<L', payload)
        self._check_ret_err_code(result['result'], result)
        result['result']=dec_payload[0]
        return result

class ads_cmd_dev_notif(_single_cmd_packet):
    # TODO: Implement this!
    def __init__(self):
        _single_cmd_packet.__init__(self)
        pass

class ads_cmd_read_write(_single_cmd_packet):
    def __init__(self, idx_group, idx_offset, read_datatype, write_data):
        _single_cmd_packet.__init__(self)
        self.command_id=cmd_codes['read_write']
        self.state_flag=state_flags['command_request']
        write_buf=array.array('c')
        write_buf.extend(write_data)
        write_size=write_buf.buffer_info()[1]
        # We generate the header and payload separately so they can be used for sum commands
        read_size=struct.calcsize('<'+read_datatype)
        self.cmd_header.extend(struct.pack('<LLLL',idx_group, idx_offset, read_size, write_size)) # Assemble the payload to be send to the plc
        self.cmd_payload.extend(write_buf)
        # Decoderstring for single commands
        self.decoderstring=read_datatype
    
    def _decode_cmd_header(self, response):
        '''Decodes the command header of the returned packet'''
        result, payload=self.decode_header(response)
        dec_payload=struct.unpack('<LL', payload[0:8])
        result['result']=dec_payload[0]
        result['data_lenght']=dec_payload[1]
        self._check_ret_err_code(result['result'], result, self)
        return result, payload[8:]
    
    def decode_response(self, response):
        '''Decode the returned response '''
        result, payload = self._decode_cmd_header(response)
        try:
            result['data']=struct.unpack('<'+self.decoderstring, payload)
        except:
            self._print_data(payload)
            raise
        return result
