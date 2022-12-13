import json
import requests
from random import randint, uniform
import time
from datetime import datetime as dt, timedelta
from concurrent.futures import ThreadPoolExecutor
import traceback
import sys

head = {
    'Accept': 'application/json',
    'Content-Type': 'application/json; charset=UTF-8',
}
exit_requested = False
frequency = 60
class ConnectedDevice():

	def __init__(self, device_type, device_model, device_id, device_firmware, device_ip):
		self.device_type = device_type
		self.device_model = device_model
		self.device_id = device_id
		self.device_firmware = device_firmware
		self.device_ip = device_ip
		self.FreeRTOS_load = 0
		self.FreeRTOS_free_heap = 0
		self.MQTT_publish_rtt = 0
		self.MQTT_publish_fail = 0
		self.MQTT_connection_time = 0
		self.MQTT_total_sent_bytes = 0
		self.MQTT_total_received_bytes = 0
		self.Uptime = 0

	def checkUpdateAvailable(self):
		uri = 'http://localhost:5010/iot_server/check_update_available'
		payload = {
			'device_model': self.device_model,
			'device_id': self.device_id,
			'device_type': self.device_type,
			'device_firmware': self.device_firmware,
			'device_ip': self.device_ip,
			'event_type' : "checkUpdateAvailable",
			'message' : "Check update available"
		}

		try:
			response = requests.post(uri,headers=head,verify=True, json=payload, timeout=5)
		except Exception:
			print("Unable to call iot_server/check_update_available. device_model ="+self.device_model+", device_id = "+self.device_id)
			return
		# For successful API call, response code will be 200 (OK)
		if(response.ok):
			jsonContent = json.loads(response.text)
			return jsonContent.get("status")
		else:
			print('checkUpdateAvailable response KO')
		
	def requestPackage(self):
		uri = 'http://localhost:5010/iot_server/request_package'
		payload = {
			'device_model': self.device_model,
			'device_id': self.device_id,
			'device_type': self.device_type,
			'device_firmware': self.device_firmware,
			'device_ip': self.device_ip,
			'event_type' : "requestPackage",
			'message' : "Request package"
		}

		try:
			response = requests.post(uri,headers=head,verify=True, json=payload, timeout=5)
		except Exception:
			print("Unable to call iot_server/request_package. device_model ="+self.device_model+", device_id = "+self.device_id)
			return
		# For successful API call, response code will be 200 (OK)
		if(response.ok):
			print('request_package OK')
		else:
			print('request_package KO')

	def acknowledgeDownload(self):
		uri = 'http://localhost:5010/iot_server/acknowledge_download'
		payload = {
			'device_model': self.device_model,
			'device_id': self.device_id,
			'device_type': self.device_type,
			'device_firmware': self.device_firmware,
			'device_ip': self.device_ip,
			'event_type' : "acknowledgeDownload",
			'message' : "Acknowledge Download"
		}

		try:
			response = requests.post(uri,headers=head,verify=True, json=payload, timeout=5)
		except Exception:
			print("Unable to call iot_server/acknowledge_download. device_model ="+self.device_model+", device_id = "+self.device_id)
			return
		# For successful API call, response code will be 200 (OK)
		if(response.ok):
			print('acknowledge_download OK')
		else:
			print('acknowledge_download KO')

	def acknowledgeInstallation(self):
		uri = 'http://localhost:5010/iot_server/acknowledge_installation'
		payload = {
			'device_model': self.device_model,
			'device_id': self.device_id,
			'device_type': self.device_type,
			'device_firmware': self.device_firmware,
			'device_ip': self.device_ip,
			'event_type' : "acknowledgeInstallation",
			'message' : "Acknowledge Installation"
		}
		value = randint(0,3)
		print("value = "+str(value))
		if value == 1:
			payload['success'] = False
			payload['message'] = "Installation failed"
			payload['error_message'] = "Installation failed"
			payload['error_code'] = 42
		else:
			payload['success'] = True
			payload['message'] = "Installation OK"
		try:
			response = requests.post(uri,headers=head,verify=True, json=payload, timeout=5)
		except Exception:
			print("Unable to call iot_server/acknowledge_installation. device_model ="+self.device_model+", device_id = "+self.device_id)
			return
		# For successful API call, response code will be 200 (OK)
		if(response.ok):
			print('acknowledge_installation OK')
		else:
			print('acknowledge_installation KO')

	def sendUsageData(self, payload):
		uri = 'http://localhost:5010/iot_server/send_usage_data'
		try:
			response = requests.post(uri,headers=head,verify=True, json=payload, timeout=5)
		except Exception:
			print("Unable to call iot_server/send_usage_data. device_model ="+self.device_model+", device_id = "+self.device_id)
			return
		# For successful API call, response code will be 200 (OK)
		if(response.ok):
			print('send_usage_data OK')
		else:
			print('send_usage_data KO')

	def sendMetrics(self, payload):
		global dt_settings
		uri = dt_settings['dynatrace_server_url'] + "/api/v2/metrics/ingest"
		token_query_param = '?api-token='+dt_settings['dynatrace_api_token']
		headers = {
			'Content-Type': 'text/plain; charset=UTF-8'
		}
		print(uri+token_query_param)
		print(headers)
		print(payload)
		response = requests.post(uri+token_query_param, headers=headers, verify=True, data=payload)
		if not response.ok:
			print(response.text)
			raise Exception("Error on request "+uri, "Dynatrace API returned an error: " + response.text)

	def manageMetrics(self):
		# increment metric values
		self.FreeRTOS_load = uniform(1.0, 5.0)
		self.FreeRTOS_free_heap = randint(500000, 600000)
		self.MQTT_publish_rtt = uniform(1.0, 5.0)
		value = randint(0,3)
		if value == 1:
			MQTT_publish_fail_delta = randint(1,5)
			self.MQTT_publish_fail = self.MQTT_publish_fail + MQTT_publish_fail_delta
		else:
			MQTT_publish_fail_delta = 0
		self.MQTT_connection_time = uniform(0.5, 2.0)
		MQTT_total_sent_bytes_delta = randint(1000,5000)
		self.MQTT_total_sent_bytes = self.MQTT_total_sent_bytes + MQTT_total_sent_bytes_delta
		MQTT_total_received_bytes_delta = randint(1000,5000)
		self.MQTT_total_received_bytes = self.MQTT_total_received_bytes + MQTT_total_received_bytes_delta
		self.Uptime = self.Uptime + 60000
		dimensions = 'device_type="'+self.device_type+'",device_model="'+self.device_model+'",device_id="'+self.device_id+'",device_firmware="'+self.device_firmware+'",device_ip="'+self.device_ip+'"'
		metricsToIngest = ""
		metricsToIngest = metricsToIngest+ 'iot.decathlon.FreeRTOS_load,'+dimensions+' '+str(self.FreeRTOS_load)+'\n'
		metricsToIngest = metricsToIngest+ 'iot.decathlon.FreeRTOS_free_heap,'+dimensions+' '+str(self.FreeRTOS_free_heap)+'\n'
		metricsToIngest = metricsToIngest+ 'iot.decathlon.MQTT_publish_rtt,'+dimensions+' '+str(self.MQTT_publish_rtt)+'\n'
		metricsToIngest = metricsToIngest+ 'iot.decathlon.MQTT_publish_fail,'+dimensions+' count,delta='+str(MQTT_publish_fail_delta)+'\n'
		metricsToIngest = metricsToIngest+ 'iot.decathlon.MQTT_connection_time,'+dimensions+' '+str(self.MQTT_connection_time)+'\n'
		metricsToIngest = metricsToIngest+ 'iot.decathlon.MQTT_total_sent_bytes,'+dimensions+' count,delta='+str(MQTT_total_sent_bytes_delta)+'\n'
		metricsToIngest = metricsToIngest+ 'iot.decathlon.MQTT_total_received_bytes,'+dimensions+' count,delta='+str(MQTT_total_received_bytes_delta)+'\n'
		metricsToIngest = metricsToIngest+ 'iot.decathlon.Uptime,'+dimensions+' '+str(self.Uptime)+'\n'
		self.sendMetrics(metricsToIngest)
        
	def run(self):
		global exit_requested
		print("run device : device_model = "+self.device_model+", device_id = "+self.device_id)

		while exit_requested == False:
			try:
				querytime = dt.utcnow()
				self.manageMetrics()
				status = self.checkUpdateAvailable()
				print(self.device_model + " "+self.device_id+ " : status = "+str(status))
				if status:
					self.requestPackage()
					time.sleep(10)
					self.acknowledgeDownload()
					time.sleep(20)
					self.acknowledgeInstallation()
				# wait until next minute
				currenttime = dt.utcnow()
				next_time = querytime + timedelta(seconds=frequency)
				delta = next_time - currenttime
				if delta.total_seconds() > 0:
					time.sleep(delta.total_seconds())
			except Exception as e:
				print(traceback.format_exc())
				next_time = querytime + timedelta(seconds=frequency)
				delta = next_time - currenttime
				if delta.total_seconds() > 0:
					time.sleep(delta.total_seconds())

	def runDeviceUsageThread(self):
		global exit_requested
		multiplicator = 5
		while exit_requested == False:
			seconds_to_sleep = randint(60*multiplicator, 180*multiplicator)
			time.sleep(seconds_to_sleep)
			if exit_requested:
				return
			# send start run event
			payload = {
				'device_model': self.device_model,
				'device_id': self.device_id,
				'device_type': self.device_type,
				'device_firmware': self.device_firmware,
				'device_ip': self.device_ip,
				'event_type' : "start_run",
				'message' : "User has started a run"
			}
			self.sendUsageData(payload)
			seconds_to_sleep = randint(20*multiplicator, 40*multiplicator)
			time.sleep(seconds_to_sleep)
			if exit_requested:
				return
			# send pause run event
			payload = {
				'device_model': self.device_model,
				'device_id': self.device_id,
				'device_type': self.device_type,
				'device_firmware': self.device_firmware,
				'device_ip': self.device_ip,
				'event_type' : "pause_run",
				'message' : "User takes a pause during run"
			}
			self.sendUsageData(payload)
			seconds_to_sleep = randint(10*multiplicator, 20*multiplicator)
			time.sleep(seconds_to_sleep)
			if exit_requested:
				return
			# send restart run event
			payload = {
				'device_model': self.device_model,
				'device_id': self.device_id,
				'device_type': self.device_type,
				'device_firmware': self.device_firmware,
				'device_ip': self.device_ip,
				'event_type' : "restart_run",
				'message' : "User restarts run after a pause"
			}
			self.sendUsageData(payload)
			seconds_to_sleep = randint(20*multiplicator, 40*multiplicator)
			time.sleep(seconds_to_sleep)
			if exit_requested:
				return
			# send stop run event
			payload = {
				'device_model': self.device_model,
				'device_id': self.device_id,
				'device_type': self.device_type,
				'device_firmware': self.device_firmware,
				'device_ip': self.device_ip,
				'event_type' : "stop_run",
				'message' : "User stops run"
			}
			self.sendUsageData(payload)
			seconds_to_sleep = randint(80*multiplicator, 200*multiplicator)
			time.sleep(seconds_to_sleep)
		
def run_devices(settings_file, devices_file):
	global exit_requested
	global dt_settings

	# read setting files
	with open(settings_file, encoding='utf-8') as f:
		dt_settings = json.load(f)

	# read devices definition file
	with open(devices_file, encoding='utf-8') as f:
		devices = json.load(f).get("devices")

	executor = ThreadPoolExecutor(max_workers=2*len(devices))

	for device in devices:
		connected_device = ConnectedDevice(device.get('device_type'), device.get('device_model'), device.get('device_id'), device.get('device_firmware'), device.get('device_ip'))
		executor.submit(connected_device.run)
		executor.submit(connected_device.runDeviceUsageThread)

	loop_forever = True
	while loop_forever:
		try:
			time.sleep(60)
		except KeyboardInterrupt:
			print("exit_requested")
			exit_requested = True
			loop_forever = False
	print("exit program")
	quit()

if __name__ == "__main__":
    run_devices(sys.argv[1], sys.argv[2])
