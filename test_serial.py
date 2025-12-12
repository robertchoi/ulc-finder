"""
Serial Port Diagnostic Tool
간단한 시리얼 포트 연결 테스트 스크립트
"""

import sys
from core.serial_manager import SerialManager
from core.ccid_protocol import CCIDProtocol
import time


def main():
    print("=" * 60)
    print("ULC Finder - Serial Port Diagnostic Tool")
    print("=" * 60)
    print()

    # List available ports
    print("1. Scanning for available COM ports...")
    ports = SerialManager.list_ports()

    if not ports:
        print("   ❌ No COM ports found!")
        print("   Please check:")
        print("   - USB cable is connected")
        print("   - Device drivers are installed")
        print("   - Device appears in Device Manager")
        return

    print(f"   ✓ Found {len(ports)} port(s):")
    for i, port in enumerate(ports, 1):
        print(f"   {i}. {port}")
    print()

    # Select port
    if len(ports) == 1:
        selected_port = ports[0]
        print(f"2. Auto-selecting only available port: {selected_port}")
    else:
        print("2. Select port to test:")
        try:
            choice = int(input(f"   Enter number (1-{len(ports)}): "))
            if 1 <= choice <= len(ports):
                selected_port = ports[choice - 1]
            else:
                print("   ❌ Invalid choice")
                return
        except ValueError:
            print("   ❌ Invalid input")
            return
    print()

    # Test connection
    print(f"3. Testing connection to {selected_port}...")
    serial_mgr = SerialManager(baudrate=57600, timeout=2.0)

    if not serial_mgr.connect(selected_port):
        print("   ❌ Failed to open serial port")
        print("   Possible reasons:")
        print("   - Port is being used by another application")
        print("   - Insufficient permissions")
        print("   - Device was disconnected")
        return

    print("   ✓ Serial port opened successfully")
    print(f"   Settings: 57600 baud, 8N1")
    print()

    # Test CCID communication
    print("4. Testing CCID protocol communication...")
    ccid = CCIDProtocol()

    # Send Power ON command
    print("   Sending Power ON command...")
    cmd = ccid.power_on()
    print(f"   TX: {' '.join(f'{b:02X}' for b in cmd)}")

    response = serial_mgr.send_receive(cmd, timeout=2.0)

    if not response:
        print("   ❌ No response from reader")
        print("   Possible reasons:")
        print("   - Wrong COM port selected")
        print("   - Reader is not powered on")
        print("   - Wrong baud rate")
        print("   - Reader does not support CCID protocol")
        serial_mgr.disconnect()
        return

    print(f"   RX: {' '.join(f'{b:02X}' for b in response)}")

    # Parse response
    try:
        msg_type, status, error, payload = ccid.parse_response(response)
        print(f"   Message Type: 0x{msg_type:02X}")
        print(f"   Status: 0x{status:02X}")
        print(f"   Error: 0x{error:02X}")
        print(f"   Payload Length: {len(payload)} bytes")

        if ccid.is_success(status, error):
            print("   ✓ Power ON successful!")
            if len(payload) > 0:
                print(f"   ATR: {' '.join(f'{b:02X}' for b in payload)}")
        else:
            print(f"   ⚠️ Command failed (status=0x{status:02X}, error=0x{error:02X})")
    except Exception as e:
        print(f"   ❌ Error parsing response: {e}")
        serial_mgr.disconnect()
        return

    print()

    # Test Get UID
    print("5. Testing Get UID command...")
    cmd = ccid.get_uid()
    print(f"   TX: {' '.join(f'{b:02X}' for b in cmd)}")

    response = serial_mgr.send_receive(cmd, timeout=2.0)

    if response:
        print(f"   RX: {' '.join(f'{b:02X}' for b in response)}")
        try:
            msg_type, status, error, payload = ccid.parse_response(response)
            if ccid.is_success(status, error) and len(payload) > 2:
                uid = payload[:-2]  # Remove SW1 SW2
                print(f"   ✓ Card UID: {' '.join(f'{b:02X}' for b in uid)}")
            else:
                print(f"   ⚠️ No card detected or command failed")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    else:
        print("   ❌ No response")

    print()

    # Cleanup
    print("6. Closing connection...")
    serial_mgr.disconnect()
    print("   ✓ Connection closed")
    print()

    print("=" * 60)
    print("Diagnostic completed!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
