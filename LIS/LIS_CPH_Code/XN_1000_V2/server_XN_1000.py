from API_CONNECTION.commonMessage import *
import socket
from XN_1000_V2.parseHL7_XN_1000 import hl7MessageParse

if __name__ == '__main__':
    infoMessage("........ Starting XN 1000 LIS ..........")
    # host = '0.0.0.0'
    host = '192.168.1.7'  # machine IP
    port = 5000  # machine port

    infoMessage("LIS HOST: " + host + " PORT: " + str(port))
    # totalclient = int(input('Enter number of clients: '))
    totalclient = 1
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, port))
    sock.listen(totalclient)
    connections = []
    infoMessage('Initiating clients ......')
    conn, address = sock.accept()
    connections.append(conn)
    # print('Connected with client', i+1)
    successMessage("Connection from: " + str(address))

    full_msg = ''
    while True:
        try:
            msg = conn.recv(8192)
            warningMessage("Result Received")
            mainMessage = str(msg)
            print("Main_Message:\n", mainMessage)
            mainMessage = mainMessage[1:]
            mainMessage = mainMessage[1:-1]
        except:
            errorMessage("Error! Connection Problem!")
            mainMessage = ""
        # infoMessage(msg)

        if len(mainMessage) > 0:
            hl7MessageParse(mainMessage)
            successMessage("Data Processed and Sent it to Server")
    conn.close()  # close the connection
