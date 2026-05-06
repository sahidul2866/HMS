from API_CONNECTION.apiCURLFunction import *
import json
backManAU480 = {}
backManAU480["011"] = "ASO"
backManAU480["051"] = "LIPL"
backManAU480["053"] = "MG"
backManAU480["061"] = "RFn"
backManAU480["066"] = "TBI"
backManAU480["071"] = "TGL"
backManAU480["002"] = "ALB"
backManAU480["004"] = "ALTI"
backManAU480["013"] = "AST"
backManAU480["042"] = "AHDL"
backManAU480["047"] = "IRON"
# backManAU480["072"] = "IBCT"
backManAU480["072"] = "TIBC"  #UIBC
backManAU480["097"] = "NA"
backManAU480["098"] = "K"
backManAU480["099"] = "CL"
backManAU480["017"] = "ECO2"
backManAU480["003"] = "ALPI"
backManAU480["038"] = "GGT"
#backManAU480["013"] = "AST"
backManAU480["023"] = "CHOL"
backManAU480["104"] = "CRE2"
backManAU480["074"] = "URCA"
backManAU480["020"] = "CALA"
backManAU480["030"] = "RCRP"
backManAU480["039"] = "GLUC"
backManAU480["050"] = "ALDL"
backManAU480["103"] = "MALB"
backManAU480["095"] = "MA/CR"
backManAU480["009"] = "AMY"
backManAU480["069"] = "TP"
backManAU480["073"] = "BUN"
backManAU480["064"] = "TBI"


def getTestCodeByName(testName):
    for key, value in backManAU480.items():
        # print(key, value)
        if testName == value:
            return key

def getNameByTestCode(testCode):
    for key, value in backManAU480.items():
        # print(key, value)
        if testCode == key:
            return value
def getMachineCodeStr(bercode):
    workListData = getWorkList(bercode)
    jsonData = json.loads(workListData)
    if len(jsonData) > 0:
        testName = str(jsonData[0]['test_name'])
        testList = testName.split(',')
        testCodeList = ""
        for t in testList:
            testCode = getTestCodeByName(t)
            if testCode is not None:
                testCodeList = testCodeList + testCode
            # print(t,testCode)
            if testCode is None:
                print(t, testCode)
        # print(testCodeList)
        return testCodeList
    else:
        return None

#
# if __name__ == '__main__':
#     # print(getTestCodeByName("CRE2"))
#     # print(getNameByTestCode("009"))
#     print(getMachineCodeStr("D1001395"))
