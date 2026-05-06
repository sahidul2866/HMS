__author__ = 'Plabon Dibra'
from API_CONNECTION.commonMessage import *
from API_CONNECTION.apiCURLFunction import *
MACHINE_NAME = "D_10"
def hl7MessageParse(message):

    sampleId = ""  # sample ID
    sampleWiseResult = {}
    resultDataDic = {}

    for m in message:
        if "23O" in m:
            tmp =  m.split('|')
            try:
                sampleId = tmp[2]
            except IndexError:
                sampleId = ""
                errorMessage("Error Except in sampleId!")

        if "R|" in m:
            tmp = m.split("|")

            try:
                test_id = tmp[2]
                test_id =test_id.replace("^^^","")
            except IndexError:
                test_id = ""
                errorMessage("Error Except in test_id!")


            try:
                result = tmp[3]
            except IndexError:
                result = ""
                errorMessage("Error Except in result!")

            res = []
            if result != "" and test_id != "":
                res.append("1")
                res.append("ADAMS_A1C_P")
                res.append(result)
                res.append("")
                resultDataDic["result"]=res


    if sampleId != "" and resultDataDic!={}:
        sampleWiseResult["sampleId"]=sampleId
        sampleWiseResult["result"]=resultDataDic

        try:
            resultSendToServer(MACHINE_NAME,sampleWiseResult)
            successMessage("successfully sent to server")
        except:
            errorMessage("Connection Error! Unsuccessfull to sent server! ")

        warningMessage("Final Result:"+ str(sampleWiseResult))
        # print("Successfully sent to server!")
    else:
        errorMessage("Unsuccessful to sent serer!")

    infoMessage("_________ Waiting For New Result ______________")