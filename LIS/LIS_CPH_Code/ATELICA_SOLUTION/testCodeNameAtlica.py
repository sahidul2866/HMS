from API_CONNECTION.apiCURLFunction import *
import json
import uuid
def getMachineCodeStr(bercode):
    workListData = getWorkList(bercode)
    jsonData = json.loads(workListData)
    if len(jsonData) > 0:
        testName = str(jsonData[0]['test_name'])
        testList = testName.split(',')
        testCodeList = []
        for t in testList:
            print(t)
            if "." in t:
                testCodeList.append(t.split('.')[0])
        return testCodeList
    else:
        return None

def getOrderString(bercode):
    testList = getMachineCodeStr(bercode)
    orderString = ""
    for testName in testList:
        orderUUID = str(uuid.uuid4()).replace("-", "")
        # print(orderUUID)
        # testName = "TSH3UL"
        orderString = orderString + "\rORC|NW\rTQ1|||||||||R^^HL70485\rOBR||" + orderUUID + "||" + testName + "^^99SiemensHDXTestCode||||||||||||01025232\rTCD|" + testName + "^^99SiemensHDXTestCode"
    # print(orderString)
    return orderString

# if __name__ == '__main__':

    # orderUUID = str(uuid.uuid4()).replace("-", "")
    # print(orderUUID)
    # testName = "TSH3UL"
    # singleTest="\rORC|NW\rTQ1|||||||||R^^HL70485\rOBR||"+orderUUID+"||"+testName+"^^99SiemensHDXTestCode||||||||||||01025232\rTCD|"+testName+"^^99SiemensHDXTestCode"
    #
    # testList = getMachineCodeStr("I1001416")
    # print(testList)
    # orderString = ""
    # for testName in testList:
    #     singleOrderString = ""
    #     orderUUID = str(uuid.uuid4()).replace("-", "")
    #     # print(orderUUID)
    #     # testName = "TSH3UL"
    #     orderString = orderString+"\\rORC|NW\\rTQ1|||||||||R^^HL70485\\rOBR||" + orderUUID + "||" + testName + "^^99SiemensHDXTestCode||||||||||||01025232\\rTCD|" + testName + "^^99SiemensHDXTestCode"
    #
    # print(orderString)
    # print(getOrderString("I1001416"))