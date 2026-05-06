import socket

if __name__ == '__main__':
	# Defining Socket
	host = '192.168.1.29'
	port = 5000
	totalclient = int(input('Enter number of clients: '))
	# totalclient = 1

	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.bind((host, port))
	sock.listen(totalclient)
	# Establishing Connections
	connections = []
	print('Initiating clients')
	for i in range(totalclient):
		# conn = sock.accept()
		conn, address=sock.accept()
		connections.append(conn)
		print('Connected with client', i+1)
		print("Connection from: " + str(address))

	fileno = 0
	idx = 0
	for conn in connections:
		# Receiving File Data
		idx += 1
		# data = conn[0].recv(1024).decode()

		while True:
			# receive data stream. it won't accept data packet greater than 1024 bytes
			data = conn.recv(1024)
			# data = conn.recv(1024)
			# print(data.decode("utf-8"))
			filename = 'DATA_RECEIVE' + str(fileno) + '.txt'
			fileno = fileno + 1
			fo = open(filename, "w")
			while data:
				if not data:
					break
				else:
					fo.write(data.decode("utf-8"))
					# data = conn[0].recv(1024).decode()

			print()
			print('Receiving file from client', idx)
			print()
			print('Received successfully! New filename is:', filename)
			fo.close()
			# print(conn)
			# print(data)
			if not data:
				# if data is not received break
				break
			print("User : " + str(data))
			# data = input(' -> ')
			# data = 'H|\^&|||||||||||E1394-97\rP|1|||100|^HARUN^TEST||55556666|M|||||^Dr.1||||||||||||^^^WEST\rC|1||PatientComments\rO|1|2^1^ 1234567890^B||^^^^WBC\^^^^RBC\^^^^HGB\^^^^HCT\^^^^MCV\^^^^MCH\^^^^MCHC\^^^^PLT\^^^^NEUT%\^^^^LYMPH%\^^^^MONO%\^^^^EO%\^^^^BASO%\^^^^NEUT#\^^^^LYMPH#\^^^^MONO#\^^^^EO#\^^^^BASO#\^^^^RDW-SD\^^^^RDW-CV\^^^^PDW\^^^^MPV\^^^^P-LCR\^^^^PCT||20010807101000|||||N||||||||||||||Q\rC|1||HARUN Comment\rL|1|N\r'
			# conn.send(data.encode())  # send data to the client

		conn.close()  # close the connection
		# Creating a new file at server end and writing the data
		# filename = 'output'+str(fileno)+'.txt'
		# fileno = fileno+1
		# fo = open(filename, "w")
		# while data:
		# 	if not data:
		# 		break
		# 	else:
		# 		fo.write(data)
		# 		data = conn[0].recv(1024).decode()
		# 		print()
		# 		print('Receiving file from client', idx)
		# 		print()
		# 		print('Received successfully! New filename is:', filename)
		# fo.close()
	# Closing all Connections
	for conn in connections:
		conn[0].close()
