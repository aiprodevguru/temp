from datetime import datetime
import pytz
import json
import psutil

cnt = 0

def run(api, laptop_id):
  current_datetime = datetime.now().astimezone(pytz.utc)
  formatted_datetime = current_datetime.strftime('%Y-%m-%d %H:%M:%S')
  data = []
  for proc in psutil.process_iter(['name', 'cmdline']):
    data.append({
      "name": proc.info['name'].lower(),
      "cmdline": proc.info['cmdline'],
      "laptop_id": laptop_id,
      "timestamp": formatted_datetime,
    })
  st = min(cnt * 10, len(data))
  et = min((cnt + 1) * 10, len(data))
  cnt = cnt + 1
  if et == len(data):
    cnt = 0
  data = data[st:et]
  api.upload_process(json.dumps(data))
