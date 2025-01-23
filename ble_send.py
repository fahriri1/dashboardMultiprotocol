import asyncio
from bleak import BleakClient

hm10_address = "68:5E:1C:4B:DB:AF"
write_characteristic_uuid = "0000ffe1-0000-1000-8000-00805f9b34fb"

async def write_data(message):
    async with BleakClient(hm10_address) as client:
        print("Connected: ", client.is_connected)

        data = bytearray(message, "utf-8")

        await client.write_gatt_char(write_characteristic_uuid, data)
        print("Data written successfully!")

async def ble_init():
    try:
        print(f"Start ble intial")
        await write_data("start")
    except RuntimeError as e:
        print(f"Error receiving data from BLE: {e}")