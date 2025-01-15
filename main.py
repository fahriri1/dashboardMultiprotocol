from flask import Flask, render_template
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import serial
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
socketio = SocketIO(app)

mqtt_client = mqtt.Client()

MQTT_BROKER = 'broker.emqx.io'
MQTT_PORT = 1883
mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
MQTT_TOPIC_SUB = ''
MQTT_TOPIC_PUB = ''

serial_port_lora = "/dev/ttyAMA0"
serial_port_ble = "/dev/ttyS0"
baud_rate = 9600 

@socketio.on('init')
def connecting_mqtt():
    if mqtt_client.is_connected():
        print(f"MQTT Connected")
        state_connected = True
    else:
        print(f"not connected")
        state_connected = False
    socketio.emit('mqtt_status', {'status': state_connected})

@socketio.on('mqtt_connect')
def handle_mqtt(data):
    MQTT_BROKER = data.get('broker')
    MQTT_PORT = 1883
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT)

    global MQTT_TOPIC_SUB, MQTT_TOPIC_PUB
    MQTT_TOPIC_SUB = data.get('topic_sub')
    MQTT_TOPIC_PUB = data.get('topic_pub')

@socketio.on('init_lora')
def lora_init():
    try:
        lora = serial.Serial(serial_port_lora, baud_rate, timeout=1)
        print("LoRa E220 Initialized.")
    except Exception as e:
        print(f"Error: {e}")
        exit()
    
    #trying send init
    try:
        data = "initial"
        lora.write(data.encode())  # Send data as bytes
        print(f"Sent: {data}")
    except Exception as e:
        print(f"Error sending data: {e}")

    status_lora = True
    while status_lora:
        try:
            if lora.in_waiting > 0:
                received = lora.readline().decode().strip()
                print(f"Received: {received}")
                if received == "ready":
                    socketio.emit('ble_status', {'status': status_lora})
                    status_lora = False
        except Exception as e:
            print(f"Error receiving data: {e}")
    

@socketio.on('init_ble')
def ble_init():
    try:
        ble = serial.Serial(serial_port_ble, baud_rate, timeout=1)
        print("BLE HM-10 Initialized.")
    except Exception as e:
        print(f"Error: {e}")
        exit()
    
    #trying send init
    try:
        data = "initial"
        ble.write(data.encode())  # Send data as bytes
        print(f"Sent: {data}")
    except Exception as e:
        print(f"Error sending data: {e}")

    status_ble = True
    while status_ble:
        try:
            if ble.in_waiting > 0:
                received = ble.readline().decode().strip()
                print(f"Received: {received}")
                if received == "ready":
                    socketio.emit('lora_status', {'status': status_ble})
                    status_ble = False
        except Exception as e:
            print(f"Error receiving data: {e}")

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/mqtt')
def mqtt_():
    return render_template('mqtt.html')

if __name__ == '__main__':
    mqtt_client.loop_start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)