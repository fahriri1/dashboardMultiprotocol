from flask import Flask, render_template
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import serial
import time
import asyncio
from bleak import BleakClient
import socket

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
socketio = SocketIO(app, async_mode=None)

mqtt_client = mqtt.Client()

MQTT_BROKER = 'broker.emqx.io'
MQTT_PORT = 1883
mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
MQTT_TOPIC_SUB = ''
MQTT_TOPIC_PUB = ''

serial_port_lora = "/dev/ttyS0"
baud_rate = 9600

hm10_address = "68:5E:1C:4B:DB:AF"
write_characteristic_uuid = "0000ffe1-0000-1000-8000-00805f9b34fb"

async def write_data(message):
    async with BleakClient(hm10_address) as client:
        print("Connected: ", client.is_connected)
        data = bytearray(message, "utf-8")
        try:
            await client.write_gatt_char(write_characteristic_uuid, data)
            print("Data written successfully!")
            socketio.emit('ble_status', {'status': True})
        except Exception as e:
            print(f"Error receiving data from BLE: {e}")

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
        print("LoRa E220 Initialized")
    except Exception as e:
        print(f"Error: {e}")
        exit()
    
    #trying send init
    try:
        data = "start"
        lora.write(data.encode())  # Send data as bytes
        print(f"Sent: {data}")
    except Exception as e:
        print(f"Error sending data: {e}")

    status_lora = True
    while status_lora:
        if lora.in_waiting > 0:
            received = lora.readline().decode().strip()
            print(f"Received: {received}")
            if received == "ready":
                socketio.emit('ble_status', {'status': status_lora})
                status_lora = False

@socketio.on('init_ble')
def ble_init():
    print(f"Start ble intial")
    asyncio.run(write_data("start"))

def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception as e:
        return f"Error: {e}"

@socketio.on('init_wifi')
def wifi_start():
    print(f"WiFi started")
    local_ip = get_local_ip()
    print(local_ip)
    socketio.emit('wifi_start', {'status': True, 'ip_local': local_ip})

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/mqtt')
def mqtt_():
    return render_template('mqtt.html')

@app.route('/wifi')
def wifi_():
    return render_template('wifi.html')

if __name__ == '__main__':
    mqtt_client.loop_start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)