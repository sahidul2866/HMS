import requests
import json

def sendDataToServer(message):
    url = "http://182.160.105.218/CPH/APIResponse/"

    message = {"Result_1": 92, "Result_2": "Data 2"}
    payload = {'api_key': 'R448Jj5a6pGtSPlq3YIWR612efHXPK8tvdQwFOYResUlT',
    'type': 'Central LIS',
    'contacts': 'Harun',
    'senderid': 'SYS_MEX_1000', # Machine Name
    'MACHINE_TEST_NAME':'CBC',
    'msg': json.dumps( message ) }

    files=[
    ]
    headers = {}

    response = requests.request("POST", url, headers=headers, data=payload, files=files)
    print(response.text)
    if response.ok:
        print("Data Send To server")
    # print(response.ok)
