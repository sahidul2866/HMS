from API_CONNECTION.commonMessage import *
import serial

serialPort = serial.Serial(port="COM", baudrate=9600, bytesize=8, parity=serial.PARITY_NONE,
                           stopbits=serial.STOPBITS_ONE, timeout=.1)
serialString = ""  # Used to hold data coming over UART
testResult = ""
while 1:
    if serialPort.in_waiting > 0:
        serialString = serialPort.readline()
        messageRawData = str(serialString)

        messageRawData = messageRawData[1:]
        messageRawData = messageRawData[1:-1]
        print("MessageRawData: ",messageRawData)

        '''
        if "\\x05'" not in messageRawData and "\\x04'" not in messageRawData:
            testResult += messageRawData.replace("\\x0", "").replace("\\x5", "").replace("\\x4", "")

        #print(messageRawData)
        if "\\x04'" in str(serialString):
            print("Message passes to hl7: ",testResult)
            hl7MessageParse(testResult)
            testResult = ""
        '''
        serialPort.write(b'\x06')





