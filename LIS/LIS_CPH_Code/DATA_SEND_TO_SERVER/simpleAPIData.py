import requests
import json

url = "http://182.160.105.218/CPH/APIResponse/"


resultData = {"Result_1": 92, "Result_2": "Data 2"}

payload = {'api_key': 'Test API Key',
'type': 'HL7 Data',
'contacts': 'Harun',
'senderid': 'HARUN_LIS',
'msg': json.dumps( resultData ) }

files=[
]
headers = {}

response = requests.request("POST", url, headers=headers, data=payload, files=files)
if response.ok:
    print("Data Send To server")
# print(response.ok)
print(response.text)