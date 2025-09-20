import json
import time
import os
import sys

payload = {
    "message": {
        "topic": "news",
        "notification": {
            "title": os.getenv("TITLE", "Proxies Updated"),
            "body": os.getenv("BODY", ""),
        },
        "data": {
            "update_type": "proxy_list",
            "proxy_count": str(os.getenv("PROXY_COUNT", "0")),
            "timestamp": str(int(time.time())),
        },
    }
}

json.dump(payload, sys.stdout)
