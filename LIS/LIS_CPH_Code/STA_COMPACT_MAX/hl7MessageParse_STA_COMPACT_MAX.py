from API_CONNECTION.commonMessage import *
from API_CONNECTION.apiCURLFunction import *
MACHINE_NAME = "STAGO COMPACT MAX"
def hl7MessageParse(message):
    msg = message.split("\\n")

    sampleId = ""  # sample ID

    sampleWiseResult = {}
    resultDataDic = {}
    ser_no = 0

    flag = False
    flag2 = False
    for m in msg:
        print(m)
        if "23O|1|" in m:
            sampleId = m.split("|")
            try:
                sampleId = sampleId[2]
            except:
                print("Error except! in sampleId!")
                sampleId =""

        if "R|" in m:
            tmp = m.split("|")

            try:
                test_id = tmp[2]
                test_id = test_id.replace("^^^","")
            except IndexError:
                print("IndexError! in result")
                test_id = ""


            try:
                result = tmp[3]
            except IndexError:
                print("IndexError! in result")
                result = ""

            try:
                unit = tmp[4]
            except IndexError:
                print("IndexError! in unit")
                unit = ""

            if test_id != "" and result != "":


                if test_id == "1" or test_id == "2" or test_id == "3" or test_id == "4":
                    test_id = "PT REC-"+test_id
                    flag = True
                elif test_id == "5":
                    test_id = "PTT CK"
                    flag2 = True
                elif test_id == "7":
                    test_id = "FIBLIQMG"
                elif test_id == "8":
                    test_id = "D-Dimer"
                else:
                    test_id = ""

                if test_id != "":
                    ser_no += 1
                    res = []
                    res.append(str(ser_no))
                    res.append(test_id)
                    res.append(result)
                    res.append(unit)
                    resultDataDic[str(ser_no)]=res



    if sampleId !="" and resultDataDic !={}:
        if flag:
            ser_no += 1
            res = []
            res.append(str(ser_no))
            res.append("Control-1")
            res.append("13.3")
            res.append("sec")
            resultDataDic[str(ser_no)] = res
        if flag2:
            ser_no += 1
            res = []
            res.append(str(ser_no))
            res.append("Control-2")
            res.append("30.0")
            res.append("sec")
            resultDataDic[str(ser_no)] = res

        sampleWiseResult["sampleId"] = sampleId
        sampleWiseResult["result"] = resultDataDic
        print("Final Result: ",sampleWiseResult)
        try:
            resultSendToServer(MACHINE_NAME,sampleWiseResult)
            print("Successfully sent to server")
        except:
            print("Error while sending...")
    else:
        print("Unsuccessful to sent server")

'''
if __name__ == '__main__':
    data = "521H|\\\\^&|||99^2.00|||||||P|1.00|20230804152048\\r31B\\r\\n22P|1|||^^^\\r3CD\\r\\n23O|1|C1010553|||R\\r323\\r\\n24R|1|^^^5|33.7|sec||||F||||\\r332\\r\\n25M|1|A|C\\r3BB\\r\\n26R|2|^^^1|86|%||||F||||\\r3BE\\r\\n27M|2|A|@\\r3BB\\r\\n20R|3|^^^2|1.08|INR||||F||||\\r3D7\\r\\n21M|3|A|@\\r3B6\\r\\n22R|4|^^^3|1.08|Ratio||||F||||\\r3F1\\r\\n23M|4|A|@\\r3B9\\r\\n24R|5|^^^4|14.9|sec||||F||||\\r336\\r\\n25M|5|A|@\\r3BC\\r\\n26R|6|^^^7|171|mg/dl||||F||||\\r3A1\\r\\n27M|6|A|@\\r3BF\\r\\n20L|1|N\\r303\\r\\n4"
    hl7MessageParse(data)
'''