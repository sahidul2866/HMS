import socket
import mysql.connector
from mysql.connector import Error
import hl7

if __name__ == '__main__':

	try:
		connection = mysql.connector.connect(host='localhost',
											 database='chp_lis',
											 user='root',
											 password='')
		if connection.is_connected():
			db_Info = connection.get_server_info()
			print("Connected to MySQL Server version ", db_Info)
			cursor = connection.cursor()
			cursor.execute("select database();")
			record = cursor.fetchone()
			print("You're connected to database: ", record)
			cursor = connection.cursor()
	except Error as e:
		print("Error while connecting to MySQL", e)


	# Defining Socket
	# host = '192.168.1.201'
	host = '0.0.0.0'
	port = 18002
	# port = 5000
	# totalclient = int(input('Enter number of clients: '))
	totalclient=1
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
		msg = conn.recv(8192)
		print("Result Received: ")
		mainMessage = str(msg.decode())
		print(msg)


		if len(msg) > 0:
			print("Data Saved to Database")

	conn.close()  # close the connection

