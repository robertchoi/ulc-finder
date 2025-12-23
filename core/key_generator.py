"""
Key Generator
Handles 16-byte key generation and incrementation
"""

from typing import Optional
import secrets


class KeyGenerator:
    """16-byte key generator with increment functionality"""

    def __init__(self, start_key: bytes):
        """
        Initialize key generator

        Args:
            start_key: Starting 16-byte key
        """
        if len(start_key) != 16:
            raise ValueError("Key must be exactly 16 bytes")

        self.start_key = start_key
        self.current_key = start_key
        self.end_key = b'\xFF' * 16
        self.attempts = 0

    def increment(self) -> bool:
        """
        Increment current key by 1

        Returns:
            True if successful, False if overflow (reached FF...FF)
        """
        # Convert to integer (big-endian)
        key_int = int.from_bytes(self.current_key, byteorder='big')

        # Increment
        key_int += 1

        # Check overflow
        if key_int > 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:
            return False

        # Convert back to bytes
        self.current_key = key_int.to_bytes(16, byteorder='big')
        self.attempts += 1
        return True

    def get_current_key(self) -> bytes:
        """Get current key"""
        return self.current_key

    def get_attempts(self) -> int:
        """Get number of attempts (keys tried)"""
        return self.attempts

    def calculate_progress(self) -> float:
        """
        Calculate progress percentage

        Returns:
            Progress from 0.0 to 100.0
        """
        start_int = int.from_bytes(self.start_key, byteorder='big')
        current_int = int.from_bytes(self.current_key, byteorder='big')
        end_int = int.from_bytes(self.end_key, byteorder='big')

        if end_int == start_int:
            return 100.0

        progress = ((current_int - start_int) / (end_int - start_int)) * 100.0
        return min(100.0, max(0.0, progress))

    def format_key(self, key: Optional[bytes] = None) -> str:
        """
        Format key as hex string with spaces

        Args:
            key: Key to format (None = current key)

        Returns:
            Formatted hex string
        """
        if key is None:
            key = self.current_key

        return ' '.join(f'{b:02X}' for b in key)

    @staticmethod
    def parse_key(hex_str: str) -> bytes:
        """
        Parse hex string to 16-byte key

        Args:
            hex_str: Hex string like "00 01 02 ... 0F" or "000102...0F"

        Returns:
            16-byte key

        Raises:
            ValueError: If invalid format or not 16 bytes
        """
        # Remove spaces and newlines
        hex_clean = hex_str.replace(' ', '').replace('\n', '').strip()

        # Convert to bytes
        try:
            key_bytes = bytes.fromhex(hex_clean)
        except ValueError as e:
            raise ValueError(f"Invalid hex string: {e}")

        # Check length
        if len(key_bytes) != 16:
            raise ValueError(f"Key must be 16 bytes, got {len(key_bytes)}")

        return key_bytes

    def reset(self, new_start_key: Optional[bytes] = None):
        """
        Reset to start key

        Args:
            new_start_key: New start key (None = use original start key)
        """
        if new_start_key:
            if len(new_start_key) != 16:
                raise ValueError("Key must be exactly 16 bytes")
            self.start_key = new_start_key

        self.current_key = self.start_key
        self.attempts = 0

    def is_at_end(self) -> bool:
        """Check if current key is at the end (FF...FF)"""
        return self.current_key == self.end_key


# Default manufacturer key for ULC
# Hex: 49 45 4D 4B 41 45 52 42 21 4E 41 43 55 4F 59 46
# ASCII: "IEMKAERB!NACUOYF" = "BREAKMEIFYOUCAN!" reversed
DEFAULT_MANUFACTURER_KEY = bytes.fromhex('49454D4B41455242214E4143554F5946')


def create_key_generator(start_key_hex: str) -> KeyGenerator:
    """
    Create key generator from hex string

    Args:
        start_key_hex: Hex string of start key

    Returns:
        KeyGenerator instance
    """
    start_key = KeyGenerator.parse_key(start_key_hex)
    return KeyGenerator(start_key)


def generate_random_key() -> bytes:
    """
    Generate a cryptographically secure random 16-byte key

    Returns:
        16-byte random key
    """
    return secrets.token_bytes(16)


def check_des_parity(key: bytes) -> tuple[bool, list[int]]:
    """
    Check DES parity bits for a 16-byte key

    DES uses odd parity: each byte should have an odd number of 1 bits.
    The 8th bit (LSB) of each byte is the parity bit.

    Args:
        key: 16-byte key to check

    Returns:
        Tuple of (all_valid: bool, invalid_byte_positions: list[int])
        - all_valid: True if all bytes have correct parity
        - invalid_byte_positions: List of byte positions (0-15) with incorrect parity
    """
    if len(key) != 16:
        raise ValueError(f"Key must be exactly 16 bytes, got {len(key)}")

    invalid_positions = []

    for i, byte in enumerate(key):
        # Count the number of 1 bits in the byte
        ones_count = bin(byte).count('1')

        # DES uses odd parity - the number of 1s should be odd
        if ones_count % 2 == 0:  # Even number of 1s = incorrect parity
            invalid_positions.append(i)

    all_valid = len(invalid_positions) == 0
    return all_valid, invalid_positions


def fix_des_parity(key: bytes) -> bytes:
    """
    Fix DES parity bits for a 16-byte key

    Adjusts the LSB (8th bit) of each byte to ensure odd parity.

    Args:
        key: 16-byte key to fix

    Returns:
        16-byte key with correct DES parity bits
    """
    if len(key) != 16:
        raise ValueError(f"Key must be exactly 16 bytes, got {len(key)}")

    fixed_key = bytearray(key)

    for i in range(16):
        byte = fixed_key[i]

        # Count 1s in the upper 7 bits (ignore LSB parity bit)
        ones_count = bin(byte >> 1).count('1')

        # Set LSB to make total count odd
        if ones_count % 2 == 0:  # Even number of 1s in upper 7 bits
            fixed_key[i] = byte | 0x01  # Set LSB to 1
        else:  # Odd number of 1s in upper 7 bits
            fixed_key[i] = byte & 0xFE  # Clear LSB to 0

    return bytes(fixed_key)
