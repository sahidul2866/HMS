import serial
#from API_CONNECTION import *
from API_CONNECTION.apiCURLFunction import getWorkList



from hl7MessageParse import *
#from parseHL7_ADVIA_CENTAUR_CP import *
serialPort = serial.Serial(port="COM5", baudrate=9600, bytesize=8, parity=serial.PARITY_NONE,
                           stopbits=serial.STOPBITS_ONE, timeout=.1)
serialString = ""  # Used to hold data coming over UART
testResult = []

print("While...")

from_machine = []
while 1:
    if serialPort.in_waiting > 0:
        serialString = serialPort.readline()
        messageRawData = str(serialString)
        messageRawData = messageRawData[1:]
        messageRawData = messageRawData[1:-1]
        print("messageRawData:",messageRawData)

        serialPort.write(b'\x06')

        if "\\x05" not in messageRawData and "\\x04" not in messageRawData:
            from_machine.append(messageRawData)

        if "\\x04" in messageRawData:
            print("hi")
            print("len:",len(from_machine),"   ;Machine:",from_machine)

            if len(from_machine)==3:
                print("From Machine:",from_machine)
                sm = from_machine[1].split("^")
                id=sm[1]
                print("ID=>",id)

                BarcodeData = getWorkList(id)
                print("testCode:",BarcodeData)
            print("bye")
            


'''
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
'''






'''
if __name__ == '__main__':
    bb = getWorkList("I1014451")
'''



















    print(bb)
