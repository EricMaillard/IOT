import sys
from flask import Flask, request, abort
import json
from random import randint
from datetime import datetime
import time
import math
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import threading
import requests
import traceback
from opentelemetry import trace as OpenTelemetry
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider, sampling
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
)

class DeviceStatus(Enum):
	TO_BE_UPDATED = 1
	UP_TO_DATE = 2
	DOWNLOAD_IN_PROGRESS = 3
	INSTALLATION_IN_PROGRESS = 4
	INSTALLATION_FAILED = 5

class ConnectedDevice():
	def __init__(self, device_type, device_model, device_id):
		self.device_type = device_type
		self.device_model = device_model
		self.device_id = device_id
		self.update_available = False
		self.status = DeviceStatus.UP_TO_DATE
	
	def setUpdateAvailable(self):
		self.update_available = True
		self.status = DeviceStatus.TO_BE_UPDATED

	def manageInstallation(self):
		tracer = OpenTelemetry.get_tracer_provider().get_tracer("iot-tracer")
		# waiting for download finished
		with tracer.start_as_current_span("start Package Installation", kind=trace.SpanKind.SERVER) as parent:
			parent.set_attribute("device-type", self.device_type)
			parent.set_attribute("device-model", self.device_model)
			parent.set_attribute("device-id", self.device_id)
			with tracer.start_as_current_span("download in progress on device") as child:
				while self.status == DeviceStatus.DOWNLOAD_IN_PROGRESS:
					time.sleep(1)
					print("Download from device in progress")
			# waiting for installation finished
			with tracer.start_as_current_span("intallation in progress on device") as child:
				while self.status == DeviceStatus.INSTALLATION_IN_PROGRESS:
					time.sleep(1)
					print("Installation of package on device in progress")
					if self.status == DeviceStatus.INSTALLATION_FAILED:
						print("installation failed")
						child.set_status(Status(StatusCode.ERROR))
						child.record_exception(Exception("Installation of package failed"))
						parent.set_status(Status(StatusCode.ERROR))
						return
			print("Installation finished")

	def setDownloadInProgress(self):
		self.update_available = False
		self.status = DeviceStatus.DOWNLOAD_IN_PROGRESS

	def setInstallationInProgress(self):
		self.update_available = False
		self.status = DeviceStatus.INSTALLATION_IN_PROGRESS

	def setDeviceUpdated(self):
		self.update_available = False
		self.status = DeviceStatus.UP_TO_DATE

	def setFailedUpdate(self):
		self.update_available = True
		self.status = DeviceStatus.INSTALLATION_FAILED

	def isUpdateAvailable(self):
		return self.update_available

	def getDeviceType(self):
		return self.device_type

	def getDeviceModel(self):
		return self.device_model

	def getDeviceId(self):
		return self.device_id

head = {
    'Accept': 'application/json',
    'Content-Type': 'application/json; charset=UTF-8',
}

app = Flask(__name__)

iot_device_ids = {}
		
@app.route('/iot_server/check_update_available', methods=['POST'])
def check_update_available():
	global connected_devices
	print("check_update_available"); sys.stdout.flush()
	if request.method == 'POST':
		print(request.json)
		device_id = request.json.get("device_id")
		device = connected_devices.get(device_id)
		if device == None:
			print("Device "+device_id+ " not found in device dict")
			status = False
		else:
			status = device.isUpdateAvailable()
		return {
			"status": status
		}			
	else:
		abort(400)

@app.route('/iot_server/set_update_available', methods=['POST'])
def set_update_available():
	global connected_devices
	print("set_update_available"); sys.stdout.flush()
	if request.method == 'POST':
		print(request.json)
		device_model = request.json.get("device_model")
		found = False
		for device in connected_devices.values():
			model = device.getDeviceModel()
			if model == device_model:
				device.setUpdateAvailable()
				found = True
		if found:
			return {"status updated":True}
		else:
			return 'Device model not found', 404
	else:
		abort(400)

@app.route('/iot_server/request_package', methods=['POST'])
def request_package():
	global connected_devices
	print("request_package"); sys.stdout.flush()
	if request.method == 'POST':
		print(request.json)
		print("package requested")
		device_id = request.json.get("device_id")
		device = connected_devices.get(device_id)
		if device == None:
			print("Device "+device_id+ " not found in device dict")
			return 'Device not found', 404
		else:
			iot_device_id = request.json.get('device_id')
			dt_device_id = iot_device_ids.get(iot_device_id)
			if dt_device_id == None:
				dt_device_id = getCustomDeviceId(iot_device_id)
				if dt_device_id != None:
					iot_device_ids[iot_device_id] = dt_device_id
			device.setDownloadInProgress()
			log_json = []
			log_payload = {
				"content" : json.dumps(request.json),
				"device_model" : request.json.get('device_model'),
				"device_id" : request.json.get('device_id'),
				"device_firmware" : request.json.get('device_firmware'),
				"device_ip" : request.json.get('device_ip'),
				"device_type" : request.json.get('device_type'),
				"log.source" : "iot."+request.json.get('device_type'),
				"severity" : "INFO"
			}
			log_json.append(log_payload)
			send_logs(log_json)

			installationThread = threading.Thread(target=device.manageInstallation)
			installationThread.start()
		return '', 200
	else:
		abort(400)

