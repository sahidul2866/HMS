from API_CONNECTION.commonMessage import *
from API_CONNECTION.apiCURLFunction import *
from LIASION_XL.test_code_Liasion import *

MACHINE_NAME = "LIASION_XL"


def hl7MessageParse(message):
    ind = 0
    for m in message:
        sampleId = ""  # sample ID
        ind += 1
        if "O|1|" in m:
            tmp = m.split("|")
            try:
                sampleId = tmp[2]
            except IndexError:
                sampleId = ""
                print("! IndexError in sampleId!")

            infoMessage("sampleId: " + sampleId)
            if sampleId != "":
                sampleWiseResult = {}
                resultDataDic = {}

                testId = ""
                result = ""
                unit = ""
                tmp = []

                try:
                    tmp = message[ind].split("|")
                except IndexError:
                    tmp = []
                    errorMessage("! >IndexError< !")

                try:
                    testId = tmp[2].replace("^^^", "")
                    testId = testId.replace("^^DOSE","")
                    print("testId:", testId)
                except IndexError:
                    testId = ""
                    errorMessage("! IndexError! Result Missing!")

                if testId != "":
                    try:
                        result = tmp[3]
                    except IndexError:
                        result = ""
                        print("! >Result Missing< !")

                    try:
                        unit = tmp[4]
                    except IndexError:
                        unit = ""
                        print("! >Unit Missing< !")

                    if result != "":

                        try:
                            testId = getTestCode(testId)
                            if testId == "":
                                print("! >TestCode Not Found< !")
                        except:
                            testId = ""
                            print("! >TestCode Not Found< !")

                        if testId != "":
                            res = []
                            res.append("1")
                            res.append(testId)
                            res.append(result)
                            res.append(unit)

                            resultDataDic["1"] = res

                            sampleWiseResult = {}
                            sampleWiseResult["sampleId"] = sampleId
                            sampleWiseResult["result"] = resultDataDic

                            print("Final:", sampleWiseResult)
                            try:
                                resultSendToServer(MACHINE_NAME, sampleWiseResult)
                                print("Successfully sent to server")
                            except:
                                print("! >Connection Problem! Unsuccessful to sent server< !")
                else:
                    print("! >testId missing< !")

            else:
                print("! >sampleId missing< !")


"""
if __name__ == '__main__':
    mess = []
    data = "23O|1|I472177||^^^TSH^|R||||||||||||||||||||F\\r363\\r\\n"
    mess.append(data)
    data = "24R|1|^^^TSH^^DOSE|0.3193|mIU/L||N||F\\\\R||||20230624174008\\r344\\r\\n"
    mess.append(data)
    data = "27O|1|I472182||^^^TSH^|R||||||||||||||||||||F\\r363\\r\\n"
    mess.append(data)
    data = "20R|1|^^^TSH^^DOSE|9.265|mIU/L||H||F\\\\R||||20230624144921\\r311\\r\\n"
    mess.append(data)
    data = "24O|1|I472205||^^^TSH^|R||||||||||||||||||||F\\r35C\\r\\n"
    mess.append(data)
    data = "25R|1|^^^TSH^^DOSE|0.03701|mIU/L||L||F\\\\R||||20230624145003\\r367\\r\\n"
    mess.append(data)
    data = "21O|1|I472238||^^^TSH^|R||||||||||||||||||||F\\r35F\\r\\n"
    mess.append(data)

    hl7MessageParse(mess)
"""
