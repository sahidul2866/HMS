import socket
import mysql.connector
from mysql.connector import Error
import hl7

if __name__ == '__main__':

	# try:
	# 	connection = mysql.connector.connect(host='localhost',
	# 										 database='chp_lis',
	# 										 user='root',
	# 										 password='')
	# 	if connection.is_connected():
	# 		db_Info = connection.get_server_info()
	# 		print("Connected to MySQL Server version ", db_Info)
	# 		cursor = connection.cursor()
	# 		cursor.execute("select database();")
	# 		record = cursor.fetchone()
	# 		print("You're connected to database: ", record)
	# 		cursor = connection.cursor()
	# except Error as e:
	# 	print("Error while connecting to MySQL", e)


	# Defining Socket
	host = '192.168.1.11'
	port = 6005
	totalclient = int(input('Enter number of clients: '))
	# totalclient=1
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.bind((host, port))
	sock.listen(totalclient)
	connections = []
	print('Initiating clients')
	conn, address=sock.accept()
	connections.append(conn)
	# print('Connected with client', i+1)
	print("Connection from: " + str(address))

	full_msg = ''
	while True:
		msg = conn.recv(1024)
		print("Result Received: ")
		mainMessage = str(msg)
		print(msg)
		mainMessage = mainMessage[1:]
		mainMessage = mainMessage[1:-1]


		if len(msg) > 0:

			# sql = """INSERT INTO sysmax_xn_1000 (data) VALUES ('Test')"""
			# cursor.execute("INSERT INTO sysmax_xn_550 (data) VALUES ('"+mainMessage+"')")
			# connection.commit()
			print("Data Saved to Database")

			# sigmentMessage = mainMessage.split("\r")
			# print(sigmentMessage)
			# for segmentIten in sigmentMessage:
			# 	print()
			# 	print(segmentIten)
			# parseMessage = hl7.parse_hl7(mainMessage)
			# parseMessage=msg
			# print(parseMessage)
			print("Data Processing and Send it to Server")
		# if len(msg) <= 0:
		# 	break
		# full_msg += msg.decode()
		# print(full_msg)

	conn.close()  # close the connection

