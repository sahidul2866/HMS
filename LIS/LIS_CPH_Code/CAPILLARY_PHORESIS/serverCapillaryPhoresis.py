import serial
from CAPILLARY_PHORESIS.messageParseCapillary import *

serialPort = serial.Serial(port="COM9", baudrate=9600, bytesize=8, parity=serial.PARITY_NONE,
                           stopbits=serial.STOPBITS_ONE, timeout=.1)
serialString = ""
testResult = []
while 1:
    if serialPort.in_waiting > 0:
        serialString = serialPort.readline()
        messageRawData = str(serialString)
        messageRawData = messageRawData[1:]
        messageRawData = messageRawData[1:-1]
        print("RawData:",messageRawData)

        # if "\\x05'" not in messageRawData and "\\x04'" not in messageRawData:
        #     if "23O|1|" in messageRawData or "^^^A1c^AREA" in messageRawData:
        #         testResult.append(messageRawData.replace("\\x0", "").replace("\\x5", "").replace("\\x4", ""))

        if "\\x04'" in str(serialString):
            print("TestData:", testResult)
            capillaryMessageParse(testResult)
            testResult.clear()

        serialPort.write(b'\x06')

