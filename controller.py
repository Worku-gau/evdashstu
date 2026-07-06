"""
EV Dashboard MQTT Controller - Industrial Grade

A production-ready Flask web controller for EV dashboard MQTT communication.
Features: robust MQTT handling, comprehensive logging, error recovery, and realistic driving demo.
"""

import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Any, Dict

import paho.mqtt.client as mqtt
from flask import Flask, jsonify, render_template, request

# ============================================================================
# LOGGING SETUP
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================
BROKER = os.getenv("MQTT_BROKER", "broker.emqx.io")
PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPIC = os.getenv("MQTT_TOPIC", "ev/dashboard/control")
MQTT_TIMEOUT = 60
RECONNECT_INTERVAL = 5
MAX_RECONNECT_ATTEMPTS = 10

# Application config
app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

# ============================================================================
# DEMO STATE
# ============================================================================
class DemoState:
    """Track demo execution state."""
    def __init__(self):
        self.running = False
        self.lock = threading.Lock()
    
    def start(self) -> bool:
        """Start demo if not already running."""
        with self.lock:
            if self.running:
                return False
            self.running = True
            return True
    
    def stop(self) -> None:
        """Stop demo."""
        with self.lock:
            self.running = False
    
    def is_running(self) -> bool:
        """Check if demo is running."""
        with self.lock:
            return self.running


demo_state = DemoState()

