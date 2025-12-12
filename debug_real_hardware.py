
import sys
import time
import traceback
from core.serial_manager import SerialManager
from core.ulc_scanner import ULCScanner

def main():
    print("DEBUG: Starting real hardware test...")
    
    # Find ports
    ports = SerialManager.list_ports()
    print(f"DEBUG: Available ports: {ports}")
    
    if not ports:
        print("DEBUG: No ports found.")
        return

    port = "COM4" # Force COM4
    print(f"DEBUG: Selecting {port}")
    
    serial_mgr = SerialManager(baudrate=57600, timeout=1.0)
    
    try:
        if not serial_mgr.connect(port):
            print("DEBUG: Failed to connect.")
            return
            
        print("DEBUG: Connected.")
        
        scanner = ULCScanner(serial_mgr)
        
        # Define callbacks
        def on_progress(progress, attempts, current_key):
            if attempts % 10 == 0:
                print(f"DEBUG: Progress {progress:.4f}%, Attempts {attempts}, Key {current_key.hex()[:4]}...")
                
        def on_key_found(key):
            print(f"DEBUG: KEY FOUND! {key.hex()}")
            
        def on_error(msg):
            print(f"DEBUG: ERROR: {msg}")
            
        scanner.on_progress = on_progress
        scanner.on_key_found = on_key_found
        scanner.on_error = on_error
        
        start_key = bytes([0]*16)
        print("DEBUG: Starting scan loop...")
        
        # Run scan
        result = scanner.start_scan(start_key)
        
        print(f"DEBUG: Scan finished. Success={result.success}, Message={result.message}")
        
    except Exception:
        print("DEBUG: CRASHED!")
        traceback.print_exc()
    finally:
        serial_mgr.disconnect()
        print("DEBUG: Disconnected.")

if __name__ == "__main__":
    main()
