# Product Requirements Document (PRD)

## Project: ULC Finder

### 1. Overview

#### 1.1 Product Name
ULC Finder - Mifare Ultralight C 인증 키 검색 프로그램

#### 1.2 Product Description
ULC Finder는 시리얼 포트를 통해 NFC/RFID 리더기 보드(PN512 기반)와 통신하여 Mifare Ultralight C 카드의 3DES 인증 키를 브루트포스 방식으로 검색하는 파이썬 기반 윈도우 데스크톱 애플리케이션입니다.

#### 1.3 Target Users
- NFC/RFID 카드 보안 연구자
- 인증 키를 분실한 카드 복구 담당자
- 보안 감사 및 펜테스터
- 카드 시스템 엔지니어

#### 1.4 Platform
- Windows 10/11
- Python 3.8+ 기반 데스크톱 애플리케이션

#### 1.5 Hardware Requirements
- PN512 기반 NFC/RFID 리더기 보드 (TITENG)
- USB-Serial 연결 (COM 포트)
- Mifare Ultralight C 카드

### 2. Goals and Objectives

#### 2.1 Primary Goals
- 16바이트 3DES 키 공간을 순차적으로 스캔
- 안정적인 시리얼 포트 CCID 프로토콜 통신
- 실시간 진행률 표시
- 인증 성공 시 키 값 표시 및 저장

#### 2.2 Success Metrics
- 통신 성공률: > 99%
- 초당 스캔 속도: > 10 keys/sec (목표)
- 인증 성공 시 정확한 키 값 표시
- 24시간 이상 안정적 동작

### 3. Technical Background

#### 3.1 Mifare Ultralight C (ULC)
- **메모리**: 192 bytes (48 pages × 4 bytes)
- **인증**: 3DES (16-byte key, 2K3DES)
- **보호 영역**: Pages 4-47 (AUTH0 설정에 따름)
- **기본 제조사 키**: `49 45 4D 4B 41 45 52 42 21 4E 41 43 55 4F 59 46`
  - ASCII: "IEMKAERB!NACUOYF" ("BREAKMEIFYOUCAN!" 역순)

#### 3.2 통신 프로토콜
- **인터페이스**: 시리얼 포트 (UART)
- **프로토콜**: USB CCID 1.1 메시지 포맷
- **Baud Rate**: 57600 bps (고정)
- **Data Format**: 8N1 (8 data bits, No parity, 1 stop bit)
- **프레임 구조**: CCID 10-byte header + APDU payload

#### 3.3 CCID 프로토콜 구조
```
CCID Header (10 bytes):
┌──────────────┬────────────────────────────────────┐
│ Byte Offset  │ Field Name                         │
├──────────────┼────────────────────────────────────┤
│ 0            │ bMessageType                       │
│ 1-4          │ dwLength (Little-endian)           │
│ 5            │ bSlot                              │
│ 6            │ bSeq                               │
│ 7-9          │ bSpecific (command-specific)       │
│ 10+          │ abData[] (APDU payload)            │
└──────────────┴────────────────────────────────────┘
```

### 4. Functional Requirements

#### 4.1 Core Features

**1. 시리얼 포트 연결**
- COM 포트 자동 검색 (드롭다운)
- 연결/해제 기능
- 통신 설정:
  - Baud Rate: 57600 (고정)
  - Data Bits: 8
  - Parity: None
  - Stop Bits: 1
- 연결 상태 표시

**2. 키 스캔 설정**
- 시작 키 입력 (16바이트 Hex)
  - 형식: `00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00`
  - 입력 검증 (Hex 형식, 16바이트)
- 종료 키: `FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF` (고정)

**3. 스캔 동작**
- **시작 버튼**: 스캔 시작
  - 시작 키부터 FF...FF까지 순차 증가
  - 각 키마다 인증 시도
  - 성공 시 자동 정지
- **정지 버튼**: 스캔 중단
- **스캔 루프**:
  ```
  1. Card Power ON (PC_to_RDR_IccPowerOn 0x62)
     - 카드를 활성화하고 ATR 수신
  2. Get UID (FF CA 00 00 00)
     - 카드의 고유 식별자(UID) 읽기
     - UID는 7바이트 또는 4바이트
  3. Load 16-byte key to reader (INS_LOAD_AUTH 0x82)
     - 시도할 키를 리더기의 KeyStore Slot 3에 로드
  4. Authenticate with loaded key (General Authenticate)
     - Authenticate command (FF 86 00 00 05 01 00 04 60 03): 3DES authentication
  5. Check authentication result:
     - Success (bStatus=0x00, SW1 SW2 = 90 00): Display key and stop
     - Fail (bError=0x69 or bStatus=0x40): Increment key and continue
  6. Repeat from step 1 with next key
  ```

