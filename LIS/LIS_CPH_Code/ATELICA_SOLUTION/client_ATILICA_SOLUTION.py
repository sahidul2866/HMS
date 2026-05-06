import socket
import uuid
from datetime import datetime
from API_CONNECTION.commonMessage import *


def sendDataToMachine(message):
    host = '192.168.1.106'
    port = 8888

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Connecting with Server
    sock.connect((host, port))
    successMessage("ATELLICA Machine Connected")
    print(message)
    sock.send(message.encode())
    # sock.send(message)
    # print("Receive: ",str(sock.recv(8192)))

    # msg = '''
    # MSH|^~\&|HIS|HOSPITAL|LAB|LAB|20230131111929||ADT^A01|1000027|P|2.3||||
    # EVN|A01|20220131111924
    # PID|1||0012345678^^^MRN^MRN||Doe^John^R||19700101|M|||123 Main St.^^Anytown^CA^91234^USA|||||||||||||||||||||
    # PV1|1||^^^100^1|||||||||||||||||||1||||||||||||||||||||||||||||||||||
    # DG1|1||123456789^Diagnosis^I9||Confirmed
    # ZCP|1|Custom Segment Data
    # '''
    #
    # parsed = hl7.parse(msg)
    # print(parsed)

# if __name__ == '__main__':
#     currentDateTimeWithZone = datetime.now()
#     SAMPLE_ID=23072810081
#     uuidData1 = str(uuid.uuid4()).replace("-", "")
#     print(uuidData1)
#     uuidData2 = str(uuid.uuid4()).replace("-", "")
#     currentTime = str(datetime.now()).split('.')[0].replace('-', '').replace(' ', '').replace(':', '')
#     ORDER_Message = f'''\x0bMSH|^~\&|LIS_ID|LIS_FAC|UIW_LIS|UIW_FAC|{currentDateTimeWithZone}||OML^O33^OML_O33|{uuidData1}|P|2.5.1|||NE|AL||UNICODE UTF-8|||LAB-28^IHE\rPID|||{SAMPLE_ID}||Doel_NAME^CPH_NAME^^^^^L||19880110|F\rPV1||U|^103\rSPM|1|{SAMPLE_ID}||SER^^HL70487|||||||P^^HL70369\rSAC|||{SAMPLE_ID}\rORC|NW|||{currentTime}.TSH3UL|||||{currentTime}\rTQ1|||||||||R^^HL70485\rOBR||{uuidData2}||2951-2^Na- S^LN||||||||||||01025232\rTCD|2951-2^Na-S^LN \r\x1c\r'''
#     sendDataToMachine(ORDER_Message)
