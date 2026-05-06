from API_CONNECTION.commonMessage import *
import socket
#from parseHL7Message_GETEIN_1600 import hl7MessageParse


if __name__ == '__main__':
    infoMessage("........ Starting CAPILLARYS_3_OCTA LIS ..........")
    host = '192.168.1.7' # server IP
    port = 55000 # server port

    infoMessage("LIS HOST: "+host+ " PORT: "+str(port))
    totalclient = 1
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, port))
    sock.listen(totalclient)
    connections = []
    infoMessage('Initiating clients ......')
    conn, address = sock.accept()
    connections.append(conn)
    successMessage("Connection from: " + str(address))

    full_msg = ''
    while True:
        msg = conn.recv(8192)
        mainMessage = str(msg)

        # infoMessage(msg)
        mainMessage = mainMessage[1:]
        mainMessage = mainMessage[1:-1]

        if len(msg) > 0:
            #hl7MessageParse(mainMessage)
            print(mainMessage)
            #successMessage("Data Processed and Sent it to Server")
    conn.close()  # close the connection