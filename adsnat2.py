#adsnat2
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

from adshli.connection import ads_connection, read_ams_packet
import adshli.connection as adsconnection
import adshli.protocol as adsprotocol 
from threading import Lock, Event 
from Queue import Queue
import socket
import asyncore

# Connection to PLC
plc_ams_id="10.23.23.57.1.1"
plc_ams_port=851
plc_ip_adr="127.0.0.1"
plc_ip_port=48898
pc_ams_id="10.23.23.57.1.12"
pc_ams_port=801
timeout=1

#Listening
listen_address=('', 48899)
server_address=("127.0.0.1", 48898)

bufsize=1024

def main():
    shutdown=Event()
    # Open connection to target PLC
    print 'Opening connection to plc...'
    connection=ads_connection(plc_ams_id, plc_ams_port, pc_ams_id, pc_ams_port)
    # Bind socket to address
    conn_server=t_server(connection) #, queue_plc_pc, queue_pc_plc)
    print 'Connection established.'
    wait_connect(listen_address, conn_server)
    print 'Now waiting for incomming connections from clients...'
    try:
        while True:
            asyncore.loop(timeout=0.1, count=10)
    except asyncore.ExitNow:
        pass
    except KeyboardInterrupt:
        pass
    print 'End.'


class tranceiver():
    def __init__(self, ads_conn):
        self.ads_conn=ads_conn
        self.buffer_out=""
        self.send_queue=Queue()
        self.receive_lock=Lock()
        self.buffer_in=''
        self.chunk_size=1024
        
    def assemble_packet(self, header, payload, ads_conn):
        # Assemble packet to be sent to PLC
        new_packet=adsprotocol.cmd_packet()
        # Set parameters for header 
        new_packet.command_id=header['command_id']
        new_packet.state_flag=header['state_flags']
        new_packet.error_code=header['error_code']
        # Set payload
        new_packet.cmd_payload=payload
        invoke_id=header['invoke_id']
        packet=new_packet.get_packet(invoke_id, ads_conn)
        return packet
    
    def handle_write(self):
        if len(self.buffer_out) >0:
            sent = self.send(self.buffer_out[:self.chunk_size])
            if sent== None:
                quit()
            self.buffer_out = self.buffer_out[sent:]
        else:
            self.buffer_out=self.send_queue.get(block=False).tostring()
        
    def handle_read(self):
        with self.receive_lock:
            # Read response
            self.buffer_in+=self.recv(self.chunk_size)
            if len(self.buffer_in) >= adsconnection.total_header_size:
                # Decode header
                header_data, payload=adsprotocol.decode_ads_header(self.buffer_in)
                total_packet_size=header_data['ams_packet_lenght']+adsconnection.total_header_size-adsconnection.ams_header_size
                if total_packet_size <= len(self.buffer_in):
                    #Process
                    header_data, payload=adsprotocol.decode_ads_header(self.buffer_in[:total_packet_size])
                    self.process_input(header_data, payload)
                    self.buffer_in=self.buffer_in[total_packet_size:]
            
    def writable(self):
        return (len(self.buffer_out) > 0) or not self.send_queue.empty() 
    
    def readable(self):
        return True
    
    def send_d(self, packet):
        self.send_queue.put(packet)
    
    
class t_client(tranceiver, asyncore.dispatcher):
    def __init__(self, tcp_conn, ads_conn, server, addr):
        asyncore.dispatcher.__init__(self, sock=tcp_conn)
        self.ads_conn_client=None
        self.ads_conn_server=ads_conn
        self.server=server
        self.addr=addr
        tranceiver.__init__(self, ads_conn)
        #print self
    
    def process_input(self, header, payload):
        # Create ADS connection to client from received data and register with server
        if self.ads_conn_client==None:
            self.ads_conn_client=ads_connection(header['source_id'], header['source_port'], header['target_id'], header['target_port'])
            self.server.register_client(self)
            print 'First ADS packet received from %s.' %(repr(self.addr))
            # Assemble outgoing packet and send
        packet=self.assemble_packet(header, payload, self.ads_conn_server)                
        self.server.send_d(packet)
            
    def handle_close(self):
        print 'Client disconnected: %s.' %(repr(self.addr))
        self.close()
        
class wait_connect(asyncore.dispatcher):
    def __init__(self, tcp_l_adr, server):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind(tcp_l_adr)
        self.listen(5)
        self.server=server
        self.ads_port=600
        self.clients=[]

        
    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            print 'Incoming connection from %s. Assigned ADS port for server communication: %d.' %(repr(addr), self.ads_port)
            ads_conn=fake_ads_connection(self.ads_port)
            self.ads_port+=1
            #print 'Starting client instance' 
            handler = t_client(sock, ads_conn, self.server, addr)
            self.clients.append(handler)
            print 'Ready to receive data from the client'
        
class t_server(tranceiver, asyncore.dispatcher):
    def __init__(self, ads_conn):
        tranceiver.__init__(self, ads_conn)
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect(server_address)
        self.client_queue=Queue()
        self.clients=[]
    
    def process_input(self, header, payload):
        # Update client list
        self.update_client_list()
        # associate packet with client
        myclient=None
        for client in self.clients:
            if client.ads_conn_server.ams_port_source == header['target_port']:
                myclient=client
        # Assemble outgoing packet and send
        packet=self.assemble_packet(header, payload, myclient.ads_conn_client)
        myclient.send_d(packet) 

    def update_client_list(self):
        '''Update the list of clients'''
        done=False
        while not done:
            try:
                self.clients.append(self.client_queue.get(block=False))
            except:
                done=True                    
    
    def register_client(self, client):
        self.client_queue.put(client)

    def handle_close(self):
        print 'The Server closed the connection... shutting down.'
        self.close()
        raise asyncore.ExitNow('Server is quitting!')
    
class fake_ads_connection(ads_connection):
    def __init__(self, port):
        ads_connection.__init__(self, plc_ams_id, plc_ams_port, pc_ams_id, port)
        
if __name__ == '__main__':
    main()