**4. 결과 표시**
- 결과창 (16바이트 Hex 형식)
  - 인증 성공한 키 값 표시
  - 입력창과 동일한 형태
- 현재 시도 중인 키 표시 (선택사항)

**5. 진행률 표시**
- 프로그래스 바
  - 계산 방식: `(현재 키 - 시작 키) / (FF...FF - 시작 키) × 100%`
  - 16바이트 Big Integer 연산
- 진행 정보:
  - 현재 시도 횟수
  - 예상 남은 시간 (선택사항)
  - 초당 스캔 속도

**6. 상태 표시**
- 현재 상태: "대기 중", "스캔 중", "성공", "중지됨"
- 마지막 통신 상태
- 에러 메시지 표시

#### 4.2 Additional Features (선택사항)
- 로그 저장 (텍스트 파일)
- 결과 저장 (CSV, JSON)
- 스캔 범위 커스텀 설정 (시작~끝)
- 멀티스레드 통신 (성능 향상)
- 통신 타임아웃 설정

### 5. Non-Functional Requirements

#### 5.1 Performance
- 메모리 사용량: < 100MB
- CPU 사용률: < 20%
- 스캔 속도: 초당 최소 10 keys (목표: 50+ keys)
- 통신 타임아웃: 각 명령당 1초

#### 5.2 Reliability
- 24시간 이상 연속 실행 가능
- 통신 오류 자동 재시도 (최대 3회)
- 예외 상황 처리 및 복구
- 크래시 방지

#### 5.3 Usability
- 직관적인 UI
- 명확한 상태 표시
- 에러 메시지 명확화
- 한글 완벽 지원

#### 5.4 Security
- 발견한 키 로컬 저장 (암호화 선택사항)
- 로그 민감정보 필터링

### 6. Technical Specifications

#### 6.1 Technology Stack

**Frontend (GUI)**
- PyQt5 또는 PyQt6 (추천)
- 대안: CustomTkinter

**Serial Communication**
- pySerial (필수)

**Backend**
- Python 3.8+
- Threading (비동기 통신)
- struct (바이너리 데이터 처리)

**Utilities**
- logging (로깅)
- datetime (시간 기록)
- json / csv (결과 저장)

#### 6.2 Project Structure
```
ulc-finder/
├── main.py                     # 애플리케이션 진입점
├── PRD.md                      # 본 문서
├── README.md                   # 사용자 가이드
├── doc/
│   └── protocol.md            # 프로토콜 문서 (참조용)
├── gui/
│   ├── main_window.py         # 메인 윈도우
│   └── widgets.py             # 커스텀 위젯
├── core/
│   ├── serial_manager.py      # 시리얼 포트 관리
│   ├── ccid_protocol.py       # CCID 프로토콜 처리
│   ├── ulc_scanner.py         # ULC 키 스캔 로직
│   └── key_generator.py       # 키 생성 및 증가
├── utils/
│   ├── logger.py              # 로거
│   └── helpers.py             # 헬퍼 함수
├── resources/
│   └── icons/                 # 아이콘
├── logs/                       # 로그 디렉토리
├── results/                    # 결과 저장 디렉토리
├── requirements.txt
└── .gitignore
```

#### 6.3 CCID 명령어 시퀀스

스캔 루프의 순서: **Power ON → Get UID → Key Load → Authenticate**

**1. 카드 Power ON**
```python
message = [
    0x62,                    # bMessageType: PC_to_RDR_IccPowerOn
    0x00, 0x00, 0x00, 0x00, # dwLength: 0
    0x00,                    # bSlot: 0
    seq,                     # bSeq
    0x00, 0x00, 0x00        # bSpecific
]

# Expected response:
# 0x80 (RDR_to_PC_DataBlock) + ATR data
```

**2. Get UID**
```python
# CCID Header (10 bytes) + APDU (5 bytes)
message = [
    0x6F,                    # bMessageType: PC_to_RDR_XfrBlock
    0x05, 0x00, 0x00, 0x00, # dwLength: 5 bytes
    0x00,                    # bSlot: 0
    seq,                     # bSeq
    0x00, 0x00, 0x00,       # bSpecific
    # APDU:
    0xFF, 0xCA, 0x00, 0x00, # CLA INS P1 P2 (GET DATA - UID)
    0x00                     # Le: 0 (expect UID response)
]

# Expected response:
# 0x80 + UID (7 or 4 bytes) + 90 00 (SW1 SW2)
```

