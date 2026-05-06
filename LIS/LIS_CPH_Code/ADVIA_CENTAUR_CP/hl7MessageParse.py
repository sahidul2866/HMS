from API_CONNECTION.apiCURLFunction import *
from ADVIA_CENTAUR_CP.test_code_cp import *

MACHINE_NAME = "ADVIA_CENTAURE_CP"

def hl7MessageParse(message):
    sampleId = ""  # sample ID
    # print("Full Message: ", message)
    indx = 0
    for r in message:
        indx += 1
        #print("indx:",indx)
        sampleIdList = r.split('|')
        # print("Splited Data ",sampleIdList[0][-1])
        sampleIdList[0] = sampleIdList[0][-1]
        try:
            #print("try")
            if (sampleIdList[0] == "O"):  # ID Hunting
                sampleId = sampleIdList[2]
                print("sampleId: ",sampleId)

                try:
                    result_container = message[indx].split('|')

                    if (result_container[0][-1] == "R" ):     # Result Hunting
                        try:
                            test_id = result_container[2].split('^')
                            #print("TestId: ", test_id)
                            test_id = test_id[3]
                        except IndexError:
                            test_id = ""
                            print("Error! test_id except")

                        try:
                            result = result_container[3]
                        except IndexError:
                            result = ""
                            print("Error! result except!")

                        try:
                            unit = result_container[4]
                            unit = unit.replace("\\xb5","")
                        except IndexError:
                            unit = ""
                            print("Error! unit except!")

                        resultDataDic = {}
                        if result != "":


                            try:
                                test_id  = getTestCode(test_id)
                            except:
                                test_id = ""
                                print("No Test Id Found!")


                            if test_id !="":
                                singlResult = []
                                singlResult.append("1")
                                singlResult.append(test_id)
                                singlResult.append(result)
                                singlResult.append(unit)
                                resultDataDic['1'] = singlResult

                        sampleWiseResult ={}
                        sampleWiseResult["sampleId"] = sampleId
                        sampleWiseResult["result"] = resultDataDic

                        print("Final Result: ", sampleWiseResult)
                        if sampleId != "" and resultDataDic != {}:
                            resultSendToServer(MACHINE_NAME,sampleWiseResult)
                            print("Successfully sent to server")
                        else:
                            errorMessage("Unsuccessful to sent server")


                except IndexError:
                    errorMessage("Error! result_container except!")
        except IndexError:
            errorMessage("Error! sampleId except")





'''
if __name__ == '__main__':
    mess = []

    data = "5"
    mess.append(data)
    data = "21H|\\\\^&|||ACCP1|||||Host||P|1|20230731192556\\r3EA\\r\\n"
    mess.append(data)
    data = "22P|1||||^^||||||||||||||||||||\\r39B\\r\\n"
    mess.append(data)
    data = "23O|1|I464431||^^^TSH^^|R||||||||||||||||||||F\\r3BB\\r\\n"
    mess.append(data)
    data = "24R|1|^^^TSH^^^^DOSE|2.80|\\xb5IU/ml||||F\\\\R||||20230612141611\\r318\\r\\n"
    mess.append(data)
    data = "25R|2|^^^TSH^^^^RLU|178985|||||F\\\\R||||20230612141611\\r305\\r\\n"
    mess.append(data)
    data = "26P|2||||^^||||||||||||||||||||\\r3A0\\r\\n"
    mess.append(data)
    data = "27O|1|I464419||^^^TSH^^|R||||||||||||||||||||F\\r3C5\\r\\n"
    mess.append(data)
    data = "R|1|^^^TSH^^^^DOSE|8.12|\\xb5IU/ml||||F\\\\R||||20230612141851\\r31B\\r\\n"
    mess.append(data)
    data = "21R|2|^^^TSH^^^^RLU|490625|||||F\\\\R||||20230612141851\\r3FB\\r\\n"
    mess.append(data)
    data = "22L|1|N\\r305\\r\\n"
    mess.append(data)
    data = "4"
    mess.append(data)

    hl7MessageParse(mess)
'''