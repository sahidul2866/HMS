from colorama import Fore
from datetime import datetime

now = datetime.now()
currentDateTimeStr = now.strftime("%d-%m-%Y %H:%M:%S")


def successMessage(messageData):
    """
    :type messageData: string
    """
    now = datetime.now()
    currentDateTimeStr = now.strftime("%d-%m-%Y %H:%M:%S")
    print(Fore.GREEN + currentDateTimeStr + " [SUCCESS] : " + messageData)


def errorMessage(messageData):
    now = datetime.now()
    currentDateTimeStr = now.strftime("%d-%m-%Y %H:%M:%S")
    print(Fore.RED + currentDateTimeStr + " [ERROR]   : " + messageData)


def warningMessage(messageData):
    now = datetime.now()
    currentDateTimeStr = now.strftime("%d-%m-%Y %H:%M:%S")
    print(Fore.YELLOW + currentDateTimeStr + " [WARNING] : " + messageData)


def infoMessage(messageData):
    now = datetime.now()
    currentDateTimeStr = now.strftime("%d-%m-%Y %H:%M:%S")
    print(Fore.CYAN + currentDateTimeStr + " [INFO]    : " + messageData)
