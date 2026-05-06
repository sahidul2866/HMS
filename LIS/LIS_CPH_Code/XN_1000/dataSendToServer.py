import requests
import json


def sendDataToServer(message):
    print(message)
    url = "http://182.160.105.218/CPH/APIResponse/"

    resultData = {"Result_1": 92, "Result_2": "Data 2"}
    payload = {'api_key': 'R448Jj5a6pGtSPlq3YIWR612efHXPK8tvdQwFOYResUlT',
               'type': 'HL7 Data',
               'contacts': 'Harun',
               'senderid': 'HARUN_LIS',
               'msg': json.dumps(message)}
    # print("Payload Data",payload)
    files = [
    ]
    headers = {}
    print(json.dumps(message))
    response = requests.request("POST", url, headers=headers, data=payload, files=files)
    print(response)
    if response.ok:
        print("Data Send To server")
    # # print(response.ok)
    print(response.text)
