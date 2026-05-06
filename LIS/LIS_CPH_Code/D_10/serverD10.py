import serial
from D_10.hl7MessageParse_D_10 import *
def serverD10():
    serialPort = serial.Serial(port="COM4", baudrate=9600, bytesize=8, parity=serial.PARITY_NONE,
                               stopbits=serial.STOPBITS_ONE, timeout=1)
    serialString = ""
    testResult = []

    infoMessage("________________ Starting Server D 10 _________________")
    while 1:
        if serialPort.in_waiting > 0:
            serialString = serialPort.readline()
            messageRawData = str(serialString)
            messageRawData = messageRawData[1:]
            messageRawData = messageRawData[1:-1]
            # print("RawData:",messageRawData)

            if "\\x05'" not in messageRawData and "\\x04'" not in messageRawData:
                if "23O|1|" in messageRawData or "^^^A1c^AREA" in messageRawData:
                    testResult.append(messageRawData.replace("\\x0", "").replace("\\x5", "").replace("\\x4", ""))

            if "\\x04'" in str(serialString):
                warningMessage("TestData:" + str(testResult))
                hl7MessageParse(testResult)
                testResult.clear()

            serialPort.write(b'\x06')
