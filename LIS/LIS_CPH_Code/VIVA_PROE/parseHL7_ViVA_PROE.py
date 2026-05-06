from API_CONNECTION.commonMessage import *
from API_CONNECTION.apiCURLFunction import *
MACHINE_NAME = "VIVA PROE"

def hl7MessageParse(message):
    sampleWiseResult = {}
    resultDataDic = {}

    sampleId = ""

    seriaL_no = 0
    splited_message = message.split('\\r')
    #print("Main_split: ", splited_message)

    have_id = splited_message[2]

    if "O|1|" in have_id:
        sampleId = have_id.split("|")
        sampleId = sampleId[2]


    #print("SampleID=>",sampleId)
    if sampleId != "":
        for m in splited_message:

            if "R|1|" in m:
                #print("Result=>",m)
                seriaL_no += 1

                splited_text = m.split('^')
                #print("splited_text", splited_text)
                result  = splited_text[4].split('|')
                result2 = ""
                if len(splited_text)>5:
                    #print("+here ", splited_text[5])
                    tmpo = splited_text[5].split('|')
                    result2 =tmpo[0]
                    unit = tmpo[1]
                else:
                    #print("-here ", splited_text[4])
                    unit = splited_text[4].split('|')
                    #print("Unit=>",unit)
                    unit = unit[2]
                #print("m4=>",m[4])
                #print("rrr=> ",result)
                result  = result[1]


                if result != 'REJECTED':
                    res = []
                    res.append(str(seriaL_no))
                    res.append(splited_text[3])
                    res.append(result)
                    res.append(unit)
                    resultDataDic[str(seriaL_no)] = res
                    print("result Append!")
                else:
                    print("Rejected!")

        sampleWiseResult["sampleId"] = sampleId
        sampleWiseResult["result"] = resultDataDic

        if sampleId != "" and resultDataDic !={}:
            print("Final Result: ",sampleWiseResult)

            try:
                resultSendToServer(MACHINE_NAME,sampleWiseResult)
                successMessage("Successfully Sent to server")
            except:
                print("Error while sending data to server!")
        else:
            print("Result Missing, Unsuccessfull to sent server! ")
    else:
        print("SampleId or Result Missing, Unsuccessful to sent server!")

'''
if __name__ == '__main__':
    # singleData = "521H|\\\\^&|||VIVA^2.5.3270.91||||2.2|DOEL||P|LIS2-A|20230726194202\\rQ|1|^23072610870||ALL||||||||O\\rL|1|F\\r3A7\\r\\n4"
    singleData = "521H|\\\\^&|||VIVA^2.5.3270.91||||2.2|DOEL||P|LIS2-A|20230726195314\\rP|1||||||00010101|M\\rO|1|23072610870|||R||||||||||Urine||||||||||F\\rR|1|^^^QT50^qTHCMED|< 10^NEGATIVE|ng/mL|50|^-||F||admin||20230726195314\\rL|1|F\\r388\\r\\n4"
    singleData = "521H|\\\\^&|||VIVA^2.5.3270.91||||2.2|DOEL||P|LIS2-A|20230726193609\\rP|1||||||00010101|M\\rO|1|23072610870|||R||||||||||Urine||||||||||I\\rR|1|^^^QALC^qEthyl Alcohol|< 10.0|mg/dL||||F||admin||20230726193609\\rL|1|F\\r392\\r\\n4"
    singleData = "521H|\\\\^&|||VIVA^2.5.3270.91||||2.2|DOEL||P|LIS2-A|20230726192119\\rP|1|||BP 8614168263|MD. ASHIF UL AHMED||19860101|M||||||20230725\\rO|1|ashif|||R||20230725000000||||||||Urine||||||||||F\\rR|1|^^^QAM3^qAmphetamines 300|< 100^NEGATIVE|ng/mL|300|^-||F||admin||20230725152118\\rL|1|F\\r32B\\r\\n22H|\\\\^&|||VIVA^2.5.3270.91||||2.2|DOEL||P|LIS2-A|20230726192119\\rP|1|||BP 8614168263|MD. ASHIF UL AHMED||19860101|M||||||20230725\\rO|1|ashif|||R||20230725000000||||||||Urine||||||||||F\\rR|1|^^^QALC^qEthyl Alcohol|< 10.0|mg/dL||||F||admin||20230725152025\\rL|1|F\\r3E6\\r\\n23H|\\\\^&|||VIVA^2.5.3270.91||||2.2|DOEL||P|LIS2-A|20230726192119\rP|1|||BP 8614168263|MD. ASHIF UL AHMED||19860101|M||||||20230725\\rO|1|ashif|||R||20230725000000||||||||Urine||||||||||F\\rR|1|^^^QBEN^q Benzodiaz|< 15^NEGATIVE|ng/mL|300|^-||F||admin||20230725152052\\rL|1|F\\r34A\\r\\n24H|\\\\^&|||VIVA^2.5.3270.91||||2.2|DOEL||P|LIS2-A|20230726192119\\rP|1|||BP 8614168263|MD. ASHIF UL AHMED||19860101|M||||||20230725\\rO|1|ashif|||R||20230725000000||||||||Urine||||||||||F\\rR|1|^^^QT50^qTHCMED|< 10^NEGATIVE|ng/mL|50|^-||F||admin||20230725152212\\rL|1|F\\r3E9\\r\\n25H|\\\\^&|||VIVA^2.5.3270.91||||2.2|DOEL||P|LIS2-A|20230726192119\\rP|1|||BP 8614168263|MD. ASHIF UL AHMED||19860101|M||||||20230725\\rO|1|ashif|||R||20230725000000||||||||Urine||||||||||F\\rR|1|^^^QOP3^qOpiates 300|< 16^NEGATIVE|ng/mL|300|^-||F||admin||20230725152146\\rL|1|F\\r310\\r\\n26H|\\\\^&|||VIVA^2.5.3270.91||||2.2|DOEL||P|LIS2-A|20230726192119\\rP|1|||BP 8614168263|MD. ASHIF UL AHMED||19860101|M||||||20230725\\rO|1|ashif|||R||20230725000000||||||||Urine||||||||||F\\rR|1|^^^Q6AM^q6Acetyl Morphine|< 2.1^NEGATIVE|ng/mL|10.0|^-||F||admin||20230725152147\\rL|1|F\\r3CC\\r\\n27H|\\\\^&|||VIVA^2.5.3270.91||||2.2|DOEL||P|LIS2-A|20230726192119\\rP|1|||BP 8614168263|MD. ASHIF UL AHMED||19860101|M||||||20230725\\rO|1|ashif|||R||20230725000000||||||||Urine||||||||||F\\rR|1|^^^QEX5^qEcstasy 500|< 75^NEGATIVE|ng/mL|500|^-||F||admin||20230725152307\\rL|1|F\\r321\\r\\n4"
    hl7MessageParse(singleData)
'''