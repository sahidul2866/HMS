import serial
import mysql.connector
from mysql.connector import Error

serialPort = serial.Serial(port="COM3", baudrate=9600, bytesize=8, parity=serial.PARITY_NONE,
                           stopbits=serial.STOPBITS_ONE, timeout=.1)
# serialPort = serial.Serial(port="COM3", baudrate=9600, bytesize=8, timeout=30, stopbits=serial.STOPBITS_ONE)
serialString = ""  # Used to hold data coming over UART

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

# adams_a1c

testResult = ""
while 1:
    # serialString = serialPort.readline()
    # print(serialString)
    # serialPort.write(b"Thank you for sending data \r\n")
    if serialPort.in_waiting > 0:
        # serialString = serialPort.read()
        serialString = serialPort.readline()
        messageRawData = str(serialString)
        # print(serialString)
        messageRawData = messageRawData[1:]
        messageRawData = messageRawData[1:-1]
        print(messageRawData)
        if "\\x05'" not in messageRawData and "\\x04'" not in messageRawData:
            testResult += messageRawData.replace("\\x0", "").replace("\\x5", "").replace("\\x4", "")

        print(messageRawData)
        if "\\x04'" in str(serialString):
            print(testResult)
            # testResult = testResult.replace("\\x05", "").replace("",)
            cursor.execute("INSERT INTO adams_a1c (data) VALUES ('" + testResult + "')")
            connection.commit()
            print("Data Saved to Database")
            testResult = ""
        # if "\\x05'" in messageRawData:
        #    testResult+=messageRawData
        # if "\\x04'" in messageRawData:
        #    cursor.execute("INSERT INTO adams_a1c (data) VALUES (" + testResult + ")")
        #    connection.commit()
        #    print("Data Saved to Database")
        #    print(testResult)
        #    testResult = ""
        serialPort.write(b'\x06')
    #      serialPort.write(b"Thank you for sending data \r\n")
