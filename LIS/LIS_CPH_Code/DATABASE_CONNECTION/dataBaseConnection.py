import mysql.connector
from mysql.connector import Error
from API_CONNECTION.commonMessage import *
def dbConnection():
    try:
        connection = mysql.connector.connect(host='localhost',
                                             database='chp_lis',
                                             user='root',
                                             password='')
        if connection.is_connected():
            db_Info = connection.get_server_info()
            successMessage("Connected to MySQL Server version: "+str(db_Info))
            cursor = connection.cursor()
            cursor.execute("select database();")
            record = cursor.fetchone()
            successMessage("You're connected to database: "+str(record))
            cursor = connection.cursor()
            return connection, cursor
    except Error as e:
        errorMessage("Error while connecting to MySQL"+ str(e))

def testFunction():
    print("From Test")