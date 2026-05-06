from API_CONNECTION.commonMessage import *
from API_CONNECTION.apiCURLFunction import *


def hl7MessageParse(message):
    # print("\nIn hl7:\n")

    sampleWiseResult = {}
    resultDataDic = {}

    data = message.split("\\x1c")
    print("Data = > ", data)

    sampleId = data[3]
    serial_no = 0
    #if data[0] == "x02R":
    for i in range(11,len(data)-2,4):
        serial_no += 1
        resultName = data[i]
        result = data[i+1]
        unit = data[i+2]


        print("test_name = ",resultName, " ; result = ", result, " ; unit = ", unit)

        res = []
        res.append(str(serial_no))
        res.append(resultName)
        res.append(result)
        res.append(unit)

        resultDataDic[str(serial_no)] = res

    sampleWiseResult["sampleId"] = sampleId
    sampleWiseResult["result"] = resultDataDic

    resultSendToServer("Dimension Exl",sampleWiseResult)

    print("Final_result: ", sampleWiseResult)


# if __name__ == '__main__':
#     #mess = []
#     #data = str(b'\x02P\x1cDIM\x1c1\x1c1\x1c0\x1c48\x03\x06')
#     #mess.append(data)
#     data = str(b'\x02R\x1c*\x1c23072610067\x1c23072610067\x1c1\x1c\x1c0\x1c153610260723\x1c1\x1c1\x1c3\x1cALPI\x1c136\x1cU/L\x1c\x1cAST\x1c220\x1cU/L\x1c\x1cALTI\x1c106\x1cU/L\x1c\x1c2B\x03\x05')
#     #mess.append(data)
#     #data = str(b'\x02P\x1cDIM\x1c1\x1c1\x1c0\x1c48\x03\x06')
#     #mess.append(data)
#     #print("data inserted")
#     hl7MessageParse(data)
