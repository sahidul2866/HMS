from API_CONNECTION.apiCURLFunction import *
import json

ADVIACentaurCP = {}

ADVIACentaurCP["FT3"] = "FT3.DOSE"
ADVIACentaurCP["FT4"] = "FT4.DOSE"
ADVIACentaurCP["ThCG"] = "ThCG.DOSE"
ADVIACentaurCP["PRL"] = "PRL.DOSE"
ADVIACentaurCP["LH"] = "LH.DOSE"
ADVIACentaurCP["TSTII"] = "TSTII.DOSE"
ADVIACentaurCP["PRGE"] = "PRGE.DOSE"
ADVIACentaurCP["tIgE"] = "tIgE.DOSE"
ADVIACentaurCP["VB12"] = "VB12.DOSE"
ADVIACentaurCP["TNIH"] = "TnIH.DOSE"
ADVIACentaurCP["aHBs2"] = "aHBs2.INDX"
ADVIACentaurCP["aHCV"] = "aHCV.INDX"
ADVIACentaurCP["COR"] = "Cor.DOSE"
ADVIACentaurCP["PSA"] = "PSA.DOSE"
ADVIACentaurCP["PBNP"] = "PBNP.DOSE"
ADVIACentaurCP["FSH"] = "FSH.DOSE"
ADVIACentaurCP["TSH"] = "TSH3UL.DOSE"
ADVIACentaurCP["CHIV"] = "CHIV.INDX"
ADVIACentaurCP["PCT"] = "PCT.DOSE"
ADVIACentaurCP["IRI"] = "IRI.DOSE"
ADVIACentaurCP["FER"] = "Fer.DOSE"
ADVIACentaurCP["aTPO"] = "aTPO.DOSE"
ADVIACentaurCP["HBs"] = "HBsII.INDX"


def getTestCode(code):
    if code in ADVIACentaurCP:
        return ADVIACentaurCP[code]
    else:
        return ""


def getTestCodeForServer(testCode):
    return ADVIACentaurCP[testCode]


def getTestCodeByName(testName):
    for key, value in ADVIACentaurCP.items():
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