@app.route('/iot_server/acknowledge_download', methods=['POST'])
def acknowledge_download():
	global connected_devices
	print("acknowledge_download"); sys.stdout.flush()
	if request.method == 'POST':
		print(request.json)
		print("download acknowledged")
		device_id = request.json.get("device_id")
		device = connected_devices.get(device_id)
		if device == None:
			print("Device "+device_id+ " not found in device dict")
			return 'Device not found', 404
		else:
			iot_device_id = request.json.get('device_id')
			dt_device_id = iot_device_ids.get(iot_device_id)
			if dt_device_id == None:
				dt_device_id = getCustomDeviceId(iot_device_id)
				if dt_device_id != None:
					iot_device_ids[iot_device_id] = dt_device_id
			log_json = []
			log_payload = {
				"content" : json.dumps(request.json),
				"device_model" : request.json.get('device_model'),
				"device_id" : request.json.get('device_id'),
				"device_firmware" : request.json.get('device_firmware'),
				"device_ip" : request.json.get('device_ip'),
				"device_type" : request.json.get('device_type'),
				"log.source" : "iot."+request.json.get('device_type'),
				"severity" : "INFO"
			}
			log_json.append(log_payload)
			send_logs(log_json)
			device.setInstallationInProgress()
		return '', 200
	else:
		abort(400)

@app.route('/iot_server/acknowledge_installation', methods=['POST'])
def acknowledge_installation():
	global connected_devices
	print("acknowledge_installation"); sys.stdout.flush()
	if request.method == 'POST':
		print(request.json)
		print("installation acknowledged")
		device_id = request.json.get("device_id")
		device = connected_devices.get(device_id)
		if device == None:
			print("Device "+device_id+ " not found in device dict")
			return 'Device not found', 404
		else:
			iot_device_id = request.json.get('device_id')
			dt_device_id = iot_device_ids.get(iot_device_id)
			if dt_device_id == None:
				dt_device_id = getCustomDeviceId(iot_device_id)
				if dt_device_id != None:
					iot_device_ids[iot_device_id] = dt_device_id
			log_json = []
			log_payload = {
				"content" : json.dumps(request.json),
				"device_model" : request.json.get('device_model'),
				"device_id" : request.json.get('device_id'),
				"device_firmware" : request.json.get('device_firmware'),
				"device_ip" : request.json.get('device_ip'),
				"device_type" : request.json.get('device_type'),
				"log.source" : "iot."+request.json.get('device_type'),
				"severity" : "INFO"
			}
			if request.json.get("success") == True:
				device.setDeviceUpdated()
				log_json.append(log_payload)
				send_logs(log_json)
			else:
				device.setFailedUpdate()
				log_payload['severity'] = "ERROR"
				log_json.append(log_payload)
				send_logs(log_json)
		return '', 200
	else:
		abort(400)

@app.route('/iot_server/send_usage_data', methods=['POST'])
def send_usage_data():
	print("send_usage_data"); sys.stdout.flush()
	if request.method == 'POST':
		print(request.json)
		iot_device_id = request.json.get('device_id')
		dt_device_id = iot_device_ids.get(iot_device_id)
		if dt_device_id == None:
			dt_device_id = getCustomDeviceId(iot_device_id)
			if dt_device_id != None:
				iot_device_ids[iot_device_id] = dt_device_id
		log_json = []
		log_payload = {
			"content" : json.dumps(request.json),
			"device_model" : request.json.get('device_model'),
			"device_id" : request.json.get('device_id'),
			"device_firmware" : request.json.get('device_firmware'),
			"device_ip" : request.json.get('device_ip'),
			"device_type" : request.json.get('device_type'),
			"log.source" : "iot."+request.json.get('device_type'),
			"severity" : "INFO"
		}
		log_json.append(log_payload)
		send_logs(log_json)
		return '', 200
	else:
		abort(400)


def send_logs(log_json):
	global dt_settings
	try:
		url = dt_settings.get("dynatrace_server_url")+ '/api/v2/logs/ingest'
		dtheader = {
			'Content-Type': 'application/json; charset=utf-8',
			'Authorization': 'Api-Token '+dt_settings.get("dynatrace_api_token"),
		}
		print(url)
		print(dtheader)
		print(log_json)
		dynatrace_response = requests.post(url, json=log_json, headers=dtheader)
		if dynatrace_response.status_code >= 400:
			print(f'Error in Dynatrace log API Response :\n'
						f'{dynatrace_response.text}\n'
						f'Message was :\n'
						f'{str(log_json)}'
						)
	except Exception as e:
		print(traceback.format_exc())

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

def run_server(settings_file, devices_file):
	global connected_devices
	global dt_settings

	# read setting files
	with open(settings_file, encoding='utf-8') as f:
		dt_settings = json.load(f)


	merged = dict()
	merged.update({
		"service.name": "iot-software-update", #TODO Replace with the name of your application
		"service.version": "1.0.0", #TODO Replace with the version of your application
	})
	resource = Resource.create(merged)

	tracer_provider = TracerProvider(sampler=sampling.ALWAYS_ON, resource=resource)
	OpenTelemetry.set_tracer_provider(tracer_provider)

	tracer_provider.add_span_processor(
		BatchSpanProcessor(OTLPSpanExporter(
			endpoint=dt_settings.get('dynatrace_server_url')+"/api/v2/otlp/v1/traces", #TODO Replace <URL> to your SaaS/Managed-URL as mentioned in the next step
			headers={
			"Authorization": "Api-Token "+dt_settings.get('dynatrace_api_token') #TODO Replace <TOKEN> with your API Token as mentioned in the next step
			},
		)))
	# read devices definition file
	with open(devices_file, encoding='utf-8') as f:
		devices = json.load(f).get("devices")

	connected_devices = {}
	for device in devices:
		connected_device = ConnectedDevice(device.get('device_type'), device.get('device_model'), device.get('device_id'))
		connected_devices[device.get('device_id')] = connected_device

	app.run(host= '0.0.0.0', port='5010')


if __name__ == "__main__":
    run_server(sys.argv[1], sys.argv[2])