# ============================================================================
# MQTT STATE & MANAGEMENT
# ============================================================================
class MQTTManager:
    """Thread-safe MQTT connection manager."""

    def __init__(self):
        self.client: mqtt.Client | None = None
        self.connected = False
        self.reconnect_attempts = 0
        self.lock = threading.Lock()
        self.stats = {
            "messages_sent": 0,
            "messages_failed": 0,
            "connection_time": None,
            "last_message_time": None,
        }

    def connect(self) -> bool:
        """Establish MQTT connection with exponential backoff."""
        with self.lock:
            if self.client is not None and self.connected:
                return True

            try:
                self.client = mqtt.Client(
                    client_id="flask-ev-controller-v2",
                    clean_session=True,
                    protocol=mqtt.MQTTv311,
                )
                self.client.on_connect = self._on_connect
                self.client.on_disconnect = self._on_disconnect
                self.client.on_message = self._on_message
                self.client.on_publish = self._on_publish

                logger.info(f"[MQTT] Connecting to {BROKER}:{PORT}...")
                self.client.connect(BROKER, PORT, keepalive=MQTT_TIMEOUT)
                self.client.loop_start()
                return True

            except Exception as e:
                logger.error(f"[MQTT] Connection failed: {e}")
                return False

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: Any,
        rc: int,
    ) -> None:
        """Handle MQTT connect event."""
        if rc == 0:
            self.connected = True
            self.reconnect_attempts = 0
            self.stats["connection_time"] = datetime.now().isoformat()
            logger.info(f"[MQTT] ✓ Connected to {BROKER}:{PORT}")
        else:
            self.connected = False
            logger.warning(f"[MQTT] Connection failed with code {rc}")

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int) -> None:
        """Handle MQTT disconnect event."""
        self.connected = False
        if rc != 0:
            logger.warning(f"[MQTT] Unexpected disconnection (code {rc}). Reconnecting...")
            self.reconnect_attempts += 1
            if self.reconnect_attempts < MAX_RECONNECT_ATTEMPTS:
                time.sleep(min(RECONNECT_INTERVAL * self.reconnect_attempts, 30))
                self.connect()

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: Any) -> None:
        """Handle incoming MQTT messages (unused in controller)."""
        pass

    def _on_publish(
        self,
        client: mqtt.Client,
        userdata: Any,
        mid: int,
    ) -> None:
        """Handle publish confirmation."""
        self.stats["last_message_time"] = datetime.now().isoformat()

    def publish(self, payload: Dict[str, Any]) -> tuple[bool, str]:
        """Publish payload to MQTT topic."""
        try:
            if not self.connected:
                self.connect()

            payload_json = json.dumps(payload)
            result = self.client.publish(TOPIC, payload_json, qos=1, retain=False)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.stats["messages_sent"] += 1
                logger.debug(f"[MQTT] Published: {payload}")
                return True, "Published"
            else:
                self.stats["messages_failed"] += 1
                error_msg = mqtt.error_string(result.rc)
                logger.error(f"[MQTT] Publish failed: {error_msg}")
                return False, error_msg

        except Exception as e:
            self.stats["messages_failed"] += 1
            logger.error(f"[MQTT] Publish exception: {e}")
            return False, str(e)

    def disconnect(self) -> None:
        """Safely disconnect MQTT."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            logger.info("[MQTT] Disconnected")


mqtt_manager = MQTTManager()

# ============================================================================
# FLASK ROUTES
# ============================================================================


@app.before_request
def before_request() -> None:
    """Initialize MQTT on first request."""
    if not mqtt_manager.connected and mqtt_manager.client is None:
        mqtt_manager.connect()


@app.route("/", methods=["GET"])
def index() -> str:
    """Serve main UI."""
    return render_template("controller.html")


@app.route("/api/health", methods=["GET"])
def health() -> tuple[Dict[str, Any], int]:
    """Health check endpoint."""
    return jsonify(
        {
            "status": "healthy",
            "mqtt": {
                "connected": mqtt_manager.connected,
                "broker": BROKER,
                "port": PORT,
                "topic": TOPIC,
            },
            "stats": mqtt_manager.stats,
            "timestamp": datetime.now().isoformat(),
        }
    ), 200


@app.route("/api/control", methods=["POST"])
def control() -> tuple[Dict[str, Any], int]:
    """Handle vehicle control commands."""
    try:
        data = request.get_json(silent=True) or {}
        action = data.get("action", "").strip()
        value = data.get("value")

        if not action:
            logger.warning("[API] Missing action parameter")
            return jsonify({"ok": False, "error": "action required"}), 400

        # Gear control
        if action == "gear":
            gear_map = {"P": "A", "R": "B", "N": "C", "D": "D"}
            gear = str(value).upper()
            if gear not in gear_map:
                logger.warning(f"[API] Invalid gear: {gear}")
                return jsonify({"ok": False, "error": "invalid gear"}), 400
            payload = {"key": gear_map[gear]}
            logger.info(f"[API] Gear shift: {gear}")

        # Light/indicator toggles
        elif action == "toggle":
            valid_keys = {"1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "*", "#"}
            key = str(value)
            if key not in valid_keys:
                logger.warning(f"[API] Invalid toggle key: {key}")
                return jsonify({"ok": False, "error": "invalid key"}), 400
            payload = {"key": key}
            logger.info(f"[API] Toggle: {key}")

        # Throttle/joystick control
        elif action == "joystick":
            try:
                slider_val = int(value)
                if not 0 <= slider_val <= 100:
                    raise ValueError("Out of range")
                # Map 0-100 to 0-4095 joystick range
                joystick_value = int(2048 - (slider_val - 50) * 40.96)
                joystick_value = max(0, min(4095, joystick_value))
                payload = {"joystickY": joystick_value}
                logger.debug(f"[API] Throttle: {slider_val}% → {joystick_value}")
            except (TypeError, ValueError) as e:
                logger.warning(f"[API] Invalid joystick value: {e}")
                return jsonify({"ok": False, "error": "invalid joystick value"}), 400

        else:
            logger.warning(f"[API] Unknown action: {action}")
            return jsonify({"ok": False, "error": "unknown action"}), 400

        # Publish to MQTT
        success, msg = mqtt_manager.publish(payload)
        if not success:
            return jsonify({"ok": False, "error": msg}), 503

        return jsonify(
            {
                "ok": True,
                "action": action,
                "payload": payload,
                "timestamp": datetime.now().isoformat(),
            }
        ), 200

    except Exception as e:
        logger.exception(f"[API] Control error: {e}")
        return jsonify({"ok": False, "error": "server error"}), 500


@app.route("/api/demo", methods=["POST"])
def demo() -> tuple[Dict[str, Any], int]:
    """Start realistic driving demo."""
    try:
        if not demo_state.start():
            return jsonify({"ok": False, "error": "demo already running"}), 409
        
        logger.info("[DEMO] Starting realistic car cruising experience...")
        thread = threading.Thread(target=_run_demo, daemon=True)
        thread.start()
        return jsonify(
            {
                "ok": True,
                "message": "Demo started",
                "duration": "~30 seconds",
                "timestamp": datetime.now().isoformat(),
            }
        ), 202
    except Exception as e:
        logger.exception(f"[DEMO] Error: {e}")
        demo_state.stop()
        return jsonify({"ok": False, "error": "demo failed"}), 500


@app.route("/api/demo/stop", methods=["POST"])
def demo_stop() -> tuple[Dict[str, Any], int]:
    """Stop running demo."""
    try:
        if not demo_state.is_running():
            return jsonify({"ok": False, "error": "demo not running"}), 400
        
        logger.info("[DEMO] Stopping demo...")
        demo_state.stop()
        mqtt_manager.publish({"key": "A"})  # Park
        mqtt_manager.publish({"joystickY": 2048})  # Neutral throttle
        
        return jsonify(
            {
                "ok": True,
                "message": "Demo stopped",
                "timestamp": datetime.now().isoformat(),
            }
        ), 200
    except Exception as e:
        logger.exception(f"[DEMO] Stop error: {e}")
        return jsonify({"ok": False, "error": "stop failed"}), 500


def _run_demo() -> None:
    """Execute realistic driving demo sequence."""
    try:
        steps = [
            ("Park", 1, {"key": "A"}),
            ("Enable seatbelt", 1, {"key": "6"}),
            ("Shift to Neutral", 0.5, {"key": "C"}),
            ("Shift to Drive", 1, {"key": "D"}),
        ]

        for name, delay, payload in steps:
            if not demo_state.is_running():
                logger.info("[DEMO] Stopped by user")
                return
            logger.info(f"[DEMO] {name}")
            mqtt_manager.publish(payload)
            time.sleep(delay)

        logger.info("[DEMO] Accelerating...")
        for speed in range(0, 51, 5):
            if not demo_state.is_running():
                logger.info("[DEMO] Stopped by user")
                return
            payload = {"joystickY": int(2048 - (speed - 50) * 40.96)}
            mqtt_manager.publish(payload)
            time.sleep(0.3)

        if demo_state.is_running():
            logger.info("[DEMO] Merging left")
            mqtt_manager.publish({"key": "1"})
            time.sleep(2)
            mqtt_manager.publish({"key": "1"})
            time.sleep(1)

        logger.info("[DEMO] Cruising at highway speed")
        for _ in range(5):
            if not demo_state.is_running():
                logger.info("[DEMO] Stopped by user")
                return
            payload = {"joystickY": int(2048 - (80 - 50) * 40.96)}
            mqtt_manager.publish(payload)
            time.sleep(0.5)

        if demo_state.is_running():
            logger.info("[DEMO] Exiting highway")
            mqtt_manager.publish({"key": "2"})
            time.sleep(2)
            mqtt_manager.publish({"key": "2"})
            time.sleep(1)

        logger.info("[DEMO] Slowing down")
        for speed in range(80, -1, -5):
            if not demo_state.is_running():
                logger.info("[DEMO] Stopped by user")
                return
            payload = {"joystickY": int(2048 - (speed - 50) * 40.96)}
            mqtt_manager.publish(payload)
            time.sleep(0.3)

        if demo_state.is_running():
            logger.info("[DEMO] Parking")
            mqtt_manager.publish({"key": "A"})
            time.sleep(1)
            logger.info("[DEMO] ✓ Complete!")
    finally:
        demo_state.stop()


# ============================================================================
# ERROR HANDLERS
# ============================================================================


@app.errorhandler(404)
def not_found(e: Any) -> tuple[Dict[str, str], int]:
    """404 error handler."""
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(e: Any) -> tuple[Dict[str, str], int]:
    """500 error handler."""
    logger.error(f"[Server] 500 Error: {e}")
    return jsonify({"error": "Internal server error"}), 500


# ============================================================================
# SHUTDOWN HANDLERS
# ============================================================================


@app.teardown_appcontext
def shutdown(exception: Any = None) -> None:
    """Cleanup on shutdown."""
    mqtt_manager.disconnect()


# ============================================================================
# MAIN
# ============================================================================


if __name__ == "__main__":
    try:
        logger.info("=" * 70)
        logger.info("EV Dashboard MQTT Controller v2.0")
        logger.info("=" * 70)
        logger.info(f"Starting Flask server on 0.0.0.0:5000")
        logger.info(f"MQTT Broker: {BROKER}:{PORT}")
        logger.info(f"Topic: {TOPIC}")
        logger.info("=" * 70)

        app.run(
            host="0.0.0.0",
            port=int(os.getenv("PORT", "5000")),
            debug=False,
            use_reloader=False,
        )
    except KeyboardInterrupt:
        logger.info("\n[Main] Shutting down...")
    except Exception as e:
        logger.exception(f"[Main] Fatal error: {e}")
    finally:
        mqtt_manager.disconnect()
