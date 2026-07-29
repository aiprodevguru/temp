# This file is screen record process for windows.

# input params.
# - screenshot_interval - 10s - take screenshot every 10 seconds
# - zip_interval - 60s - make zip file of created screenshots efvery minute
# - ftp_url - ftp server url to save files
# - api_url - http api url to submit metadata
# workflows
#   1. runs infinite loop every screenshot_interval seconds and take screenshots
#   2. runs infinite loop every zip_interval seconds, process dup, empty files
#   3. upload via ftp, api

from PIL import Image

from datetime import datetime
import subprocess
import time
import re
import os
import json
import imagehash
import paramiko
import traceback
import pytz
from multiprocessing import Process
from const import prevent_list, runtime_tmp_dir
from utils import zip_directory, delete_files_in_directory
from db import dbCreateZip, dbGetZip, dbRemoveZip
import random

from ftplib import FTP
from api import get_server_ip


IMG_DIR = os.path.join(runtime_tmp_dir, "imgs")
ZIP_DIR = os.path.join(runtime_tmp_dir, "zips")
LOG_DIR = os.path.join(runtime_tmp_dir, 'img_log.txt')
HASH_FILE_PATH = os.path.join(runtime_tmp_dir, 'hashes.txt')

if os.name == 'nt':
    import pygetwindow as gw
elif os.name == 'posix':
    if os.uname().sysname == 'Darwin':
        import Quartz
        import Quartz.CoreGraphics as CG
        from AppKit import NSWorkspace
        pass
    elif os.uname().sysname == 'Linux':
        # subprocess.run('sudo apt-get install -y imagemagick wmctrl')
        pass

def check_dup(hash_value):
    try:
        hash_file = HASH_FILE_PATH
        # Open the file in read mode to check if hash exists
        with open(hash_file, 'r') as file:
            # Read all hashes into a set for efficient lookup
            existing_hashes = set(line.strip() for line in file)

        # Check if the given hash is already in the set of hashes
        if hash_value in existing_hashes:
            return True
        else:
            # If hash doesn't exist, add it to the file
            with open(hash_file, 'a') as file:
                file.write(hash_value + '\n')
            return False
    except FileNotFoundError:
        # If the hash file doesn't exist, create a new file and add the hash
        with open(hash_file, 'w') as file:
            file.write(hash_value + '\n')
        return False

def need_prevent(win_title):
    for item in prevent_list:
        if win_title.find(item) != -1:
            return True
    return False

def get_current_window():
    if os.name == 'nt':
        w = gw.getActiveWindow()
        if w is not None:
            return w.title
        else:
            return "-"
    elif os.name == 'posix' and os.uname().sysname == 'Linux':
        result = subprocess.run(['xdotool', 'getactivewindow', 'getwindowname'], stdout=subprocess.PIPE)
        return result.stdout.decode().strip()
    return "_"

def get_window_ids():
    # get list of windows per OS
    if os.name == 'nt':
        # on windows we just get window titles using pygetwindow
        full_capture = ["full_capture"]
        w = gw.getActiveWindow()
        if w is not None and need_prevent(w.title):
            full_capture = []
        return gw.getAllTitles() + full_capture + ["current_active"]
    elif os.name == 'posix' and os.uname().sysname == 'Linux':
        # on linux we use wmctrl -l command
        command = ['wmctrl', '-l']
        result = subprocess.run(command, capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        window_ids = [line.split()[0]+'::_::'+' '.join(line.split()[3:]) for line in lines if line != ""]
        result = subprocess.run(['xdotool', 'getactivewindow', 'getwindowname'], stdout=subprocess.PIPE)
        full_capture = ["root::_::full_capture"]
        if need_prevent(result.stdout.decode().strip()):
            full_capture = []
        return window_ids + full_capture
    elif os.name == 'posix' and os.uname().sysname == 'Darwin':
        window_list = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)
        if window_list is None:
            return []
        full_capture = ["full_capture"]
        curr_app = NSWorkspace.sharedWorkspace().frontmostApplication()
        curr_pid = NSWorkspace.sharedWorkspace().activeApplication()['NSApplicationProcessIdentifier']
        for window in window_list:
            pid = window['kCGWindowOwnerPID']
            if curr_pid == pid:
                if need_prevent(window.get('kCGWindowName', u'Unknown')):
                    full_capture = []
                break
        return window_list + full_capture

