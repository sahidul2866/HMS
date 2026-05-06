"""
# s = "client_user_username_type_1234567"
# print(s.split('_')[-2:-1])
import requests as requests
from colorama import Fore
from datetime import datetime

# now = datetime.now()
# # print("now =", now)
# # dd/mm/YY H:M:S
# currentDateTimeStr = now.strftime("%d-%m-%Y %H:%M:%S")
# print(currentDateTimeStr)
#
# print(Fore.GREEN + currentDateTimeStr+" [SUCCESS] : Success Message")
# print(Fore.RED + currentDateTimeStr+" [ERROR]   : Error Message")
# print(Fore.YELLOW + currentDateTimeStr+" [WARNING] : Warning Message")
# print(Fore.CYAN + currentDateTimeStr+" [INFO]    : Info Message")


<<<<<<< HEAD
"""
"""
sampleRequestMessage = "\\x023O|1|23072410646|^6^1|^^^TSH3^1|||||||||||Serum||||||||||F\\r\\x0352\\r\\n"
print(sampleRequestMessage)

mainMessage = "\x0bMSH|^~\\&|YHLO|VP30003995|||20230721205025||ORU^R01|1|P|2.3.1||||0||ASCII|||\rPID|1|||||||U|||||||||||||||||||||||\rOBR|1||H488577|YHLO^VP30003995|N||||30.250000|16||||||||||||||||||||||||||||||||||||||\rOBX|1|BOTH|1|ESR|8|mm/h|2.000000-20.000000|N|27.9375\\S\\0.25|4|F|||20230720185135||||\rOBX|2|BOTH|2|KATZ|12|mm/h|||27.9375\\S\\0.25||F|||20230720185135||||\r\x1c\r"

if "\x0b" in mainMessage:
    dataSigment = mainMessage.split("\r")
    print(dataSigment)


    sampleWiseResult = {}
    resultDataDic = {}

    sampleIDSegment = dataSigment[2]
    sampleIDSegmentList = sampleIDSegment.split('|')
    sampleId = ""

    if sampleIDSegmentList[0] == "OBR":
        sampleId = sampleIDSegmentList[3]
        sampleWiseResult["sampleId"] = sampleId
        singleResultItem=[]

    esrResultSegment = dataSigment[3]
    esrResultSegmentList = esrResultSegment.split('|')
    if esrResultSegmentList[0] == "OBX":
        resultId = esrResultSegmentList[1]
        resultName = esrResultSegmentList[4]
        resultValue = esrResultSegmentList[5]
        resultUnit = esrResultSegmentList[6]

        singleResultItem.append(resultId)
        singleResultItem.append(resultName)
        singleResultItem.append(resultValue)
        singleResultItem.append(resultUnit)
        resultDataDic[resultId] = singleResultItem

    sampleWiseResult["result"] = resultDataDic
    print(sampleWiseResult)
    # infoMessage(sampleWiseResult)
    # resultSendToServer(sampleWiseResult)
    """
trayAndRack[0]="123456"
trayAndRack[1]="1234"
sampleId="12345678"
testCode="E061"
orderMessage = "\x02S " + str(trayAndRack[0]) + " " + str(trayAndRack[1]) + "    " + sampleId + "    E" + testCode + "\x03"
print(orderMessage)
