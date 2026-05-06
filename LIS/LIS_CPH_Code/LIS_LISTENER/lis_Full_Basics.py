from DATABASE_CONNECTION.dataBaseConnection import dbConnection,testFunction

resultObj = dbConnection()
connection = resultObj[0]
cursor = resultObj[1]

cursor.execute("select data FROM sysmax_xn_1000 limit 3")
# record = cursor.fetchone()
myresult = cursor.fetchall()
# print(myresult)
for x in myresult:
    singleData = str(x)
    print(singleData)

testFunction()