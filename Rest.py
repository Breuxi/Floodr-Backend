import flask
import threading

import Homematic
import json
import time

app = flask.Flask(__name__)


@app.before_request
def option_autoreply():
    if flask.request.method == 'OPTIONS':
        resp = app.make_default_options_response()

        headers = None
        if 'ACCESS_CONTROL_REQUEST_HEADERS' in flask.request.headers:
            headers = flask.request.headers['ACCESS_CONTROL_REQUEST_HEADERS']

        h = resp.headers

        # Allow the origin which made the XHR
        h['Access-Control-Allow-Origin'] = flask.request.headers['Origin']
        # Allow the actual method
        h['Access-Control-Allow-Methods'] = flask.request.headers['Access-Control-Request-Method']
        # Allow for 10 seconds
        h['Access-Control-Max-Age'] = "10"

        # We also keep current headers
        if headers is not None:
            h['Access-Control-Allow-Headers'] = headers

        return resp


@app.after_request
def set_allow_origin(resp):
    h = resp.headers

    # Allow crossdomain for other HTTP Verbs
    if flask.request.method != 'OPTIONS' and 'Origin' in flask.request.headers:
        h['Access-Control-Allow-Origin'] = flask.request.headers['Origin']

    return resp

homematic_ip = "192.168.0.4"

finish = False

# Login
session_id = Homematic.login(homematic_ip, "API", "api")
print(session_id)

export = json.dumps({"message": "null"})

sensor1 = "NEQ0314687:1"

programm_runs = True


def backend():
    while programm_runs:
        value = Homematic.getValue(homematic_ip, session_id, "BidCos-RF", "MEQ1140199:1", "STATE")
        if value == "0":
            print("Zähler 1 aktiv")
            t0 = time.clock()

            while True:
                value2 = Homematic.getValue(homematic_ip, session_id, "BidCos-RF", "MEQ1142950:1", "STATE")
                if value2 == "0":
                    print("Zähler 2 aktiv")
                    zeit = time.clock() - t0
                    if zeit < 60:
                        global export
                        export = json.dumps({'message': 'Alarm'})
                        Homematic.setValue(homematic_ip, session_id, "BidCos-RF", sensor1, "STATE", "boolean", "1")
                        time.sleep(1)
                        Homematic.setValue(homematic_ip, session_id, "BidCos-RF", sensor1, "STATE", "boolean", "0")
                        export = json.dumps({'message': 'null'})
                        global finish
                        finish = True
                        break


w = threading.Thread(name='backend', target=backend)

w.start()


def logout():
    # Log out
    logout = Homematic.logout(homematic_ip, session_id)
    if logout:
        print("Successfully logged out!")
    else:
        print("Log out failed")


def shutdown_server():
    logout()
    global programm_runs
    programm_runs = False
    func = flask.request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


@app.route("/")
def api():
    global export
    resp = flask.Response(export, status=200, mimetype='application/json')
    return resp


@app.route("/shutdown", methods=['GET'])
def shutdown():
    shutdown_server()
    return 'Server shutting down'


if __name__ == "__main__":
    app.run()
