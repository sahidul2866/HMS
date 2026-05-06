from DATABASE_CONNECTION.dataBaseConnection import dbConnection, testFunction
from API_CONNECTION.commonMessage import *
import socket
from VISION_PRO_C.parseResultMessage import hl7MessageParse

if __name__ == '__main__':
    infoMessage("........ Starting VISION PRO C LIS ..........")

    # Defining Socket
    # host = '0.0.0.0'
    host = '192.168.1.7' # machine IP
    port = 7051 # machine port Previous 7050

    infoMessage("LIS HOST: "+host+ " PORT: "+str(port))
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
        msg = conn.recv(8192)
        successMessage("Result Received")
        mainMessage = str(msg)
        print(mainMessage)
        # infoMessage(msg)
        mainMessage = mainMessage[1:]
        mainMessage = mainMessage[1:-1]

        if len(msg) > 0:
            # sql = """INSERT INTO sysmax_xn_1000 (data) VALUES ('Test')"""
            # cursor.execute("INSERT INTO lis_work_list (machine_name,machine_id,data) VALUES ('sysmax_xn_1000',1," + mainMessage + ")")
            # cursor.execute("INSERT INTO sysmax_xn_1000 (data) VALUES (" + mainMessage + ")")
            # connection.commit()
            infoMessage(mainMessage)
            # print("Data Saved to Database")
            hl7MessageParse(mainMessage)
            successMessage("Data Processed and Sent it to Server")
    conn.close()  # close the connection
