from API_CONNECTION.commonMessage import *
import requests
import json

url = "http://103.237.37.108:9561/CPH/APIResponse/"


def getTestNameWithId():
    payload = {'api_key': 'R448Jj5a6pGtSPlq3YIWR612efHXPK8tvdQwFOYInvEstiGATtIoN'}
    files = [
    ]
    headers = {}
    response = requests.request("POST", url, headers=headers, data=payload, files=files)
    if response.ok:
        print("Data Got")
        return response.text
    print(response.text)


def getBarcodeData(barcodeId):
    payload = {'api_key': 'R44BaRCodeStatusGtSPlq3YIWR612efHXPK8tvdQwFOYInvEstiGATtIoN',
               'barcode_id': barcodeId}
    files = [
    ]
    headers = {}
    response = requests.request("POST", url, headers=headers, data=payload, files=files)
    if response.ok:
        print("Data Got")
        return response.text
    print(response.text)


def worklistGotSendStatus(barcodeId, status):
    payload = {'api_key': 'BaRCodeStatusResponseGtSPlq3YIWR612efHXPK8tvdQwFOYInvEstiGATtIoN',
               'barcode_id': barcodeId,
               'status': status}
    files = [
    ]
    headers = {}
    response = requests.request("POST", url, headers=headers, data=payload, files=files)
    if response.ok:
        print("Data Got")
        return response.text
    print(response.text)


def resultSendToServer(sentFrom, resultMessage):
    try:
        # resultData = {"Result_1": 92, "Result_2": "Data 2"}
        payload = {'api_key': 'R448Jj5a6pGtSPlq3YIWR612efHXPK8tvdQwFOYResUlT',
                   'type': 'HL7 Data',
                   'contacts': 'Doel E Services',
                   'senderid': sentFrom,
                   'msg': json.dumps(resultMessage)}

        files = [
        ]
        headers = {}
        warningMessage("Data Sending To Server")
        response = requests.request("POST", url, headers=headers, data=payload, files=files)
        if response.ok:
            successMessage("Data Sent To server")
        # print(response.ok)
        infoMessage(str(response.text))
    except Exception as error:
        errorMessage("Network DisConnected: " + str(error))


def getWorkList(barcodeId):
    try:
        payload = {'api_key': 'R44BaRCodeStatusGtSPlq3YIWR612efHXPK8tvdFOYSingInvEstiGATtIoN',
                   'barcode_id': barcodeId}
        files = [
        ]
        headers = {}
        response = requests.request("POST", url, headers=headers, data=payload, files=files)
        if response.ok:
            # print("Data Got")
            return response.text
        infoMessage(str(response.text))
    # except:
    #     errorMessage("Network DisConnected")
    except Exception as error:
        errorMessage("Network DisConnected: " + str(error))
