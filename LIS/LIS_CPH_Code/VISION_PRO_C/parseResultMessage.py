from API_CONNECTION.commonMessage import *
from API_CONNECTION.apiCURLFunction import *
MACHINE_NAME = "VISION Pro C"

def hl7MessageParse(message):
    if "\\x0b" in message:
        dataSigment = message.split("\\r")
        print(dataSigment)

        sampleWiseResult = {}
        resultDataDic = {}

        sampleIDSegment = dataSigment[2]
        sampleIDSegmentList = sampleIDSegment.split('|')
        sampleId = ""

        if sampleIDSegmentList[0] == "OBR":
            sampleId = sampleIDSegmentList[3]
            sampleWiseResult["sampleId"] = sampleId
            singleResultItem = []

        esrResultSegment = dataSigment[3]
        esrResultSegmentList = esrResultSegment.split('|')
        if esrResultSegmentList[0] == "OBX":
            resultId = esrResultSegmentList[1]
            resultName = esrResultSegmentList[4]
            resultValue = esrResultSegmentList[5]
            resultUnit = esrResultSegmentList[6]

            singleResultItem.append(resultId)
            singleResultItem.append(resultName)
            singleResultItem.append(resultValue)
            singleResultItem.append(resultUnit)
            resultDataDic[resultId] = singleResultItem

        sampleWiseResult["result"] = resultDataDic
        warningMessage(str(sampleWiseResult))

        try:
            resultSendToServer(MACHINE_NAME,sampleWiseResult)
            successMessage("Successfully Sent to server")
        except:
            errorMessage("Error while sending data to server!")
