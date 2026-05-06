from API_CONNECTION.apiCURLFunction import *
import json

liasonXLCode = {}
# liasonXLCode["HBsAgQ^^DOSE"] = "HBsII.INDX"
# liasonXLCode["FT3^^DOSE"] = "FT3.DOSE"
# liasonXLCode["FT4^^DOSE"] = "FT4.DOSE"
# liasonXLCode["HCVAb^^DOSE"] = "aHCV.INDX"
# liasonXLCode["Trep^^DOSE"] = "SYPH.INDX"
# liasonXLCode["TSH^^DOSE"] = "TSH3UL.DOSE"
# liasonXLCode["HCG^^DOSE"] = "ThCG.DOSE"
# liasonXLCode["Prol^^DOSE"] = "PRL.DOSE"
# liasonXLCode["TESTO19^^DOSE"] = "TSTII.DOSE"
# liasonXLCode["PSA^^DOSE"] = "PSA.DOSE"
# liasonXLCode["Ferr^^DOSE"] = "Fer.DOSE"
# # liasonXLCode["CHIV"] ="CHIV.INDX"    # CONFUSED HIV 3 TA
# liasonXLCode["HPYG^^DOSE"] = "HPYG.DOSE"  # New

liasonXLCode["HBsAgQ"] = "HBsII.INDX"
liasonXLCode["FT3"] = "FT3.DOSE"
liasonXLCode["FT4"] = "FT4.DOSE"
liasonXLCode["HCVAb"] = "aHCV.INDX"
liasonXLCode["Trep"] = "SYPH.INDX"
liasonXLCode["TSH"] = "TSH3UL.DOSE"
liasonXLCode["HCG"] = "ThCG.DOSE"
liasonXLCode["Prol"] = "PRL.DOSE"
liasonXLCode["TESTO19"] = "TSTII.DOSE"
liasonXLCode["PSA"] = "PSA.DOSE"
liasonXLCode["Ferr"] = "Fer.DOSE"
# liasonXLCode["CHIV"] ="CHIV.INDX"    # CONFUSED HIV 3 TA
liasonXLCode["HPYG"] = "HPYG.DOSE"  # New

def getTestCode(code):
    if code in liasonXLCode:
        return liasonXLCode[code]
    else:
        return ""


def getTestCodeForServer(testCode):
    return liasonXLCode[testCode]


def getTestCodeByName(testName):
    for key, value in liasonXLCode.items():
        if testName == value:
            return key


def getTestListStr(barcode):
    workListData = getWorkList(barcode)
    jsonData = json.loads(workListData)
    if len(jsonData) > 0:
        testName = str(jsonData[0]['test_name'])
        testList = testName.split(',')
        testCodeList = ""

        for t in testList:
            testCode = getTestCodeByName(t)
            if testCode is not None:
                if testCodeList == "":
                    testCodeList = testCodeList + "^^^" + testCode
                else:
                    testCodeList = testCodeList + "\^^^" + testCode
            # print(t,testCode)
            if testCode is None:
                print(t, testCode)
        # print(testCodeList)
        return testCodeList
