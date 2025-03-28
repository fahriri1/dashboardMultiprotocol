from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
import paho.mqtt.client as mqtt
import serial
import time
import asyncio
from bleak import BleakClient
import socket
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
socketio = SocketIO(app, async_mode=None, cors_allowed_origins="*")
CORS(app)

wifi_data = 0
lora_data = 0
ble_data = 0

wifi_test = False
test_buffer = ['','','','','','','','','','']
time_buffer = [0,0,0,0,0,0,0,0,0,0]
wifi_count = 0

mqtt_client = mqtt.Client()
lastTime = 0

MQTT_BROKER = 'broker.emqx.io'
MQTT_PORT = 1883
mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
MQTT_TOPIC_SUB = ''
MQTT_TOPIC_PUB = ''

serial_port_lora = "/dev/ttyS0"
baud_rate = 9600

hm10_address = "68:5E:1C:4B:DB:AF"
write_characteristic_uuid = "0000ffe1-0000-1000-8000-00805f9b34fb"
state_ble = False

async def write_data(message):
    try:
        async with BleakClient(hm10_address, timeout=1000) as client:
            print("Connected: ", client.is_connected)
            data = bytearray(message, "utf-8")
            try:
                await client.write_gatt_char(write_characteristic_uuid, data)
                print("Data written successfully!")
                global state_ble
                state_ble = True
                socketio.emit('ble_status', {'status': state_ble})
            except TimeoutError as e:
                print(f"Error receiving data from BLE: {e}")
    except TimeoutError as e:
        print(f"Timeout ble not found")

async def read_data():
    try:
        async with BleakClient(hm10_address, timeout=1000) as client:
            def getDataHandler(sender,data):
                print(f"data received: {data.decode('utf-8')}")
                socketio.emit('ble_data', {'data': data.decode('utf-8')})
                PubMqtt('gateway/lora', data.decode('utf-8'))

            await client.start_notify(write_characteristic_uuid, getDataHandler)
            while(1):
                await asyncio.sleep(1)
    except TimeoutError as e:
        print(f"Timeout ble not found")

def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception as e:
        return f"Error: {e}"

def PubMqtt(topic, data):
    mqtt_client.publish(topic, data)
    socketio.emit('mqtt_data', {'topic':topic, 'data':data})

@socketio.on('init')
def connecting_mqtt():
    if mqtt_client.is_connected():
        print(f"MQTT Connected")
        state_connected = True
    else:
        print(f"not connected")
        state_connected = False
    socketio.emit('mqtt_status', {'status': state_connected})

@socketio.on('start_lora')
def lora_init():
    try:
        lora = serial.Serial(serial_port_lora, baud_rate, timeout=1)
        print("LoRa E220 Initialized")
    except Exception as e:
        print(f"Error: {e}")
        exit()

    status_lora = True
    while status_lora:
        if lora.in_waiting > 0:
            received = lora.readline().decode().strip()
            print(f"Received: {received}")
            socketio.emit('lora_data', {'data':received})

            PubMqtt('gateway/lora', received)


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
                socketio.emit('lora_status', {'status': status_lora})
                break

@socketio.on('test_lora')
def lora_test():
    try:
        lora = serial.Serial(serial_port_lora, baud_rate, timeout=1)
        print("LoRa E220 Initialized")
    except Exception as e:
        print(f"Error: {e}")
        exit()
    
    #trying send init
    try:
        data = "test"
        lora.write(data.encode())  # Send data as bytes
        print(f"Sent: {data}")
    except Exception as e:
        print(f"Error sending data: {e}")

    status_lora = True
    iter = 0
    lastTime = time.time()
    while status_lora:
        if lora.in_waiting > 0:
            currentTime = time.time()
            received = lora.readline().decode().strip()
            test_buffer[iter] = received
            time_buffer[iter] = currentTime - lastTime
            print(f"iteration test: {iter}")
            if iter == 9 :
                latency = 0
                througput = 0
                packetLoss = 0
                
                for n in range(10):
                    print("packet: ")
                    print(test_buffer[n])

                    print("time: ")
                    print(time_buffer[n])

                    latency = latency + time_buffer[n]
                    print(f"latency: {latency}")

                    packetSize = len(test_buffer[n])
                    througput = througput + packetSize/time_buffer[n]
                    print(f"througput: {througput}")

                    if test_buffer[n] != "testingLoRa":
                        packetLoss += 1
                    print(f"packetLoss: {packetLoss}")
                    print("")
                
                latency = latency/10
                print(f"latency result: {latency}")

                througput = througput/10
                print(f"througput result: {througput}")

                packetLoss = (packetLoss/10)*100
                print(f"packetLoss result: {packetLoss}")

                socketio.emit('lora_result', {'latency':round(latency,3), 'througput':round(througput,3), 'packetLoss':packetLoss})
                status_lora = False
            else:
                iter += 1

