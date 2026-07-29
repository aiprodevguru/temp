from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import requests
import json
from const import API_TOKEN, STREAM_STATUS, runtime_tmp_dir, server_ip
import os
import subprocess
from record import IMG_DIR, ZIP_DIR, LOG_DIR, HASH_FILE_PATH, get_window_ids, get_current_window
from db import dbGetZip
import psutil
import traceback

from api import get_server_api

origins = [
    "*",
]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def __init__(self):
    pass

def kill_process(pid):
    print ("killing process", pid)
    process = psutil.Process(pid)
    children = process.children(recursive=True)
    for child in children:
        print ('kill child', child)
        child.kill()
    process.kill()

def kill_processes_by_name(process_name):
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] == process_name:
                proc.kill()  # Or proc.kill() for forceful termination
                print(f"Process {proc.info['pid']} ({process_name}) terminated successfully.")
    except psutil.NoSuchProcess:
        print(f"No process with name {process_name} found.")

def update_stream_status(status):
    with open(os.path.join(runtime_tmp_dir, 'macAddress'), 'r') as f:
        macAddress = f.read()
        requests.post(
            "%s/rest/v1/client/connection" % get_server_api(),
            data=json.dumps({
                "macAddress": macAddress,
                "streamStatus": status
            }),
            headers={
                "x-hasura-admin-secret": API_TOKEN,
                "Content-Type": "application/json"
            },
            timeout=5
        )

def send_extension_data(data):
    with open(os.path.join(runtime_tmp_dir, 'macAddress'), 'r') as f:
        macAddress = f.read()
        requests.post(
            "%s/rest/v1/client/connection" % get_server_api(),
            data=json.dumps({
                "macAddress": macAddress,
                "extensionData": data
            }),
            headers={
                "x-hasura-admin-secret": API_TOKEN,
                "Content-Type": "application/json"
            },
            timeout=5
        )

def get_window_audio_device():
    cmd = "ffmpeg -list_devices true -f dshow -i dummy"
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout + '\n' + result.stderr
    line = [line for line in output.split('\n') if "(audio)" in line][0]
    audio_device_name = line.split('"')[1]
    return audio_device_name

def handle_start_stream(stream_host, laptop_id):
    handle_stop_stream()
    update_stream_status(STREAM_STATUS["STARTING"])
    try:
        cmd = ''
        if os.name == 'posix' and os.uname().sysname == 'Linux':
            cmd = f'ffmpeg -loglevel quiet -y -f x11grab -framerate 25 -i {os.environ["DISPLAY"]} -c:v libx264 -preset ultrafast -pix_fmt yuv420p -f rtsp -timeout 5000 rtsp://{stream_host}:8554/live/{str(laptop_id)}'
        if os.name == 'nt':
            cmd = f'%SystemRoot%\\Recorder\\ffmpeg -loglevel quiet -y -f gdigrab -framerate 25 -i desktop -f dshow -i audio="{get_window_audio_device()}" -c:v libx264 -preset ultrafast -crf 23 -c:a aac -b:a 128k -f rtsp -timeout 5000 "rtsp://{stream_host}:8554/live/{str(laptop_id)}"'
        if os.name == 'posix' and os.uname().sysname == 'Darwin':
            cmd = f'ffmpeg -loglevel quiet -y -f avfoundation -i "1:1" -r 25 -s 1280x720 -f rtsp rtsp://{stream_host}:8554/live/{str(laptop_id)}'
        running_stream_process = subprocess.Popen(cmd, shell=True)
        f = open(os.path.join(runtime_tmp_dir, 'stream_pid'), 'w')
        f.write(str(running_stream_process.pid))
        f.close()
        print ('stream pid', running_stream_process.pid)
        print (cmd)
        with open(LOG_DIR, 'a') as lf:
            lf.write(cmd + '\n')
        update_stream_status(STREAM_STATUS["STREAMING"])
    except Exception as e:
        print (e)
        traceback.print_exc()
        update_stream_status(STREAM_STATUS["IDLE"])
    return running_stream_process.pid

def handle_stop_stream():
    update_stream_status(STREAM_STATUS["STOPPING"])
    try:
        f = open(os.path.join(runtime_tmp_dir, 'stream_pid'), 'r')
        pid = int(f.read())
        f.close()
        print ('stopping stream process', pid)
        kill_process(pid)
        os.remove(os.path.join(runtime_tmp_dir, 'stream_pid'))
    except Exception as e:
        pass
    update_stream_status(STREAM_STATUS["IDLE"])


# Define the allowed IP address
# REQUEST_IP = get_server_api().split('//')[1]  # Change this to your desired IP address


@app.post("/start-stream")
async def start_stream(request: Request):
    # if request.client.host != REQUEST_IP:
    #     raise HTTPException(status_code=403, detail="Forbidden")
    try:
        data = await request.json()
        stream_host = get_server_api() or data.get('stream_host', server_ip)
        with open(os.path.join(runtime_tmp_dir, 'laptop_id'), 'r') as f:
            laptop_id = f.read()
            handle_start_stream(stream_host, laptop_id)
        # Process start stream command here
        return {"message": "Stream started"}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=403, detail=str(e))

@app.post("/stop-stream")
async def stop_stream():
    # if request.client.host != REQUEST_IP:
    #     raise HTTPException(status_code=403, detail="Forbidden")
    try:
        handle_stop_stream()
        # Process stop stream command here
        return {"message": "Stream stopped"}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=403, detail=str(e))

@app.post("/restart")
async def restart():
    # if request.client.host != REQUEST_IP:
    #     raise HTTPException(status_code=403, detail="Forbidden")
    try:
        if os.name == 'posix' and os.uname().sysname == 'Linux':
            handle_stop_stream()
            kill_processes_by_name('code1')
        if os.name == 'nt':
            # Process restart command here
            handle_stop_stream()
            kill_processes_by_name('code1.exe')
        return {"message": "something went wrong"}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=403, detail=str(e))

@app.get("/screen-status")
async def screen_status():
    img_files = os.listdir(IMG_DIR)
    zip_files = os.listdir(ZIP_DIR)
    db_records = dbGetZip(None)
    win_ids = get_window_ids()
    current_window = get_current_window()

    return {
        "img_files": img_files,
        "zip_files": zip_files,
        "db_records": db_records,
        "window_ids": win_ids,
        "current_window": current_window
    }

@app.get("/img-logs")
async def screen_status():
    with open(LOG_DIR, 'r') as f:
        return f.readlines()

@app.get("/img-hashes")
async def screen_status():
    with open(HASH_FILE_PATH, 'r') as f:
        return f.readlines()

@app.get("/clear-logs")
async def screen_status():
    with open(LOG_DIR, 'w') as f:
        return f.write('')


@app.get("/mac-address")
async def get_mac_address():
    with open(os.path.join(runtime_tmp_dir, 'macAddress'), 'r') as f:
        return f.read()

@app.post("/extension-data")
async def start_stream(request: Request):
    if request.client.host != "127.0.0.1":
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        data = await request.json()
        send_extension_data(data)
        return { "notified": True }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=403, detail=str(e))


def run(port=49151):
    uvicorn.run("server:app", host="0.0.0.0", port=port)

if __name__ == "__main__":
    run()
