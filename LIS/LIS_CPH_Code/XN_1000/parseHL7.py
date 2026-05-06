from typing import Dict, List

import mysql.connector
from mysql.connector import Error
from dataSendToServer import *

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
            cursor.execute("select data FROM sysmax_xn_1000 limit 1")
            # record = cursor.fetchone()
            myresult = cursor.fetchall()
            # print(myresult)
            for x in myresult:
                singleData = str(x)
                splitedData = singleData.split("\\r")
                # print(words[0])
                i = 0
                sampleWiseResult = {}
                resultDataDic: dict[str, list[str]] = {}
                for r in splitedData:
                    if i == 3:
                        # print("Sample Id: ",r)
                        sampleIdList = r.split('|')
                        sampleId = sampleIdList[3].split(" ")[15].replace("^B", "")
                        # print(sampleId)
                        # H80720230003
                        sampleId = 2023070910005
                        sampleWiseResult["sampleId"] = sampleId

                    if 5 <= i <= 50:
                        singleResultItem=[]
                        # print("Result: ", r)
                        resultItemParam = r.split('|')
                        # print(resultItemParam)

                        resultID = resultItemParam[1]
                        resultName = resultItemParam[2].replace("^1","")
                        resultName=resultName.replace("^","")
                        resultValue = resultItemParam[3]
                        resultUnit = resultItemParam[4]

                        singleResultItem.append(resultID)
                        singleResultItem.append(resultName)
                        singleResultItem.append(resultValue)
                        singleResultItem.append(resultUnit)

                        # print(resultID, resultName, resultValue, resultUnit)
                        resultDataDic[resultID]=singleResultItem

                    i = i + 1
                # print('\n')
                sampleWiseResult["result"] = resultDataDic
                print(sampleWiseResult)
                sendDataToServer(sampleWiseResult)

    except Error as e:
        print("Error while connecting to MySQL", e)
