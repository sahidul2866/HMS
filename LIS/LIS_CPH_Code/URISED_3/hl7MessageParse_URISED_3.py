from API_CONNECTION.commonMessage import *
from API_CONNECTION.apiCURLFunction import *
MACHINE_NAME = "URISED_3"

def hl7MessageParse(message):
    sampleId = ""
    ln  = len(message[0])
    ln2 = len(message[1])
    if message[0][3] == message[1][3]:
        #print("Same Id")
        sampleWiseResult = {}
        sampleId = message[0][3]
        result = {}

        #ekhane kaj baki ase
        data = message[1][16].split('^')

        res = []
        res.append("1")
        res.append("Specific Gravity")
        res.append(data[0])
        res.append("")
        result["1"] = res

        res = []
        res.append("2")
        res.append("Colour")
        res.append(data[4])
        res.append("")
        result["2"] = res

        res = []
        res.append("3")
        res.append("Appearance/Turbidity")
        res.append(data[2])
        res.append("")
        result["3"] = res


        data = message[1][20].split('^')
        #print("1nnn=> ", data)

        res = []
        res.append("4")
        res.append(data[0])




        if data[1] == "neg" or data[1] == "0.5" or data[1] == "1" :
            res.append("Absent")  # Result
            res.append("")  # Unit
        elif data[1] == "3" or data[1] == "6":
            res.append("Present")  # Result
            res.append("")  # Unit
        else:
            res.append("")  # Result
            res.append("")  # Unit

        res.append(data[1])
        res.append(data[2])
        result["4"] = res


        ind=4
        for i in range(25, ln+1, 5):
            if ln-1>i:
                # serial || test_id  || result || unit
                data = message[0][i].split('^')
                #print("mmm=> ", data)
                ind +=1

                res = []
                res.append(str(ind))
                res.append(data[0])  # ID

                dbl = float(data[3])

                #print("\n------------------dbl=>",dbl)
                if data[0]=="RBC":
                    if dbl >=0.00 and dbl <=0.80:
                        res.append("Nil")  # Result
                        res.append("")  # Unit
                    elif dbl >=0.81 and dbl <=0.99:
                        res.append("0-1")  # Result
                        res.append(data[4])  # Unit
                    elif dbl >= 1.00 and dbl <= 1.40:
                        res.append("0-2")  # Result
                        res.append(data[4])  # Unit
                    elif dbl >= 1.41 and dbl <= 2.00:
                        res.append("1-2")  # Result
                        res.append(data[4])  # Unit
                    elif dbl >= 2.01 and dbl <= 4.00 :
                        res.append("2-3")  # Result
                        res.append(data[4])  # Unit
                    elif dbl >= 4.01 and dbl <= 6.00:
                        res.append("2-4")  # Result
                        res.append(data[4])  # Unit
                    elif dbl >= 6.01 and dbl <= 8.00:
                        res.append("4-6")  # Result
                        res.append(data[4])  # Unit
                    elif dbl >= 8.01 and dbl <= 12.00:
                        res.append("6-8")  # Result
                        res.append(data[4])  # Unit
                    elif dbl >= 12.01 and dbl <= 15.00 :
                        res.append("8-10")  # Result
                        res.append(data[4])  # Unit
                    elif dbl >= 15.01 and dbl <= 18.00 :
                        res.append("10-12")  # Result
                        res.append(data[4])  # Unit
                    elif dbl >= 18.01 and dbl <=20.00 :
                        res.append("12-15")  # Result
                        res.append(data[4])  # Unit
                    elif dbl >= 20.01 and dbl <= 25.00:
                        res.append("15-20")  # Result
                        res.append(data[4])  # Unit
                    elif dbl >= 25.01 and dbl <= 30.00:
                        res.append("20-25")  # Result
                        res.append(data[4])  # Unit
                    elif dbl >= 30.01 and dbl <= 40.00:
                        res.append("25-30")  # Result
                        res.append(data[4])  # Unit
                    elif dbl >= 40.01 and dbl <= 50.00 :
                        res.append("30-35")  # Result
                        res.append(data[4])  # Unit
                    elif dbl >= 50.01 and dbl <= 70.00:
                        res.append("35-40")  # Result
                        res.append(data[4])  # Unit
                    elif dbl >= 70.01 and dbl <= 99.00:
                        res.append("40-50")  # Result
                        res.append(data[4])  # Unit
                    else:
                        res.append("Plenty")  # Result
                        res.append("") # unit


                elif data[0]=="WBC":
                    if dbl >=0.00 and dbl <=0.50:
                        res.append("0-1")  # Result
                        res.append(data[4])  # Unit
                    elif dbl >=0.51 and dbl <=0.99:
                        res.append("0-2")  # Result
                        res.append(data[4])  # Unit'
                    elif dbl >= 1.00 and dbl <= 2.00:
                        res.append("1-2")  # Result
                        res.append(data[4])  # Unit'
                    elif dbl >= 2.01 and dbl <= 4.00:
                        res.append("2-4")  # Result
                        res.append(data[4])  # Unit'
                    elif dbl >=4.01 and dbl <=6.00 :
                        res.append("4-6")  # Result
                        res.append(data[4])  # Unit

                    elif dbl >= 6.01 and dbl <=8.00 :
                        res.append("6-8")  # Result
                        res.append(data[4])  # Unit'
                    elif dbl >= 8.01 and dbl <=12.00 :
                        res.append("8-10")  # Result
                        res.append(data[4])  # Unit'
                    elif dbl >=12.01 and dbl <= 15.00:
                        res.append("10-12")  # Result
                        res.append(data[4])  # Unit'
                    elif dbl >=15.01 and dbl <=20.00:
                        res.append("12-15")  # Result
                        res.append(data[4])  # Unit'
                    elif dbl >=20.01 and dbl <=25.00:
                        res.append("15-20")  # Result
                        res.append(data[4])  # Unit'
                    elif dbl >=25.01 and dbl <= 30.00:
                        res.append("20-25")  # Result
                        res.append(data[4])  # Unit

                    elif dbl >=30.01 and dbl <=35.00:
                        res.append("25-30")  # Result
                        res.append(data[4])  # Unit'
                    elif dbl >=35.01 and dbl <= 40.00:
                        res.append("30-35")  # Result
                        res.append(data[4])  # Unit'
                    elif dbl >=40.01 and dbl <=50.00:
                        res.append("35-50")  # Result
                        res.append(data[4])  # Unit'
                    elif dbl >=50.01 and dbl <=60.00:
                        res.append("40-45")  # Result
                        res.append(data[4])  # Unit'
                    elif dbl >=60.01 and dbl <=90.00:
                        res.append("45-50")  # Result
                        res.append(data[4])  # Unit'
                    elif dbl > 90.01:
                        res.append("Plenty")  # Result
                        res.append("")  # Unit
                    else :
                        res.append("")  # Result
                        res.append("")  # Unit



                elif data[0] == "EPI":
                    if dbl >=0.00 and dbl <=0.10:
                        res.append("0-2")  # Result
                        res.append(data[4])  # Unit'
                    elif dbl >=0.11 and dbl <=0.20:
                        res.append("1-2")  # Result
                        res.append(data[4])  # Unit'
                    elif dbl >=0.21 and dbl <=0.40:
                        res.append("2-3")  # Result
                        res.append(data[4])  # Unit'
                    elif dbl >=0.41 and dbl <=0.60:
                        res.append("2-4")  # Result
                        res.append(data[4])  # Unit'
                    elif dbl >=0.61 and dbl <=0.99:
                        res.append("4-6")  # Result
                        res.append(data[4])  # Unit'
                    elif dbl >=1.00 and dbl <=2.00:
                        res.append("6-8")  # Result
                        res.append(data[4])  # Unit

                    elif dbl >=2.01 and dbl <=3.00:
                        res.append("8-10")  # Result
                        res.append(data[4])  # Unit'
                    elif dbl >=3.01 and dbl <=5.00:
                        res.append("10-12")  # Result
                        res.append(data[4])  # Unit'
                    elif dbl >=5.01 and dbl <=6.00:
                        res.append("12-15")  # Result
                        res.append(data[4])  # Unit'
                    elif dbl >=6.01 and dbl <=10.00:
                        res.append("15-18")  # Result
                        res.append(data[4])  # Unit'
                    elif dbl >=10.01 and dbl <=12.00:
                        res.append("18-22")  # Result
                        res.append(data[4])  # Unit'
                    elif dbl >=12.01 and dbl <=15.00:
                        res.append("20-25")  # Result
                        res.append(data[4])  # Unit'
                    elif dbl >=15.01 and dbl <=20.00:
                        res.append("25-30")  # Result
                        res.append(data[4])  # Unit'
                    else:
                        res.append("Plenty")  # Result
                        res.append("")  # Unit'

                else:
                    if data[1]=="-":
                        res.append("Nil")  # Result
                    else:
                        res.append(data[1])
                    res.append("")  # Unit

                result[str(ind)] = res



            result_flag = True
            if ln2-1>i:
                data = message[1][i].split('^')
                #print("nnn=> ", data)
                ind += 1

                res = []
                res.append(str(ind)) # Serial
                res.append(data[0])  # ID


                if data[0] == "GLU" :
                    if data[5] == "norm" or data[5] == "(+)":
                        res.append("Nil")  # Result
                        res.append("")  # Unit
                    elif data[5] == "+":
                        res.append("Trace")  # Result
                        res.append("")  # Unit
                    elif data[5] == "++":
                        res.append("+")  # Result
                        res.append("")  # Unit
                    elif data[5] == "+++":
                        res.append("++")  # Result
                        res.append("")  # Unit
                    elif data[5] == "++++":
                        res.append("+++")  # Result
                        res.append("")  # Unit
                    else :
                        res.append("")  # Result
                        res.append("")  # Unit

                elif data[0] == "PRO" :
                    if data[5] == "neg":
                        res.append("Nil")  # Result
                        res.append("")  # Unit
                    elif data[5] == "(+)":
                        res.append("Trace")  # Result
                        res.append("")  # Unit
                    elif data[5] == "+":
                        res.append("+")  # Result
                        res.append("")  # Unit
                    elif data[5] == "++":
                        res.append("++")  # Result
                        res.append("")  # Unit
                    elif data[5] == "+++":
                        res.append("+++")  # Result
                        res.append("")  # Unit
                    else :
                        res.append("")  # Result
                        res.append("")  # Unit


                elif data[0] == "KET" :
                    if data[5] == "neg" or data[5] == "(+)":
                        res.append("Nil")  # Result
                        res.append("")  # Unit
                    elif data[5] == "+":
                        res.append("Trace")  # Result
                        res.append("")  # Unit
                    elif data[5] == "++":
                        res.append("+")  # Result
                        res.append("")  # Unit
                    elif data[5] == "+++":
                        res.append("++")  # Result
                        res.append("")  # Unit
                    else :
                        res.append("")  # Result
                        res.append("")  # Unit


                elif data[0] == "ASC" :
                    if data[5] == "neg" :
                        res.append("Nil")  # Result
                        res.append("")  # Unit
                    else:
                        res.append(data[5])
                        res.append("")  # Unit


                elif data[0] == "NIT" :
                    if data[1] == "neg":
                        res.append("Negative")  # Result
                        res.append("")  # Unit
                    else:
                        res.append("Positive")
                        res.append("")  # Unit


                elif data[0] == "UBG" :
                    if data[1] == "norm":
                        res.append("Absent")  # Result
                        res.append("")  # Unit
                    else:
                        res.append("Present")
                        res.append("")  # Unit

                elif data[0] == "UBG":
                    if data[1] == "norm":
                        res.append("Absent")  # Result
                        res.append("")  # Unit
                    else:
                        res.append("Present")
                        res.append("")  # Unit

                elif data[0] == "PH":
                    res.append(data[1])  # Result
                    res.append("")  # Unit
                else:
                    result_flag = False
                    ind -= 1

                if result_flag == True:
                    result[str(ind)] = res

        sampleWiseResult["sampleId"]=sampleId
        sampleWiseResult["result"]=result
        print("Final Result:", sampleWiseResult)

        try:
            resultSendToServer(MACHINE_NAME,sampleWiseResult)
            successMessage("Successfully Sent to server")
        except:
            errorMessage("Error while sending data to server!")


        #print("Successfully sent to server")

    else:
        errorMessage("Mismatch of ID's , Unsuccessful to sent server")
    infoMessage ("__________ Waiting For the New Result ________")