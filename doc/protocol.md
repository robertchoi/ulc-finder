# PN512 NFC/RFID Reader Firmware

## Project Overview

**Organization**: TITENG Co., LTD.
**Version**: v004 (2022-09-02)
**Target Hardware**: STM32F103xB (ARM Cortex-M3) or GD32F103
**NFC Chipset**: NXP PN512
**IDE**: IAR Embedded Workbench for ARM 7.40+

This firmware implements a USB CCID (Chip Card Interface Device) compliant NFC/RFID reader that supports:
- Contactless NFC/RFID cards (ISO14443A/B, Mifare, FeliCa, ISO15693)
- Contact-based smart cards (EMV, SAM interfaces)
- Mifare Ultralight, Ultralight C, Ultralight EV1
- USB and UART communication interfaces

---

## Communication Protocols

### USB Interface (Primary)

The device implements **USB CCID 1.1** protocol for smart card reader communication.

#### USB Configuration
- **Device Class**: CCID (0x0B)
- **Protocol**: CCID 1.1
- **Endpoints**:
  - Bulk IN (reader → host)
  - Bulk OUT (host → reader)
  - Interrupt IN (notifications)
- **Speed**: Full-speed USB (12 Mbps)

#### CCID Message Format

All CCID messages follow a 10-byte header + data format:

```
┌──────────────┬────────────────────────────────────────────────┐
│ Byte Offset  │ Field Name                                     │
├──────────────┼────────────────────────────────────────────────┤
│ 0            │ bMessageType (Command/Response type)           │
│ 1-4          │ dwLength (Data length, excluding header)       │
│ 5            │ bSlot (Slot number: 0-4)                       │
│ 6            │ bSeq (Sequence number)                         │
│ 7            │ bSpecific_0 (Command-specific parameter)       │
│ 8            │ bSpecific_1 (Command-specific parameter)       │
│ 9            │ bSpecific_2 (Command-specific parameter)       │
│ 10+          │ abData[] (Payload data, max 261 bytes)         │
└──────────────┴────────────────────────────────────────────────┘
```

#### CCID Command Messages (PC → Reader)

| Message Type | Code | Description |
|--------------|------|-------------|
| `PC_to_RDR_IccPowerOn` | 0x62 | Power on ICC and get ATR |
| `PC_to_RDR_IccPowerOff` | 0x63 | Power off ICC |
| `PC_to_RDR_GetSlotStatus` | 0x65 | Get current slot status |
| `PC_to_RDR_XfrBlock` | 0x6F | Transfer data block (APDU) |
| `PC_to_RDR_GetParameters` | 0x6C | Get ICC parameters |
| `PC_to_RDR_ResetParameters` | 0x6D | Reset ICC parameters |
| `PC_to_RDR_SetParameters` | 0x61 | Set ICC parameters |
| `PC_to_RDR_Escape` | 0x6B | Vendor-specific command |
| `PC_to_RDR_IccClock` | 0x6E | Control ICC clock |
| `PC_to_RDR_T0APDU` | 0x6A | T=0 APDU command |
| `PC_to_RDR_Secure` | 0x69 | Secure message |
| `PC_to_RDR_Mechanical` | 0x71 | Mechanical control |
| `PC_to_RDR_Abort` | 0x72 | Abort current operation |
| `PC_to_RDR_SetDataRateAndClock` | 0x73 | Set data rate and clock |

#### CCID Response Messages (Reader → PC)

| Message Type | Code | Description |
|--------------|------|-------------|
| `RDR_to_PC_DataBlock` | 0x80 | Response with data |
| `RDR_to_PC_SlotStatus` | 0x81 | Slot status response |
| `RDR_to_PC_Parameters` | 0x82 | ICC parameters |
| `RDR_to_PC_Escape` | 0x83 | Vendor-specific response |
| `RDR_to_PC_DataRateAndClock` | 0x84 | Data rate/clock response |
| `RDR_to_PC_NotifySlotChange` | 0x50 | Slot change notification |
| `RDR_to_PC_HardwareError` | 0x51 | Hardware error |

#### Response Status Codes

**bStatus (Byte 7)**:
- `0x00`: Command processed successfully
- `0x40`: Command failed
- `0x80`: Time extension requested

**bError (Byte 8)** - CCID Specification Section 6.2.6:
- `0x00`: No error
- `0x01`: CMD_ABORTED
- `0x02`: ICC_MUTE
- `0x03`: XFR_PARITY_ERROR
- `0x04`: XFR_OVERRUN
- `0x05`: HW_ERROR
- `0x06`: BAD_ATR_TS
- `0x07`: BAD_ATR_TCK
- `0x08`: ICC_PROTOCOL_NOT_SUPPORTED
- `0x09`: ICC_CLASS_NOT_SUPPORTED
- `0x0A`: PROCEDURE_BYTE_CONFLICT
- `0x0B`: DEACTIVATED_PROTOCOL
- `0x0C`: BUSY_WITH_AUTO_SEQUENCE
- `0x0D`: PIN_TIMEOUT
- `0x0E`: PIN_CANCELLED
- `0x0F`: CMD_SLOT_BUSY
- `0x69`: Authentication error (custom)

#### Escape Commands (Vendor-Specific)

Escape commands are sent via `PC_to_RDR_Escape (0x6B)` with custom payload:

| Command | Code | Parameters | Description |
|---------|------|------------|-------------|
| LED Control | 0x00 | [channel, mode] | Control LED on/off |
| Antenna LED Control | 0x01 | [LED1/2, LED3/4] | Control antenna LEDs |
| Get Version | 0x02 | - | Get firmware version |
| RF Polling | 0x03 | [type] | RF card polling control |
| Card Move Request | 0x50 | - | Request card presence notification |
| Jump to Bootloader | 'Z' | - | Enter firmware update mode |
| Antenna Select | 'A' | [antenna] | Select antenna (1-4) |
| Communication Select | 'B' | [mode] | Select communication mode |

**Example: Get Firmware Version**
```
Request:
  [0x6B][0x01][0x00][0x00][0x00][0x00][0xXX][0x00][0x00][0x00][0x02]

Response:
  [0x83][0x02][0x00][0x00][0x00][0x00][0xXX][0x00][0x00][0x00]['v']['0']['0']['4']
```

---

### UART Interface (Secondary)

The device supports 3 USART interfaces for serial communication and SAM module control.

#### UART Configuration

| UART | Port | Default Use | Baud Rate |
|------|------|-------------|-----------|
| USART1 (COM1) | HOST_PORT | Host communication | Configurable |
| USART2 (COM2) | USB_SAM1_PORT | SAM1 module | Configurable |
| USART3 (COM3) | USB_SAM2_PORT | SAM2 module | Configurable |
| UART4 (COM4) | USB_RF_PORT | Reserved | Configurable |
| UART5 (COM5) | DEBUG_PORT | Debug output | Configurable |

