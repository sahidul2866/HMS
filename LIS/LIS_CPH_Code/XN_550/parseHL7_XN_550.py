from API_CONNECTION.commonMessage import *
from API_CONNECTION.apiCURLFunction import *
MACHINE_NAME = "XN 550"
def hl7MessageParse(message):
    splitedData = message.split("\\r")
    i = 0
    sampleWiseResult = {}
    resultDataDic = {}
    for r in splitedData:
        if i == 3:
            # print("Sample Id: ",r)
            sampleIdList = r.split('|')
            # print(sampleIdList)
            # sampleId = sampleIdList[3].replace("^B", "").replace("1^", "").replace("2^", "")
            try:
                sampleId =sampleIdList[3].split('^')[-2:-1]
            except IndexError:
                sampleId =""

            if len(sampleId)>0:
                sampleId=str(sampleId[0])
                sampleId = sampleId.strip()
                #print(sampleId)
                # print(sampleId)
                sampleWiseResult["sampleId"] = sampleId


        if 5 <= i <= 45:
            errorFlag = False
            singleResultItem=[]

            resultItemParam = r.split('|')
            # print(resultItemParam)

            ################# Updated ###################### by Plabon
            try:
                resultID = resultItemParam[1]
                # print("Index exists")
            except IndexError:
                errorFlag = True
                # print("Index doesn't exist")
                resultID = ""

            try:
                resultName = resultItemParam[2].replace("^1","")
                resultName = resultName.replace("^", "")
                # print("Index exists")
            except IndexError:
                errorFlag = True
                # print("Index doesn't exist")
                resultName = ""

            try:
                resultValue = resultItemParam[3]
                # print("Index exists")
            except IndexError:
                errorFlag = True
                # print("Index doesn't exist")
                resultValue = ""
            ################################################



            try:
                resultUnit = resultItemParam[4]
                # print("Index exists")
            except IndexError:
                # print("Index doesn't exist")
                resultUnit = ""
            # if resultItemParam[4] in resultItemParam:
            #     resultUnit = resultItemParam[4]
            # else:
            #     resultUnit = ""



            ################# Updated ###################### by Plabon
            if errorFlag == False:
                if "NEUT" in resultName or "LYMPH" in resultName or "MONO" in resultName or "EO" in resultName or "BASO" in resultName:
                    try:
                        resultValue = round(float(resultValue))
                    except:
                        resultValue = 0
                    # if resultValue.isnumeric():
                    #     resultValue=round(float(resultValue))
                    # else:
                    #     resultValue="0"

                singleResultItem.append(resultID)
                singleResultItem.append(resultName)
                singleResultItem.append(resultValue)
                singleResultItem.append(resultUnit)

                # print(resultID, resultName, resultValue, resultUnit)
                resultDataDic[resultID] = singleResultItem
                # print(resultDataDic)
            ################################################


        i = i + 1
    # print('\n')
    sampleWiseResult["result"] = resultDataDic
    # print(resultDataDic)
    # infoMessage(sampleWiseResult)
    warningMessage(str(sampleWiseResult))
    if 'sampleId' in sampleWiseResult.keys():
        try:
            resultSendToServer(MACHINE_NAME,sampleWiseResult)
            successMessage("Successfully Sent to server")
        except:
            errorMessage("Error while sending data to server!")
    else:
        errorMessage("Not Sent to server")

