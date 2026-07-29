import json
import os
import time
import requests
import threading
from const import CLIENT_VERSION, runtime_tmp_dir, API_TOKEN, server_ip
from zeroconf import Zeroconf, ServiceBrowser
import socket


# server_api_host_ip = None
server_api_host_ip = server_ip
server_ip_event = threading.Event()

def get_server_ip():
    global server_api_host_ip
    while server_api_host_ip is None:
        print("Searching for server...")
        server_ip_event.wait(timeout=0.25)
    return server_api_host_ip

def get_server_api():
    return "http://%s" % get_server_ip()

class MyListener:
    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        if info:
            ip = socket.inet_ntoa(info.addresses[0])
            global server_api_host_ip
            server_api_host_ip = ip
            server_ip_event.set()

    def update_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        if info:
            ip = socket.inet_ntoa(info.addresses[0])
            global server_api_host_ip
            server_api_host_ip = ip
            server_ip_event.set()

zeroconf = Zeroconf()
listener = MyListener()
browser = ServiceBrowser(zeroconf, "_security._tcp.local.", listener)

class DetectorAPI:
    def __init__(
        self,
        mac="01-01-01-01-01-01",
        os="windows",
        token=API_TOKEN
    ):
        self.mac = mac
        self.os = os
        self.token = token
        self.headers = {
            "x-hasura-admin-secret": self.token,
            "Content-Type": "application/json",
        }
        global server_api_host_ip
        while server_api_host_ip is None:
            print("Searching for server...")
            server_ip_event.wait(timeout=0.25)

        self.config = None

    def api_host(self):
        global server_api_host_ip
        # try:
        #     response = requests.get(
        #         "%s/rest/v1/client/pulse-check" % get_server_api(),
        #         headers=self.headers, timeout=2
        #     )
        #     is_ok = response.ok
        # except Exception:
        #     is_ok = False

        # while server_api_host_ip is None or not is_ok:
        #     print("Searching for server...")
        #     server_ip_event.wait(timeout=0.25)
        #     try:
        #         response = requests.get(
        #             "%s/rest/v1/client/pulse-check" % get_server_api(),
        #             headers=self.headers, timeout=2
        #         )
        #         is_ok = response.ok
        #     except Exception:
        #         is_ok = False
        return f"http://{server_api_host_ip}"

    def getConfig(self):
        return self.config

    def get_config(self, vm_count=None):
        config = self._get_config(vm_count)
        try:
            self.config = config['config']
            self.config['laptop_id'] = config['laptop']['id']
            self.config['laptop'] = config['laptop']
            if config['laptop'].get('client', {}) is not None:
                self.config['client_id'] = config['laptop'].get('client', {}).get('id', 0)
            with open(os.path.join(runtime_tmp_dir, 'laptop_id'), 'w') as f:
                f.write(str(config['laptop']['id']))
        except Exception as e:
            self.config = None

    def _get_config(self, vm_count):
        try:
            payload = {
                "macAddress": self.mac,
                "os": self.os,
                "clientVersion": CLIENT_VERSION
            }
            if vm_count is not None:
                payload['activeVMCount'] = vm_count

            response = requests.post(
                "%s/rest/v1/client/connection" % self.api_host(),
                data=json.dumps(payload),
                headers=self.headers, timeout=5
            ).json()

            return response
        except:
            return "error - get_config"

    def upload_screenshot(self, payload):
        try:
            return requests.post(
                "%s/rest/v1/client/upload" % self.api_host(),
                headers=self.headers,
                data=payload
            ).json()
        except:
            return "error - upload_screenshot"

    def upload_process(self, payload):
        try:
            print ('_' * 100)
            print (payload)
            print ("%s/rest/v1/processes/create" % self.api_host())
            print (self.headers)
            res = requests.post(
                "%s/rest/v1/processes/create" % self.api_host(),
                headers=self.headers,
                data=payload
            ).json()
            print ('___')
            print (res)
            return res
        except:
            return "error - upload_process"

    def upload_extension(self, payload):
        try:
            return requests.post(
                "%s/rest/v1/client/browsers" % self.api_host(),
                headers=self.headers,
                data=payload
            ).json()
        except:
            return "error - upload_screenshot"

    def upload_web_logs(self, payload):
        try:
            print ("%s/rest/v1/client/browser-log" % self.api_host())
            return requests.post(
                "%s/rest/v1/client/browser-log" % self.api_host(),
                headers=self.headers,
                data=payload
            ).json()
        except:
            return "error - upload_screenshot"

    def upload_keyboard(self, payload):
        try:
            return requests.post(
                "%s/rest/v1/client/keyboard" % self.api_host(),
                headers=self.headers,
                data=payload
            ).json()
        except:
            return "error - upload_screenshot"

    def push_log(self, laptop_id, message, log_type='ERROR'):
        try:
            print ('push_log', message)
            return requests.post(
                "%s/rest/v1/client/app-log" % self.api_host(),
                headers=self.headers,
                data=(json.dumps([{
                    'laptop_id': laptop_id,
                    'content': message,
                    'log_type': log_type
                }]))
            ).json()
        except:
            return "error - push app log"

    def load_browser_history(self, laptop_id):
        pass
