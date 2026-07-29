# from browser_history_master import get_history, get_extension
import json
from datetime import datetime
import pytz

def fetch_browser_history(api, last_run_time, q, laptop_id=1):
    # Get all browser history: list of (datetime.datetime, url, title) tuples
    utc = pytz.UTC
    outputs = get_history()
    histories = outputs.histories
    print(f"Browser history ({len(histories)} records)")
    res = []
    item = {}

    histories.reverse()
    for history in histories:
        if history[0] is None or history[0] <= last_run_time:
            break

        dt = history[0]
        item = {
            'captured_at': dt.astimezone(pytz.utc).isoformat(),
            'content': history[1],
            'app_title': history[2],
            'type': history[3],
            'user': str(history[4]),
            'laptop_id': laptop_id
        }
        res.append(item)

    if len(res) > 0:
        # file_name = "data/res_%s.json" % (datetime.now().strftime("%H_%M"))
        # with open(file_name, "w") as fp:
        #     fp.write(json.dumps(res, indent=2))
        #     fp.close()

        print(api.upload_web_logs(json.dumps(res)))
    print("Completed successfully.")

    if len(histories) == 0:
        last_run_time = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0)
        last_run_time = utc.localize(last_run_time)
    else:
        last_run_time = histories[0][0]

    histories.clear()
    # outputs.clear()
    res.clear()

    q.put(last_run_time)

    fetch_extension_data(api, laptop_id)
    return last_run_time


def fetch_extension_data(api, laptop_id=1):
    output = get_extension(laptop_id=laptop_id)
    api.upload_extension(json.dumps(output))