#### Supported Baud Rates
- 9600 bps
- 19200 bps
- 38400 bps
- 57600 bps
- 76800 bps
- 115200 bps

#### UART Protocol

The UART interface uses the same CCID message format as USB, allowing transparent bridging between USB and serial interfaces.

**Card Insertion Notification** (when `USB_CCID_SERIAL_INSERT_DEF = 1`):
- Card presence/removal events are sent via UART
- Uses `RDR_to_PC_NotifySlotChange (0x50)` message

#### UART API Functions

```c
// Initialize UART
void busart1_initialization(unsigned int bps);
void busart2_initialization(unsigned int bps);
void busart3_initialization(unsigned int bps);

// Send data
void buart_send_byte(unsigned char com, unsigned char data);
void buart_send_datas(unsigned char com, unsigned char *data, unsigned int len);

// Receive data (circular queue based)
unsigned char buart_rx_status_check(int com);  // Returns CQ_EXIST_DATA or CQ_NONE_DATA
unsigned char buart_rev_data(unsigned char com, unsigned char *data);

// Clear receive buffer
void buart_rxfifo_clear(unsigned char com);

// Debug output
void bdbg_printf(unsigned char com, char *fmt, ...);
void bprint_hex(unsigned char com, unsigned char *addr, unsigned int len, char *from, ...);
```

#### ASCII Control Characters

The UART driver defines standard ASCII control characters:

| Character | Code | Description |
|-----------|------|-------------|
| STX | 0x02 | Start of text |
| ETX | 0x03 | End of text |
| EOT | 0x04 | End of transmission |
| ACK | 0x06 | Acknowledge |
| NAK | 0x15 | Negative acknowledge |
| CR | 0x0D | Carriage return |
| LF | 0x0A | Line feed |

---

## Operating Modes

The device supports multiple operating modes, selected via the `Interface_mode` global variable:

| Mode | Value | Description |
|------|-------|-------------|
| Normal_Mode | 5 | Default smart card interface mode |
| RF_Mode | 0 | Contactless NFC/RFID card polling |
| SAM1_Mode | 1 | Secure Access Module 1 interface |
| SAM2_Mode | 2 | Secure Access Module 2 interface |
| SAM3_Mode | 3 | Secure Access Module 3 interface |
| SAM4_Mode | 4 | Secure Access Module 4 interface |

### Slot Mapping

The device supports 5 card slots (0-4):
- **Slot 0**: RF/NFC contactless cards (when in RF_Mode)
- **Slot 1**: SAM1 module
- **Slot 2**: SAM2 module
- **Slot 3**: SAM3 module
- **Slot 4**: SAM4 module

---

## Supported Card Types

### Contactless NFC/RFID Cards

The firmware supports various card types through the NXP PN512 chipset and NFC Reader Library v4.40.5:

#### ISO 14443 Type A Cards

| Card Type | ATQA | SAK | Memory | Authentication | Features |
|-----------|------|-----|--------|----------------|----------|
| **Mifare Classic 1K** | 0x0004 | 0x08 | 1024 bytes | CRYPTO1 (48-bit key) | 16 sectors × 4 blocks |
| **Mifare Classic 4K** | 0x0002 | 0x18 | 4096 bytes | CRYPTO1 (48-bit key) | 32 sectors + 8 sectors |
| **Mifare Ultralight** | 0x0044 | 0x00 | 64 bytes | None | 16 pages × 4 bytes |
| **Mifare Ultralight C** | 0x0044 | 0x00 | 192 bytes | 3DES (16-byte key) | 48 pages × 4 bytes, automatic auth |
| **Mifare Ultralight EV1** | 0x0044 | 0x00 | 64-192 bytes | None | Enhanced features, counters |
| **Mifare DESFire EV1/2/3** | 0x0344 | 0x20 | 2KB-8KB | 3DES/AES | File system, multiple apps |
| **NTAG 21x Series** | 0x0044 | 0x00 | 144-888 bytes | Password (32-bit) | NFC Forum Type 2 |

#### ISO 14443 Type B Cards

| Card Type | ATQB | Features |
|-----------|------|----------|
| **Calypso** | Various | Public transport ticketing |
| **SRI512/SRIX4K** | Various | Storage cards |

#### ISO 15693 Cards (Vicinity Cards)

| Card Type | Frequency | Features |
|-----------|-----------|----------|
| **ICODE SLI/SLIX** | 13.56 MHz | Inventory, EAS |
| **Tag-it HF-I** | 13.56 MHz | Library, asset tracking |

#### FeliCa Cards

| Card Type | IDm | Features |
|-----------|-----|----------|
| **FeliCa Standard** | 8 bytes | Sony contactless IC |
| **FeliCa Lite** | 8 bytes | Reduced memory version |

### Contact-based Smart Cards

#### EMV Payment Cards
- **EMV Level 1**: Physical/electrical interface (ISO 7816-3)
- **EMV Level 2**: Payment application (Visa, Mastercard, etc.)
- **T=0 Protocol**: Character-oriented transmission
- **T=1 Protocol**: Block-oriented transmission

#### SIM/SAM Cards
- **GSM SIM**: Subscriber Identity Module
- **SAM (Secure Access Module)**: Up to 4 SAM slots supported
- **UICC**: Universal Integrated Circuit Card

### Supported Protocols and Standards

| Protocol/Standard | Description | Supported Operations |
|-------------------|-------------|---------------------|
| **ISO 14443-3** | Contactless initialization and anticollision | Card detection, UID read, SAK/ATQA |
| **ISO 14443-4** | Transmission protocol (T=CL) | APDU exchange, block chaining |
| **ISO 15693** | Vicinity cards | Inventory, read/write blocks |
| **ISO 7816-3** | Contact cards physical interface | ATR parsing, T=0/T=1 protocols |
| **EMV 4.x** | Payment card application | PSE selection, application selection, GPO |
| **NFC Forum Type 2** | NDEF message format | NDEF read/write (Ultralight, NTAG) |
| **FeliCa** | Sony contactless standard | Read/write blocks, polling |

### Card Detection and Automatic Handling

The firmware implements automatic card type detection and authentication:

#### Ultralight C (ULC) - Automatic Authentication
```c
// ULC cards are automatically authenticated with default manufacturer key
// Key: "BREAKMEIFYOUCAN!" (reversed)
// Stored in KeyStore slot 2: 49 45 4D 4B 41 45 52 42 21 4E 41 43 55 4F 59 46

// Authentication is automatic when accessing protected pages (Page 4+)
// Pages 0-3 (UID, OTP) are readable without authentication

uint8_t data[16];
// First read to protected page triggers authentication
phalMful_Read(&salMFUL, 0x04, data);  // Returns 00 (authentication in progress)
// Second read returns actual data
phalMful_Read(&salMFUL, 0x04, data);  // Returns actual page data
```

