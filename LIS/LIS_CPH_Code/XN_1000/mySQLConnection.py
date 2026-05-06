import mysql.connector
from mysql.connector import Error

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
        dataString="aaaaaaaa";
        # sql = """INSERT INTO sysmax_xn_1000 (data) VALUES ('Test')"""
        cursor.execute("INSERT INTO sysmax_xn_1000 (data) VALUES ('"+dataString+"')")
        connection.commit()

except Error as e:
    print("Error while connecting to MySQL", e)
finally:
    if connection.is_connected():
        cursor.close()
        connection.close()
        print("MySQL connection is closed")
