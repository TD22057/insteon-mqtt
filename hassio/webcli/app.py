import sys
import time
import subprocess
from shlex import split
from flask import Flask, render_template
from flask_socketio import SocketIO, emit


cli = sys.modules['flask.cli']
cli.show_server_banner = lambda *x: None
app = Flask(__name__, template_folder=".")
app.config['output'] = None
app.config['cmd'] = []
socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template("index.html")

@socketio.on('message')
def handle_message(message):
    command = ['../../insteon-mqtt', '../../config.yaml']
    command.extend(split(message))
    app.config['cmd'].append(command)

@socketio.on('connect')
def test_connect():
    # If already defined, then skip
    if app.config["output"]:
        return
    socketio.start_background_task(target=insteon_mqtt_webcli)

def insteon_mqtt_webcli():
    while True:
        if len(app.config['cmd']):
            command = app.config['cmd'].pop()
            socketio.emit('message', "-->" + " ".join(command) + "\n")
            app.config["output"] = subprocess.Popen(command,
                                                    text=True,
                                                    stdout=subprocess.PIPE,
                                                    stderr=subprocess.STDOUT)
            line = app.config["output"].stdout.readline()
            while line:
                socketio.emit('message', line)
                line = app.config["output"].stdout.readline()
        else:
            time.sleep(.1)

if __name__ == '__main__':
    # host='172.30.32.2' for hass ingest
    socketio.run(app, host='127.0.0.1', port='8099')
