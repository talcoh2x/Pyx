#!/usr/bin/env python

__author__ = """
tal4.cohen@intel.com (Cohen Tal)
"""

import sys
import serial
import logging
import argparse
import traceback

from time import sleep

BYTES_PER_LINE = 200
IO_TIME = 0.5
DASH = 10 * "===="


class SendToDut(object):

    def __init__(self, serial_port, baudrate, name=None):
        self.__serial_port = serial_port
        self.__baudrate = baudrate
        self.__name = name
        self.__mode = None
        self.__console = None
        self._initialize()

    def _initialize(self, *args, **dargs):
        self.__init_console()

    def __del__(self):
        """ Destructor """
        pass

    def __verify_file(self):
        cmd = 'echo $?'
        self.__non_block_write(cmd + '\x0D')
        leneol = len(b'\n\n')
        line = bytearray()
        while True:
            c = self.console.read(1)
            if c:
                line += c
                if line[-leneol:] == b'\n\n':
                    break
            else:
                break
        #print(bytes(line))
        # TODO: Verfiy if destination file create and return code is 0!
        return True

    def __init_console(self):
        """ Initialize the target serial console
            Create handle to the target serial console port for communication during the test
            :returns status - True if handle created, False otherwise
        """
        status = True
        if self.__serial_port:
            print('Initializing {} console on {}'.format(self.__name, self.__serial_port))
            self.console = serial.Serial(port=self.__serial_port,  timeout=1, baudrate=self.__baudrate)
            if not self.console.isOpen():
                raise Exception("Failed to connect to {}, port: {}, baudrate: {}"
                                .format(self.__name, self.__serial_port, self.__baudrate))

        return status

    def __non_block_write(self, data, mode='ascii'):
        """ Perform non blocking write to target console port
            :param data - String to send to target console port
            :param mode - 'binary' for binary data, 'ascii' for text

            :returns Status - True if operation succeeded, False otherwise
        """
        if mode == 'binary':
            result = self.console.write(data)
        else:
            result = self.console.write(data.encode('utf-8'))

        return result

    def send_file(self, source, destination, quiet=False):
        """ Send time over UART protocol.
        :param source:
        :param destination:
        :param quiet:
        :return:
        """
        data = open(source).read()
        data_size = len(data)
        i = 0
        j = 0
        print('Starting send: {} over UART...'.format(source))
        # Create/zero the file
        self.__non_block_write('\necho -ne > %s\n' % destination)
        # TODO: add verify check
        # if not self.__verify_file():
        #     exit(1)
        sleep(IO_TIME)

        # Loop through all the bytes in the source file and append them to
        # the destination file BYTES_PER_LINE bytes at a time
        while i < data_size:
            j = 0
            dpart = ''

            while j < BYTES_PER_LINE and i < data_size:
                dpart += '\\x%.2X' % int(ord(data[i]))
                j += 1
                i += 1

            self.__non_block_write('\necho -ne "%s" >> %s\n' % (dpart, destination))
            sleep(IO_TIME)

            # Show upload status
            if not quiet:
                print('Upload status: {} / {}'.format(i, data_size))
                sleep(.001)

        status = True if i == data_size else False

        msg = 'Uploaded {} bytes from {} to {}'.format(i, source, destination)
        sleep(2)  # For I/O.
        if status:
            print(msg)
            print('Transfer complete')
        else:
            print('[ERROR] Incomplete Transfer')

        return status


if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser(description='API: Send to DUT over Serial connection')
        parser.add_argument('--name', dest='name', type=str, default='Dut',
                            action='store', help='name of DUT: %(default)s')
        parser.add_argument('--serial_port', dest='serial_port', type=str, default='/dev/ttyUSB1',
                            action='store', help='Serial port. default: %(default)s')
        parser.add_argument('--baudrate', dest='baudrate', type=int, default=115200, action='store',
                            help='baudrate, how fast data is sent over a serial line. default: %(default)s')
        parser.add_argument('--mode', '-m', dest='mode', type=str, default='local', action='store',
                            help='Run with local mode or API: %(default)s')
        parser.add_argument('--source', '-s', dest='source', type=str, action='store',
                            help='Full path to source file. Exemple: /home/test.txt')
        parser.add_argument('--destination', '-d', dest='destination', type=str, action='store',
                            help='Full path to destination, Exemple: /test.txt')

        args = parser.parse_args()

        if args.mode == 'local':
            if not args.source or not args.destination:
                raise Exception('"local" mode required: "--source" and "--destination"')

        dut = SendToDut(args.serial_port, args.baudrate, args.name)
        job_status = True

        if args.mode == 'local':
            job_status = dut.send_file(args.source, args.destination)

    except (KeyboardInterrupt, SystemExit) as ex:
        logging.critical("\nAborted requested (Ctrl-C pressed). Stopping...")
        sys.exit(1)

    except Exception as ex:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logging.critical(DASH)
        logging.critical("ERROR = {}".format(str(ex)))
        logging.critical("FILE = {}".format(traceback.extract_tb(exc_tb)[-1][0]))
        logging.critical("LINE = {}".format(traceback.extract_tb(exc_tb)[-1][1]))
        logging.critical(DASH)
        sys.exit(1)

    # If job_status is True, running in successfully else Fail.
    if job_status:
        sys.exit(0)
    else:
        sys.exit(1)
