from ATELICA_SOLUTION.client_ATILICA_SOLUTION import *
from ATELICA_SOLUTION.HL7Parse import *
import uuid
from API_CONNECTION.commonMessage import *
from ATELICA_SOLUTION.testCodeNameAtlica import getOrderString

if __name__ == '__main__':
    try:
        # Defining Socket
        host = '192.168.1.201'
        # host = '192.168.1.5'
        # host = '0.0.0.0'
        port = 7787
        # port = 5000
        # totalclient = int(input('Enter number of clients: '))
        totalclient = 1
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((host, port))
        sock.listen(totalclient)
        connections = []
        infoMessage('Initiating clients')
        conn, address = sock.accept()
        connections.append(conn)
        # print('Connected with client', i+1)
        successMessage("Connection from: " + str(address))

        full_msg = ''
        while True:
            msg = conn.recv(8192)
            infoMessage("Result Received: ")
            mainMessage = str(msg)
            print("Main_message:\n", msg)
            mainMessage = mainMessage[1:]
            mainMessage = mainMessage[1:-1]
            # mainMessage = mainMessage.replace("\\x0b","").replace("\\r","").replace("\\x1c","")
            mainMessage = mainMessage.replace("\\x0b", "").replace("\\x1c", "")
            # Result Receive ACK
            print("after_all:\n", mainMessage)

            #Result Receive

            if "OUL^R22^OUL_R22" in mainMessage:
                hl7MessageParse(mainMessage)

                sigmentMessage = mainMessage.split("\\r")
                try:
                    print("Sigment",sigmentMessage[1])
                    if "^" in sigmentMessage[1].split('|')[3]:
                        SAMPLE_ID = sigmentMessage[1].split('|')[3].split('^')[0]
                    else:
                        SAMPLE_ID = sigmentMessage[1].split('|')[3]
                    MSH_ID = sigmentMessage[0].split('|')[9]
                    QPD_ID = sigmentMessage[1].split('|')[3]

                    print(sigmentMessage[1].split('|')[3])  # SAMPLE ID
                    print(sigmentMessage[0].split('|')[9])  # MSH ID
                    print(sigmentMessage[1].split('|')[2])  # QPD ID
                    print(sigmentMessage[2])  # RPD

                    currentDateTimeWithZone = datetime.now()

                    resultReceiveACK=f'''\x0bMSH|^~\&|xyzco|AM_xyzco_xyzlab|Siemens Analyzer|Siemens Lab|{currentDateTimeWithZone}||ACK^R22^ACK|1|P|2.5.1|||| ||UNICODE UTF-8|||LAB-29^IHE\rMSA|AA|{MSH_ID}\r\x1c\r'''
                    sendDataToMachine(resultReceiveACK)
                    successMessage("Result Receive ACK")
                except Exception as error:
                    errorMessage("Error occured!")
                    print(error)

            if "QBP^Q11^QBP_Q11" in mainMessage:
                sigmentMessage = mainMessage.split("\\r")
                # print("Sigment List: ", sigmentMessage)

                SAMPLE_ID = sigmentMessage[1].split('|')[3]
                MSH_ID = sigmentMessage[0].split('|')[9]
                QPD_ID = sigmentMessage[1].split('|')[2]

                infoMessage("Sample Id: "+ SAMPLE_ID)  # SAMPLE ID
                infoMessage("Message Id: "+ MSH_ID)  # MSH ID
                infoMessage("Message Query Id: "+ QPD_ID)  # QPD ID
                # print("Sigment 2: ",sigmentMessage[2])  # RPD

                # ORDER ACK Message

                # currentDateTimeWithZone = datetime.now()
                currentDateTimeWithZone = datetime.now().strftime("%Y%m%d%H%M%S")+"+0600"
                uuidData1 = str(uuid.uuid4()).replace("-", "")
                # SAMPLE_ID = 23072410692
                ORDER_GET_ACK = f'''\x0bMSH|^~\&|LIS_ID|LIS_FAC|UIW_LIS|UIW_FAC|{currentDateTimeWithZone}||RSP^K11^RSP_K11|{uuidData1}|P|2.5.1||||||UNICODE UTF-8|||LAB- 27^IHE\rMSA|AA|{MSH_ID}\rQAK|{QPD_ID}|OK|WOS^Work Order Step^IHELAW\rQPD|WOS^Work Order Step^IHELAW|{QPD_ID}|{SAMPLE_ID}\r\x1c\r'''
                sendDataToMachine(ORDER_GET_ACK)

                # ORDER Message
                # currentDateTimeWithZone = datetime.now()
                currentDateTimeWithZone = datetime.now().strftime("%Y%m%d%H%M%S")+"+0600"
                # SAMPLE_ID=23072410692
                uuidData1 = str(uuid.uuid4()).replace("-", "")
                uuidData2 = str(uuid.uuid4()).replace("-", "")
                currentTime = str(datetime.now()).split('.')[0].replace('-', '').replace(' ', '').replace(':', '')

                if SAMPLE_ID != "":
                    print("+++++++++++++++++++++++++++++++++++",SAMPLE_ID,"++++++++++++++++++++++++++++++")
                    if "I" in SAMPLE_ID:
                        orderString = getOrderString(SAMPLE_ID)
                    else:
                        orderString = None
                else:
                    orderString = None
                if orderString is not None:
                    ORDER_Message = f'''\x0bMSH|^~\&|LIS_ID|LIS_FAC|UIW_LIS|UIW_FAC|{currentDateTimeWithZone}||OML^O33^OML_O33|{uuidData1}|P|2.5.1|||NE|AL||UNICODE UTF-8|||LAB-28^IHE\rPID|||{SAMPLE_ID}||DOEL_NAME^CPH_NAME^^^^^L||19880110|F\rPV1||U|^103\rSPM|1|{SAMPLE_ID}||SER^^HL70487|||||||P^^HL70369\rSAC|||{SAMPLE_ID}{orderString}\r\x1c\r'''
                    # ORDER_Message = f'''\x0bMSH|^~\&|LIS_ID|LIS_FAC|UIW_LIS|UIW_FAC|{currentDateTimeWithZone}||OML^O33^OML_O33|{uuidData1}|P|2.5.1|||NE|AL||UNICODE UTF-8|||LAB-28^IHE\rPID|||{SAMPLE_ID}||DOEL_NAME^CPH_NAME^^^^^L||19880110|F\rPV1||U|^103\rSPM|1|{SAMPLE_ID}||SER^^HL70487|||||||P^^HL70369\rSAC|||{SAMPLE_ID}\rORC|NW\rTQ1|||||||||R^^HL70485\rOBR||{uuidData2}||TSH3UL^^99SiemensHDXTestCode||||||||||||01025232\rTCD|TSH3UL^^99SiemensHDXTestCode\r\x1c\r'''
                    sendDataToMachine(ORDER_Message)
                    successMessage("Order Message Sent")
                else:
                    errorMessage(SAMPLE_ID+" Sample Order Not Found")

        conn.close()  # close the connection
    except Exception as error:
        errorMessage("An exception occurred:" + str(error))
