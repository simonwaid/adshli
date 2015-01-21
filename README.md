# adshli

Introduction
------------

ADSHLI implements a python client for the Beckhoff Twincat AMS/ADS protocoll. It provides two APIs. The first is a low level API allowing you to directly send ADS commands to the PLC (protocol). The second (hli) provides convenience funtions to make access to the PLC as easy as possible without having to care too much about the unerlying protocoll.

Usage
-----

See "sample_code.py" for an example on how to use the client.

Installation
------------

Notes
-----

The implementation of the protocol is not complete yet. So far the following ADS commands are implemented and tested:
- ADS Read Device Info 
- ADS Read 
- ADS Write 
- ADS Read State
- ADS Read Write

The following ADS commands are only partially implemented and not tested:
- ADS Write Control 
- ADS Add Device Notification 
- ADS Delete Device Notification 
- ADS Device Notification 

The high level API currently supports:
- Reading the Device info and state
- Reading and writing single variables using handles (including large arrays)

Currently on the list for implementation are:
- Write support for the device state
- Grouping of variables for reading/writing using ADS sum commands

 
