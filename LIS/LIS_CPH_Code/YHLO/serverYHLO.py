from DATABASE_CONNECTION.dataBaseConnection import dbConnection
import socket

import hl7
import  json

if __name__ == '__main__':

    resultObj = dbConnection()
    connection = resultObj[0]
    cursor = resultObj[1]

    # Defining Socket
    host = '192.168.3.195'
	# host = '0.0.0.0'
    port = 8000
    # totalclient = int(input('Enter number of clients: '))
    totalclient = 1
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, port))
    sock.listen(totalclient)
    connections = []
    print("Current HOST IP: " + str(host) + " PORT: " + str(port))
    print('Initiating clients')
    conn, address = sock.accept()
    connections.append(conn)
    # print('Connected with client', i+1)
    print("Connection from: " + str(address))

    full_msg = ''
    while True:
        msg = conn.recv(8192)
        print("Data Received: ", str(msg))
        # mainMessage = json.dumps( str(msg) )
        # print(msg)
        # mainMessage = mainMessage[1:]
        # mainMessage = mainMessage[1:-1]

        # if len(msg) > 0:
        #     # sql = """INSERT INTO sysmax_xn_1000 (data) VALUES ('Test')"""
        #     cursor.execute("INSERT INTO yholo_iflash_1200 (data) VALUES ('" + mainMessage + "')")
        #     connection.commit()
        #     print("Data Saved to Database")
        #
        #     # sigmentMessage = mainMessage.split("\r")
        #     # print(sigmentMessage)
        #     # for segmentIten in sigmentMessage:
        #     # 	print()
        #     # 	print(segmentIten)
        #     # parseMessage = hl7.parse_hl7(mainMessage)
        #     # parseMessage=msg
        #     # print(parseMessage)
        #     print("Data Processing and Send it to Server")
    # if len(msg) <= 0:
    # 	break
    # full_msg += msg.decode()
    # print(full_msg)

    conn.close()  # close the connection
