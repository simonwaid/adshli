from adshli.connection import ads_connection
import adshli.protocol as adsprotocol 
from adshli.hli import ads_device, ads_variable, idx_grp

plc_ams_id="10.23.23.57.1.1"
plc_ams_port=851
plc_ip_adr="127.0.0.1"
plc_ip_port=48898
pc_ams_id="10.23.23.57.1.5"
pc_ams_port=801
timeout=5
var_name='Main.I_b_SafeState'
var_type='?'
#var_name='GVL.fb_maps.Height'
#var_type='100f'


def main():
    # *** Reading and writing variables using the low level interface
    print 'Accessing the PLC using the low level ADS interface'
    connection=ads_connection(plc_ams_id, plc_ams_port, pc_ams_id, pc_ams_port)
    connection.open(plc_ip_adr, plc_ip_port, timeout)
    #Read the device name
    cmd=adsprotocol.ads_cmd_read_dev_info()
    dev_name= connection.execute_cmd(cmd)['dev_name']
    print 'Device name: ', dev_name
    #Read the device and ads state
    cmd=adsprotocol.ads_cmd_read_state()
    retval=connection.execute_cmd(cmd)
    ads_state=retval['ads_state']
    dev_state=retval['dev_state']
    print 'ADS state: ', ads_state
    print 'Device state: ', dev_state
    #Get a handle for a variable
    cmd=adsprotocol.ads_cmd_read_write(idx_grp['SYM_HNDBYNAME'], 0x0, 'L',  var_name)
    handle= connection.execute_cmd(cmd)['data'][0]
    #Read the variable
    cmd=adsprotocol.ads_cmd_read(idx_grp['SYM_VALBYHND'], handle, var_type)
    var_content=connection.execute_cmd(cmd)['data'][0]
    print 'Variable contents: ',  var_content
    #Write back the variable
    cmd=adsprotocol.ads_cmd_write(idx_grp['SYM_VALBYHND'], handle, var_type, var_content)
    connection.execute_cmd(cmd)
    connection.close()
    # ***************************************************
    # *** Do the same using the high level interface
    # Open the connection
    print '\n\nNow accessing the PLC using the high level ADS interface'
    connection=ads_connection(plc_ams_id, plc_ams_port, pc_ams_id, pc_ams_port)
    connection.open(plc_ip_adr, plc_ip_port, timeout)
    #Instanciate device: this immediately reads the device information
    device=ads_device(connection)
    print 'Device name: ', device.device_name
    print 'ADS state: ', device.ads_state
    print 'Device state: ', device.device_state
    #Accessing the variable: First instanciate, then read and write back 
    variable=ads_variable(connection, var_name, var_type)
    variable_content=variable.read()
    print 'Variable content: ', variable_content
    variable.write(variable_content)
    connection.close()


if __name__ == '__main__':
    main()


