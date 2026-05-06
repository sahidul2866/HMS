# Import socket module
import socket

# Create a socket object
s = socket.socket()
# Bind the socket to a port
port = 12345
s.bind(('', port))
# Listen for incoming connections
s.listen(5)

# Accept a connection from a client
c, addr = s.accept()

# Print the client address
print('Connected to', addr)

# Receive a message from the client
msg = c.recv(1024)

# Print the received message
print(msg.decode())

# Close the connection
c.close()