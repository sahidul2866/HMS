import serial
from ADAMS_A1C.hl7MessageParse_ADAMS_A1C import *

def serverADMAS_A1c():
    serialPort = serial.Serial(port="COM5", baudrate=9600, bytesize=8, parity=serial.PARITY_NONE,
                               stopbits=serial.STOPBITS_ONE, timeout=.1)
    serialString = ""

    testResult = ""

    flag = False
    message = []
    infoMessage("_______________ Starting Server ADMAS A1C  ______________________")
    while 1:

        if serialPort.in_waiting > 0:
            serialString = serialPort.readline()
            messageRawData = str(serialString)
            # print(serialString)
            messageRawData = messageRawData[1:]
            messageRawData = messageRawData[1:-1]

            if "\\x05'" not in messageRawData and "\\x04'" not in messageRawData:
                testResult += messageRawData.replace("\\x0", "").replace("\\x5", "").replace("\\x4", "")

            first_value = testResult.split('|')

            if len(first_value) < 2:
                second_value = ""
            else:
                second_value = first_value[1]

            first_value = first_value[0]

            if first_value == "521H":

                flag = True
            elif first_value == "26R" and second_value == "3":
                flag = False
                if len(message) > 3:
                    hl7MessageParse(message)
                message.clear()

            if flag:
                message.append(testResult)
            testResult = ""

        serialPort.write(b'\x06')

