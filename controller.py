import json
import os
from typing import Any

import paho.mqtt.client as mqtt
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

BROKER = os.getenv("MQTT_BROKER", "broker.emqx.io")
PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPIC = os.getenv("MQTT_TOPIC", "ev/dashboard/control")

mqtt_client: mqtt.Client | None = None
mqtt_connected = False


def on_connect(client: mqtt.Client, userdata: Any, flags: Any, rc: int) -> None:
    global mqtt_connected
    mqtt_connected = rc == 0
    status = "connected" if mqtt_connected else "failed"
    print(f"[MQTT] {status} to {BROKER}:{PORT}")


def on_disconnect(client: mqtt.Client, userdata: Any, rc: int) -> None:
    global mqtt_connected
    mqtt_connected = False
    print(f"[MQTT] disconnected (rc={rc})")


def ensure_mqtt_client() -> mqtt.Client:
    global mqtt_client
    if mqtt_client is None:
        mqtt_client = mqtt.Client(client_id="flask-ev-controller", clean_session=True)
        mqtt_client.on_connect = on_connect
        mqtt_client.on_disconnect = on_disconnect
        mqtt_client.connect(BROKER, PORT, 60)
        mqtt_client.loop_start()
    return mqtt_client


def publish_payload(payload: dict[str, Any]) -> dict[str, Any]:
    client = ensure_mqtt_client()
    if not mqtt_connected and not client.is_connected():
        client.reconnect()

    payload_json = json.dumps(payload)
    client.publish(TOPIC, payload_json, qos=1, retain=False)
    return {"topic": TOPIC, "payload": payload}


@app.get("/")
def index() -> str:
    return render_template("controller.html")


@app.get("/health")
def health() -> tuple[Any, int]:
    return jsonify({
        "status": "ok",
        "mqtt": "connected" if mqtt_connected else "disconnected",
        "broker": BROKER,
        "port": PORT,
        "topic": TOPIC,
    }), 200


@app.post("/api/control")
def control() -> tuple[Any, int]:
    data = request.get_json(silent=True) or {}
    action = data.get("action")
    value = data.get("value")

    if action == "gear":
        gear_map = {"P": "A", "R": "B", "N": "C", "D": "D"}
        key = gear_map.get(str(value))
        if not key:
            return jsonify({"ok": False, "error": "invalid gear"}), 400
        payload = {"key": key}

    elif action == "toggle":
        payload = {"key": str(value)}

    elif action == "joystick":
        try:
            joystick_value = int(value)
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "invalid joystick value"}), 400
        payload = {"joystickY": joystick_value}

    else:
        return jsonify({"ok": False, "error": "unknown action"}), 400

    result = publish_payload(payload)
    return jsonify({"ok": True, **result}), 200


if __name__ == "__main__":
    ensure_mqtt_client()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
