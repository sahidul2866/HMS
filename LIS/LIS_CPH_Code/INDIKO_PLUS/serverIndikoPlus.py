import socket
from hl7MessageParse_INDIKO_PLUS import *
import hl7
import  json

if __name__ == '__main__':
    host = '192.168.1.7'
    port = 10100
    totalclient = 1
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, port))
    sock.listen(totalclient)
    connections = []
    print("Current HOST IP: " + str(host) + " PORT: " + str(port))
    print('Initiating clients')
    conn, address = sock.accept()
    connections.append(conn)
    print("Connection from: " + str(address))

    result_message = []
    while True:
        msg = conn.recv(8192)
        #print(msg)
        mainMessage = str(msg)
        if len(mainMessage) > 0:
            #print("Data Received: ", mainMessage)
            if "\\x05" in mainMessage:
                print("ENQ=>",mainMessage)
                mess = f'''\x06'''
                conn.send(mess.encode())
                #print("ACK sent")
            if "\\x02" in mainMessage:
                mess = f'''\x06'''
                conn.send(mess.encode())
                #print("ACK sent")

                if "O|" in mainMessage or "R|" in mainMessage:
                    result_message.append(mainMessage)
            if "\\x04" in mainMessage:
                print("+++++++++++++++++++++++++++++++++++++++++++++++")
                for m in result_message:
                    print(m)
                print("------------------------------------------------")
                hl7MessageParse(result_message)
                result_message.clear()

    conn.close()  # close the connection
































