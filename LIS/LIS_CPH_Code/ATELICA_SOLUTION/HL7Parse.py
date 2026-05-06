from API_CONNECTION.commonMessage import *
from API_CONNECTION.apiCURLFunction import *
def hl7MessageParse(message):
    try:
        sampleWiseResult = {}
        resultDataDic = {}

        sigmentMessage = message.split("\\r")
        ind = 0
        for m in sigmentMessage:
            if "OBX|" in m:
                ind +=1
                #print(m)
                sp = m.split("|")
                #print(sp)

                test_name = sp[3].split('^')
                test_name = test_name[0]
                res = sp[5]
                unit = sp[6].split('^')
                unit = unit[0]

                result = []
                result.append(str(ind))
                result.append(test_name)
                result.append(res)
                result.append(unit)

                resultDataDic[str(ind)] = result
            if "SAC|||" in m:
                sampleId = m.replace("SAC|||", "")

        # sampleId = sigmentMessage[2].replace("SAC|||","")
        #print("sampleId=>",sampleId)
        # sampleId=23072910140
        sampleWiseResult["sampleId"]=sampleId
        sampleWiseResult["result"]=resultDataDic
        print(sampleWiseResult)
        # resultSendToServer(sampleWiseResult)

        if "sampleId" in sampleWiseResult:
            resultSendToServer('Atellica Solution',sampleWiseResult)
            successMessage("+++++++++++++++++++++successfull++++++++++++++++++++++")
        else:
            errorMessage("SampleID Missing!")
    except Exception as error:
        print(error)

"""
if __name__ == '__main__':

    data = str(b'\x0bMSH|^~\\&|UIW_LIS|AA|LIS_ID|BB|20230625183706+0600||OUL^R22^OUL_R22|8d2e38b2448b485185aebcd99da876f6|P|2.5.1|||NE|AL||UNICODE UTF-8|||LAB-29^IHE~LAW_REFLEX^IHE~LAW_SPECIMEN^IHE~LAW_RERUN^IHE~LAW_CONTAINER^IHE~LAW_DILUTIONS^IHE~LAW_PAT_DEM^IHE\rSPM|1|I473261^""|""^""|SER^Serum^HL70487|||||||P^Patient specimen^HL70369\rSAC|||I473261\rOBR|1|""||FT3^FT3^99SiemensHDXTestCode\rORC|OK||||CM\rTQ1|||||||||R^Routine^HL70486\rOBX|1|NM|FT3.COFF^FT3^99SiemensHDXTestCode|1^1|1.00|pg/mL^pg/mL^UCUM|([ Normal : 1.5 - 4.2 ] )|""^""^HL70078|||F|||||System~LabManager||NextGenAnalyzer^SiemensHDX~DL00519^SystemSN~IH01507^ModuleSN|20230625183705||||||||||RSLT\rTCD|FT3^FT3^99SiemensHDXTestCode\rOBX|2|NM|FT3.RLU^FT3^99SiemensHDXTestCode|1^1|149870|pg/mL^pg/mL^UCUM|([ Normal : 1.5 - 4.2 ] )|""^""^HL70078|||F|||||System~LabManager||NextGenAnalyzer^SiemensHDX~DL00519^SystemSN~IH01507^ModuleSN|20230625183705||||||||||RSLT\rTCD|FT3^FT3^99SiemensHDXTestCode\rOBX|3|NM|FT3.DOSE^FT3^99SiemensHDXTestCode|1^1|3.50|pg/mL^pg/mL^UCUM|([ Normal : 1.5 - 4.2 ] )|""^""^HL70078|||F|||||System~LabManager||NextGenAnalyzer^SiemensHDX~DL00519^SystemSN~IH01507^ModuleSN|20230625183705||326418||||||||RSLT\rTCD|FT3^FT3^99SiemensHDXTestCode\r\x1c\r')
    print("First Sample")
    hl7MessageParse(data)


    data = str(b'\x0bMSH|^~\\&|UIW_LIS|AA|LIS_ID|BB|20230625183803+0600||OUL^R22^OUL_R22|036314492b444f7b93517f4397d25647|P|2.5.1|||NE|AL||UNICODE UTF-8|||LAB-29^IHE~LAW_REFLEX^IHE~LAW_SPECIMEN^IHE~LAW_RERUN^IHE~LAW_CONTAINER^IHE~LAW_DILUTIONS^IHE~LAW_PAT_DEM^IHE\rSPM|1|I473224^""|""^""|SER^Serum^HL70487|||||||P^Patient specimen^HL70369\rSAC|||I473224\rOBR|1|""||aHCV^aHCV^99SiemensHDXTestCode\rORC|OK||||CM\rTQ1|||||||||R^Routine^HL70486\rOBX|1|NM|aHCV.COFF^aHCV^99SiemensHDXTestCode|1^1|1.00|Index^Index^UCUM||""^""^HL70078|||F|||||System~LabManager||NextGenAnalyzer^SiemensHDX~DL00519^SystemSN~IH01507^ModuleSN|20230625171651||||||||||RSLT\rTCD|aHCV^aHCV^99SiemensHDXTestCode\rNTE|1|Z|Below Check|FLAG^^99SiemensHDXResultFlag\rNTE|2|Z|Final Result Ru|FLAG^^99SiemensHDXResultFlag\rOBX|2|ST|aHCV.INTR^aHCV^99SiemensHDXTestCode|1^1|NR|Index^Index^UCUM||""^""^HL70078|||F|||||System~LabManager||NextGenAnalyzer^SiemensHDX~DL00519^SystemSN~IH01507^ModuleSN|20230625171651||||||||||RSLT\rTCD|aHCV^aHCV^99SiemensHDXTestCode\rNTE|1|Z|Below Check|FLAG^^99SiemensHDXResultFlag\rNTE|2|Z|Final Result Ru|FLAG^^99SiemensHDXResultFlag\rOBX|3|NM|aHCV.RLU^aHCV^99SiemensHDXTestCode|1^1|24727|Index^Index^UCUM||""^""^HL70078|||F|||||System~LabManager||NextGenAnalyzer^SiemensHDX~DL00519^SystemSN~IH01507^ModuleSN|20230625171651||||||||||RSLT\rTCD|aHCV^aHCV^99SiemensHDXTestCode\rNTE|1|Z|Below Check|FLAG^^99SiemensHDXResultFlag\rNTE|2|Z|Final Result Ru|FLAG^^99SiemensHDXResultFlag\rOBX|4|NM|aHCV.INDX^aHCV^99SiemensHDXTestCode|1^1|0.12|Index^Index^UCUM||""^""^HL70078|||F|||||System~LabManager||NextGenAnalyzer^SiemensHDX~DL00519^SystemSN~IH01507^ModuleSN|20230625171651||326402||||||||RSLT\rTCD|aHCV^aHCV^99SiemensHDXTestCode\rNTE|1|Z|Below Check|FLAG^^99SiemensHDXResultFlag\rNTE|2|Z|Final Result Ru|FLAG^^99SiemensHDXResultFlag\r\x1c\r')
    print("\n\nSecond Sample")
    hl7MessageParse(data)
    #mess.append(data)
    #data = str(b'\x02P\x1cDIM\x1c1\x1c1\x1c0\x1c48\x03\x06')
    #mess.append(data)
    #print("data inserted")
    #hl7MessageParse(data)
"""


