from API_CONNECTION.commonMessage import *
from API_CONNECTION.apiCURLFunction import *
from testCodeParse import *
MACHINE_NAME = "GETEIN_1600"

def hl7MessageParse(rawMessage):
    mm = rawMessage.split("\\x02")
    print("here",mm)
    idx = 0
    for message in mm:
        if len(message)>10:
            print("Messae:",message)
            sampleWiseResult = {}
            resultDataDic = {}

            res = ""
            unit = ""
            sampleId =""
            test_id =""

           # print("Raw Message: ",message)

            sp_m = message.split("|")
            print(sp_m)

            try:
                sampleId =  sp_m[1]
               # print("sample_id: ",sampleId)
            except IndexError:
                print("Sample_ID missing!")


            try:
                test_id =  sp_m[5]
                #print("test_id: ",test_id)
            except IndexError:
                test_id = ""
                print("test_id missing!")

            try:
                res = sp_m[7]
            except :
                print("result missing!",res)


            try:
                res = res.split("^")
                if test_id =="hs-CRP^CRP":
                    print("++++++++++++++++++ res ++++++++++++++++++++++++")
                    res = res[1]
                else:
                    print("------------------ res ------------------------")
                    res = res[0]
            except IndexError:
                print("Error! ResultIndex")


            try:
                res = float(res)
                if res < 0.05:
                    res = "<0.05"
                # print("result: ", res)
            except ValueError:
                print("Error! Value Error Detected!")


            try:
                unit = sp_m[6]
                #print("unit: ", unit)
            except IndexError:
                print("unit missing!")

            unit = unit.split("^")
            try:
                if test_id =="hs-CRP^CRP":
                    print("++++++++++++++++++ Unit ++++++++++++++++++++++++")
                    unit = unit[1]
                else:
                    print("------------------ Unit ------------------------")
                    unit = unit[0]
            except IndexError:
                print("Error! Unit Index Error!")




            try:
                test_id = getServerTestCode(test_id)   ### hs-CRP bug +++++++++++++++++++++++++++++++++++++++++++++++++
            except:
                test_id = ""
                print("Error! except, text_id missing")

            if test_id != "":
                idx += 1

                result = []
                result.append(str(idx)) # +++++
                result.append(test_id)
                result.append(str(res))
                result.append(unit)

                resultDataDic["1"]=result

                sampleWiseResult["sampleId"] = sampleId
                sampleWiseResult["result"] = resultDataDic

                print("Final Result: ", sampleWiseResult)

                if sampleId != "" and res != "" and test_id!="":
                    try:
                        resultSendToServer(MACHINE_NAME,sampleWiseResult)
                        print("successfully sent to server")
                    except:
                        print("Connection Error!")
                else:
                    print("Result Missing, Unsuccessfull to sent server! ")

'''
if __name__ == '__main__':

    mess = "\\x02\\x01O\\x00\\x81|I1003567|29107|5|7|PCT|ng/mL|50.55|0.05|50.00|0.50|1|0|2023-08-01 11:10:06|0|9|"
    hl7MessageParse(mess)
    mess = "\\x01j\\x00\\xe1|B1008293|29128|7|3|hs-CRP^CRP|mg/L^mg/L|12.6^12.6|0.5^5.0|5.0^200.0|3.0^10.0|1|0|2023-08-02 20:06:27|0|1|"
    hl7MessageParse(mess)
'''