# Import socket module
import socket

# Create a socket object
s = socket.socket()

# Define the port on which you want to connect
port = 12345

# Connect to the server on local computer
s.connect(('127.0.0.1', port))

# Receive data from the server
data = s.recv(1024)

# Print the received data
print(data.decode())

# Close the connection
s.close()