**3. 키 로드 (INS_LOAD_AUTH)**
```python
# CCID Header (10 bytes) + APDU (21 bytes)
message = [
    0x6F,                    # bMessageType: PC_to_RDR_XfrBlock
    0x15, 0x00, 0x00, 0x00, # dwLength: 21 bytes
    0x00,                    # bSlot: 0
    seq,                     # bSeq: sequence number
    0x00, 0x00, 0x00,       # bSpecific
    # APDU:
    0xFF, 0x82, 0x00, 0x03, # CLA INS P1 P2 (LOAD AUTH KEY to slot 3)
    0x10,                    # Lc: 16 bytes
    *key_bytes              # 16-byte key
]

# Expected response:
# 0x80 + 90 00 (success) or error code
```

**4. Authenticate (General Authenticate - 0x86)**
```python
# CCID Header (10 bytes) + APDU (10 bytes)
message = [
    0x6F,                    # bMessageType: PC_to_RDR_XfrBlock
    0x0A, 0x00, 0x00, 0x00, # dwLength: 10 bytes
    0x00,                    # bSlot: 0
    seq,                     # bSeq
    0x00, 0x00, 0x00,       # bSpecific
    # APDU:
    0xFF, 0x86,              # CLA INS (GENERAL AUTHENTICATE)
    0x00, 0x00,              # P1 P2
    0x05,                    # Lc: 5 bytes
    0x01,                    # Version
    0x00,                    # Address (MSB)
    0x04,                    # Address (LSB) - Page 4
    0x60,                    # Auth mode (0x60 = Key A for 3DES)
    0x03                     # Key number (Slot 3)
]

# Expected response:
# Success: 0x80 + bStatus=0x00 + 90 00
# Fail: 0x80 + bStatus=0x40 or bError=0x69 (authentication error)
```

**5. 응답 해석**
```python
# Success response:
response = [
    0x80,                    # bMessageType: RDR_to_PC_DataBlock
    length[4],               # dwLength
    slot,                    # bSlot
    seq,                     # bSeq
    0x00,                    # bStatus: 0x00 = success, 0x40 = fail
    0x00,                    # bError: 0x00 = no error, 0x69 = auth error
    0x00,                    # bSpecific
    *data                    # Response data
]

# Authentication success: bStatus = 0x00, data != all zeros
# Authentication fail: bStatus = 0x40 or bError = 0x69
```

#### 6.4 키 증가 알고리즘
```python
def increment_key(key_bytes: bytes) -> bytes:
    """
    16바이트 키를 1 증가 (Big-endian)
    Returns None if overflow (FF...FF → 00...00)
    """
    key_int = int.from_bytes(key_bytes, byteorder='big')
    key_int += 1

    if key_int > 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:
        return None  # Overflow

    return key_int.to_bytes(16, byteorder='big')
```

#### 6.5 진행률 계산
```python
def calculate_progress(start_key: bytes, current_key: bytes) -> float:
    """
    진행률 계산 (0.0 ~ 100.0)
    """
    end_key = b'\xFF' * 16

    start_int = int.from_bytes(start_key, byteorder='big')
    current_int = int.from_bytes(current_key, byteorder='big')
    end_int = int.from_bytes(end_key, byteorder='big')

    progress = (current_int - start_int) / (end_int - start_int) * 100.0
    return progress
```

### 7. UI/UX Design

