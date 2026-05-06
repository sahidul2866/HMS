from API_CONNECTION.apiCURLFunction import *
from API_CONNECTION.commonMessage import *
import json

DimantionEXL = {}
DimantionEXL["ALB"] = "ALB"
DimantionEXL["ALPI"] = "ALPI"
DimantionEXL["GLUC"] = "GLUC"
DimantionEXL["CHOL"] = "CHOL"
DimantionEXL["TGL"] = "TGL"
DimantionEXL["AHDL"] = "AHDL"
DimantionEXL["ALDL"] = "ALDL"
DimantionEXL["BUN"] = "BUN"
DimantionEXL["CRE2"] = "CRE2"
DimantionEXL["TBI"] = "TBI"
DimantionEXL["ALTI"] = "ALTI"
DimantionEXL["AST"] = "AST"
DimantionEXL["TP"] = "TP"
DimantionEXL["URCA"] = "URCA"
DimantionEXL["MBI"] = "MBI"
DimantionEXL["RCRP"] = "RCRP"
DimantionEXL["CA"] = "CA"
DimantionEXL["AMY"] = "AMY"
DimantionEXL["LIPL"] = "LIPL"
DimantionEXL["IRON"] = "IRON"
DimantionEXL["IBCT"] = "IBCT"
DimantionEXL["PHOS"] = "PHOS"
DimantionEXL["CKI"] = "CKI"
DimantionEXL["DBI"] = "DBI"
DimantionEXL["GGT"] = "GGT"
DimantionEXL["LDI"] = "LDI"
DimantionEXL["MG"] = "MG"
DimantionEXL["MALB"] = "MALB"
DimantionEXL["UCFP"] = "UCFP"
DimantionEXL["ECO2"] = "ECO2"
DimantionEXL["NA"] = "NA"
DimantionEXL["K"] = "K"
DimantionEXL["CL"] = "CL"
DimantionEXL["VITD"] = "VitD.DOSE"
DimantionEXL["MA/CR"] = "MA/CR"
DimantionEXL["IBIL"] = "IBIL"

def getTestCodeByName(testName):
    for key, value in DimantionEXL.items():
        if testName == value:
            return key


def getTestListStr(barcode):
    workListData = getWorkList(barcode)
    jsonData = json.loads(workListData)
    totalTestCount = 0
    if len(jsonData) > 0:
        testName = str(jsonData[0]['test_name'])
        testList = testName.split(',')
        testCodeList = ""
        for t in testList:
            testCode = getTestCodeByName(t)
            if testCode is not None:
                testCodeList = testCodeList + "\x1c" + testCode
                totalTestCount = totalTestCount + 1
            if testCode is None:
                errorMessage("Test Id: " + t + " Test Name: " + str(testCode))
        return [totalTestCount,testCodeList]


# if __name__ == '__main__':
#     totalTestString = getTestListStr('B1033342')
#     # totalTest = totalTestString.split("\x1c")
#     print(totalTestString,totalTestString[1])
