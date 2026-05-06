import socket

from API_CONNECTION.commonMessage import *
from DATABASE_CONNECTION.dataBaseConnection import dbConnection
from XN_550.parseHL7_XN_550 import hl7MessageParse


if __name__ == '__main__':
	infoMessage("........ Starting XN 550 LIS ..........")
	dataBaseObj = dbConnection()
	connection = dataBaseObj[0]
	cursor = dataBaseObj[1]

	# Defining Socket
	# host = '192.168.1.11'
	# host = '0.0.0.0'
	host = '192.168.1.7'
	port = 6005
	# totalclient = int(input('Enter number of clients: '))
	totalclient=1
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.bind((host, port))
	sock.listen(totalclient)
	connections = []

	infoMessage("Current HOST IP: "+ str(host) + " PORT: "+ str(port))
	warningMessage('Initiating clients........')

	conn, address=sock.accept()
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

		if len(mainMessage) > 0:

			# sql = """INSERT INTO sysmax_xn_1000 (data) VALUES ('Test')"""
			# cursor.execute("INSERT INTO sysmax_xn_550 (data) VALUES ('"+mainMessage+"')")
			# cursor.execute("INSERT INTO lis_work_list (machine_name,machine_id,data) VALUES ('sysmax_xn_550',2," + mainMessage + ")")
			# connection.commit()
			# print("Data Saved to Database")
			hl7MessageParse(mainMessage)
			successMessage("Data Processed and Sent it to Server")
		# if len(msg) <= 0:
		# 	break
		# full_msg += msg.decode()
		# print(full_msg)

	conn.close()  # close the connection

