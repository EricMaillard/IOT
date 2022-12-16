import json
import requests
import sys
from random import randint
from datetime import datetime
import time

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

def main(argv):

    # read devices definition file
    with open(argv[1], encoding='utf-8') as f:
        devices = json.load(f).get("devices")

    while (True):
        time_between_updates = randint(60,120)
        index = randint(0, len(devices))
        device_model = devices[index].get('device_model')
        sendMessage(device_model)
        time.sleep(time_between_updates*60)
    

if __name__ == "__main__":
    main(sys.argv)