def take_screenshot(win, formatted_datetime, api, laptop_id):
    try:
        # Take screenshot per OS and return filename, filepath
        if os.name == 'posix' and os.uname().sysname == 'Linux':
            # On linux we use imagemagick's import command
            [win_id, win_title] = win.split('::_::')
            if need_prevent(win_title):
                return [None, None, None, None]
            filename = replace_special_chars(win_title) + '__' + formatted_datetime + '.jpg'
            filepath = os.path.join(IMG_DIR, filename)
            import_command = ' '.join([
                'import',
                '-silent',
                '-window',
                win_id, filepath
            ])
            process = subprocess.run(import_command, shell=True)
            win_type = re.split(r'\||-', win_title)[-1].strip()
            return [filepath, filename, win_type, win_title]
        if os.name == 'nt':
            # On windows we use ffmpeg
            if need_prevent(win):
                return [None, None, None, None]
            filename = replace_special_chars(win) + '__' + formatted_datetime + '.jpg'
            filepath = os.path.join(IMG_DIR, filename)
            win_type = re.split(r'\||-', win)[-1].strip()
            crop_param = ''
            if win == 'current_active':
                w = gw.getActiveWindow()
                if w is None:
                    return [None, None, None, None]
                crop_param = f'-offset_x {str(w.topleft.x)} -offset_y {str(w.topleft.y)} -video_size {str(w.width)}x{str(w.height)}'
                filename = replace_special_chars(w.title) + '_current_active__' + formatted_datetime + '.jpg'
                filepath = os.path.join(IMG_DIR, filename)
                win_type = re.split(r'\||-', w.title)[-1].strip()
            ffmpeg_command = ' '.join([
                'ffmpeg', '-loglevel quiet',
                '-f', 'gdigrab', '-draw_mouse 0',
                crop_param,
                '-i', ('desktop' if win in ["full_capture", "current_active"] else 'title="' + win + '"'),
                '-frames:v', '1',
                filepath
            ])
            subprocess.run(ffmpeg_command)
            return [filepath, filename, win_type, win]
        if os.name == 'posix' and os.uname().sysname == 'Darwin':
            if win == "full_capture":
                filename = 'full_capture__' + formatted_datetime + '.jpg'
                filepath = os.path.join(IMG_DIR, filename)
                process = subprocess.run("screencapture -x " + filepath, shell=True)
                win_type = "main"
                return [filepath, filename, win_type, win]
            image = CG.CGWindowListCreateImage(
                CG.CGRectInfinite,
                CG.kCGWindowListOptionIncludingWindow,
                win["kCGWindowNumber"],
                CG.kCGWindowImageDefault
            )
            window_name = win.get("kCGWindowName", "") or win.get("kCGWindowOwnerName", "") or "no_name"
            print (window_name, win["kCGWindowNumber"], image)
            if need_prevent(window_name) or image is None:
                return [None, None, None, None]
            width = CG.CGImageGetWidth(image)
            height = CG.CGImageGetHeight(image)
            bpr = CG.CGImageGetBytesPerRow(image)
            pixeldata = CG.CGDataProviderCopyData(CG.CGImageGetDataProvider(image))
            pilimg = Image.frombuffer("RGBA", (width, height), pixeldata, "raw", "RGBA", bpr, 1)
            width, height = pilimg.size
            if width < 100 or height < 100:
                return [None, None, None, None]
            filename = replace_special_chars(window_name) + '__' + formatted_datetime + '.png'
            filepath = os.path.join(IMG_DIR, filename)
            win_type = win["kCGWindowOwnerName"]
            pilimg.save(filepath)
            return [filepath, filename, win_type, window_name]
    except Exception as e:
        print ('capture fail!', e, win)
        traceback.print_exc()
        api.push_log(
            laptop_id,
            'Take screenshot failed: %s (%s)' % (str(e), laptop_id)
        )
        return [None, None, None, None]

"""
not using sftp for now due to ... server
"""
def upload_file_to_sftp(host, port, username, password, local_file_path, remote_file_path):
    # Establish an SFTP connection
    transport = paramiko.Transport((host, int(port))) # int(port)
    transport.connect(username=username, password=password)
    # sftp = paramiko.SFTPClient.from_transport(transport)
    sftp = paramiko.SFTPClient.from_transport(transport)

    # Create remote directories recursively if they don't exist
    directories_to_create = remote_file_path.split('/')[:-1]
    current_directory = '/'
    for directory in directories_to_create:
        current_directory += directory + '/'
        try:
            sftp.listdir(current_directory)
        except IOError:
            sftp.mkdir(current_directory)

    # Upload the file
    print (local_file_path)
    sftp.put(local_file_path, remote_file_path)
    print (remote_file_path)

    # Close the SFTP session
    sftp.close()
    transport.close()