#### Mifare Classic - Key-based Authentication
```c
// Authenticate before read/write
uint8_t key[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};  // Default key
phalMfc_Authenticate(&salMFC, blockNum, PHHAL_HW_MFC_KEYA, key, uid);

// Read 16-byte block
uint8_t data[16];
phalMfc_Read(&salMFC, blockNum, data);

// Write 16-byte block
uint8_t writeData[16] = {...};
phalMfc_Write(&salMFC, blockNum, writeData);
```

#### Card Type Detection
```c
uint8_t cardType = DetectUltralightType();

switch(cardType) {
    case CARD_TYPE_MIFARE_UL_C:
        // Ultralight C - 3DES authentication, 192 bytes
        // Automatic authentication with default key
        break;
    case CARD_TYPE_MIFARE_UL_EV1:
        // Ultralight EV1 - Enhanced features, counters
        break;
    case CARD_TYPE_MIFARE_ULTRALIGHT:
        // Classic Ultralight - 64 bytes, no authentication
        break;
    case CARD_TYPE_MIFARE_CLASSIC:
        // Mifare Classic - CRYPTO1 authentication required
        break;
    case CARD_TYPE_MIFARE_DESFIRE:
        // DESFire - File system, AES/3DES authentication
        break;
}
```

### Mifare Ultralight C 상세 가이드

#### ULC 메모리 맵 (192 bytes, 48 pages)

| Page Range | Address | Bytes | Usage | Access | Description |
|------------|---------|-------|-------|--------|-------------|
| 0-1 | 0x00-0x01 | 8 | UID | Read-only | 7바이트 UID + BCC0 |
| 2-3 | 0x02-0x03 | 8 | Lock/OTP | OTP/Read-only | Lock Bytes 0-1 + OTP (4 bytes) |
| 4-39 | 0x04-0x27 | 144 | User Memory | R/W | 사용자 데이터 영역 |
| 40 | 0x28 | 4 | Lock Bytes 2-3 | OTP | 상위 페이지 잠금 제어 |
| 41 | 0x29 | 4 | Counter | Read-only | 16비트 단방향 카운터 |
| 42 | 0x2A | 4 | AUTH0 | R/W | 인증 시작 페이지 설정 |
| 43 | 0x2B | 4 | AUTH1 | R/W | 인증 모드 설정 |
| 44-47 | 0x2C-0x2F | 16 | 3DES Key | Write-only | 3DES 인증 키 (OTP 특성) |

#### Page 0x02 - Lock Bytes 0-1 (기본 잠금 바이트)

**메모리 구조:**
```
Page 2 (0x02): [UID Byte 7] [Internal] [Lock Byte 0] [Lock Byte 1]
               └─ 읽기전용 ─┘ └읽기전용┘ └───── OTP 특성 ─────┘
```

**Lock Byte 0 (Byte 2 of Page 0x02):**
```
Bit 7 | Bit 6 | Bit 5 | Bit 4 | Bit 3      | Bit 2      | Bit 1      | Bit 0
──────┼───────┼───────┼───────┼────────────┼────────────┼────────────┼─────────
 L15  |  L14  |  L13  |  L12  | BL-OTP(11) | BL-OTP(10) | BL-OTP(9)  | BL-OTP(3)
      |       |       |       | Pages 11-8 | Pages 10-8 | Pages 9-4  | Page 3
```

**Bit 설명:**
- **Bit 0 (0x01)**: Block-Locking Bit for Page 3 (OTP)
  - 1로 설정 시: Page 3의 잠금 상태가 영구 고정 (Lock Byte 1의 Bit 0 수정 불가)
- **Bit 1 (0x02)**: Block-Locking Bit for Pages 4-9
  - 1로 설정 시: Pages 4-9의 잠금 설정이 영구 고정
- **Bit 2 (0x04)**: Block-Locking Bit for Pages 10-15
  - 1로 설정 시: Pages 10-15의 잠금 설정이 영구 고정
- **Bit 3-7**: Individual Page Locking Bits for Pages 12-15
  - 1로 설정 시: 해당 페이지 영구 읽기 전용

**Lock Byte 1 (Byte 3 of Page 0x02):**
```
Bit 7 | Bit 6 | Bit 5 | Bit 4 | Bit 3 | Bit 2 | Bit 1 | Bit 0
──────┼───────┼───────┼───────┼───────┼───────┼───────┼───────
 L11  |  L10  |  L9   |  L8   |  L7   |  L6   |  L5   |  L4
```

**Bit 설명:**
- **Bit 0 (0x01)**: Lock Page 4
- **Bit 1 (0x02)**: Lock Page 5
- **Bit 2 (0x04)**: Lock Page 6
- **Bit 3 (0x08)**: Lock Page 7
- **Bit 4 (0x10)**: Lock Page 8
- **Bit 5 (0x20)**: Lock Page 9
- **Bit 6 (0x40)**: Lock Page 10
- **Bit 7 (0x80)**: Lock Page 11

**OTP 특성:**
- Lock Byte 0-1은 **비트 OR 연산**으로 쓰기됩니다
- 한 번 1로 설정된 비트는 0으로 되돌릴 수 없습니다
- 쓰기 예제:
  ```
  현재 값: 00 00
  Write:   03 01  (Page 3과 Page 4 잠금)
  결과:    03 01

  추가 Write: 00 02  (Page 5 추가 잠금)
  결과:       03 03  (비트 OR: 01 | 02 = 03)
  ```

**Block-Locking Bit의 중요성:**
- Block-Locking Bit를 1로 설정하면 해당 범위의 잠금 설정이 **영구 고정**됩니다
- 예: Lock Byte 0의 Bit 1을 1로 설정하면, Lock Byte 1의 Bit 0-5 (Pages 4-9)는 더 이상 수정 불가
- **권장**: 데이터 완전 확정 후 최종 단계에서만 Block-Locking Bit 설정

**사용 예제:**

**예제 1: Page 3 (OTP) 잠금**
```
// Page 3을 읽기 전용으로 설정
Write to Page 0x02: [XX] [XX] [01] [00]
                                └── Lock Byte 0, Bit 0 = 1 (BL-OTP for Page 3)

// Page 3 잠금 상태 영구 고정 (선택사항)
Write to Page 0x02: [XX] [XX] [01] [00]
                                └── 동일 명령 (이미 1이므로 변화 없음)
```

**예제 2: Pages 4-7 잠금**
```
// Pages 4-7을 개별 잠금
Write to Page 0x02: [XX] [XX] [00] [0F]
                                     └── Lock Byte 1: 0x0F = Bits 0-3 = Pages 4-7

// Pages 4-9 범위 잠금 설정 영구 고정
Write to Page 0x02: [XX] [XX] [02] [0F]
                                └── Lock Byte 0, Bit 1 = 1 (Block-Lock Pages 4-9)
```

