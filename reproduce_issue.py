
import sys
import time
from unittest.mock import MagicMock
from core.ulc_scanner import ULCScanner
from core.serial_manager import SerialManager

def test_power_on_failure():
    print("Testing Power ON failure behavior...")
    
    # Mock SerialManager
    mock_serial = MagicMock(spec=SerialManager)
    
    # Mock send_receive to return a "Failed" Power ON response
    # CCID Message: Type(1) + Length(4) + Slot(1) + Seq(1) + Status(1) + Error(1) + Specific(1)
    # Status = 0x40 (Failed), Error = 0xFE (Some error)
    failure_response = bytes([0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x40, 0xFE, 0x00])
    
    # Frame it: STX + Body + ETX + Checksum
    framed_response = bytearray([0x02])
    framed_response.extend(failure_response)
    framed_response.append(0x03)
    framed_response.append(0x00) # Checksum (dummy)
    
    mock_serial.send_receive.return_value = bytes(framed_response)
    
    # Create Scanner
    scanner = ULCScanner(mock_serial)
    
    # Mock callbacks
    def on_error(msg):
        print(f"Callback Error: {msg}")
        
    scanner.on_error = on_error
    
    # Start Scan
    start_key = bytes([0]*16)
    print("Starting scan...")
    result = scanner.start_scan(start_key)
    
    print(f"Scan Result: Success={result.success}, Message='{result.message}'")
    print(f"Is Scanning: {scanner.is_scanning}")
    
    # Verify if it stopped immediately
    if not scanner.is_scanning and "Power ON 실패" in str(mock_serial.mock_calls) or result.success is False:
        print("CONFIRMED: Scan stopped immediately after Power ON failure.")
    else:
        print("OBSERVATION: Scan did not stop immediately.")

if __name__ == "__main__":
    test_power_on_failure()