def upload_file_to_ftp(host, port, username, password, local_file_path, remote_file_path):
    ftp = FTP()
    ftp.connect(host, int(port))
    ftp.login(user=username, passwd=password)

    current_directory = '/'
    directories_to_create = [f for f in remote_file_path.split('/')[:-1] if f]
    for directory in directories_to_create:
        current_directory += directory + '/'
        try:
            ftp.mkd(current_directory)
            ftp.sendcmd(f"SITE CHMOD 775 {current_directory}")
        except Exception as e:
            print (e)

    with open(local_file_path, 'rb') as file:
        ftp.storbinary(f'STOR {remote_file_path}', file)

    ftp.quit()

def create_directory_if_not_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def replace_special_chars(input_string):
    # Replace spaces and special characters with underscores
    output_string = re.sub(r'[\s\W]+', '_', input_string)
    return output_string[:100]

def run_upload_zips(api, _):
    while True:
        config = api.getConfig()
        if config is None:
            time.sleep(1)
            api.get_config()
            continue

        zip_interval = config.get('secondsOfUploadZipFile', 60)
        laptop_id = config['laptop_id']
        ftp_host = get_server_ip()
        ftp_port = config['ftpServerPort']
        ftp_username = config['ftpUserName']
        ftp_password = config['ftpPassword']

        db_records = dbGetZip(None)
        print ('_' * 100)
        print (len(db_records))
        max_records = 50
        if len(db_records) > max_records:
            for to_del in db_records[max_records:]:
                zip_path = to_del["zip_file_path"]
                dbRemoveZip(to_del["id"])
                try:
                    os.remove(zip_path)
                except:
                    pass

        for record in db_records[:max_records]:
            zip_path = record["zip_file_path"]
            req_payload = record["request_payload"]
            upload_path = record["upload_file_path"]

            print ('processing record > ', zip_path, upload_path)

            retries = 3
            st = time.time()
            print ('uploading...', ftp_host, ftp_port, ftp_username, ftp_password, zip_path, req_payload, upload_path)
            uploaded = False
            while retries > 0:
                try:
                    upload_file_to_ftp(ftp_host, ftp_port, ftp_username, ftp_password, zip_path, upload_path)
                    print (req_payload)
                    response = api.upload_screenshot(req_payload)
                    et = time.time()
                    print ('upload finished', et - st, 'seconds')
                    print (response)

                    os.remove(zip_path)
                    dbRemoveZip(record["id"])
                    print ('Upload succeeded', zip_path)
                    uploaded = True
                    break
                except Exception as e:
                    traceback.print_exc()
                    api.push_log(
                        laptop_id,
                        'upload try failed!: %s (%s)' % (str(e), laptop_id)
                    )
                retries -= 1
                time.sleep(5)
            if uploaded is True:
                continue

            et = time.time()

            api.push_log(
                laptop_id,
                'upload failed! after %s seconds (%s)' % (str(et - st), laptop_id)
            )
            try:
                os.remove(zip_path)
            except Exception as e:
                pass

            dbRemoveZip(record["id"])

        time.sleep(zip_interval + 5)
        api.get_config()