@socketio.on('init_ble')
def ble_init():
    print(f"Start BLE intial")
    socketio.start_background_task(asyncio.run, write_data("start"))

@app.route('/init_wifi', methods=['POST'])
def init_wifi():
    data = request.json
    print(f"device send data: {data['status']}")
    if data['status']:
        print(f"device connected")
        print(f"data sent: {data['status']} and {data['ip']}")

        socketio.emit('ip_device', {'status':data['status'], 'ip':data['ip']})
        return jsonify({'connection':'connected'})
    else:
        print(f"device restart")
        return jsonify({'connection':'restart'})

@socketio.on('wifiTestOn')
def wifiTestOn():
    print("before rock and roll")
    global wifi_test
    wifi_test = True

@app.route('/dataStream_wifi', methods=['POST'])
def dataStream_wifi():
    global wifi_data, wifi_test, lastTime
    wifi_data = request.json
    print(f"device send data: {wifi_data['data']}")

    socketio.emit('wifi_data', {'data':wifi_data['data']})
    PubMqtt('gateway/wifi', wifi_data['data'])
    lastTime = time.time()

    return jsonify({'data sent':'sent', 'test':wifi_test})

@app.route('/wifiTest', methods=['POST'])
def wifiTest():
    global wifi_count, lastTime, wifi_test
    currentTime = time.time()
    testDataWifi = request.json
    test_buffer[wifi_count] = testDataWifi['data']
    time_buffer[wifi_count] = currentTime - lastTime
    if wifi_count == 9 :
        latency = 0
        througput = 0
        packetLoss = 0
        
        for n in range(10):
            print("packet: ")
            print(test_buffer[n])

            print("time: ")
            print(time_buffer[n])

            latency = latency + time_buffer[n]
            print(f"latency: {latency}")

            packetSize = len(test_buffer[n])
            througput = througput + packetSize/time_buffer[n]
            print(f"througput: {througput}")

            if test_buffer[n] != "testingWifi":
                packetLoss += 1
            print(f"packetLoss: {packetLoss}")
            print("")
        
        latency = latency/10
        print(f"latency result: {latency}")

        througput = througput/10
        print(f"througput result: {througput}")

        packetLoss = (packetLoss/10)*100
        print(f"packetLoss result: {packetLoss}")

        wifi_count = 0
        wifi_test = False

        socketio.emit('wifi_result', {'latency':round(latency,3), 'througput':round(througput,3), 'packetLoss':packetLoss})
        return jsonify({'data sent':'sent'})
    else:
        wifi_count += 1
        lastTime = time.time()
        return jsonify({'data sent':'sent'})

@socketio.on('init_server')
def wifi_start():
    print(f"WiFi started")
    local_ip = get_local_ip()
    print(local_ip)
    socketio.emit('ip_server', {'ip': local_ip})

@socketio.on('ble_getData')
def ble_getData():
    socketio.start_background_task(asyncio.run, read_data())

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/mqtt')
def mqtt_():
    return render_template('mqtt.html')

@app.route('/wifi')
def wifi_():
    return render_template('wifi.html')

@app.route('/test')
def test_():
    return render_template('testing.html')

if __name__ == '__main__':
    mqtt_client.loop_start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)