**예제 3: 단계적 잠금**
```
// 1단계: Page 5만 잠금
Write: [XX] [XX] [00] [02]  → Lock Byte 1 = 0x02 (Page 5)

// 2단계: Page 6도 추가 잠금
Write: [XX] [XX] [00] [04]  → Lock Byte 1 = 0x06 (비트 OR: 02 | 04)

// 3단계: Pages 4-9 잠금 설정 영구 고정
Write: [XX] [XX] [02] [00]  → Lock Byte 0 = 0x02 (Block-Lock)
```

**CCID 명령 예제:**

**Page 0x02 읽기:**
```
6F 05 00 00 00 00 01 00 00 00 FF B0 00 02 10

응답 예:
80 10 00 00 00 00 01 00 00 00 [UID7] [Int] [LB0] [LB1] [BCC1] ...
                               └───────────────────┘
                               Page 2 내용
```

**Page 3 잠금 설정:**
```
// Page 3를 읽기 전용으로 설정
6F 09 00 00 00 00 02 00 00 00 FF D6 00 02 04 00 00 01 00
                                                    └─ Lock Byte 0 = 0x01

⚠️ 주의: 이 명령 후 Page 3은 영구 읽기 전용!
```

**Pages 4-7 잠금:**
```
// Pages 4-7 잠금
6F 09 00 00 00 00 03 00 00 00 FF D6 00 02 04 00 00 00 0F
                                                       └─ Lock Byte 1 = 0x0F

⚠️ 주의: 이 명령 후 Pages 4-7은 영구 읽기 전용!
```

**Block-Locking 설정:**
```
// Pages 4-9 잠금 설정 영구 고정
6F 09 00 00 00 00 04 00 00 00 FF D6 00 02 04 00 00 02 00
                                                    └─ Lock Byte 0, Bit 1 = 1

⚠️ 주의: 이 명령 후 Lock Byte 1의 Bits 0-5는 더 이상 수정 불가!
```

**주의사항:**
1. **비가역성**: Lock Bytes는 한 번 설정하면 되돌릴 수 없습니다
2. **테스트 카드 사용**: 프로덕션 전 반드시 테스트 카드로 실험
3. **Block-Locking 신중히**: Block-Locking Bit 설정 후에는 잠금 해제 불가능
4. **단계적 접근**: 필요한 페이지만 순차적으로 잠금, 한 번에 모두 잠그지 말 것
5. **백업**: 중요한 데이터는 잠금 전 백업 필수

#### Page 40-48 상세 설명

**Page 40 (0x28): Lock Bytes 2-3 (상위 페이지 잠금 바이트)**
```
Page 40 (0x28): [Lock Byte 2] [Lock Byte 3] [Reserved] [Reserved]

구조:
  Byte 0-1: Lock Bytes 2-3 (Pages 16-39 잠금 제어)
  Byte 2-3: Reserved (00 00)

Lock Byte 2 (Byte 0 of Page 0x28):
  각 비트가 4개 페이지 블록을 잠금
  Bit 0 (0x01): Pages 16-19 잠금
  Bit 1 (0x02): Pages 20-23 잠금
  Bit 2 (0x04): Pages 24-27 잠금
  Bit 3 (0x08): Pages 28-31 잠금
  Bit 4 (0x10): Pages 32-35 잠금
  Bit 5 (0x20): Pages 36-39 잠금
  Bit 6-7: Reserved

Lock Byte 3 (Byte 1 of Page 0x28):
  Block-Locking Bits for Lock Byte 2
  Bit 0 (0x01): Lock Byte 2 영구 고정
  Bit 1-7: Reserved

OTP 특성:
  - 비트 OR 연산으로 쓰기
  - 한 번 1로 설정된 비트는 0으로 되돌릴 수 없음

예제:
  // Pages 16-19 잠금
  Write to Page 0x28: [01] [00] [00] [00]

  // Lock Byte 2 영구 고정
  Write to Page 0x28: [01] [01] [00] [00]
```

**Page 41 (0x29): Counter (카운터)**
```
Page 41 (0x29): [Counter Low] [Counter High] [Counter Valid] [Reserved]

구조:
  Byte 0: Counter Low Byte
  Byte 1: Counter High Byte
  Byte 2: Counter Valid Flag
  Byte 3: Reserved (00)

기능:
  - 16비트 단방향 카운터 (0x0000 → 0xFFFF)
  - 읽기 전용 (증가 명령으로만 수정 가능)
  - 주로 재생 공격 방지, 티켓 사용 횟수 추적용

증가 명령:
  INCR_CNT (0x39) 명령으로 카운터 증가
  증가만 가능, 감소 불가
```

**Page 42 (0x2A): AUTH0 (인증 시작 페이지)**
```
Page 42 (0x2A): [AUTH0] [Reserved] [Reserved] [Reserved]

AUTH0 (Byte 0):
  인증이 필요한 시작 페이지 번호 설정

  값의 의미:
  - 0x00: 인증 비활성화 (모든 페이지 자유 접근)
  - 0x03: Page 3부터 인증 필요
  - 0x04: Page 4부터 인증 필요 (권장 기본값)
  - 0x30: Page 48부터 인증 필요
  - 0xFF: 인증 비활성화

예제:
  // Page 4부터 인증 필요
  Write to Page 0x2A: [04] [00] [00] [00]

  // 모든 페이지 자유 접근 (인증 없음)
  Write to Page 0x2A: [FF] [00] [00] [00]
```

**Page 43 (0x2B): AUTH1 (인증 모드 설정)**
```
Page 43 (0x2B): [AUTH1] [Reserved] [Reserved] [Reserved]

AUTH1 (Byte 0):
  인증 후 접근 제어 모드 설정

  Bit 0 (0x01): Write access restriction
    - 0: 읽기는 자유, 쓰기만 인증 필요
    - 1: 쓰기만 인증 필요

  Bit 1 (0x02): Read and Write access restriction
    - 0: Bit 0에 따름
    - 1: 읽기/쓰기 모두 인증 필요 (권장)

  Bit 2-7: Reserved

권장 설정:
  AUTH1 = 0x00: 읽기 자유, 쓰기 인증 필요
  AUTH1 = 0x01: 쓰기만 인증 필요
  AUTH1 = 0x02: 읽기/쓰기 모두 인증 필요 (보안 강화)

예제:
  // 읽기/쓰기 모두 인증 필요
  Write to Page 0x2B: [02] [00] [00] [00]

  // 쓰기만 인증 필요
  Write to Page 0x2B: [01] [00] [00] [00]
```

