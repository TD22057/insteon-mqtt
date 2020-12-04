import subprocess
from flask import Flask, Response
import sys


cli = sys.modules['flask.cli']
cli.show_server_banner = lambda *x: None
app = Flask(__name__)

@app.route('/')
def insteon_mqtt_webcli():
    def stream():
        output = subprocess.Popen(["../insteon-mqtt", "../config.yaml", "-h"],
                                  text=True,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT)
        yield "<pre style='white-space: pre-wrap;'>"
        line = output.stdout.readline()
        while line:
            yield line
            line = output.stdout.readline()
        yield "</pre>"
    return  Response(stream())

if __name__ == '__main__':
    # host='172.30.32.2' for hass ingest
    app.run(host='127.0.0.1', port='8099')
