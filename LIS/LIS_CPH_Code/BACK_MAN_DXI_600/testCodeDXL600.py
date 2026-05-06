from API_CONNECTION.apiCURLFunction import *
import json

BackManDXL600 = {}
BackManDXL600["Prog"] = "PRGE.DOSE"
BackManDXL600["hFSH"] = "FSH.DOSE"
BackManDXL600["hLH"] = "LH.DOSE"
BackManDXL600["Cortisol"] = "Cor.DOSE"
BackManDXL600["Ferritin"] = "Fer.DOSE"
BackManDXL600["PRL"] = "PRL.DOSE"
BackManDXL600["PSA-Hyb"] = "PSA.DOSE"
BackManDXL600["AFP"] = "AFP.DOSE"
BackManDXL600["VitB12"] = "VB12.DOSE"
BackManDXL600["Testo"] = "TSTII.DOSE"
BackManDXL600["FT-6"] = "IL6.DOSE"
BackManDXL600["FT3"] = "FT3.DOSE"
BackManDXL600["FRT4"] = "FT4.DOSE"
BackManDXL600["FFT4"] = "FT4.DOSE"
BackManDXL600["HBsAgV3"] = "HBsAg.DOSE"
BackManDXL600["CEA2"] = "CEA.DOSE"
BackManDXL600["HIVCO"] = "CHIV.DOSE"
BackManDXL600["VitdD"] = "VitD.DOSE"
BackManDXL600["HCG5"] = "ThCG.DOSE"
BackManDXL600["HCV-3"] = "aHCV.DOSE"
BackManDXL600["TSH3"] = "TSH3UL.DOSE"
BackManDXL600["AMH"] = "AMH.DOSE"
BackManDXL600["hsTnI"] = "TnIH.DOSE"
BackManDXL600["GI19-9Ag"] = "CA_19-9.DOSE"
BackManDXL600["OV125Ag"] = "CA_125.DOSE"
BackManDXL600["BR15-3Ag"] = "CA_15-3.DOSE"


def getTestCodeForServer(testCode):
    return BackManDXL600[testCode]
def getTestCodeByName(testName):
    for key, value in BackManDXL600.items():
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
                    testCodeList = testCodeList + "^^^"+testCode
                else:
                    testCodeList = testCodeList + "\^^^" + testCode
            # print(t,testCode)
            if testCode is None:
                print(t, testCode)
        # print(testCodeList)
        return testCodeList

# if __name__ == '__main__':
#     try:
#         # print(getTestListStr('I1017526'))
#         print(getTestListStr('I1017527'))
#
#     except:
#         print("Not Found")
