import serial
from hl7MessageParse_LIASION_XL import *
serialPort = serial.Serial(port="COM6", baudrate=9600, bytesize=8, parity=serial.PARITY_NONE,
                           stopbits=serial.STOPBITS_ONE, timeout=.1)
serialString = ""  # Used to hold data coming over UART
testResult = []

while 1:
    if serialPort.in_waiting > 0:
        serialString = serialPort.readline()
        messageRawData = str(serialString)
        messageRawData = messageRawData[1:]
        messageRawData = messageRawData[1:-1]
        print("Rawdata:",messageRawData)
        if "\\x05" not in messageRawData and "\\x04" not in messageRawData:
            if "O|1|" in messageRawData or  "R|1|" in messageRawData:
                testResult.append(messageRawData.replace("\\x0", "").replace("\\x5", "").replace("\\x4", ""))
        if "\\x04'" in str(serialString):
            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            for t in testResult:
                print(t)
            print("-----------------------------------------------------------------------------------")
            hl7MessageParse(testResult)
            testResult.clear()
        serialPort.write(b'\x06')















