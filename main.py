from flask import Flask, render_template
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
socketio = SocketIO(app)

mqtt_client = mqtt.Client()

MQTT_BROKER = 'broker.emqx.io'
MQTT_PORT = 1883
mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
MQTT_TOPIC_SUB = ''
MQTT_TOPIC_PUB = ''

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

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/blue')
def blue():
    return render_template('blue.html')

@app.route('/mqtt')
def mqtt_():
    return render_template('mqtt.html')

if __name__ == '__main__':
    mqtt_client.loop_start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)