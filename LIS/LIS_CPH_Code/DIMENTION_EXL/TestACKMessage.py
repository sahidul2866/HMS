import serial
import time
from DIMENTION_EXL.hl7MessageParse_DIMENTION_EXL import hl7MessageParse
from getSampleRequest import *
import datetime

serialPort = serial.Serial(port="COM6", baudrate=9600, bytesize=8, parity=serial.PARITY_NONE,
                           stopbits=serial.STOPBITS_ONE, timeout=15)
# serialPort = serial.Serial(port="COM3", baudrate=9600, bytesize=8, timeout=30, stopbits=serial.STOPBITS_ONE)
serialString = ""  # Used to hold data coming over UART
# adams_a1c
i = 0
testResult = ""

print("Start")
while 1:
    # serialString = serialPort.read()
    serialString = serialPort.readline()
    messageRawData = str(serialString)
    if "\\x02P" in messageRawData:
        # if "\\x02P" in messageRawData and "\\x05" not in messageRawData:
        print(str(datetime.datetime.now()) + " : Poll Message", messageRawData)
        noOrderAck = '\x02N\x1c6A\x03'
        serialPort.write(noOrderAck.encode())
        ackMessage = '\x06'
        serialPort.write(ackMessage.encode())
        # time.sleep(0.1)
print("Close")
