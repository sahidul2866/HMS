import serial
from URISED_3.hl7MessageParse_URISED_3 import *

def serverUrised3():
    serialPort = serial.Serial(port="COM3", baudrate=9600, bytesize=8, parity=serial.PARITY_NONE,
                               stopbits=serial.STOPBITS_ONE, timeout=.1)
    serialString = ""
    testResult = ""
    frames = []

    dialation_flag = False
    ch2 = {} # Saved for Dialation

    infoMessage("__________ Starting Server URISED 3 ______________________")
    while 1:
        if serialPort.in_waiting > 0:
            serialString = serialPort.readline()
            messageRawData = str(serialString)
            #print(serialString)
            messageRawData = messageRawData[1:]
            messageRawData = messageRawData[1:-1]


            if "\\x05'" not in messageRawData and "\\x04'" not in messageRawData:
                testResult += messageRawData.replace("\\x0", "").replace("\\x5", "").replace("\\x4", "")
                print("\nTest: ",testResult)

                frame = testResult.split('|')

                if len(frame)>0 and frame[0]=="2S2":
                    N_A = ""
                    try:
                        #print("frame: ", frame)
                        #print("RBC=>", frame[25])

                        rbc_list = frame[25].split("^")  # Bug +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
                        N_A = rbc_list[1]  # Bug +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
                    except IndexError:
                        errorMessage("N/A error!, list out of range.")


                    ########################   Updated ##########################
                    flag_ekhn = False
                    if N_A == "N/A":
                        dialation_flag =True
                    else:
                        if len(frame)>3 and frame[3] in ch2:
                            # key ta kete dite hobe dictionary theke jokhn dialation hobe
                            flag_ekhn = True
                    ##############################################################

                    if len(frames)>0:
                        frames[0] = frame
                    else:
                        frames.append(frame)

                    if flag_ekhn == True:
                        # ekhane Dialation hobe
                        frames.append(ch2[frame[3]])
                        ch2.pop(frame[3])  # removed from queue of dialation

                        infoMessage("++++++++++++++++++++++Dialation start++++++++++++++++++++++")
                        hl7MessageParse(frames)  # Dialation
                        frames.clear()

                elif len(frame)>0 and frame[0]=="2CH2":
                    ########################   Updated ##########################
                    if dialation_flag ==True:
                        ch2[frame[3]] = frame   # Saved for dialation
                        dialation_flag = False
                    ##############################################################


                    if len(frames)>1:
                        frames[1] = frame
                    else:
                        frames.append(frame)
                    warningMessage("++++++++++++++++++++++ Message pass to hl7 ++++++++++++++++++++++")
                    hl7MessageParse(frames)
                    frames.clear()

            testResult=""
            serialPort.write(b'\x06')
        #      serialPort.write(b"Thank you for sending data \r\n")
