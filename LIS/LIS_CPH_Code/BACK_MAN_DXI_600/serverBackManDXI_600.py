import time
import serial

from BACK_MAN_DXI_600.getOrderAndCheckSum import *
from BACK_MAN_DXI_600.hl7MessageParse_BACK_MAN_DXI_600 import *

STX = b'\x02'
ETX = b'\x03'
CR = b'\x0D'
LF = b'\x0A'


def serverBackManDXI600():
    try:
        serialPort = serial.Serial(port="COM11", baudrate=9600, bytesize=8, parity=serial.PARITY_NONE,
                                   stopbits=serial.STOPBITS_ONE, timeout=3)
        serialString = ""

        infoMessage("............Starting Back Man 600 DXI.............")

        testResult = ""
        ind = 0
        flag = False
        queryFlag = False
        resultFlag = False
        message = []
        sampleId = ""
        messageFrame = 0
        while 1:

            if serialPort.in_waiting > 0:
                serialString = serialPort.readline()
                messageRawData = str(serialString)
                print(serialString)
                messageRawData = messageRawData[1:]
                messageRawData = messageRawData[1:-1]

                print(str(datetime.now()) + ": messageRawdata: ", messageRawData)
                messageSplitted = messageRawData.split('|')
                print("message First Sig ", messageSplitted[0])

                # Order Message
                if "\\x06" == messageSplitted[0]:

                    messageFrame = messageFrame + 1
                    infoMessage("Frame: " + str(messageFrame))

                    if messageFrame == 1:
                        currentDateTime = str(datetime.now().strftime("%Y%m%d%H%M%S"))
                        firstFrame = "\x021H|\^&|||LIS HOST|||||ACCESS^901894||P|1|" + currentDateTime + "\x0D\x03"
                        firstFrame = firstFrame + getCheckSum(firstFrame.encode()) + "\x0D\x0A"
                        serialPort.write(firstFrame.encode())

                    if messageFrame == 2:
                        secondFrameData = "\x022P|1|1234567890|||Doel^CPH^Back^M^Man||20000420|M||123456\x0D\x03"
                        secondFrameData = secondFrameData + getCheckSum(secondFrameData.encode()) + "\x0D\x0A"
                        serialPort.write(secondFrameData.encode())

                    if messageFrame == 3:
                        successMessage("Order Message")
                        orderMessage = "\x023O|1|" + sampleId + "||" + getTestListStr(
                            sampleId) + "|||||||||||Serum||||||||||F\x0D\x03"
                        orderMessage = orderMessage + getCheckSum(orderMessage.encode()) + "\x0D\x0A"
                        serialPort.write(orderMessage.encode())

                    if messageFrame == 4:
                        successMessage("Termination Message")
                        terminationMessage = b'\x024L|1|F\x0D\x03FF\x0D\x0A'
                        serialPort.write(terminationMessage)

                    if messageFrame == 5:
                        serialPort.write(b'\x04')
                        messageFrame = 0

                if "\\x023L" == messageSplitted[0]:
                    infoMessage("last message")
                    serialPort.write(b'\x06')
                    time.sleep(1)
                if "\\x022Q" == messageSplitted[0]:
                    queryFlag = True
                    resultFlag = False
                    messageFrame = 0
                    sampleId = messageSplitted[2].rsplit('^', 1)[-1]
                    infoMessage("sample ID: " + sampleId)

                if "\\x024R" == messageSplitted[0]:
                    resultFlag = True
                    queryFlag = False
                if messageRawData == "\\x05":
                    flag = True
                    serialPort.write(b'\x06')
                elif messageRawData == "\\x04":
                    serialPort.write(b'\x06')
                    messageData = ''
                    if queryFlag:
                        print("Order Query Message: ", message)
                        serialPort.write(b'\x05')
                        infoMessage("Message Writing .... ")
                    if resultFlag:
                        hl7MessageParse(message)
                        message.clear()
                        flag = False
                        queryFlag = False
                        resultFlag = False
                        messageFrame = 0
                elif messageRawData == "\\x04\\x05":
                    serialPort.write(b'\x06')
                    if resultFlag:
                        print(message)
                        hl7MessageParse(message)
                        message.clear()
                        flag = True

                messageType = messageSplitted[0][5:]
                acceptedData = ["H", "P", "O", "R", "C", "S", "M", "Q", "L"]
                if messageType in acceptedData:
                    serialPort.write(b'\x06')
                # if messageType == "H" or messageType == "P" or messageType == "O" or \
                #         messageType == "R" or messageType == "L" or messageType == "Q" or messageType == "C":
                #     serialPort.write(b'\x06')

                if flag:
                    # print("appended")
                    message.append(messageRawData)
    except Exception as error:
        errorMessage("An exception occurred: " + str(error))
