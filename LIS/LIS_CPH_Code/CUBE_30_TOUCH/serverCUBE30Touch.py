import serial
from hl7MessageParse_CUBE_30_TOUCH import *
serialPort = serial.Serial(port="COM8", baudrate=9600, bytesize=8, parity=serial.PARITY_NONE,
                           stopbits=serial.STOPBITS_ONE, timeout=.1)
# serialPort = serial.Serial(port="COM3", baudrate=9600, bytesize=8, timeout=30, stopbits=serial.STOPBITS_ONE)
serialString = ""  # Used to hold data coming over UART
testResult = ""

while 1:
    # serialString = serialPort.readline()
    # print(serialString)
    # serialPort.write(b"Thank you for sending data \r\n")
    if serialPort.in_waiting > 0:
        # serialString = serialPort.read()
        serialString = serialPort.readline()
        messageRawData = str(serialString)
        messageRawData = messageRawData[1:]
        messageRawData = messageRawData[1:-1]

        print("messageRawData=>",messageRawData)
        if len(messageRawData)>40:
            hl7MessageParse(messageRawData)
        else:
            print("Data Missing!")

