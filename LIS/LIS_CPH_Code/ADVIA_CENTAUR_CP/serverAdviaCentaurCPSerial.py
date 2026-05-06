import serial
from ADVIA_CENTAUR_CP.hl7MessageParse import *
from API_CONNECTION.commonMessage import *

STX = b'\x02'
ETX = b'\x03'
CR = b'\x0D'
LF = b'\x0A'

serialPort = serial.Serial(port="COM5", baudrate=9600, bytesize=8, parity=serial.PARITY_NONE,
                           stopbits=serial.STOPBITS_ONE, timeout=.1)

infoMessage("............Starting Advia Centaur CP.............")
serialString = ""
testResult = []

while 1:
    if serialPort.in_waiting > 0:
        serialString = serialPort.readline()
        messageRawData = str(serialString)
        messageRawData = messageRawData[1:]
        messageRawData = messageRawData[1:-1]
        #print("messageRawData:",messageRawData)

        if "\\x05'" not in messageRawData and "\\x04'" not in messageRawData:
            if "23O|1|" in messageRawData or "24R|1|" in messageRawData:
                testResult.append(messageRawData.replace("\\x0", "").replace("\\x5", "").replace("\\x4", ""))

        if "\\x04'" in str(serialString):
            print("testResult:")
            for r in testResult:
                print(r)
            print("---------------------------------------------------------")
            hl7MessageParse(testResult)
            testResult.clear()

        serialPort.write(b'\x06')
