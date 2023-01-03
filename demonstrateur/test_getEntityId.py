import requests
import json
import sys


# return the custom device id in Dynatrace given the device_id (device serial number)
def getCustomDeviceId(device_id):
    global dt_settings

    url = dt_settings.get("dynatrace_server_url")+'/api/v2/entities?entitySelector=type(\"device:iot-device\"),entityName('+device_id+')'
    print('url = '+url)
    # query Dynatrace API to get Device ID
    r = requests.get(
        url, 
        headers={'Authorization': "Api-Token " + dt_settings.get("dynatrace_api_token")},
        verify=True
        )

    # eror ?
    if(r.ok):
        if(len(r.text) > 0):
            jsonContent = json.loads(r.text)
            print(jsonContent)
    else:
        print('status code = '+str(r.status_code)+' reason = '+r.reason+' text = '+r.text)    
        jsonContent = None
    if jsonContent:
        entities = jsonContent.get('entities')
        if entities and len(entities) > 0:
            return entities[0].get('entityId')
    else:
        return None

def run(settings_file):
    global dt_settings
    # read setting files
    with open(settings_file, encoding='utf-8') as f:
        dt_settings = json.load(f)

    entityId = getCustomDeviceId('ADIDAS_T-19L_234243')
    print("entityId = "+entityId)

if __name__ == "__main__":
    run(sys.argv[1])
