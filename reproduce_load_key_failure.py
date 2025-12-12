
import sys
import time
from unittest.mock import MagicMock
from core.ulc_scanner import ULCScanner
from core.serial_manager import SerialManager

def test_load_key_failure():
    print("Testing Load Key failure behavior...")
    
    mock_serial = MagicMock(spec=SerialManager)
    
    # Mock responses
    # 1. Power ON: Success
    power_on_response = bytes([0x80, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00])
    framed_power_on = bytearray([0x02]) + power_on_response + bytearray([0x03, 0x00])

    # 2. Get UID: Success
    get_uid_response = bytes([0x80, 0x09, 0x00, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00]) + bytes([0x04, 0x59, 0x79, 0xFA, 0xB2, 0x7B, 0x80, 0x90, 0x00])
    framed_get_uid = bytearray([0x02]) + get_uid_response + bytearray([0x03, 0x00])

    # 3. Load Key: Failure (Status=0x40, Error=0xFE)
    load_key_response = bytes([0x80, 0x00, 0x00, 0x00, 0x00, 0x03, 0x40, 0xFE, 0x00])
    framed_load_key = bytearray([0x02]) + load_key_response + bytearray([0x03, 0x00])

    # Sequence of responses for one iteration
    # We need to provide enough for multiple iterations to prove it loops
    mock_serial.send_receive.side_effect = [
        bytes(framed_power_on), bytes(framed_get_uid), bytes(framed_load_key), # Iteration 1
        bytes(framed_power_on), bytes(framed_get_uid), bytes(framed_load_key), # Iteration 2
        bytes(framed_power_on), bytes(framed_get_uid), bytes(framed_load_key), # Iteration 3
    ]
    
    scanner = ULCScanner(mock_serial)
    
    def on_error(msg):
        print(f"Callback Error: {msg}")
        
    def on_progress(p, a, k):
        print(f"Callback Progress: Attempts={a}, Key={k.hex()[:4]}...")

    scanner.on_error = on_error
    scanner.on_progress = on_progress
    
    start_key = bytes([0]*16)
    print("Starting scan...")
    
    # Run in a separate thread or just let it run for a bit?
    # Since start_scan is blocking, we can't easily interrupt it in this script without threading.
    # But we can mock key_gen to stop after 2 iterations?
    
    # Let's just run it and expect it to crash if side_effect runs out (StopIteration)
    # If it stops early, it won't consume all side_effects.
    
    try:
        scanner.start_scan(start_key)
    except StopIteration:
        print("Mock side_effect exhausted - Scan continued successfully!")
    except Exception as e:
        print(f"Scan stopped with exception: {e}")

    print(f"Attempts made: {scanner.key_gen.get_attempts()}")

if __name__ == "__main__":
    test_load_key_failure()
