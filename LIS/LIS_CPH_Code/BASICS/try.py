print("hi")

#message1 = "\x023O|1|B1487867----------^0002^01|0002|^^^HbA1c|R||||||||||||||00000080^00000000^0^F^3C1102^2024-03^2L1111^2023-12^2L1401^2023-12^3A1661^2024-01^CA82F43^2024-01\r\x17A7\r\n"
message1 = "\x023O|1|B1487916----------^0001^01|0001|^^^HbA1c|R||||||||||||||00000000^00000000^0^F^3C1102^2024-03^2L1111^2023-12^2L1401^2023-12^3A1661^2024-01^CA82F43^2024-01\r\x1798\r\n"

#message2 = "\x024R|1|^^^ValueHbA1c|6.7|%||||F|||202307200914\r\x1729\r\n"
message2 = "\x024R|1|^^^ValueHbA1c|6.2|%||||F|||202307200913\r\x1723\r\n"

#message3 = "\x025R|2|^^^ValueIFCC|50|mmol/mol||||F\r\x17C0\r\n"
message3 = "\x025R|2|^^^ValueIFCC|45|mmol/mol||||F\r\x17C4\r\n"


'''
print(message1)
print(message2)
print(message3)
'''


sampleId = ""  # sample ID
resultInPercentise = []  # sample Result in Percentise
resultInMol = []  # sample Result in mol

sampleIdList = message1.split('|')
#print(sampleIdList)

if (sampleIdList[0] == "\x023O" and sampleIdList[1] == "1"):  # ID Hunting
    sampleId = sampleIdList[2].split('-')
    sampleId = sampleId[0]
    print("ID = > ", sampleId)

if (sampleIdList[0] == "\x024R" and sampleIdList[1] == "1"):  # Percentise Result Hunting
    resultInPercentise.append(sampleIdList[3])
    resultInPercentise.append("%")
    print("Percentise => ", resultInPercentise)

if (sampleIdList[0] == "\x025R" and sampleIdList[1] == "2"):  # mol Result Hunting
    resultInMol.append(sampleIdList[3])
    resultInMol.append("mmol/mol")
    print("Mol => ", resultInMol)
