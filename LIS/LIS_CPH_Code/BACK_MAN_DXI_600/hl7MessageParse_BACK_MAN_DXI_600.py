from BACK_MAN_DXI_600.testCodeDXL600 import *


def hl7MessageParse(message):
    sampleWiseResult = {}
    resultDataDic = {}

    sampleId = ""
    result = []

    ind = 0
    for m in message:
        # print(m)
        if "\\x023O|1|" in m:
            m = m.split("|")
            sampleId = m[2]
        elif "\\x024R" in m:
            m = m.split("|")
            # print("result=>",m)

            test_name = m[2].split('^')
            while ("" in test_name):
                test_name.remove("")
            test_name = test_name[0]
            # print("test_name =",test_name)

            try:
                test_name = getTestCodeForServer(test_name)
            except:
                errorMessage(test_name + " Not Found")

            ind += 1
            res = []
            res.append(str(ind))  # serial
            res.append(test_name)  # id
            res.append(m[3])  # result
            res.append(m[4])  # unit

            resultDataDic[str(ind)] = res

    # print("SampleId = ",sampleId)
    # print("result = ",resultDataDic)

    sampleWiseResult["sampleId"] = sampleId
    sampleWiseResult["result"] = resultDataDic

    print("Final_Result=>", sampleWiseResult)

    if "sampleId" in sampleWiseResult and resultDataDic != {}:
        resultSendToServer("DXI 600", sampleWiseResult)
        successMessage("+++++++++++++++++++++" + sampleId + ": Successfully Uploaded ++++++++++++++++++++++")
    else:
        errorMessage("SampleID Missing!")

    # print("hl7close")


"""
if __name__ == '__main__':
    m=[]
    data = "\\x021H|\\\\^&|||ACCESS^901894|||||LIS||P|1|20230723154057\\r\\x0336\\r\\n"
    m.append(data)
    data = "\\x022P|1|\\r\\x03BB\\r\\n"
    m.append(data)
    data = "\\x023O|1|I485846|^6^1|^^^TSH3^1|||||||||||Serum||||||||||F\\r\\x03AB\\r\\n"
    m.append(data)
    data = "\\x024R|1|^^^TSH3^1|17.51|uIU/mL||N||F||||20230719100857|901894\\r\\x0375\\r\\n"
    m.append(data)
    data = "\\x025L|1|F\\r\\x0300\\r\\n"
    m.append(data)
    hl7MessageParse(m)
"""
