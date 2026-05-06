from testCode import *
from API_CONNECTION.commonMessage import *
from API_CONNECTION.apiCURLFunction import *

MACHINE_NAME = "INDIKO PLUS"
def hl7MessageParse(message):
    sampleId = ""  # sample ID



    print("hi")

    ind = 0
    for r in message:
        ind +=1
        if "O|" in r:  # ID Hunting
            sampleIdList = r.split('|')
            try:
                sampleId = sampleIdList[2]
                print("sampleId = > ", sampleId)
                sampleId = sampleId.split("^")
                sampleId = sampleId[0]
            except IndexError:
                sampleId =""

            if sampleId != "":

                try:
                    # ^^^ETOH1^0.0
                    if "R|" in message[ind]:
                        tmp = message[ind].split('|')
                        try:
                            testId = tmp[2]
                            testId = testId.split("^")
                            testId = testId[3]
                            testId = get_test_code(testId)
                            print("testId=>",testId)
                        except IndexError:
                            print("IndexError in message[ind]")
                            testId = ""

                        if testId !="":
                            try:
                                result = tmp[3]
                                unit = tmp[4]
                                print("Result=> ",testId,result,unit)

                                try:
                                    result = float(result)
                                except ValueError:
                                    print("Result Missing!")
                                    result =""


                                if testId !="" and result !="":

                                    if testId == "QALC":
                                        if result<10.0:
                                            result = "<10.0"
                                        else:
                                            result = str(result)

                                    if testId == "QBEN":
                                        if result < 15.0:
                                            result = "<15.0"
                                        else:
                                            result = str(result)

                                    if testId == "QT50":
                                        if result < 10.0:
                                            result = "<10.0"
                                        else:
                                            result = str(result)

                                    if testId == "QOP3":
                                        if result < 16.0:
                                            result = "<16.0"
                                        else:
                                            result = str(result)

                                    if testId == "Q6AM":
                                        if result < 2.1:
                                            result = "<2.1"
                                        else:
                                            result = str(result)


                                    if testId == "QEX5":
                                        if result < 75.0:
                                            result = "<75.0"
                                        else:
                                            result = str(result)

                                    if testId == "QAM3":
                                        if result < 100:
                                            result = "<100.0"
                                        else:
                                            result = str(result)

                                    res = []
                                    res.append("1")
                                    res.append(testId)
                                    res.append(result)
                                    res.append(unit)

                                    resultDataDic = {}
                                    sampleWiseResult = {}

                                    resultDataDic["1"]=res

                                    sampleWiseResult["sampleId"]=sampleId
                                    sampleWiseResult["result"] = resultDataDic

                                    print("Final Result:",sampleWiseResult)

                                    try:
                                        resultSendToServer(MACHINE_NAME,sampleWiseResult)
                                        successMessage("Successfully Sent to server")
                                    except:
                                        print("Error while sending data to server!")

                            except IndexError:
                                print("IndexError in tmp!")

                except IndexError:
                    testId = ""

    print("bye")

'''
if __name__ == '__main__':
    mess = []

    data = "\\x023O|1|DU468001||^^^ETOH1^0.0|R||||||X||||3|||||||||1|F\\r\\x0366\\r"
    mess.append(data)
    data = "\\x024R|1|^^^ETOH1^0.0|0|mg/dl||N||F\\\\R||Indiko||20230618130405|Analyzer 1\\r\\x0377\\r"
    mess.append(data)
    data = "\\x026O|2|DU468001||^^^BENZ^0.0|R||||||X||||3|||||||||1|F\\r\\x0338\\r"
    mess.append(data)
    data = "\\x027R|1|^^^BENZ^0.0|2|ng/ml||N||F\\\\R||Automatic||20230618130500|Analyzer 1\\r\\x0399\\r"
    mess.append(data)
    data = "\\x020O|3|DU468001||^^^CANNAB^0.0|R||||||X||||3|||||||||1|F\\r\\x03A7\\r"
    mess.append(data)

    hl7MessageParse(mess)
'''