**Page 44-47: 3DES Authentication Key (인증 키)**
```
Page 44 (0x2C): Key[0-3]
Page 45 (0x2D): Key[4-7]
Page 46 (0x2E): Key[8-11]
Page 47 (0x2F): Key[12-15]

특징:
  - 16바이트 3DES 키 (2K3DES)
  - 쓰기만 가능 (Write-Only)
  - 읽기 시도 시 실패
  - 한 번만 쓰기 가능 (OTP)
  - 기본값: 49 45 4D 4B 41 45 52 42 21 4E 41 43 55 4F 59 46
            (ASCII: "IEMKAERB!NACUOYF" = "BREAKMEIFYOUCAN!" 역순)
```

**Page 48: Authentication Configuration (인증 설정)**
```
Page 48 (0x30): [AUTH0] [AUTH1] [Reserved] [Reserved]

AUTH0: 인증 필요 시작 페이지
  - 0x00: 인증 비활성화 (모든 페이지 자유 접근)
  - 0x03: Page 3부터 인증 필요
  - 0x04: Page 4부터 인증 필요 (기본값)
  - 0x30: Page 48부터 인증 필요

AUTH1: 인증 모드 설정
  - Bit 0 (0x01): Write access restriction
  - Bit 1 (0x02): Read and Write access restriction (권장)

예제:
  AUTH0=0x04, AUTH1=0x00: Page 4 이상 쓰기만 인증 필요
  AUTH0=0x04, AUTH1=0x01: Page 4 이상 쓰기만 인증 필요
  AUTH0=0x04, AUTH1=0x02: Page 4 이상 읽기/쓰기 모두 인증 필요
```

#### ULC Read/Write 명령어

**CCID를 통한 READ 명령:**
```
// Page 5 읽기 (인증 불필요한 경우)
6F 05 00 00 00 00 02 00 00 00 FF B0 00 05 10

// Page 40 읽기 (Lock Bytes)
6F 05 00 00 00 00 02 00 00 00 FF B0 00 28 10

APDU 구조:
  CLA: FF (Proprietary)
  INS: B0 (READ BINARY)
  P1:  00
  P2:  05 (Page address)
  Le:  10 (16 bytes = 4 pages)

응답:
  80 10 00 00 00 00 02 00 00 00 [16 bytes data]
```

**CCID를 통한 WRITE 명령:**
```
// Page 5에 데이터 쓰기
6F 09 00 00 00 00 04 00 00 00 FF D6 00 05 04 11 22 33 44

// Page 40에 Lock Bit 설정 (주의: OTP!)
6F 09 00 00 00 00 04 00 00 00 FF D6 00 28 04 04 00 00 00

APDU 구조:
  CLA: FF
  INS: D6 (UPDATE BINARY)
  P1:  00
  P2:  05 (Page address)
  Lc:  04 (4 bytes)
  Data: 11 22 33 44 (4 bytes per page)

응답:
  80 00 00 00 00 00 04 00 00 00
```

#### ULC 커스텀 키 설정 방법

**Step 1: 키 준비**
```
// 16바이트 3DES 키 생성
예: 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F 10
```

**Step 2: 리더기에 키 로딩 (INS_LOAD_AUTH)**
```
// CCID Escape 명령으로 키 로드
6F 15 00 00 00 00 01 00 00 00 FF 82 00 03 10 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F 10

설명:
  FF 82: LOAD AUTHENTICATION KEYS
  P1: 00
  P2: 03 (KeyStore Slot 3)
  Lc: 10 (16 bytes)
  Data: 01 02 03 04 ... 10 (16-byte key)

응답:
  80 02 00 00 00 00 01 00 00 00 90 00
  (90 00 = Success)
```

**Step 3: 카드에 키 쓰기 (Pages 44-47)**
```
// Page 44 쓰기 (Key bytes 0-3)
6F 09 00 00 00 00 02 00 00 00 FF D6 00 2C 04 01 02 03 04

// Page 45 쓰기 (Key bytes 4-7)
6F 09 00 00 00 00 03 00 00 00 FF D6 00 2D 04 05 06 07 08

// Page 46 쓰기 (Key bytes 8-11)
6F 09 00 00 00 00 04 00 00 00 FF D6 00 2E 04 09 0A 0B 0C

// Page 47 쓰기 (Key bytes 12-15)
6F 09 00 00 00 00 05 00 00 00 FF D6 00 2F 04 0D 0E 0F 10

⚠️ 중요: Pages 44-47은 단 한 번만 쓸 수 있습니다!
        잘못 쓰면 복구 불가능!
```

**Step 4: 인증 설정 (Page 48)**
```
// Page 4부터 읽기/쓰기 인증 필요로 설정
6F 09 00 00 00 00 06 00 00 00 FF D6 00 30 04 04 01 00 00

AUTH0 = 0x04: Page 4부터 보호
AUTH1 = 0x01: 쓰기만 인증 필요 (또는 0x02: 읽기/쓰기 모두)
```

**Step 5: 커스텀 키로 인증 테스트**
```
// 카드 Power ON
62 00 00 00 00 00 00 00 00 00

// 리더기에 커스텀 키 로드 (Slot 3)
6F 15 00 00 00 00 01 00 00 00 FF 82 00 03 10 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F 10

// 보호된 페이지 읽기 시도 (자동 인증)
6F 05 00 00 00 00 02 00 00 00 FF B0 00 04 10

// 첫 번째 READ는 인증만 수행 (응답: 00 00 00 00...)
// 두 번째 READ에서 실제 데이터 반환
6F 05 00 00 00 00 03 00 00 00 FF B0 00 04 10
```

#### ULC 보안 권장 사항

1. **키 관리**
   - 기본 제조사 키 절대 사용 금지
   - 카드별로 고유한 랜덤 키 생성
   - 키를 안전한 데이터베이스에 UID와 함께 저장

2. **Lock Bytes 설정 주의**
   - Pages 40-41은 OTP (한 번만 쓰기 가능)
   - 잘못 설정 시 되돌릴 수 없음
   - 테스트용 카드로 먼저 실험

3. **인증 키 쓰기 주의**
   - Pages 44-47은 단 한 번만 쓰기 가능
   - 쓰기 전 키 값 3중 확인
   - 백업 카드 준비

4. **AUTH0/AUTH1 설정**
   - 프로덕션 전 테스트 필수
   - AUTH0=0x03으로 설정하면 UID도 보호됨
   - AUTH1=0x02 (읽기/쓰기 모두 보호) 권장

#### ULC Authentication (3DES 인증)

