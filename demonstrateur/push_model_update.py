import json
import requests
import sys

def sendMessage(device_model):
    head = {
        'Accept': 'application/json',
        'Content-Type': 'application/json; charset=UTF-8',
    }
    uri = 'http://localhost:5010/iot_server/set_update_available'
    payload = {
        'device_model': device_model,
    }

    try:
        response = requests.post(uri,headers=head,verify=True, json=payload, timeout=5)
    except Exception:
        print("Unable to call iot_server/set_update_available. device_model ="+device_model)
    if(response.ok):
        jsonContent = json.loads(response.text)
        print(jsonContent)
    else:
        print('set_update_available response KO')

if __name__ == "__main__":
    sendMessage(sys.argv[1])
