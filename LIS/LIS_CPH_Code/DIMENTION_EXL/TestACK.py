import serial
import time
from DIMENTION_EXL.hl7MessageParse_DIMENTION_EXL import hl7MessageParse
from getSampleRequest import *
import datetime

ser = serial.Serial('COM6',baudrate=9600, bytesize=8, timeout=3, stopbits=serial.STOPBITS_ONE )

# serialPort = serial.Serial(port="COM3", baudrate=9600, bytesize=8, timeout=30, stopbits=serial.STOPBITS_ONE)
serialString = ""  # Used to hold data coming over UART

while 1:
    message = ser.readline()
    messageAfterDecode = message.decode()
    print(messageAfterDecode)