**Default Manufacturer Key** (Key #2):
```
ASCII: "IEMKAERB!NACUOYF"
Hex:   49 45 4D 4B 41 45 52 42 21 4E 41 43 55 4F 59 46
Note:  "BREAKMEIFYOUCAN!" 문자열을 역순으로 배열
```

**펌웨어의 자동 인증 처리**:
```c
// 펌웨어는 Page 4 이상 접근 시 자동으로 인증 수행
// ULC_Active_KeySlot 변수가 사용할 키 슬롯 지정 (기본: Slot 2)

// 1. 첫 번째 READ: 인증만 수행
phalMful_Read(&salMFUL, 0x04, data);  // Returns 00 (인증 진행 중)

// 2. 두 번째 READ: 실제 데이터 반환
phalMful_Read(&salMFUL, 0x04, data);  // Returns actual data

// 인증 성공 후 ULC_Authenticated = 1로 설정됨
// Power OFF까지 인증 세션 유지
```

**수동 인증 예제**:
```c
// Authenticate with default key
phStatus_t status = phalMful_UlcAuthenticate(&salMFUL, 2, 0);

if(status == PH_ERR_SUCCESS) {
    // Authentication successful
    uint8_t data[16];
    phalMful_Read(&salMFUL, 0x04, data);  // Read pages 4-7
}
```

#### ULC Custom Key Loading (사용자 정의 키 로드)

펌웨어는 `INS_LOAD_AUTH` (0x82) 명령을 통해 사용자 정의 3DES 키를 동적으로 로드할 수 있습니다.

**CCID 명령 형식**:
```
FF 82 00 [KeySlot] 10 [16-byte 3DES Key]

Parameters:
- INS: 82 (LOAD AUTHENTICATION KEYS)
- P1:  00 (Reserved)
- P2:  [KeySlot] - Key slot number (0 = auto-assign to slot 3, or specify 3-15)
- Lc:  10 (16 bytes for ULC 3DES key)
- Data: 16-byte 3DES key (2K3DES format)
```

**Host Application 사용 예시**:
```
1. Power ON card:
   6F 0A 00 00 00 00 01 00 00 00

2. Load custom key into slot 3:
   6F 1A 00 00 00 00 01 00 00 00 FF 82 00 03 10
   [11 22 33 44 55 66 77 88 99 AA BB CC DD EE FF 00]

3. Read protected page (automatically uses slot 3):
   6F 10 00 00 00 00 01 00 00 00 FF B0 00 04 10
   -> First read: Returns 00 (authentication in progress)
   -> Second read: Returns actual data

4. Power OFF to reset to default key:
   6F 0A 00 00 00 00 01 00 00 00 63
```

**Key Slot 관리**:
- **Slot 2**: 제조사 기본 키 (BREAKMEIFYOUCAN! reversed) - 항상 사용 가능
- **Slot 3-15**: 사용자 정의 키 - `INS_LOAD_AUTH`로 동적 로드
- **ULC_Active_KeySlot**: 현재 활성 키 슬롯 (기본값: 2)
- Power OFF 시 Slot 2로 자동 리셋

**구현 특징**:
- 키는 런타임에 KeyStore에 저장 (비휘발성 아님)
- 각 Power ON 세션마다 새로 로드 필요
- `ULC_Active_KeySlot` 변수가 어느 키를 사용할지 결정
- 인증 성공 시 `ULC_Authenticated = 1` 설정, Power OFF 시 리셋

**Error Handling**:
- Data length ≠ 0x10: Returns `bError = PH_ERR_INVALID_PARAMETER`
- KeyStore error: Returns `bError` with NXP library error code
- Success: Returns `90 00` (SW1 SW2)

---

## Build Instructions

### Prerequisites
- **IAR Embedded Workbench for ARM** version 7.40 or higher
- **Hardware**: STM32F103xB microcontroller development board
- **Debugger**: JTAG/SWD programmer (ST-Link, J-Link, etc.)

### Build Steps

1. **Open Project**
   ```
   File → Open Workspace
   Navigate to: TIT_IntegralAntPn512/EWARM/TIT-ICRFReader.eww
   ```

2. **Select Configuration**
   - Right-click project → Set as Active → Debug

3. **Build**
   - Press **F7** or Project → Make
   - Output: `EWARM/Debug/Exe/TIT-ICRFReader.out`

4. **Flash to Device**
   - Project → Download → Download Active Application
   - Or use external programmer with generated `.hex` file

### Build Configuration

The build uses the following key defines (in `main.c`):

```c
#define USB_DEVICE_USE_DEF          1   // Enable USB device mode
#define USB_CCID_SELF_POLLING_DEF   0   // Manual card polling (host-driven)
#define USB_CCID_SERIAL_INSERT_DEF  1   // Serial port card insertion notification
#define SAM_INTERFACE_EN            1   // Enable SAM interfaces
#define SLIM_DIP_LED_EN             0   // LED control for DIP board variant
```

### Memory Configuration

- **Flash**: 128KB (STM32F103xB)
- **SRAM**: 20KB
- **Linker Script**: `EWARM/stm32f103x8.icf`

---

## Hardware Configuration

### Pin Assignments

Refer to [platform_config.h](TIT_IntegralAntPn512/project/driver/system/platform_config.h) for complete pin mappings.

**Key Interfaces**:
- **SPI1/SPI2**: PN512 NFC chipset communication
- **USART1**: Host serial port
- **USART2**: SAM1 interface
- **USART3**: SAM2 interface
- **USB**: Full-speed USB device

### Clock Configuration

- **Source**: 16 MHz internal oscillator
- **System Clock**: 48 MHz (16 MHz × 3 PLL for USB)
- **Alternative**: 64 MHz (requires USB clock adjustment)

### Board Variants

- **Standard**: TIT_SLIM_MCRW
- **MON Board**: `TIT_MON_BOARD` (different GPIO mappings)
- **Antenna**: Supports switchable antenna configurations (1-4)

---

## Debugging

### Debug Output

Enable debug output in `RF_app.c`:
```c
#define RF_LIB_DEBUG    1
```

Debug messages are sent via UART (COM port configurable).

### Common Debug Points

1. **Card Power-On Failures**
   - Check `PC_to_RDR_IccPowerOn` handling in [ccid_process.c](TIT_IntegralAntPn512/project/ccid_process.c)
   - Monitor `bError` field in CCID responses

2. **Slot Status Errors**
   - Check `slotstatus[]` and `sloterror[]` arrays in IC structure

3. **SPI Communication Issues**
   - Verify PN512 register reads in SPI driver
   - Check clock speed and GPIO configuration

### Error Codes

CCID error codes follow USB CCID Specification v1.1, Section 6.2.6.

---

## API Usage Examples

### Example 1: Read Mifare Ultralight C Card

```c
#include "RF_app.h"

void read_ultralight_c_example(void)
{
    phStatus_t status;
    uint8_t cardType;
    uint8_t data[PHAL_MFUL_READ_BLOCK_LENGTH];  // 16 bytes

    // Detect card type
    cardType = DetectUltralightType();

    if(cardType == CARD_TYPE_MIFARE_UL_C) {
        // Authenticate with default manufacturer key (Key #2)
        status = phalMful_UlcAuthenticate(&salMFUL, 2, 0);

        if(status == PH_ERR_SUCCESS) {
            // Read pages 4-7 (16 bytes total)
            status = phalMful_Read(&salMFUL, 0x04, data);

            if(status == PH_ERR_SUCCESS) {
                // Process data
                // data[0-15] contains the read data
            }
        } else if(status == PH_ERR_AUTH_ERROR) {
            // Wrong key or authentication failed
        }
    }
}
```

### Example 2: Write to Ultralight C

```c
void write_ultralight_c_example(void)
{
    phStatus_t status;
    uint8_t writeData[PHAL_MFUL_WRITE_BLOCK_LENGTH] = {0x11, 0x22, 0x33, 0x44};

    // Authenticate first
    status = phalMful_UlcAuthenticate(&salMFUL, 2, 0);

    if(status == PH_ERR_SUCCESS) {
        // Write 4 bytes to page 4
        status = phalMful_Write(&salMFUL, 0x04, writeData);

        if(status == PH_ERR_SUCCESS) {
            // Write successful
        }
    }
}
```

### Example 3: Handle CCID Commands via USB

```c
void handle_ccid_command(uint8_t *rxbuf, uint8_t *txbuf)
{
    switch(rxbuf[0]) {  // bMessageType
        case PC_TO_RDR_ICCPOWERON:
            // Power on card and return ATR
            txbuf[0] = RDR_TO_PC_DATABLOCK;
            txbuf[7] = 0x00;  // bStatus: success
            txbuf[8] = 0x00;  // bError: no error
            // Add ATR data in txbuf[10+]
            break;

        case PC_TO_RDR_XFRBLOCK:
            // Exchange APDU with card
            // Process rxbuf[10+] as command APDU
            // Return response in txbuf[10+]
            break;

        case PC_TO_RDR_ESCAPE:
            // Vendor-specific command
            uint8_t escCmd = rxbuf[10];
            if(escCmd == 0x02) {  // Get version
                memcpy(&txbuf[10], "v004", 4);
                txbuf[1] = 4;  // dwLength
            }
            break;
    }
}
```

---

## Firmware Version History

| Version | Date | Changes |
|---------|------|---------|
| v0001 | 2020-10-05 | Initial STM32F103 → GD32F103 port, SPI/EXTI porting |
| v0001 | 2020-10-07 | SAM Power ON verification |
| v0001 | 2020-10-12 | SAM APDU support, USB module addition |
| v0001 | 2020-10-15 | Antenna selection, power timing optimization |
| v004 | 2022-09-02 | Current stable version with enhanced features |

---

## References

### Specifications
- **USB CCID**: USB Device Class Specification for CCID Rev 1.1
- **EMV**: EMVCo payment card standards
- **ISO/IEC 14443**: Contactless smart card standard
- **Mifare**: NXP Mifare product specifications

### Datasheets (in repository)
- [PN512 Full Datasheet](PN512_FULL-Datasheet.pdf) - NFC/RFID controller
- STM32F103 Reference Manual - Microcontroller reference
- GD32F103 Datasheet - Alternative MCU documentation
- [ANT Design AN1445](ANT_Design_AN1445.pdf) - Antenna design guidelines
- [Hardware Schematic](TIT-NUVIA-RF-READER-REV1_0.pdf)

### NXP Libraries
- **NFC Reader Library**: v4.40.5 (included in `Libraries/NxpNfcRdLib/`)
- Documentation: [Libraries/NxpNfcRdLib/docs/](TIT_IntegralAntPn512/Libraries/NxpNfcRdLib/docs/)

---

## License

Copyright (C) 2019-2022 TITENG Co., LTD.
All rights reserved.

---

## Support

For technical support or inquiries, please contact TITENG Co., LTD.

**Repository**: This firmware is maintained in a private Git repository.
**Build System**: IAR Embedded Workbench for ARM
**Target Platform**: STM32F103xB / GD32F103

## 다이렉트 커맨드 예제

### 명령어 해석

```
6F 15 00 00 00 00 20 00 00 00 FF D6 00 05 10 30 31 32 33 34 35 36 37 38 39 3A 3B 3C 3D 3E 3F 03 65
6F15000000000C000000FFD6000510303132333435363738393A3B3C3D3E3F
6F150000000001000000FF8200031001020304050607081112131415161718
암호화 활성화 명령 : 6F090000000004000000FFD6002A0404000000

28 라이팅 명령 : 6F090000000004000000FFD600280400000000
5페이지 Read 명령 : 6F050000000002000000FFB0000510
40페이지 Read 명령 : 6F050000000002000000FFB0002810
6F090000000004000000FFD6002A0400000000
```

#### CCID 헤더 (10바이트)

| Offset | Hex Value | Field | Description |
|--------|-----------|-------|-------------|
| 0 | 6F | bMessageType | `PC_to_RDR_XfrBlock` - APDU 전송 명령 |
| 1-4 | 15 00 00 00 | dwLength | 데이터 길이: 21 bytes (0x15) |
| 5 | 00 | bSlot | Slot 0 (RF/NFC contactless card) |
| 6 | 20 | bSeq | Sequence number: 32 |
| 7 | 00 | bBWI | Block Waiting time Integer |
| 8-9 | 00 00 | wLevelParameter | 0 (reserved) |

#### APDU 페이로드 (21바이트)

| Field | Hex Value | Description |
|-------|-----------|-------------|
| CLA | FF | Class byte (Mifare proprietary command) |
| INS | D6 | `UPDATE BINARY BLOCK` - Mifare 블록 쓰기 명령 |
| P1 | 00 | Parameter 1: 0 |
| P2 | 05 | Parameter 2: **Block number 5** (쓰기 대상 블록) |
| Lc | 10 | Data length: 16 bytes |
| Data | 30 31 32 33 34 35 36 37 38 39 3A 3B 3C 3D 3E 3F | Write data (16 bytes) |
| Le | 03 | Expected response length (optional) |
| - | 65 | Additional parameter (checksum or padding) |

#### 쓰기 데이터 분석

```
Hex:   30 31 32 33 34 35 36 37 38 39 3A 3B 3C 3D 3E 3F
ASCII: 0  1  2  3  4  5  6  7  8  9  :  ;  <  =  >  ?
```

### 명령 요약

**이 명령은 Mifare 카드의 블록 5번에 "0123456789:;<=>?" (16바이트)를 쓰는 명령입니다.**

- **카드 타입**: Mifare Classic (or compatible)
- **동작**: 블록 5번에 데이터 쓰기
- **데이터**: ASCII 문자열 "0123456789:;<=>?"
- **블록 크기**: 16 bytes

### Mifare Classic 메모리 구조

Mifare Classic 1K:
- **총 용량**: 1024 bytes
- **섹터**: 16개 (Sector 0-15)
- **블록/섹터**: 4개 (각 16바이트)
- **블록 5**: Sector 1, Block 1

```
Sector 1:
  Block 4: Data block (16 bytes)
  Block 5: Data block (16 bytes) ← 이 명령의 대상
  Block 6: Data block (16 bytes)
  Block 7: Trailer block (Key A, Access Bits, Key B)
```

### 주의사항

1. **인증 필요**: 블록 5에 쓰기 전에 Sector 1에 대한 인증이 필요합니다
   ```
   FF 86 00 00 05 01 00 05 60 00  // Authenticate with Key A
   ```

2. **Access Bits**: Sector trailer의 Access Bits 설정에 따라 쓰기 권한이 결정됩니다

3. **Key**: 기본 Mifare 키는 `FF FF FF FF FF FF` (Key A/B 모두)

### 예상 응답

**성공 시**:
```
80 00 00 00 00 00 20 00 00 00
```
- `80` = RDR_to_PC_DataBlock
- `00 00 00 00` = Length: 0 (no data)
- `00` = bSlot: 0
- `20` = bSeq: 32 (same as request)
- `00` = bStatus: Success
- `00` = bError: No error

**실패 시** (인증 안 됨):
```
80 00 00 00 00 00 20 01 00 00
```
- `01` = bStatus: Failed
- `00` = bError: Specific error code

### 완전한 쓰기 시퀀스 예제

```bash
# 1. Card Power On
62 00 00 00 00 00 00 00 00 00

# 2. Authenticate Sector 1 with Key A
6F 0A 00 00 00 00 01 00 00 00 FF 86 00 00 05 01 00 05 60 00

# 3. Write to Block 5
6F 15 00 00 00 00 02 00 00 00 FF D6 00 05 10 30 31 32 33 34 35 36 37 38 39 3A 3B 3C 3D 3E 3F

# 4. Read Block 5 (verify)
6F 05 00 00 00 00 03 00 00 00 FF B0 00 05 10

# 5. Card Power Off
63 00 00 00 00 00 04 00 00 00
```

### 다른 유용한 Mifare 명령어

#### 블록 읽기
```
6F 05 00 00 00 00 XX 00 00 00 FF B0 00 05 10
```
- `FF B0` = READ BINARY BLOCK
- `00 05` = Block 5
- `10` = Read 16 bytes

#### Value Block 증가
```
6F 05 00 00 00 00 XX 00 00 00 FF D7 00 05 04 01 00 00 00
```
- `FF D7` = INCREMENT
- `00 05` = Block 5
- `04` = 4 bytes
- `01 00 00 00` = Increment by 1 (little-endian)

#### UID 읽기
```
6F 00 00 00 00 00 XX 00 00 00 FF CA 00 00 00
```
- `FF CA 00 00` = GET DATA (UID)
락 설정 비트의 의미
Byte 0: Block Locking
각 비트가 4개의 페이지를 보호
Bit 0 (0x01): Pages 3-0 잠금
Bit 1 (0x02): Pages 7-4 잠금
Bit 2 (0x04): Pages 11-8 잠금 (OTP)
Bit 3 (0x08): Pages 15-12 잠금
Bit 4 (0x10): Pages 19-16 잠금
Bit 5 (0x20): Pages 23-20 잠금
Bit 6 (0x40): Pages 27-24 잠금
Bit 7 (0x80): Pages 31-28 잠금

---

## IAR 빌드 설정

### Preprocessor Defines

IAR Embedded Workbench 프로젝트에 설정된 전처리기 정의:

```
HSE_VALUE=16000000              // 외부 16MHz 크리스탈
USE_STDPERIPH_DRIVER            // STM32 표준 주변장치 라이브러리 사용
STM32F10X_MD                    // STM32F10X Medium Density (128KB Flash)
USB_USE_EXTERNAL_PULLUP         // USB 외부 풀업 저항 사용
USE_STM3210E_EVAL               // STM32 평가 보드 설정
USE_USB_INTERFACE               // USB 인터페이스 활성화
NFC_RF                          // NFC/RFID 기능 활성화
NXPBUILD__PH_KEYSTORE_SW        // NXP KeyStore 소프트웨어 컴포넌트
PH_PLATFORM_HAS_ICFRONTEND      // 플랫폼 IC 프론트엔드 지원
NXPBUILD_CUSTOMER_HEADER_INCLUDED  // 커스텀 NXP 빌드 헤더 포함
TIT_FW_RF                       // TITENG RF 펌웨어 빌드
xTIT_MON_BOARD                  // MON 보드 변형 (비활성화)
xUSE_LED                        // LED 제어 (비활성화)
UseIWDG                         // 독립 워치독 타이머 사용
xDEBUG                          // 디버그 모드 (비활성화)
NXPBUILD__PH_CRYPTORNG_SW       // NXP 암호화 난수 생성기 (ULC용)
NXPBUILD__PH_CRYPTOSYM_SW       // NXP 암호화 심볼 (ULC용)
PH_CRYPTOSYM_SW_DES             // DES/3DES 암호화 지원
PH_CRYPTOSYM_SW_ONLINE_KEYSCHEDULING  // 온라인 키 스케줄링
```

### Optimization Settings

**컴파일러 최적화 레벨:**
- **Size**: High (코드 크기 최적화 우선)
- **Speed**: None
- **Enabled transformations**:
  - Common subexpression elimination
  - Loop unrolling (4)
  - Function inlining
  - Code motion
  - Type-based alias analysis

**링커 설정:**
- **Optimization**: Remove unused sections
- **Merge duplicate sections**: Enabled

### Memory Configuration

**Flash (ROM):**
- 시작: `0x08006000` (24KB 부트로더 오프셋)
- 끝: `0x0801FFFF`
- 사용 가능: **104KB** (106,496 bytes)
- 현재 사용: ~97.7KB (91.8%)
- 여유: ~8.5KB

**RAM:**
- Stack: **8KB** (0x2000)
- Heap: **2KB** (0x800)
- 총 RAM: 20KB

### Build Output

최근 빌드 결과 (크립토 라이브러리 포함):
```
Code (readonly):   94,606 bytes
Data (readonly):    3,134 bytes
Total ROM:         97,740 bytes
Readwrite data:    17,691 bytes
```

**크립토 라이브러리 크기:**
- 3DES (ULC 인증용): ~3KB
- AES (라이브러리 의존성): ~3KB
- RNG (난수 생성): ~1.2KB
- 인프라 + KeyStore: ~3.4KB
- **총 크립토 라이브러리: ~10.6KB**
