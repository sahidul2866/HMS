from API_CONNECTION.commonMessage import *
import time

def testForExe():
    while 1:
        infoMessage("This is Info Message")
        time.sleep(2)
        warningMessage("This is Warning Message")
        time.sleep(2)
        successMessage("This is Success Message")
        time.sleep(2)
        errorMessage("This is Error Message")
        time.sleep(2)
