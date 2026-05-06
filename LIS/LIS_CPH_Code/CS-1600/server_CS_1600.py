import socket
from API_CONNECTION.commonMessage import *
from hl7messageParse_CS_1600 import *

if __name__ == '__main__':

    infoMessage("........Starting CS-1600...........")
    # Defining Socket
    # host = '172.16.22.1'
    host = '0.0.0.0'
    port = 6000
    # totalclient = int(input('Enter number of clients: '))
    totalclient = 1
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, port))
    sock.listen(totalclient)
    connections = []
    infoMessage("Current HOST IP: " + str(host) + " PORT: " + str(port))
    infoMessage('Initiating clients...................')
    conn, address = sock.accept()
    connections.append(conn)
    # print('Connected with client', i+1)
    successMessage("Connection from: " + str(address))

    full_msg = ''
    while True:
        msg = conn.recv(8192)
        # successMessage("Data Received: "+ str(msg))
        mainMessage = str(msg)
        mainMessage = mainMessage[1:]
        mainMessage = mainMessage[1:-1]
        # print(mainMessage)

        if len(mainMessage) > 0:
            print("mainMessage:",mainMessage)
            try:
                if "\\x03" in mainMessage:
                    mainMessage = mainMessage.split("\\x03")
                    try:
                        mainMessage = mainMessage[0]
                        hl7MessageParse(mainMessage)
                    except IndexError:
                        print(">>>>>>>>>>>>>>>>>>>>>>>Index Error!<<<<<<<<<<<<<<<<<<<<<<<")
            except IndexError:
                print(">>>>>>>>>>>>>>>>>>>>No output!",mainMessage,"<<<<<<<<<<<<<<<<<<<<<<<")


            #successMessage("Data Processed and Sent it to Server")
            # print("Result Message",mainMessage)
            # print(len(mainMessage.split("\x03")))
            # if len(mainMessage.split("\x03")) == 2:
            # # if "\x03'" in mainMessage:
            #     print("Result Message ACP",mainMessage)
            #     hl7MessageParse(mainMessage)
            #     successMessage("Data Processed and Sent it to Server")

    conn.close()  # close the connection
