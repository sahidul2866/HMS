import time
import serial
from LIASION_XL.liasionXLCheckSum import *
from LIASION_XL.hl7MessageParse_LIASION_XL import *

STX = b'\x02'
ETX = b'\x03'
CR = b'\x0D'
LF = b'\x0A'

def serverLiasinXL():
    try:
        serialPort = serial.Serial(port="COM6", baudrate=9600, bytesize=8, parity=serial.PARITY_NONE,
                                   stopbits=serial.STOPBITS_ONE, timeout=1)
        serialString = ""

        infoMessage("............Starting Liaison XL.............")

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
                        firstFrame = "\x021H|\^&|||1234|||||LIAISON XL||P|1|" + currentDateTime + "\x0D\x03"
                        firstFrame = firstFrame + getCheckSum(firstFrame.encode()) + "\x0D\x0A"
                        serialPort.write(firstFrame.encode())

                    if messageFrame == 2:
                        # secondFrameData = "\x022P|1|1234567890|||Doel^CPH^ADVIA^C^CP||20000420|M||123456\x0D\x03"
                        secondFrameData = "\x022P|1||||^^|||||\x0D\x03"
                        secondFrameData = secondFrameData + getCheckSum(secondFrameData.encode()) + "\x0D\x0A"
                        serialPort.write(secondFrameData.encode())

                    if messageFrame == 3:
                        successMessage("Order Message")
                        orderMessage = "\x023O|1|" + sampleId + "||" + getTestListStr(sampleId) + "|R||||||||||||||||||||O\x0D\x03"
                        # orderMessage = "\x023O|1|" + sampleId + "||^^^FT4|R||||||||||||||||||||O\x0D\x03"
                        orderMessage = orderMessage + getCheckSum(orderMessage.encode()) + "\x0D\x0A"
                        serialPort.write(orderMessage.encode())

                    if messageFrame == 4:
                        successMessage("Termination Message")
                        terminationMessage = b'\x024L|1|N\x0D\x0307\x0D\x0A'
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
                    try:
                        # sampleId = messageSplitted[2].rsplit('^', 1)[-1]
                        # sampleId = messageSplitted[2].split('^')[1]
                        sampleId = messageSplitted[2]
                        infoMessage("sample ID: " + sampleId)
                    except:
                        sampleId = ""
                        errorMessage("Sample Id is missing")

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
                        warningMessage("Result Message Got And Parsing")
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

if __name__ == '__main__':
    serverLiasinXL()