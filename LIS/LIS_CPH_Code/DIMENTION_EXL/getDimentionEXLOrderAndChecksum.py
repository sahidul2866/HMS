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
    checkSumValue = astm_checksum(message+b'\x03')
    return checkSumValue
    # flagData = '10'
    # finalValue = hex(int(checkSumValue, 16) + int(flagData, 16))[2:].upper()
    # return finalValue

# if __name__ == '__main__':
#     # print(getCheckSum(b'\x02P\x1c9300\x1c1\x1c1\x1c0\x03')) #6C
#
#     # print(getCheckSum(b'\x02P\x1c92300\x1c0\x1c1\x1c0\x1c\x03')) #6B
#     # print(getCheckSum(b'\x02N\x1c\x03')) #6A
#     # print(getCheckSum(b'\x02M\x1c\x1cA\x1cA\x1c1\x1c42\x1c\x03')) #0E
#     print(getCheckSum(b'\x02P\x1cDIM\x1c1\x1c1\x1c0\x1c')) #48
