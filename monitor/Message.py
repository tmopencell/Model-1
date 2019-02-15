import base64
import binascii
import json
import uuid
import serial
import socket
import struct
import sys
import threading
import time
import fcntl


"""
.. module:: Message
    :platform: Raspbian
    :synopsis: Incubator module for serial communication between RPi and Arduino

"""


class Interface():
    """ Class that holds everything important concerning communication.

    Mainly stuff about the serial connection, but also
    identification and internet connectivity. Objects indended
    to be displayed on the Incubator LCD should be found in this class.

    Attributes:
        serial_connection (:obj:`Serial`): serial connection from GPIO
    """
    def __init__(self):
      ''' Initialization
      Args:
        None
      '''
      self.serial_connection = serial.Serial('/dev/serial0', 9600)

    def connects_to_internet(self, host="8.8.8.8", port=53, timeout=3):
      """ Tests internet connectivity
      Test intenet connectivity by checking with Google
      Host: 8.8.8.8 (google-public-dns-a.google.com)
      OpenPort: 53/tcp
      Service: domain (DNS/TCP)
      Args:
        host (str): the host to test connection
        port (int): the port to use
        timeout (timeout): the timeout value (in seconds)
      """

      try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
      except Exception as err:
        print(err.message)
        return False

    def get_serial_number(self):
      """ Get uniqeu serial number
      Get a unique serial number from the cpu
      Args:
        None
      """
      serial = "0000000000"
      try:
        with open('/proc/cpuinfo','r') as fp:
          for line in fp:
            if line[0:6]=='Serial':
              serial = line[10:26]
        if serial == "0000000000":
          raise TypeError('Could not extract serial from /proc/cpuinfo')
      except FileExistsError as err :
        serial = "0000000000"
        print(err.message)

      except TypeError as err :
        serial = "0000000000"
        print(err.message)
      return serial

    def get_mac_address(self):
      """ Get the ethernet MAC address
      This returns in the MAC address in the canonical human-reable form
      Args:
        None
      """
      hex = uuid.getnode()
      formatted = ':'.join(['{:02x}'.format((hex >> ele) & 0xff) for ele in range(0,8*6,8)][::-1])
      return formatted

class Sensors():
    """ Class to handle sensor communication
    This
    Attributes:
        sensorframe (dict : Dictionary holding all sensor key-value pairs
        verbosity (int) : set sthe amount of information printed to screen
        arduino_link (): Instance of the Interface() class
        lock (): Instance of threading Lock to
        monitor (): Process that continuously read incomming serial messages
    """
    def __init__(self):
        """ Initialization
        """
        # dictionary to hold incubator status
        self.sensorframe = {}

        # set verbosity=1 to view more
        self.verbosity = 1

        self.arduino_link = Interface()

        self.lock = threading.Lock()
        self.monitor = threading.Thread(target=self.monitor_incubator_message)
        self.monitor.setDaemon(True)
        self.monitor.start()

    def __str__(self):
        with self.lock:
            toReturn = self.sensorframe
        return str(toReturn)

    def json_sensorframe(self):
        """ JSON object conaining arduino serial message
        Returns a JSON formated string of the current state
        Args:
            None
        """
        with self.lock:
            toReturn = {'incubator': self.sensorframe}
        return toReturn

    def monitor_incubator_message(self):
        ''' Processes serial messages from Arduino
        This runs continuously to maintain an updated
        status of the sensors from the arduino
        '''
        if (self.verbosity == 1):
            print("starting monitor")
        while True:
            try:
                line = self.arduino_link.serial_connection.readline()
                if self.checksum_passed(line):
                    if (self.verbosity == 1):
                        print("checksum passed")
                    with self.lock:
                        self.save_message_dict(line)
                else:
                    if (self.verbosity == 1):
                        print('Ign: ' + line.decode().rstrip())
            except BaseException:
                time.sleep(1)
                print('Error: ', sys.exc_info()[0])
                # return

    def checksum_passed(self, string):
        ''' Check if the checksum passed
        recompute message checksum and compares with appended hash
        Args:
            string (str): a string containing the message, a separation
            indicator: '||||', follwed by the CRC hash.
        '''
        lineSplit = string.decode().split('||||')
        partCount = len(lineSplit)
        if partCount == 2:
            calcCRC = binascii.crc32(lineSplit[0].encode())
            if format(calcCRC, 'X') == lineSplit[1].rstrip():
                if (self.verbosity == 1):
                    print("CRC32 matches")
                return True
            else:
                if (self.verbosity == 1):
                    print(
                        "CRC32 Fail: calculated " +
                        format(
                            calcCRC,
                            'X') +
                        " but received " +
                        lineSplit[1])
                return False
        else:
            if (self.verbosity == 1):
                print("CRC32 Fail: wrong number of parts")
            return False

    def save_message_dict(self, msg):
        '''
        Takes the serial output from the incubator and creates a dictionary
        using the two letter ident as a key and the value as a value.
        Args:
            msg (string): The raw serial message (including the trailing checksum)
        Only use a message that passed the checksum!
        NOTE: The time stamp from the arduino is replaced here
        '''
        msg_serial = msg.split("||||")[0]
        msg_serial = msg_serial.split(" ")
        self.sensorframe = {}
        self.sensorframe['time'] = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.gmtime())
        for i in range(1, len(msg_serial) - 1, 2):
                # do not add the ID field!
            if not msg_serial[i] == 'ID':
                self.sensorframe[msg_serial[i]] = msg_serial[i + 1]
        return


if __name__ == '__main__':

    test_connections = False
    if test_connections:
        iface = Interface()
        print("Hardware serial number: {}".format(iface.get_serial_number()))
        print("Hardware address (ethernet): {}".format(iface.get_mac_address()))
        print("Can connect to the internet: {}".format(iface.connects_to_internet()))
        print("Can contact the mothership: {}".format(iface.connects_to_internet(host='35.183.143.177', port=80)))
        print("Has serial connection with Arduino: {}".format(iface.serial_connection.is_open))
        del iface

    monitor_serial = False
    if monitor_serial:
        mon = Sensors()
        mon.verbosity = 1
        print("Has serial connection with Arduino: {}".format(mon.arduino_link.serial_connection.is_open))
        print("Displaying serial data")
        while True:
            time.sleep(5)
            print(mon)
        del mon