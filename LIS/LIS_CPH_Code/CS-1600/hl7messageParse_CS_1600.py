__author__ = "Plabon Dibra"
###################################### final #######################################

from API_CONNECTION.apiCURLFunction import *
from API_CONNECTION.commonMessage import *
def hl7MessageParse(message):
    print("----------------------------------------------- S T A R T -------------------------------------------------")
    print("Test:",message)
    splitted_message = message.split(" ")
    splitted_message = list(filter(None,splitted_message))
    #print("after:", splitted_message)
    try:
        if splitted_message[2]=="-":
            print("result Missing")
        else:
            try:
                sampleId = splitted_message[1]          # Barcode ID/ sampleId
                sampleId = sampleId[:-1]
            except IndexError:
                print("Index Error in splitted_message[1] !")
                sampleId = ""

            if len(sampleId)>3:
                #print("sampleId:",sampleId)

                '''
                #################################### MAPPING #####################################
                # PT = Patient                  => 041
                # control1 = 13.3
                # INR = Machine Show            => 044
                # ISI = Looks Reagent Sheet
                # Index = (control1 / PT) * 100
                # Ratio = PT / control1         => 043
                #---------------------------------------------------------------------------------
                # APTT =                        => 051
                # control1 = 30.0
                ##################################################################################
                '''

                for i in range(58, len(message)-3,9):
                    target = ""    # 3 digits code of test_id
                    try:
                        target +=message[i]
                        target += message[i+1]
                        target += message[i+2]
                    except IndexError:
                        target =""
                        print("Index Error! message[i]")

                    #print("target:",target)
                    if len(target)>2:
                        test_id = ""
                        result = ""
                        unit = ""
                        #print("here Target: ",target)


                        # Hunting PT and APPT
                        if (target[0] == '0' and target[2] == '1' and target[1] == '4') or (target[0] == '0' and target[2] == '1' and target[1] == '5') :      # patient=4 (pt)   ; APTT=5
                            #print("entered")
                            try:
                                val = ""            # result value
                                val = message[i+5]
                                val = val + message[i+6]
                                val = val + "."
                                val = val + message[i+7]

                                #print("value: ",val)

                                try:
                                    result = float(val)
                                    result = str(result)
                                except ValueError:
                                    print("ValueError! 041 or 051")
                                    if message[i+5]=='*':
                                        result="**.*"
                                    else:
                                        result = ""
                            except IndexError:
                                result = ""
                                print("IndexError! message[i+5] for 041 or 051")
                            #print("result:",result)


                            if result != "":
                                if target[1] == '5':
                                    resultDataDic = {}
                                    sampleWiseResult = {}

                                    res = []
                                    res.append("1")
                                    res.append("PTT CK")            # APTT
                                    res.append(result)
                                    res.append("Sec")
                                    resultDataDic["1"] = res

                                    res = []
                                    res.append("2")
                                    res.append("Control-2")         # APTT Control
                                    res.append("30.0")
                                    res.append("sec")

                                    resultDataDic["2"] = res

                                    sampleWiseResult["sampleId"]=sampleId
                                    sampleWiseResult["result"]=resultDataDic
                                    print("Final Result:", sampleWiseResult)
                                    try:
                                        #resultSendToServer(sampleWiseResult)
                                        successMessage("Successfully Sent to server")
                                    except:
                                        errorMessage("Error while sending data to server!")
                                else:
                                    resultDataDic = {}
                                    sampleWiseResult = {}

                                    res = []
                                    res.append("1")
                                    res.append("PT REC-4")      # PT (Patient)
                                    res.append(result)
                                    res.append("Sec")
                                    resultDataDic["1"] = res

                                    res = []
                                    res.append("2")
                                    res.append("Control-1")     # PT control
                                    res.append("13.3")
                                    res.append("sec")
                                    resultDataDic["2"] = res


                                    ##################### Calculation for Index #########################
                                    try:
                                        Index =  (13.3) / float(result) * 100
                                        Index = round(Index+0.5)
                                        #print("Index: ",Index)
                                    except ValueError:
                                        #print("ValueError! Index...")
                                        Index = "***"
                                    #####################################################################

                                    res = []
                                    res.append("3")
                                    res.append("PT REC-1")      # Index
                                    res.append(str(Index))
                                    res.append("%")
                                    resultDataDic["3"] = res

                                    sampleWiseResult["sampleId"] = sampleId
                                    sampleWiseResult["result"] = resultDataDic
                                    print("Final Result:",sampleWiseResult)
                                    try:
                                        # resultSendToServer(sampleWiseResult)
                                        successMessage("Successfully Sent to server")
                                    except:
                                        errorMessage("Error while sending data to server!")
                            else:
                                print("Result Missing! 041 or 051")
                            result = ""
                        # Hunting PT and APPT --close



                        # Hunting INR and RATIO
                        elif (target[0] == '0' and target[1] == '4' and target[2] == '3') or (target[0] == '0' and target[1] == '4' and target[2] == '4'):    # ratio
                            #print("entered2")
                            try:
                                val = ""
                                val = message[i + 5]
                                val = val + "."
                                val = val + message[i + 6]
                                val = val + message[i + 7]

                                #print("value: ", val)

                                try:
                                    result = float(val)
                                    result = str(result)
                                except ValueError:
                                    print("ValueError! 043 or 044")
                                    if message[i+5]=='*':
                                        result="*.**"
                                    else:
                                        result = ""

                            except IndexError:
                                result = ""
                                print("IndexError! message[i + 5] for 043 or 044")
                            #print("result:", result)

                            if result != "":
                                if target[2] == '3':        # Ratio
                                    resultDataDic = {}
                                    sampleWiseResult = {}

                                    res = []
                                    res.append("1")
                                    res.append("PT REC-3")            # ratio
                                    res.append(result)
                                    res.append("Ratio")
                                    resultDataDic["1"] = res


                                    sampleWiseResult["sampleId"]=sampleId
                                    sampleWiseResult["result"]=resultDataDic
                                    print("Final Result:", sampleWiseResult)
                                    try:
                                        #resultSendToServer(sampleWiseResult)
                                        successMessage("Successfully Sent to server")
                                    except:
                                        errorMessage("Error while sending data to server!")

                                else:                       #INR
                                    resultDataDic = {}
                                    sampleWiseResult = {}

                                    res = []
                                    res.append("1")
                                    res.append("PT REC-2")      # INR
                                    res.append(result)
                                    res.append("INR")
                                    resultDataDic["1"] = res

                                    sampleWiseResult["sampleId"] = sampleId
                                    sampleWiseResult["result"] = resultDataDic
                                    print("Final Result:", sampleWiseResult)
                                    try:
                                        # resultSendToServer(sampleWiseResult)
                                        successMessage("Successfully Sent to server")
                                    except:
                                        errorMessage("Error while sending data to server!")

                            result = ""
                        # Hunting INR and RATIO --close


                    target = ""
            else:
                print("SampleId Missing!")

    except IndexError:
        print("Index Error! there is no data")
    print("++++++++++++++++++++++++++++++++++++++++++++++++ E N D ++++++++++++++++++++++++++++++++++++++++++++++++++++\n")



if __name__ == '__main__':
    message = "D1210101U210723151900000101  2023072110007B               041  145 043  109 044  110 051  231 "     # test PT and APPT
    #message = "D1210101U210723151900000101  2023072110007B               041******043******044******051******"     # test errors for PT and APPT
    #message = "DS210101U200723123400000105       CO488185B                  -                                                                                       "
    #message = "D1210101U120723154500000101       CO482587B               041  128 043  096 044  096 "              # test only PT
    #message = "D1210101U120723154500000101       CO482587B               041******043  096 044  096 "  # test only PT
    message = "D1210101U120723154500000101       CO482587B               041******043******044******"              # test for errors
    #message = "D1210101U120723155600000101       CO482567B               051  271 "                                # test only APPT
    #message = "D1210101U120723155600000101       CO482567B               051******"                                # test for error
    #message = "D1210101U120723155600000101                               051  271"                                 # test sample missing
    #message = "D1210101U130723145800000206       CO483284B               041  129 043  097 044  097 051******"     # test for error
    hl7MessageParse(message)
