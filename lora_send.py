import serial

serial_port_lora = "/dev/ttyS0"
baud_rate = 9600

try:
    lora = serial.Serial(serial_port_lora, baud_rate, timeout=1)
    print("LoRa E220 Initialized")
except Exception as e:
    print(f"Error: {e}")
    exit()

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