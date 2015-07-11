#!/usr/bin/python

from flask import Flask, request, render_template, redirect, jsonify
import threading, time
import RPi.GPIO as GPIO
import logging

ENABLE_PIN = 22
ZOOM_STEP_PIN = 25
ZOOM_DIR_PIN = 18
FOCUS_STEP_PIN = 17
FOCUS_DIR_PIN = 4
MOVE_STEP_PIN = 24
MOVE_DIR_PIN = 23

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)
zoom_thread = None

class StepMotor(threading.Thread):
    def __init__(self, pin, step_data, forward, direction_pin):
        self._stop = False
        self._pin = pin
        self._step_data = step_data.split(',')
        self._forward = forward
	self._direction_pin = direction_pin
        threading.Thread.__init__(self)
        return

    def run(self):
        GPIO.setup(self._pin, GPIO.OUT)
        GPIO.setup(self._direction_pin, GPIO.OUT)
        if self._forward:
            GPIO.output(self._direction_pin, True)
        else:
            GPIO.output(self._direction_pin, False)
        for stage in self._step_data:
            sps = int(stage.split(':')[0])
            steps = int(stage.split(':')[1])
            step_count = 0
            while step_count < steps:
                if self._stop:
                   break
                GPIO.output(self._pin, False)
                GPIO.output(self._pin, True)
                time.sleep((float(1000.0)/float(sps))/float(1000.00))
                step_count += 1
            if self._stop:
               break

@app.route("/")
def index():
    return render_template('index.html')


@app.route("/start", methods=["POST"])
def start():
    # enable easydriver
    GPIO.output(ENABLE_PIN, False)
    global zoom_thread
    global focus_thread
    global move_thread
    if request.form['zoom_direction'] == "forwards":
        zoom_forward = True
    else:
        zoom_forward = False
    if request.form['focus_direction'] == "forwards":
        focus_forward = True
    else:
        focus_forward = False
    if request.form['move_direction'] == "forwards":
        move_forward = True
    else:
        move_forward = False
    print("Zoom: {0} steps per second - FWD:{1}".format(request.form['zoom_speed'], zoom_forward))
    print("Focus: {0} steps per second - FWD:{1}".format(request.form['focus_speed'], focus_forward))
    print("Move: {0} steps per second - FWD:{1}".format(request.form['move_speed'], move_forward))
    zoom_thread = StepMotor(ZOOM_STEP_PIN,
			    request.form['zoom_speed'],
			    zoom_forward,
			    ZOOM_DIR_PIN)
    focus_thread = StepMotor(FOCUS_STEP_PIN,
			    request.form['focus_speed'],
			    focus_forward,
			    FOCUS_DIR_PIN)
    move_thread = StepMotor(MOVE_STEP_PIN,
                            request.form['move_speed'],
                            move_forward,
                            MOVE_DIR_PIN)
    with open('/var/push_pull/config/{}.cfg'.format(request.form['config_id']), 'w') as config_file:
        config_file.write("{}\n{}\n{}\n{}\n{}\n{}".format(
		request.form['zoom_speed'],
                "forward" if zoom_forward else "reverse",
		request.form['focus_speed'],
                "forward" if focus_forward else "reverse",
		request.form['move_speed'],
                "forward" if move_forward else "reverse"))
    zoom_thread.start()
    focus_thread.start()
    move_thread.start()
    return render_template('stop.html')

@app.route("/load/<config_id>", methods=['GET'])
def load_config(config_id):
    config_dict = {}
    with open('/var/push_pull/config/{}.cfg'.format(config_id), 'r') as config_file:
        config = config_file.readlines()
        config_dict = {
            "zoom": config[0].strip(),
            "zoom_dir": config[1].strip(),
            "focus": config[2].strip(),
            "focus_dir": config[3].strip(),
            "move": config[4].strip(),
            "move_dir": config[5].strip()
        }
    print config_dict
    return jsonify(config_dict)

@app.route("/stop", methods=["POST"])
def stop():
    # disable easydriver
    GPIO.output(ENABLE_PIN, True)
    global zoom_thread
    zoom_thread._stop = True
    zoom_thread.join()
    global focus_thread
    focus_thread._stop = True
    focus_thread.join()
    global move_treah
    move_thread._stop = True
    move_thread.join()
    return redirect('/', code="302")

if __name__ == "__main__":
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(ENABLE_PIN, GPIO.OUT)
    app.run(host='0.0.0.0', debug=True)
