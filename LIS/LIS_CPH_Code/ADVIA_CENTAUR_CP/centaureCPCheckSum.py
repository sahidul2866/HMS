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
    checkSumValue = astm_checksum(message + b'\n')
    # checkSumValue = astm_checksum(message)
    return checkSumValue
    # flagData = '10'
    # finalValue = hex(int(checkSumValue, 16) + int(flagData, 16))[2:].upper()
    # return finalValue


# if __name__ == '__main__':
#     message = "\x021H|\^&|||Host|||||ACCP1||P|1\x0D\x03"  # EE
#     print(getCheckSum(message.encode()))
#     message = "\x022P|1|P1234567038|||Tim Tam||1968909|M|||||MD_DOC\x0D\x03"  # 5F
#     print(getCheckSum(message.encode()))
#     message = "\x023O|1|LIS3023||^^^T4\^^^TSH\^^^TUP|R||||||||||||||||||||O\x0D\x03"  # A6
#     print(getCheckSum(message.encode()))
#     message = "\x024L|1|N\x0D\x03"  # 07
#     print(getCheckSum(message.encode()))
