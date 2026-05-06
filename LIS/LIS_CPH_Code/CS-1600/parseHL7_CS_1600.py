from API_CONNECTION.apiCURLFunction import *
from API_CONNECTION.commonMessage import *


def hl7MessageParse(message):
    print("Test:",message)
    splitedData = message.split(" ")
    print("Splitted:",splitedData)
    i = 0
    sampleWiseResult = {}
    resultDataDic = {}
    dataList = []
    singleResultItem = []

    for r in splitedData:
        if r.strip():
            print(r)
            dataList.append(r)
    try:
        sampleId = dataList[1]
        sampleWiseResult["sampleId"] = sampleId
    except IndexError:
        print("Index Error!")
        sampleId=""

    try:
        resultID = dataList[2]
        singleResultItem.append(dataList[2])
        singleResultItem.append(dataList[2])
        singleResultItem.append(dataList[3])
        singleResultItem.append("")
    except IndexError:
        resultID = ""

    resultDataDic[resultID] = singleResultItem
    singleResultItem = []

    try:
        resultID = dataList[4]
        singleResultItem.append(dataList[4])
        singleResultItem.append(dataList[4])
        singleResultItem.append(dataList[5])
        singleResultItem.append("")
    except IndexError:
        resultID=""

    resultDataDic[resultID] = singleResultItem
    singleResultItem=[]

    try:
        resultID = dataList[6]
        singleResultItem.append(dataList[6])
        singleResultItem.append(dataList[6])
        singleResultItem.append(dataList[7])
        singleResultItem.append("")

    except IndexError:
        resultID=""

    resultDataDic[resultID] = singleResultItem
    singleResultItem = []
    try:
        resultID = dataList[8]
        singleResultItem.append(dataList[8])
        singleResultItem.append(dataList[8])
        singleResultItem.append(dataList[9])
        singleResultItem.append("")
    except IndexError:
        singleResultItem.append("")
        resultID=""

    resultDataDic[resultID] = singleResultItem
    singleResultItem = []
    sampleWiseResult["result"] = resultDataDic
    # infoMessage(sampleWiseResult)
    print("Final Result:",sampleWiseResult)
    #resultSendToServer(sampleWiseResult)


if __name__ == '__main__':
    message = "D1210101U210723151900000101  2023072110007B               041  145 043  109 044  110 051  231 \x03"
    hl7MessageParse(message)
