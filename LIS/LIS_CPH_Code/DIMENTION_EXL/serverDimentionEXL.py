import time

import serial

from DIMENTION_EXL.getDimentionEXLOrderAndChecksum import *
from DIMENTION_EXL.hl7MessageParse_DIMENTION_EXL import hl7MessageParse
from DIMENTION_EXL.getSampleRequest import *
def serverDimantionExl200():
    try:
        serialPort = serial.Serial(port="COM6", baudrate=9600, bytesize=8, parity=serial.PARITY_NONE,
                                   stopbits=serial.STOPBITS_ONE, timeout=1)

        # Define the ACK and NAK bytes
        ACK = "\x06"
        NAK = "\x15"
        STX = "\x02"
        ETX = "\x03"
        FS = "\x1c"

        testResult = ""

        infoMessage("********************* Starting Dimension EXL 200 ******************************")

        while 1:
            if serialPort.in_waiting > 0:
                serialString = serialPort.readline()
                messageRawData = str(serialString)

                infoMessage("Raw Message: " + messageRawData)

                # Result Receive ACK Message
                if "\\x02R" in messageRawData:
                    ackMessage = '\x06'
                    serialPort.write(ackMessage.encode())

                    successMessage("Result Received: " + messageRawData)
                    serialPort.write(b'\x02M\x1cA\x1c\x1cE2\x03')  # Result Receive ACK
                    hl7MessageParse(messageRawData)

                if "\\x02I" in messageRawData:

                    infoMessage("Inquiry Order Message: " + messageRawData)
                    ackMessage = '\x06'
                    serialPort.write(ackMessage.encode())

                    splitedMessage = messageRawData.split('\\x1c')
                    sampleId = splitedMessage[1]
                    warningMessage("Sample Id: " + sampleId)
                    # testName = getTestName(sampleId)
                    testCountAndName = getTestListStr(sampleId)
                    if testCountAndName[0] == 0:
                        serialPort.write(b'\x02N\x1c6A\x03')  # No Smaple ACK
                    else:
                        noOfTest = testCountAndName[0]
                        # noOfTest = 2
                        # sampleOrderMessage = "\x02A\x1c0\x1c0\x1cA\x1cL_N,F_N\x1c" + str(sampleId) + "\x1c1\x1c\x1c2\x1c1\x1c**\x1c1\x1c" + str(noOfTest) + testCountAndName[1] + "\x1c"
                        # sampleOrderMessage = "\x02D\x1c0\x1c0\x1cA\x1cL_N,F_N\x1c" + str(sampleId) + "\x1c1\x1c\x1c2\x1c1\x1c**\x1c1\x1c"+noOfTest+"\x1cBUN\x1cCRE2\x1cF5\x03"
                        # serialPort.write(b'\x02D\x1c0\x1c0\x1cA\x1cL_N,F_N\x1c'"+str(sampleId)+"'\x1cW\x1c\x1c2\x1c1\x1c**\x1c1\x1c2\x1cBUN\x1cCREA\x1cF5\x03')
                        # sampleOrderMessage = STX + "D" + FS + "0" + FS + "0" + FS + "A" + FS + "" + FS + str(sampleId) + FS + "1" + FS + "" + FS + "0" + FS + "1" + FS + "**" + FS + "1" + FS + "1" + FS + "CRE2" + FS
                        sampleOrderMessage = STX + "D" + FS + "0" + FS + "0" + FS + "A" + FS + "" + FS + str(sampleId) + FS + "1" + FS + "" + FS + "0" + FS + "1" + FS + "**" + FS + "1" + FS + str(noOfTest) + testCountAndName[1] + FS

                        sampleOrderMessageWithCheckSum = sampleOrderMessage + getCheckSum(sampleOrderMessage.encode()) + "\x03"
                        warningMessage("Main Order Message: " + sampleOrderMessageWithCheckSum)
                        serialPort.write(sampleOrderMessageWithCheckSum.encode())
                        infoMessage("Order Message: " + testCountAndName[1])
                        # order Message

                if "\\x02P" in messageRawData:
                    # if "\\x02P" in messageRawData and "\\x05" not in messageRawData:
                    infoMessage("Poll Message"+ messageRawData)

                    ackMessage = '\x06'
                    serialPort.write(ackMessage.encode())

                    noOrderAck = STX + "N" + FS
                    noOrderAckWithCheckSum = noOrderAck + getCheckSum(noOrderAck.encode()) + ETX
                    serialPort.write(noOrderAckWithCheckSum.encode())
                    time.sleep(1)
                if "\\x02M" in messageRawData:
                    warningMessage("Barcode Read: " + messageRawData)
                    isBarcodeAccepted = messageRawData.split("\\x1c")
                    warningMessage("Barcode Status: " + str(isBarcodeAccepted))
                    ackMessage = "\x06"
                    serialPort.write(ackMessage.encode())
                if "\\x02C" in messageRawData:
                    ackMessage = '\x06'
                    serialPort.write(ackMessage.encode())
                    warningMessage("Calibration Result Received: " + messageRawData)
                    serialPort.write(b'\x02M\x1cA\x1c\x1cE2\x03')  # Result Receive ACK
                if "\\x05" in messageRawData:
                    # noOrderAck = "\x02N\x1c6A\x03"
                    # serialPort.write(noOrderAck.encode())
                    errorMessage("05 Message: "+ messageRawData)
                    ackMessage = "\x06"
                    serialPort.write(ackMessage.encode())
                testResult = ""
    except Exception as error:
        errorMessage("An exception occurred:" + str(error))