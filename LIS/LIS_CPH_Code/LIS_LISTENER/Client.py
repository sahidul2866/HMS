import socket
from DATABASE_CONNECTION.dataBaseConnection import dbConnection
# Creating Client Socket
if __name__ == '__main__':
	# host = '127.0.0.1'
	# port = 8080
	host = '192.168.1.29'
	# host = '0.0.0.0'
	port = 5000

	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	# Connecting with Server
	sock.connect((host, port))
	data=""
	while True:
		sock.send(str(data).encode())