#### 7.1 Main Window Layout
```
┌─────────────────────────────────────────────────────────┐
│  ULC Finder - 인증 키 검색                    [ _ □ X ] │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─ 연결 설정 ──────────────────────────────────────┐  │
│  │                                                   │  │
│  │  COM Port:  [COM3 ▼]           [연결] [해제]    │  │
│  │  상태: ● 연결됨  |  57600 8N1                    │  │
│  │                                                   │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌─ 키 스캔 설정 ────────────────────────────────────┐  │
│  │                                                   │  │
│  │  시작 키 (Hex):                                  │  │
│  │  ┌─────────────────────────────────────────────┐ │  │
│  │  │ 00 00 00 00 00 00 00 00 00 00 00 00 00 00  │ │  │
│  │  │ 00 00                                       │ │  │
│  │  └─────────────────────────────────────────────┘ │  │
│  │                                                   │  │
│  │  [시작]  [정지]                                  │  │
│  │                                                   │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌─ 결과 ────────────────────────────────────────────┐  │
│  │                                                   │  │
│  │  발견된 키 (Hex):                                │  │
│  │  ┌─────────────────────────────────────────────┐ │  │
│  │  │                                             │ │  │
│  │  │                                             │ │  │
│  │  └─────────────────────────────────────────────┘ │  │
│  │                                                   │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌─ 진행 상태 ───────────────────────────────────────┐  │
│  │                                                   │  │
│  │  [████████████████░░░░░░░░░░░░░░░░] 54.3%       │  │
│  │                                                   │  │
│  │  시도: 1,234,567 / 2,273,456,789                 │  │
│  │  속도: 42.5 keys/sec  |  예상 시간: 15시간 23분  │  │
│  │  상태: 스캔 중...                                │  │
│  │                                                   │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### 7.2 UI 컴포넌트 상세

**1. COM Port 선택**
- QComboBox: 사용 가능한 포트 목록
- 새로고침 버튼 (선택사항)
- 연결/해제 버튼

**2. 시작 키 입력**
- QLineEdit 또는 QPlainTextEdit
- 입력 마스크: Hex만 허용
- 자동 포맷팅: 2자리마다 공백
- 입력 검증: 16바이트 (32자 hex + 15 spaces)

**3. 결과창**
- QLineEdit (읽기 전용)
- 동일한 형태로 16바이트 Hex 표시
- 복사 버튼 (선택사항)

**4. 프로그래스 바**
- QProgressBar
- 텍스트 오버레이: "54.3%"
- 범위: 0-100

**5. 상태 정보**
- QLabel 또는 QTextEdit
- 실시간 업데이트
- 색상 코딩: 성공(녹색), 실패(빨강), 스캔 중(파랑)

#### 7.3 Design Principles
- 깔끔하고 기능적인 디자인
- 명확한 시각적 피드백
- 진행 상태 실시간 업데이트
- 에러 메시지 명확 표시

### 8. User Stories

1. **사용자로서**, COM 포트를 선택하여 리더기에 연결하고 싶다.
2. **사용자로서**, 시작 키를 입력하여 스캔 범위를 설정하고 싶다.
3. **사용자로서**, 시작 버튼을 눌러 자동으로 키를 검색하고 싶다.
4. **사용자로서**, 실시간으로 진행률과 현재 상태를 확인하고 싶다.
5. **사용자로서**, 인증에 성공하면 키 값을 결과창에서 확인하고 싶다.
6. **사용자로서**, 스캔 중 언제든지 정지할 수 있어야 한다.
7. **연구자로서**, 발견한 키를 파일로 저장하고 싶다.
8. **관리자로서**, 장시간 스캔 시 안정적으로 동작하기를 원한다.

### 9. Timeline and Milestones

#### Phase 1: 프로토타입 개발 (1주)
- [ ] 기본 GUI 구현
- [ ] 시리얼 포트 연결 기능
- [ ] CCID 프로토콜 기본 구현
- [ ] 키 입력/표시 기능

#### Phase 2: 스캔 로직 구현 (1주)
- [ ] 키 생성 및 증가 알고리즘
- [ ] CCID 명령 시퀀스 구현
- [ ] 인증 성공/실패 판별
- [ ] 스캔 루프 구현

#### Phase 3: UI 완성 (3일)
- [ ] 진행률 계산 및 표시
- [ ] 상태 메시지 표시
- [ ] 에러 처리 및 표시
- [ ] 시작/정지 버튼 로직

#### Phase 4: 테스트 및 최적화 (1주)
- [ ] 실제 하드웨어 테스트
- [ ] 통신 안정성 테스트
- [ ] 성능 최적화
- [ ] 장시간 안정성 테스트
- [ ] 버그 수정

#### Phase 5: 배포 (2일)
- [ ] 실행 파일 빌드 (PyInstaller)
- [ ] 사용자 매뉴얼 작성
- [ ] 릴리즈

**총 예상 기간: 3-4주**

### 10. Risks and Mitigation

| Risk | Impact | Probability | Mitigation Strategy |
|------|--------|-------------|---------------------|
| 시리얼 통신 불안정 | Critical | Medium | 재시도 로직, 타임아웃, 에러 핸들링 |
| 스캔 속도 너무 느림 | High | High | 멀티스레드, 통신 최적화, 불필요한 지연 제거 |
| 16바이트 Big Integer 오버플로 | Medium | Low | Python의 arbitrary precision integer 사용 |
| 메모리 누수 (장시간 실행) | Medium | Medium | 프로파일링, 리소스 정리 |
| 인증 성공 판별 실패 | Critical | Low | 응답 코드 정확한 해석, 다중 검증 |

### 11. Testing Strategy

#### 11.1 Unit Testing
- 키 증가 알고리즘 검증
- CCID 메시지 생성/파싱 테스트
- 진행률 계산 테스트

#### 11.2 Integration Testing
- 시리얼 포트 통신 테스트 (실제 하드웨어)
- CCID 명령 시퀀스 테스트
- 인증 성공/실패 시나리오

#### 11.3 System Testing
- 전체 스캔 프로세스 테스트 (작은 범위)
- 기본 제조사 키로 검증
- 장시간 안정성 테스트 (24시간+)

#### 11.4 Performance Testing
- 스캔 속도 측정
- 메모리 사용량 모니터링
- CPU 사용률 체크

### 12. Known Limitations

#### 12.1 스캔 시간
- **전체 키 공간**: 2^128 = 3.4 × 10^38 keys
- **스캔 속도**: 50 keys/sec (낙관적 추정)
- **전체 스캔 시간**: ~2.16 × 10^29 years (비현실적)

**현실적 사용 시나리오**:
1. **부분 키 알려진 경우**: 일부 바이트만 스캔
2. **키 패턴 추정**: 특정 패턴의 키만 시도
3. **레인보우 테이블**: 사전 계산된 일반적인 키
4. **제조사 기본 키**: 알려진 기본 키 우선 시도

#### 12.2 하드웨어 의존성
- PN512 기반 리더기 전용
- 시리얼 포트 연결 필수
- ULC 카드 전용 (다른 카드 타입 미지원)

### 13. Future Enhancements (v2.0+)

- 멀티스레드 병렬 스캔 (여러 리더기 동시 사용)
- 스마트 키 생성 (패턴 기반, 사전 공격)
- 레인보우 테이블 통합
- 데이터베이스 연동 (시도한 키 기록)
- 분산 스캔 (여러 PC 협업)
- 통계 및 분석 기능
- GPU 가속 (가능한 경우)
- CLI 모드
- 원격 모니터링

### 14. Security and Ethics

#### 14.1 법적 고려사항
⚠️ **중요**: 이 도구는 다음 목적으로만 사용해야 합니다:
- 본인 소유 카드의 분실 키 복구
- 보안 연구 및 교육 목적
- 승인된 펜테스팅 및 보안 감사
- CTF 챌린지

**금지 사항**:
- 타인 소유 카드의 무단 접근
- 불법적인 목적으로 사용
- 상업적 불법 복제

#### 14.2 윤리적 사용 지침
1. 반드시 소유권이나 승인을 확인
2. 발견한 키의 안전한 보관
3. 보안 취약점 발견 시 책임있는 공개
4. 교육 및 연구 목적 명시

### 15. Open Questions

- [ ] 실제 스캔 속도는 얼마나 되는가?
- [ ] 통신 오버헤드를 어떻게 최소화할 수 있는가?
- [ ] 카드 Power ON/OFF 사이클이 필요한가, 아니면 키만 재로드?
- [ ] 인증 실패 시 정확한 응답 코드는 무엇인가?
- [ ] 멀티스레드 구현 시 시리얼 포트 동시 접근 문제는?

### 16. Appendix

#### 16.1 Glossary
- **ULC**: Mifare Ultralight C
- **3DES**: Triple Data Encryption Standard
- **CCID**: Chip Card Interface Device
- **PN512**: NXP NFC/RFID controller chip
- **APDU**: Application Protocol Data Unit
- **ATR**: Answer To Reset
- **Brute Force**: 전수 조사 공격

#### 16.2 References
- [CCID Specification 1.1](https://www.usb.org/sites/default/files/DWG_Smart-Card_CCID_Rev110.pdf)
- [Mifare Ultralight C Datasheet](https://www.nxp.com/docs/en/data-sheet/MF0ICU2.pdf)
- [PN512 Protocol Documentation](doc/protocol.md)
- ISO/IEC 14443 Standard

#### 16.3 Test Vectors

**기본 제조사 키 테스트**:
```
시작 키: 49 45 4D 4B 41 45 52 42 21 4E 41 43 55 4F 59 46
예상 결과: 인증 성공
```

**알려진 실패 키**:
```
키: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
예상 결과: 인증 실패 (bError = 0x69)
```

#### 16.4 Python Packages
```
PyQt5>=5.15.0
pyserial>=3.5
```

---

**Document Version**: 1.0
**Last Updated**: 2025-12-12
**Author**: Development Team
**Status**: Final Draft
**Approval**: Pending Review
