
from __future__ import absolute_import, print_function

import json

from flask import Flask
from flask import request

from . import scheduler

app = Flask(__name__)

@app.route("/long", methods=["POST"])
def start_long():
    spec = request.get_json(force=True)
    for i in xrange(spec["num"]):
        scheduler.TASKS.put(spec)

    return "ok"

@app.route("/stop")
def stop():
    for i in xrange(int(request.args.get("num"))):
        scheduler.CURRENT.stop_task()
    return "ok"
