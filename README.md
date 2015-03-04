# adshli

Introduction
------------

ADSHLI implements a python client for the Beckhoff Twincat AMS/ADS protocoll. It provides two APIs. The first is a low level API allowing you to directly send ADS commands to the PLC (see protocol.py). The second  (see hli.py) provides convenience funtions to make access to the PLC in an fast and easy way and without having to care about the underlying protocoll.

Limitations
-----------

ADSHLI uses TCP/IP to connect to the Twincat AMS/ADS router. Beckhoff currently limits (for whatever reason) the number of available AMS/ADS routes via TCP/IP to one per IP address. If you need more than one connection there are two possibilities to overcome the issue: 
(i) If you are on Windows, you may use another library using a transport protocol not subjected to the abovementioned limitation. Pyads seems to be a good option for python here.
(ii) You put a second, unlimited ads router that does ADS network address translation (NAT) in front of the crippled Beckhoff router. I've implemented something like that in adsnat2.py. Note that it is currently limited to one AMS/ADS port per IP, but you can easily change that.

Usage
-----

See "sample_code.py" for an example on how to use the library.

Installation
------------

Run python setup.py install

Notes
-----

The implementation of the protocol is not yet complete. So far the following ADS commands are implemented and tested:
- ADS Read Device Info 
- ADS Read 
- ADS Write 
- ADS Read State
- ADS Read Write
- ADS Read via sum command
- ADS Write via sum command
- ADS Read Write via sum command

The high level API currently supports:
- Reading the Device info and state
- Reading and writing single variables using handles (including large arrays)
- Grouping of variables for efficient access using ADS sum-commands

The following ADS commands are only partially implemented and currently do not work:
- ADS Write Control 
- ADS Add Device Notification 
- ADS Delete Device Notification 
- ADS Device Notification 
- Write support for the device state

I you need one the missing AMS/ADS commands implementing it should be fast, as the protocol is simple and well documented.
 
