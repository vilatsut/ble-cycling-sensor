import asyncio
from bleak import BleakClient

# Replace with your device's MAC address or UUID
DEVICE_ADDRESS = "XX:XX:XX:XX:XX:XX"

async def main():
    async with BleakClient(DEVICE_ADDRESS) as client:
        connected = await client.is_connected()
        print(f"Connected: {connected}")

        print("\nDiscovering services...\n")
        for service in client.services:
            print(f"Service: {service.uuid} | {service.description}")
            for char in service.characteristics:
                props = ",".join(char.properties)
                print(f"  Characteristic: {char.uuid} | {char.description} | Properties: {props}")

                # If readable, read the value
                if "read" in char.properties:
                    try:
                        value = await client.read_gatt_char(char.uuid)
                        print(f"    Value: {value}")
                    except Exception as e:
                        print(f"    Could not read: {e}")

                # List descriptors if any
                for desc in char.descriptors:
                    print(f"    Descriptor: {desc.uuid}")

if __name__ == "__main__":
    asyncio.run(main())