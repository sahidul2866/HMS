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
