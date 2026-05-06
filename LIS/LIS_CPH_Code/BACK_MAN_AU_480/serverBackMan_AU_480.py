import serial
from BACK_MAN_AU_480.hl7MessageParse_BACK_MAN_AU_480 import *
from BACK_MAN_AU_480.testCodeName import *

STX = b'\x02'
ETX = b'\x03'
CR = b'\x0D'
LF = b'\x0A'

def serverBackManAU480():
    try:
        serialPort = serial.Serial(port="COM9", baudrate=9600, bytesize=8, parity=serial.PARITY_NONE,
                                   stopbits=serial.STOPBITS_ONE, timeout=0.05)
        serialString = ""
        testResult = ""
        infoMessage("Starting BACK MAN AU 480...")

        index = 0
        while 1:
            # serialString = serialPort.readline()
            # serialPort.write(b"Thank you for sending data \r\n")

            if serialPort.in_waiting > 0:
                index += 1
                serialString = serialPort.readline()
                messageRawData = str(serialString)
                print(serialString)
                messageRawData = messageRawData[1:]
                messageRawData = messageRawData[1:-1]

                print("messageRawData:", messageRawData)
                splited_message = messageRawData.split(" ")
                print("here=>", splited_message)

                # Result Message
                if splited_message[0] == "\\x02D":
                    hl7MessageParse(splited_message)

                # Sample Request Message
                if splited_message[0] == "\\x02R":
                    # hl7MessageParse(splited_message)
                    sampleIdSigment=len(splited_message)
                    sampleId = splited_message[sampleIdSigment-1].replace("\\x03", "")
                    messageId = splited_message[1]
                    successMessage("Sample Id: "+ str(sampleId))
                    # serialPort.write(b'\x02S 001101 0001 23072410646 E002\x03')
                    # message = '\x02S 001101 0001 23072610820 E061\x03'
                    trayAndRack = messageId.split('N')
                    # print(trayAndRack)
                    # message = 'S 001801 0001 23072610820 E061'
                    testCode = getMachineCodeStr(sampleId)
                    if testCode is not None:
                        # orderMessage = "\\x02S "+trayAndRack[0]+" "+trayAndRack[1]+" "+sampleId+" E061\\x03"
                        orderMessage = "\x02S " + str(trayAndRack[0]) + " " + str(trayAndRack[1]) + "    " + sampleId + "    E" + testCode + "\x03"
                        infoMessage(orderMessage)
                        serialPort.write(orderMessage.encode())
                    else :
                        errorMessage("No Order Found")
                    # data = '\x02' + "S "+trayAndRack[0]+" "+trayAndRack[1]+" "+sampleId+" E061"+'\x03'
                    # order_message = b'\x02S 001101 0001    52896378    E061\x03'  # Main Working Message
                    # order_message = 'S '+trayAndRack[0]+' '+trayAndRack[1]+'    '+sampleId+'    E061'

                    # dataToSend=STX+" "+trayAndRack[0]+" "+trayAndRack[1]+" "+sampleId+" E061"+ETX
                    # serialPort.inWaiting()
                    # order_message = STX + order_message + ETX + checksum_hex.encode() + CR + LF
                    # order_message = STX + order_message + ETX

                    # serialPort.write(order_message)
    except Exception as error:
        errorMessage("An exception occurred: " + str(error))
