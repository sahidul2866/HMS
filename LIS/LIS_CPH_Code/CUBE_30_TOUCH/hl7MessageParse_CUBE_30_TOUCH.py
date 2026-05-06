from API_CONNECTION.commonMessage import *
from API_CONNECTION.apiCURLFunction import *
MACHINE_NAME = "CUBE 30 TOUCH"
def hl7MessageParse(message):
    sampleWiseResult = {}
    resultDataDic = {}

    data = message.split("\\x")


    # ['>0020015101H463560', '101106231113   001000002\\r79']  =>>>>> 001000002 here '1' is High, '2' is Low, '8' is Err
    # Sesher dike 7 number bit



    sampleId = ""
    cnt = 0
    for i in range(0, len(data[0])):
        cnt+=1
        if cnt>11:
            sampleId +=data[0][i]

    try:
        result = data[1][13]+data[1][14]+data[1][15]
        print("Result=>",result)
    except IndexError:
        print("Index Error! in result")
        result ="Err"


    try:
        result = int(result)
    except ValueError:
        print("Value Error! in result")
        result = "Err"



    print("data=>", data)
    flag = True
    try:
        isError = data[1]
    except IndexError:
        print("Index Error! in isError => data[1]")
        flag = False

    if flag:
        isError = isError.split(" ")

        try:
            isError = isError[len(isError) - 1]
            #print("isError: ", isError)
        except IndexError:
            print("!!! --->isError!")

        try:
            isError = isError.split("\\r")
            isError = isError[0]
            print("Final isError:", isError)

            print("digit: ", isError[len(isError)-7])
            digit = isError[len(isError)-7]

            if digit=='8':
                result = "Err"
            elif digit=='1':
                result = "HIGH"
            elif digit=='2':
                result = "LOW"
        except IndexError:
            print("!!!IndexError in splitted isError!")

        result = str(result)

        res = []
        res.append("1")
        res.append("ESR")
        res.append(result)
        res.append("")

        resultDataDic["1"] = res

        sampleWiseResult["sampleId"] = sampleId
        sampleWiseResult["result"]=resultDataDic

        print("Final_Result: ",sampleWiseResult)
        if sampleId =="":
            print("Unsuccessful to sent server")
        else:
            try:
                resultSendToServer(MACHINE_NAME,sampleWiseResult)
                successMessage("Successfully Sent to server")
            except:
                print("Error while sending data to server!")
    else:
        print("!!! Error found! in ",message )
