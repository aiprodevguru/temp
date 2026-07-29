from browser import fetch_browser_history
from keyboard import KeyboardMonitor
from vm_process import list_vm_processes

from datetime import datetime, timedelta
import threading
import pytz
import time
import platform
from multiprocessing import Process, Queue, freeze_support
from getmac import get_mac_address
from api import DetectorAPI
import json
from record import run_main, run_zip_upload
import traceback
import server
import os
from const import runtime_tmp_dir
from browser_history_master import get_extension
from processes import run as upload_processes

OS_NAME = platform.system()
class Main:
    interval = 60 # seconds
    last_run_time = None
    use_log = False
    utc = pytz.UTC
    keyboardm = None

    def __init__(self):
        self.mac = self.getMacAddress()
        print ("mac >>>: %s" % self.mac)

        self.keyboardm = None
        self.config = None
        self.secondsOfBrowserHistory = 60
        self.interval = 60

        if self.mac:
            self.api = DetectorAPI(mac=self.mac, os=self.getOSName())
        else:
            print ('mac not available')

        self.getConfig()

        with open(os.path.join(runtime_tmp_dir, 'pid'), 'w') as f:
            f.write(str(os.getpid()))

        with open(os.path.join(runtime_tmp_dir, 'macAddress'), 'w') as f:
            f.write(str(self.mac))
        if self.config is not None:
            try:
                self.keyboardm = KeyboardMonitor(self.api, OS_NAME, self.config.get('laptop_id'))
            except Exception as e:
                print ("keyboard init failed", e)
                traceback.print_exc()
                pass

    def getConfig(self):
        vm_count = list_vm_processes()
        self.api.get_config(vm_count)
        self.config = self.api.getConfig()

        if self.config == None:
            self.interval = 60
            return None

        self.secondsOfBrowserHistory = self.config.get('secondsOfBrowserHistory', 60)
        if self.secondsOfBrowserHistory > 60:
            self.interval = 60
        else:
            self.interval = self.secondsOfBrowserHistory

        return self.config

    def getMacAddress(self):
        if OS_NAME == 'Windows':
            names = ["Ethernet"]
            for i in range(50):
                names.append(f'Ethernet {i}')
            for name in names:
                mac = get_mac_address(name)
                if mac:
                    return mac
        elif OS_NAME == 'Linux':
            names = []
            for i in range(10):
                for j in range(10):
                    names.append(f'enp{i}s{j}')
                    names.append(f'wlp{i}s{j}')

            for name in names:
                mac = get_mac_address(name)
                if mac:
                    return mac
        else:
            return get_mac_address()

        return None

    def getOSName(self):
        if OS_NAME == 'Windows':
            return 'windows'
        elif OS_NAME == 'Linux':
            return 'linux'
        else:
            return 'mac'

    def start_process(self):
        step = 0
        thread_browser = None
        self.print_out("Started process...")

        # listen to user's typing
        try:
            if self.keyboardm is not None:
                thread = threading.Thread(target=self.keyboardm.listen, args=())
                thread.start()
        except Exception as e:
            self.api.push_log(
                self.config.get('laptop_id'),
                'Starting thread for user typing: %s (%s)' % (str(e), self.config.get('laptop_id'))
            )

        q = Queue()

        # start process to upload screenshots
        try:
            p = Process(target=run_main, args=(
                self.api, "test"
            ))
            p.start()
            p = Process(target=run_zip_upload, args=(
                self.api, "test"
            ))
            p.start()
        except Exception as e:
            self.api.push_log(
                self.config.get('laptop_id'),
                'Starting process to upload screenshots: %s (%s)' % (str(e), self.config.get('laptop_id'))
            )

        try:
            p = Process(target=server.run)
            p.start()
        except Exception as e:
            print ("keyboard init failed", e)
            traceback.print_exc()
            pass

        # main process to fetch data
        while True:
            try:
                if self.getConfig() and step >= self.secondsOfBrowserHistory:
                    self.print_out("run sub process: %s" % datetime.now().astimezone(pytz.utc).isoformat())

                    # fetch browser history and push data into the server
                    if self.last_run_time is None:
                        self.last_run_time = datetime.now().replace(
                            hour=0, minute=0, second=0, microsecond=0)
                        self.last_run_time = self.utc.localize(self.last_run_time)

                    p = Process(target=fetch_browser_history, args=(
                        self.api, self.last_run_time, q, self.config['laptop_id']
                    ))
                    p.start()
                    p.join()
                    self.last_run_time = q.get()

                    # press ESC to push typing data into the server
                    if self.keyboardm is not None:
                        self.keyboardm.fire()

                    upload_processes(self.api, self.config['laptop_id'])

                    step = 0
                else:
                    step += self.interval
            except Exception as e:
                self.api.push_log(
                    self.config.get('laptop_id'),
                    'Stop main process: %s (%s)' % (str(e), self.config.get('laptop_id'))
                )

            # sleep process
            time.sleep(self.interval)

    def print_out(self, value):
        if self.use_log:
            logging.info(value)
        else:
            print(value)


if __name__ == '__main__':
    freeze_support()
    main = Main()
    main.start_process()
