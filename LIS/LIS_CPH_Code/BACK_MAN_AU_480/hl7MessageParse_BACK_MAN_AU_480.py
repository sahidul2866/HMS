from BACK_MAN_AU_480.testCodeName import *
def hl7MessageParse(message):
    sampleWiseResult = {}
    resultDataDic = {}
    while ("" in message):
        message.remove("")
    print("hl7_After:",message)

    sampleId = message[3]

    mapping = {}
    for i in range(1, 121):
        mp = str(i)
        if len(mp) == 1:
            mp = "00" + mp
        elif len(mp) == 2:
            mp = "0" + mp
        # print(mp)
        mapping[mp] = True

    ind = 0

    test_ok = False
    test_name = ""

    for i in range(4,len(message)-1,1):
        tmp = message[i].replace("E","")

        if test_ok == True:
            tmp = tmp.replace("r", "")

            ind += 1
            result = []
            result.append(str(ind))
            test_name = getNameByTestCode(test_name)
            result.append(test_name)
            result.append(tmp)
            result.append("")
            resultDataDic[str(ind)] = result

            test_ok = False
        elif tmp in mapping:
            test_ok = True
            test_name = tmp

    sampleWiseResult["sampleId"]=sampleId
    sampleWiseResult["result"]=resultDataDic

    print(sampleWiseResult)
    if "sampleId" in sampleWiseResult and resultDataDic != {}:
        resultSendToServer('BackMan 480',sampleWiseResult)
        successMessage("+++++++++++++++++++++successfull++++++++++++++++++++++")
    else:
        errorMessage("SampleID or Result Missing!")


# if __name__ == '__main__':
#     #data = "\\x02D 001102 0009    B5488820    E017  23.5r 020  9.12r 023   118r 080    25r 097   139r 098   4.1r 099   104r \\x03"
#     #data = "\\x02D 001102 0009    B5488820    E017  23.5r 667 020  9.12r 023   118r 080    25r 097   139r 098   4.1r 099   104r \\x03"  ## error
#
#     data = str("\\x02D 000101 E005 23072410646    E002  4.15  003  73.4  009    43  011144.58  013    14  017  18.3  020  9.31  023   164  030  0.68  042    50  047 77.08  050   104  051 18.74  053  2.09  061 20.44  066  0.47  069  4.05  071    58  072248.29  073 22.84  074  3.45  080    20  097   142  098   4.0  099   108  104  0.77  \\x03")
#     hl7MessageParse(data)
#     # hl7MessageParse(data.split(" "))

