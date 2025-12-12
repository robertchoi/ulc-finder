"""
CCID Protocol Handler
Handles CCID 1.1 protocol message construction and parsing
"""

import struct
from typing import List, Tuple, Optional


class CCIDMessage:
    """CCID Message Types"""
    # PC to Reader
    PC_TO_RDR_ICCPOWERON = 0x62
    PC_TO_RDR_ICCPOWEROFF = 0x63
    PC_TO_RDR_XFRBLOCK = 0x6F

    # Reader to PC
    RDR_TO_PC_DATABLOCK = 0x80
    RDR_TO_PC_SLOTSTATUS = 0x81


class CCIDProtocol:
    """CCID Protocol Handler for ULC Reader"""

    def __init__(self):
        self.sequence = 0

    def get_next_seq(self) -> int:
        """Get next sequence number and increment"""
        seq = self.sequence
        self.sequence = (self.sequence + 1) & 0xFF
        return seq

    def reset_seq(self):
        """Reset sequence number to 0"""
        self.sequence = 0

    # ========== Command Construction ==========

    def power_on(self) -> bytes:
        """
        Construct Power ON command
        Returns: CCID message bytes
        """
        seq = self.get_next_seq()
        message = bytearray([
            CCIDMessage.PC_TO_RDR_ICCPOWERON,  # bMessageType
            0x00, 0x00, 0x00, 0x00,             # dwLength (0)
            0x00,                                # bSlot
            seq,                                 # bSeq
            0x00, 0x00, 0x00                    # bSpecific
        ])
        return bytes(message)

    def power_off(self) -> bytes:
        """
        Construct Power OFF command
        Returns: CCID message bytes
        """
        seq = self.get_next_seq()
        message = bytearray([
            CCIDMessage.PC_TO_RDR_ICCPOWEROFF,  # bMessageType
            0x00, 0x00, 0x00, 0x00,             # dwLength (0)
            0x00,                                # bSlot
            seq,                                 # bSeq
            0x00, 0x00, 0x00                    # bSpecific
        ])
        return bytes(message)

    def get_uid(self) -> bytes:
        """
        Construct Get UID command (FF CA 00 00 00)
        Returns: CCID message bytes
        """
        seq = self.get_next_seq()
        apdu = [0xFF, 0xCA, 0x00, 0x00, 0x00]

        message = bytearray([
            CCIDMessage.PC_TO_RDR_XFRBLOCK,     # bMessageType
            len(apdu), 0x00, 0x00, 0x00,        # dwLength
            0x00,                                # bSlot
            seq,                                 # bSeq
            0x00, 0x00, 0x00                    # bSpecific
        ])
        message.extend(apdu)
        return bytes(message)

    def load_key(self, key_bytes: bytes, slot: int = 3) -> bytes:
        """
        Construct Load Authentication Key command (FF 82 00 slot Lc key)

        Args:
            key_bytes: 16-byte 3DES key
            slot: Key slot number (default: 3)

        Returns: CCID message bytes
        """
        if len(key_bytes) != 16:
            raise ValueError("Key must be exactly 16 bytes")

        seq = self.get_next_seq()
        apdu = [0xFF, 0x82, 0x00, slot, 0x10]  # CLA INS P1 P2 Lc
        apdu.extend(key_bytes)

        message = bytearray([
            CCIDMessage.PC_TO_RDR_XFRBLOCK,     # bMessageType
            len(apdu), 0x00, 0x00, 0x00,        # dwLength
            0x00,                                # bSlot
            seq,                                 # bSeq
            0x00, 0x00, 0x00                    # bSpecific
        ])
        message.extend(apdu)
        return bytes(message)

    def authenticate(self, page: int = 4, key_slot: int = 3) -> bytes:
        """
        Construct General Authenticate command (FF 86 00 00 05 01 00 page 60 slot)

        Args:
            page: Page number to authenticate (default: 4)
            key_slot: Key slot number (default: 3)

        Returns: CCID message bytes
        """
        seq = self.get_next_seq()
        apdu = [
            0xFF, 0x86,              # CLA INS (GENERAL AUTHENTICATE)
            0x00, 0x00,              # P1 P2
            0x05,                    # Lc (5 bytes)
            0x01,                    # Version
            0x00,                    # Address MSB
            page,                    # Address LSB
            0x60,                    # Auth mode (0x60 = Key A for 3DES)
            key_slot                 # Key number
        ]

        message = bytearray([
            CCIDMessage.PC_TO_RDR_XFRBLOCK,     # bMessageType
            len(apdu), 0x00, 0x00, 0x00,        # dwLength
            0x00,                                # bSlot
            seq,                                 # bSeq
            0x00, 0x00, 0x00                    # bSpecific
        ])
        message.extend(apdu)
        return bytes(message)

    # ========== Response Parsing ==========

    def parse_response(self, data: bytes) -> Tuple[int, int, int, bytes]:
        """
        Parse CCID response message

        Args:
            data: Response bytes

        Returns:
            Tuple of (bMessageType, bStatus, bError, payload)
        """
        if len(data) < 10:
            raise ValueError(f"Response too short: {len(data)} bytes")

        bMessageType = data[0]
        dwLength = struct.unpack('<I', data[1:5])[0]
        bSlot = data[5]
        bSeq = data[6]
        bStatus = data[7]
        bError = data[8]
        bSpecific = data[9]

        payload = data[10:10+dwLength] if dwLength > 0 else b''

        return bMessageType, bStatus, bError, payload

    def is_success(self, bStatus: int, bError: int) -> bool:
        """
        Check if response indicates success

        Args:
            bStatus: Status byte from response
            bError: Error byte from response

        Returns:
            True if successful, False otherwise
        """
        return bStatus == 0x00 and bError == 0x00

    def is_auth_success(self, bStatus: int, bError: int, payload: bytes) -> bool:
        """
        Check if authentication was successful

        Args:
            bStatus: Status byte from response
            bError: Error byte from response
            payload: Response payload

        Returns:
            True if authentication successful, False otherwise
        """
        # Check APDU status words (SW1 SW2)
        if len(payload) >= 2:
            sw1 = payload[-2]
            sw2 = payload[-1]

            # 90 00 = Success
            if sw1 == 0x90 and sw2 == 0x00:
                return True

            # 63 00 = Authentication failed
            if sw1 == 0x63 and sw2 == 0x00:
                return False

        # Also check CCID status
        if bStatus == 0x00 and bError == 0x00:
            return True

        # 0x69 = Authentication error
        if bError == 0x69:
            return False

        # 0x40 = Command failed
        if bStatus == 0x40:
            return False

        return False

    def format_hex(self, data: bytes) -> str:
        """Format bytes as hex string with spaces"""
        return ' '.join(f'{b:02X}' for b in data)

    def parse_hex(self, hex_str: str) -> bytes:
        """
        Parse hex string to bytes

        Args:
            hex_str: Hex string like "00 01 02 03" or "00010203"

        Returns:
            bytes object
        """
        # Remove spaces and convert
        hex_clean = hex_str.replace(' ', '').replace('\n', '')
        return bytes.fromhex(hex_clean)


# Convenience functions
def create_ccid_protocol() -> CCIDProtocol:
    """Create a new CCID protocol handler"""
    return CCIDProtocol()
