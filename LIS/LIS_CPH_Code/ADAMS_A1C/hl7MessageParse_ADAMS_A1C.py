from API_CONNECTION.commonMessage import *
from API_CONNECTION.apiCURLFunction import *

MACHINE_NAME = "ADAMS_A1C"

def hl7MessageParse(message):
    print("Raw Message: ",message)
    sampleId = ""  # sample ID
    resultInPercentise = []  # sample Result in Percentise
    resultInMol = []  # sample Result in mol

    sampleWiseResult = {}
    resultDataDic = {}

    for r in message:
        sampleIdList = r.split('|')

        if (sampleIdList[0] == "23O" and sampleIdList[1] == "1"):  # ID Hunting
            sampleId = sampleIdList[2].split('-')
            sampleId = sampleId[0]
            infoMessage("ID = > "+ str(sampleId))

        if (sampleIdList[0] == "24R" and sampleIdList[1] == "1" and len(resultInPercentise)==0):  # Percentise Result Hunting\
            resultInPercentise.append("1")
            resultInPercentise.append("ADAMS_A1C_P")   # Updated
            resultInPercentise.append(sampleIdList[3])
            resultInPercentise.append("%")
            print("Percentise => ", resultInPercentise)

        if (sampleIdList[0] == "25R" and sampleIdList[1] == "2" and len(resultInMol)==0):  # mol Result Hunting
            resultInMol.append("2")
            resultInMol.append("ADAMS_A1C_mm") # Updated
            resultInMol.append(sampleIdList[3])
            resultInMol.append("mmol/mol")
            print("Mol => ", resultInMol)

    resultDataDic["1"] = resultInPercentise
    resultDataDic["2"] = resultInMol

    sampleWiseResult["sampleId"] = sampleId
    sampleWiseResult["result"] = resultDataDic
    warningMessage("Result: "+str(sampleWiseResult))
    #infoMessage(sampleWiseResult)
    if sampleId != "":
        try:
            resultSendToServer(MACHINE_NAME, sampleWiseResult)
            successMessage("Successfully Sent to server")
        except:
            errorMessage("Error while sending data to server!")
    else:
        errorMessage("Unsuccessful to sent server")
