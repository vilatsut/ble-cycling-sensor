"""
Polar Cycling Speed Sensor Monitor
Connects to Polar Speed Sensor and displays real-time measurements
"""

import asyncio
from bleak import BleakClient
import struct
import sys
from datetime import datetime

# Device configuration
TARGET_MAC = "C5:82:31:C6:EF:50"

# Service and Characteristic UUIDs
CSC_SERVICE_UUID = "00001816-0000-1000-8000-00805f9b34fb"
CSC_MEASUREMENT_UUID = "00002a5b-0000-1000-8000-00805f9b34fb"
CSC_FEATURE_UUID = "00002a5c-0000-1000-8000-00805f9b34fb"
BATTERY_LEVEL_UUID = "00002a19-0000-1000-8000-00805f9b34fb"
DEVICE_NAME_UUID = "00002a00-0000-1000-8000-00805f9b34fb"
MANUFACTURER_UUID = "00002a29-0000-1000-8000-00805f9b34fb"
MODEL_NUMBER_UUID = "00002a24-0000-1000-8000-00805f9b34fb"
SERIAL_NUMBER_UUID = "00002a25-0000-1000-8000-00805f9b34fb"
FIRMWARE_UUID = "00002a26-0000-1000-8000-00805f9b34fb"
SOFTWARE_UUID = "00002a28-0000-1000-8000-00805f9b34fb"
HARDWARE_UUID = "00002a27-0000-1000-8000-00805f9b34fb"

# Wheel circumference in mm (700x25c tire = ~2105mm, adjust for your wheel)
WHEEL_CIRCUMFERENCE_MM = 2105

