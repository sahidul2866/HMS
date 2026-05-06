def astm_checksum(message):
    # message should be a bytes object
    # exclude STX and ETX characters
    message = message[1:-1]
    # sum up the ASCII values of all characters
    print(message)
    checksum = sum(message)
    # take modulo 256
    checksum = checksum % 256
    # convert to hexadecimal string
    checksum = hex(checksum)[2:].upper()
    # pad with zero if necessary
    if len(checksum) == 1:
        checksum = "0" + checksum
    return checksum


def getCheckSum(message):
    checkSumValue = astm_checksum(message+b'\n')
    return checkSumValue
    # flagData = '10'
    # finalValue = hex(int(checkSumValue, 16) + int(flagData, 16))[2:].upper()
    # return finalValue


if __name__ == '__main__':
    # checkSumValue = astm_checksum(b'\x02H|\^&|||BING|||||P|E1394-97|\x03')
    # checkSumValue = astm_checksum(b'\x021H|\\^&|||ACCESS^901894|||||LIS||P|1|20230805114457\x03')  #37
    # checkSumValue = astm_checksum(b'\x022P|1|\x03')  # BB
    # checkSumValue = astm_checksum(b'\x021H|\\^&|||ACCESS^901894|||||LIS||P|1|20230805114457\x0D\x03\n')  # 37
    # checkSumValue = astm_checksum(b'\x022P|1|098765678\x0D\x03\n') #A3
    # checkSumValue = astm_checksum(b'\x023O|1|I488785||^^^hLH\^^^CEA2\^^^VitB12|R||||||A||||Serum\x0D\x03\n')
    # checkSumValue = astm_checksum(b'\x022P|1||||^^^^^||19430421|F||\x0D\x03\n') #4F
    checkSumValue = getCheckSum(b'\x022P|1||||^^^^^||19430421|F||\x0D\x03') #4F
    # checkSumValue = getCheckSum(b'\x022P|1|\x0D\x03') #BB
    print(checkSumValue)
    # flagData = '10'
    # finalValue = hex(int(checkSumValue, 16) + int(flagData, 16))[2:].upper()
    # print(finalValue)