def run_screenshots(api, _):
    create_directory_if_not_exists(IMG_DIR)
    create_directory_if_not_exists(ZIP_DIR)
    zip_tick = 0
    screen_tick = 0
    images = []
    captured_images = []

    while True:
        config = api.getConfig()
        if config is None:
            time.sleep(1)
            api.get_config()
            continue

        screenshot_interval = config.get('secondsOfScreenshot', 10)
        zip_interval = config.get('secondsOfUploadZipFile', 60)
        client_id = config.get('client_id', 0)
        laptop_id = config['laptop_id']
        ftp_root = config['ftpServerRootPath']
        image_diff_threshold = int(config.get('image_diff_threshold', 3))

        current_datetime = datetime.now().astimezone(pytz.utc)
        formatted_datetime = current_datetime.strftime('%Y-%m-%d_%H-%M-%S')
        formatted_date = current_datetime.strftime('%Y-%m-%d')

        if os.name == 'nt' and screen_tick > random.randint(0, int(screenshot_interval / 2)):
            if len(captured_images) == 0:
                [filepath, filename, app_type, win_title] = take_screenshot("current_active", formatted_datetime, api, laptop_id)
                if filepath is None:
                    continue
                captured_images.append([filepath, filename, app_type, win_title])

        if screen_tick > random.randint(int(screenshot_interval / 2), screenshot_interval):
            try:
                # take screenshot every screenshot_interval
                window_ids = get_window_ids()
                if window_ids is None:
                    continue
                for win in list(set(window_ids)):
                    if win != "":
                        try:
                            screen_result = take_screenshot(win, formatted_datetime, api, laptop_id)
                            if screen_result is None:
                                continue
                            [filepath, filename, app_type, win_title] = screen_result
                            if filepath is None:
                                continue
                            captured_images.append([filepath, filename, app_type, win_title])
                        except Exception as e:
                            api.push_log(
                                config.get('laptop_id'),
                                'Fetch images for individual application and compare images: %s (%s)' % (str(e), config.get('laptop_id'))
                            )
                for [filepath, filename, app_type, win_title] in captured_images:
                    try:
                        is_dup = False
                        with open(filepath, 'rb') as f:
                            img = Image.open(f)
                            img.filename = filename
                            img.captured_at = current_datetime.isoformat()
                            img.type = "main" if filename.startswith("full_capture") else app_type
                            img.hash = str(imagehash.dhash(img))
                            img.win_title = win_title

                            with open(LOG_DIR, 'a') as lf:
                                lf.write(str(img.hash) + ':' + img.filename + '\n')

                            for item in images:
                                if item.hash == img.hash:
                                    is_dup = True
                                    break
                            is_dup = is_dup or check_dup(img.hash)

                            if is_dup is False:
                                images.append(img)

                        if is_dup is True:
                            os.remove(filepath)
                    except Exception as e:
                        print (e)
                        pass
                screen_tick = 0
                captured_images = []
            except Exception as e:
                traceback.print_exc()
                print ('_' * 100)
                api.push_log(
                    config.get('laptop_id'),
                    'screenshot interval error: %s (%s)' % (str(e), config.get('laptop_id'))
                )


        if zip_tick > random.randint(screenshot_interval + 1, zip_interval):
            try:
                api.get_config()
                # check dup & zip & upload every zip_interval
                if len(images) == 0:
                    zip_tick = 0
                    time.sleep(1)
                    continue
                new_item_unique = []
                img_req_payload = []
                for new_item in images:
                    img_req_payload.append({
                        "name": new_item.filename,
                        "captured_at": new_item.captured_at,
                        "type": new_item.type,
                        "app_title": new_item.win_title
                    })
                    in_cache = check_dup(new_item.hash)
                    if in_cache is False:
                        new_item_unique.append(new_item.hash)

                zip_file_path = os.path.join(ZIP_DIR, formatted_datetime + ".zip")

                zip_directory(IMG_DIR, zip_file_path)

                images = []
                delete_files_in_directory(IMG_DIR)

                upload_file_path = ftp_root + '/' + str(laptop_id) + '/' + formatted_date + '/' + formatted_datetime+'.zip'

                request_payload = {
                    "path": upload_file_path,
                    "files": img_req_payload,
                    "laptop_id": laptop_id
                }
                if client_id != 0:
                    request_payload['client_id'] = client_id

                request_payload = json.dumps(request_payload)

                dbCreateZip({
                    "zip_file_path": zip_file_path,
                    "request_payload": request_payload,
                    "upload_file_path": upload_file_path,
                    "created_at": datetime.now()
                })

                need_screenshot = True
                zip_tick = 0
                continue

            except Exception as e:
                api.push_log(
                    config.get('laptop_id'),
                    'making Zip error: %s (%s)' % (str(e), config.get('laptop_id'))
                )

        screen_tick = screen_tick + 1
        zip_tick = zip_tick + 1
        time.sleep(1)


def run_main (api, _):
    while True:
        try:
            api.get_config()
            p = Process(target=run_screenshots, args=(
                api, "test"
            ))
            p.start()
            p.join()
        except Exception as e:
            print("Recorder Process error:", e)
            config = api.getConfig()
            api.push_log(
                config.get('laptop_id'),
                'Recorder Process error: %s (%s)' % (str(e), config.get('laptop_id'))
            )
        finally:
            print("Restarting process...")
        time.sleep(1)


def run_zip_upload (api, _):
    while True:
        try:
            api.get_config()
            p = Process(target=run_upload_zips, args=(
                api, "test"
            ))
            p.start()
            p.join()
        except Exception as e:
            print("Recorder Process error:", e)
            config = api.getConfig()
            api.push_log(
                config.get('laptop_id'),
                'Recorder Process error: %s (%s)' % (str(e), config.get('laptop_id'))
            )
        finally:
            print("Restarting process...")
        time.sleep(1)