class CyclingSensorMonitor:
    def __init__(self, address):
        self.address = address
        self.client = None
        self.last_wheel_revs = None
        self.last_wheel_time = None
        self.speed_kmh = 0.0
        
    async def read_device_info(self):
        """Read and display device information"""
        print("=" * 80)
        print("DEVICE INFORMATION")
        print("=" * 80)
        
        try:
            device_name = await self.client.read_gatt_char(DEVICE_NAME_UUID)
            print(f"Device Name:    {device_name.decode('utf-8')}")
        except:
            print(f"Device Name:    Unable to read")
        
        try:
            manufacturer = await self.client.read_gatt_char(MANUFACTURER_UUID)
            print(f"Manufacturer:   {manufacturer.decode('utf-8')}")
        except:
            pass
        
        try:
            model = await self.client.read_gatt_char(MODEL_NUMBER_UUID)
            print(f"Model:          {model.decode('utf-8')}")
        except:
            pass
        
        try:
            serial = await self.client.read_gatt_char(SERIAL_NUMBER_UUID)
            print(f"Serial Number:  {serial.decode('utf-8')}")
        except:
            pass
        
        try:
            firmware = await self.client.read_gatt_char(FIRMWARE_UUID)
            print(f"Firmware:       {firmware.decode('utf-8')}")
        except:
            pass
        
        try:
            software = await self.client.read_gatt_char(SOFTWARE_UUID)
            print(f"Software:       {software.decode('utf-8')}")
        except:
            pass
        
        try:
            hardware = await self.client.read_gatt_char(HARDWARE_UUID)
            print(f"Hardware:       {hardware.decode('utf-8')}")
        except:
            pass
        
        try:
            battery = await self.client.read_gatt_char(BATTERY_LEVEL_UUID)
            battery_level = int(battery[0])
            print(f"Battery Level:  {battery_level}%")
        except:
            pass
        
        try:
            feature = await self.client.read_gatt_char(CSC_FEATURE_UUID)
            feature_flags = struct.unpack('<H', feature)[0]
            wheel_supported = feature_flags & 0x01
            crank_supported = feature_flags & 0x02
            print(f"\nFeatures:")
            print(f"  Wheel Revolution: {'Yes' if wheel_supported else 'No'}")
            print(f"  Crank Revolution: {'Yes' if crank_supported else 'No'}")
        except:
            pass
        
        print("=" * 80)
        print()
    
    def parse_csc_measurement(self, data):
        """Parse CSC Measurement data according to BLE CSC specification"""
        if len(data) < 1:
            return None
        
        flags = data[0]
        wheel_revolution_present = flags & 0x01
        crank_revolution_present = flags & 0x02
        
        offset = 1
        result = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'wheel_revs': None,
            'wheel_time': None,
            'crank_revs': None,
            'crank_time': None,
            'speed_kmh': 0.0
        }
        
        # Parse Wheel Revolution Data
        if wheel_revolution_present and len(data) >= offset + 6:
            wheel_revs = struct.unpack('<I', data[offset:offset+4])[0]
            wheel_time = struct.unpack('<H', data[offset+4:offset+6])[0]
            result['wheel_revs'] = wheel_revs
            result['wheel_time'] = wheel_time
            
            # Calculate speed
            if self.last_wheel_revs is not None and self.last_wheel_time is not None:
                rev_diff = wheel_revs - self.last_wheel_revs
                time_diff = wheel_time - self.last_wheel_time
                
                # Handle rollover for time (uint16 max = 65535)
                if time_diff < 0:
                    time_diff += 65536
                
                if time_diff > 0:
                    # Time is in 1/1024 seconds
                    time_seconds = time_diff / 1024.0
                    distance_meters = (rev_diff * WHEEL_CIRCUMFERENCE_MM) / 1000.0
                    speed_ms = distance_meters / time_seconds
                    self.speed_kmh = speed_ms * 3.6  # Convert m/s to km/h
                    result['speed_kmh'] = self.speed_kmh
            
            self.last_wheel_revs = wheel_revs
            self.last_wheel_time = wheel_time
            offset += 6
        
        # Parse Crank Revolution Data
        if crank_revolution_present and len(data) >= offset + 4:
            crank_revs = struct.unpack('<H', data[offset:offset+2])[0]
            crank_time = struct.unpack('<H', data[offset+2:offset+4])[0]
            result['crank_revs'] = crank_revs
            result['crank_time'] = crank_time
        
        return result
    
    def measurement_callback(self, sender, data):
        """Callback for CSC measurement notifications"""
        measurement = self.parse_csc_measurement(data)
        
        if measurement:
            # Clear line and print measurement
            print(f"\r[{measurement['timestamp']}] ", end='')
            
            if measurement['wheel_revs'] is not None:
                print(f"Speed: {measurement['speed_kmh']:6.2f} km/h | ", end='')
                print(f"Wheel Revs: {measurement['wheel_revs']:8d} | ", end='')
                print(f"Time: {measurement['wheel_time']:5d}", end='')
            
            if measurement['crank_revs'] is not None:
                print(f" | Crank Revs: {measurement['crank_revs']:5d}", end='')
            
            sys.stdout.flush()
    
    async def connect_and_monitor(self):
        """Connect to device and start monitoring"""
        print(f"Connecting to {self.address}...")
        
        try:
            self.client = BleakClient(self.address, timeout=30.0)
            
            # Try to connect with retries
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    print(f"Connection attempt {attempt + 1}/{max_retries}...")
                    await self.client.connect()
                    if self.client.is_connected:
                        break
                except asyncio.TimeoutError:
                    if attempt < max_retries - 1:
                        print("Timeout, retrying...")
                        await asyncio.sleep(2)
                    else:
                        raise
            
            if not self.client.is_connected:
                print("Failed to connect after all retries")
                return
            
            print(f"✓ Connected!\n")
            
            # Small delay to ensure connection is stable
            await asyncio.sleep(0.5)
            
            # Read and display device info
            await self.read_device_info()
            
            # Start notifications
            print("Starting measurement monitoring...")
            print("Wheel circumference: {}mm (adjust in code if needed)".format(WHEEL_CIRCUMFERENCE_MM))
            print("-" * 80)
            print("Waiting for measurements... (move the sensor to see data)\n")
            
            await self.client.start_notify(CSC_MEASUREMENT_UUID, self.measurement_callback)
            
            # Keep running until interrupted
            try:
                while self.client.is_connected:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n\nStopping...")
            
            # Stop notifications
            try:
                await self.client.stop_notify(CSC_MEASUREMENT_UUID)
            except:
                pass
            
        except asyncio.TimeoutError:
            print("Connection timeout - device may not be responding")
            print("\nTips:")
            print("- Make sure device is awake (spin the wheel)")
            print("- Check battery level")
            print("- Move device closer")
        except Exception as e:
            print(f"Error: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            if self.client and self.client.is_connected:
                try:
                    await self.client.disconnect()
                    print("Disconnected")
                except:
                    pass

async def main():
    print("\n" + "=" * 80)
    print("POLAR CYCLING SPEED SENSOR MONITOR")
    print("=" * 80)
    print()
    
    monitor = CyclingSensorMonitor(TARGET_MAC)
    await monitor.connect_and_monitor()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)