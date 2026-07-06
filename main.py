import sys
import os
import json
import paho.mqtt.client as mqtt
from PySide6.QtCore import QObject, Property, Signal, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

# Fix Image Paths
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# MQTT CONFIGURATION
BROKER = "broker.emqx.io"
PORT = 1883
TOPIC = "ev/dashboard/control"

class VehicleState(QObject):
    stateChanged = Signal()

    def __init__(self):
        super().__init__()

        # --- VEHICLE PHYSICS DATA ---
        self._speed = 0.0
        self._power = 0.0
        self._range = 300
        self._soc = 78
        self._gear = "P"
        self._brakes = False
        self._charging = False
        self._hazard = False
        
        # --- INPUT BUFFERS ---
        self.last_joystick_y = 2048 # Center position (approx)
        self.max_speed = 200.0
        
        # --- ICON STATES ---
        self.icon_states = {
            "leftTurn": False, "rightTurn": False, 
            "lowBeam": False, "highBeam": False, "fogFront": False, 
            "seatbelt": False, "airbag": False, "doorOpen": False, 
            "parkingBrake": False, "absWarn": False,
            "batteryLow": False, "fault": False, "hvFault": False
        }

        # --- KEYPAD MAPPING ---
        # Maps Keypad Char -> Icon Name to TOGGLE
        self.key_map = {
            '1': "leftTurn",
            '2': "rightTurn",
            '3': "highBeam",
            '4': "lowBeam",
            '5': "fogFront",
            '6': "seatbelt",
            '7': "airbag",
            '8': "doorOpen",
            '9': "parkingBrake",
            '0': "absWarn",
            '*': "batteryLow",
            '#': "fault"
        }

        # --- PHYSICS TIMER (60 FPS) ---
        # This makes the acceleration smooth regardless of MQTT lag
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_physics)
        self.timer.start(16) # ~60 FPS

        # --- MQTT SETUP ---
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        try:
            self.client.connect(BROKER, PORT, 60)
            self.client.loop_start()
            print(f"[MQTT] Connected to {BROKER}, Listening on {TOPIC}")
        except Exception as e:
            print(f"[MQTT] Connection Failed: {e}")

    # ==========================================
    # PHYSICS ENGINE (Calculates Speed)
    # ==========================================
    def update_physics(self):
        # 1. Normalize Joystick (0..4095 -> -1.0..1.0)
        # Assuming 0 is FULL FORWARD, 4095 is FULL BACK
        # Center is roughly 2048. Deadzone +/- 200
        
        raw_y = self.last_joystick_y
        throttle = 0.0
        
        # Deadzone Logic
        if raw_y < 1800: # Pushing Forward
            throttle = (1800 - raw_y) / 1800.0 # 0.0 to 1.0
        elif raw_y > 2300: # Pulling Back
            throttle = -(raw_y - 2300) / 1795.0 # 0.0 to -1.0

        # 2. Gear Logic
        if self._gear == "P" or self._gear == "N":
            throttle = 0 # Engine disconnect
            
            # Friction (slow down naturally)
            if self._speed > 0: self._speed -= 0.5
            elif self._speed < 0: self._speed += 0.5
            
            if abs(self._speed) < 1: self._speed = 0

        elif self._gear == "D":
            # Acceleration
            if throttle > 0: 
                self._speed += throttle * 0.8 # Acceleration rate
            # Braking/Coast
            else:
                self._speed -= 0.5 # Friction
                
        elif self._gear == "R":
            # Reverse has lower max speed
            if throttle > 0: # Joystick Forward actually means reverse speed here? 
                # Usually Joystick Back maps to Reverse speed in games, 
                # but for simplicity, let's say Joystick Forward = Gas Pedal
                self._speed += throttle * 0.5 
            else:
                self._speed -= 0.5

        # 3. Cap Speed
        if self._gear == "R":
            if self._speed > 30: self._speed = 30
        else:
            if self._speed > self.max_speed: self._speed = self.max_speed
        
        if self._speed < 0: self._speed = 0

        # 4. Update Power Display based on throttle
        if throttle > 0: self._power = throttle * 100
        else: self._power = -10 # Regen braking simulation

        self.stateChanged.emit()

    # ==========================================
    # MQTT HANDLING
    # ==========================================
    def on_connect(self, client, userdata, flags, rc):
        client.subscribe(TOPIC)

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            # Expected format: {"key": "A", "joystickY": 2030}

            # 1. Update Joystick Target
            if "joystickY" in payload:
                self.last_joystick_y = int(payload["joystickY"])

            # 2. Handle Key Press (Instant Actions)
            if "key" in payload:
                key = str(payload["key"])
                
                # Gear Shifter
                if key == 'A': self._gear = "P"
                elif key == 'B': self._gear = "R"
                elif key == 'C': self._gear = "N"
                elif key == 'D': self._gear = "D"
                
                # Icon Toggles
                elif key in self.key_map:
                    target_icon = self.key_map[key]
                    # Toggle the boolean state
                    self.icon_states[target_icon] = not self.icon_states[target_icon]

        except Exception as e:
            print(f"[ERROR] JSON Parse: {e}")

    # ==========================================
    # QML PROPERTIES
    # ==========================================
    @Property(int, notify=stateChanged)
    def speed(self): return int(self._speed)

    @Property(int, notify=stateChanged)
    def power(self): return int(self._power)

    @Property(int, notify=stateChanged)
    def soc(self): return self._soc

    @Property(int, notify=stateChanged)
    def range(self): return self._range

    @Property(str, notify=stateChanged)
    def gear(self): return self._gear

    @Property(bool, notify=stateChanged)
    def brakes(self): return self._brakes

    @Property(bool, notify=stateChanged)
    def charging(self): return self._charging

    # --- Dynamic Icons ---
    def get_icon(self, name): return self.icon_states.get(name, False)

    @Property(bool, notify=stateChanged)
    def leftTurn(self): return self.get_icon("leftTurn")

    @Property(bool, notify=stateChanged)
    def rightTurn(self): return self.get_icon("rightTurn")

    @Property(bool, notify=stateChanged)
    def highBeam(self): return self.get_icon("highBeam")

    @Property(bool, notify=stateChanged)
    def lowBeam(self): return self.get_icon("lowBeam")

    @Property(bool, notify=stateChanged)
    def fogFront(self): return self.get_icon("fogFront")

    @Property(bool, notify=stateChanged)
    def seatbelt(self): return self.get_icon("seatbelt")

    @Property(bool, notify=stateChanged)
    def airbag(self): return self.get_icon("airbag")

    @Property(bool, notify=stateChanged)
    def doorOpen(self): return self.get_icon("doorOpen")

    @Property(bool, notify=stateChanged)
    def parkingBrake(self): return self.get_icon("parkingBrake")

    @Property(bool, notify=stateChanged)
    def absWarn(self): return self.get_icon("absWarn")

    @Property(bool, notify=stateChanged)
    def batteryLow(self): return self.get_icon("batteryLow")
    
    @Property(bool, notify=stateChanged)
    def fault(self): return self.get_icon("fault")

if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    backend = VehicleState()
    engine.rootContext().setContextProperty("vehicleState", backend)
    engine.load("main.qml")
    if not engine.rootObjects(): sys.exit(-1)
    sys.exit(app.exec())