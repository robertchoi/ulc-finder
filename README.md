# ULC Finder

Mifare Ultralight C 인증 키 검색 프로그램

## 개요

ULC Finder는 시리얼 포트를 통해 NFC/RFID 리더기 보드(PN512 기반)와 통신하여 Mifare Ultralight C 카드의 3DES 인증 키를 브루트포스 방식으로 검색하는 파이썬 기반 윈도우 데스크톱 애플리케이션입니다.

## 주요 기능

- ✅ COM 포트 자동 검색 및 연결
- ✅ 16바이트 3DES 키 공간 순차 스캔
- ✅ 실시간 진행률 표시
- ✅ 스캔 속도 및 예상 시간 계산
- ✅ 인증 성공 시 키 값 표시
- ✅ 시작/정지 기능

## 시스템 요구사항

### 하드웨어
- PN512 기반 NFC/RFID 리더기 보드 (TITENG)
- USB-Serial 연결 (COM 포트)
- Mifare Ultralight C 카드
- Windows 10/11 PC

### 소프트웨어
- Python 3.8 이상
- PyQt5
- pyserial

## 설치

### 방법 1: uv 사용 (추천)

[uv](https://github.com/astral-sh/uv)는 빠르고 현대적인 Python 패키지 관리 도구입니다.

#### 1. uv 설치
```bash
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 또는 pip로 설치
pip install uv
```

#### 2. 프로젝트 실행
```bash
cd ulc-finder

# 의존성 자동 설치 및 실행
uv run main.py
```

uv는 자동으로 필요한 Python 버전과 의존성을 설치하고 실행합니다.

### 방법 2: 기존 pip 사용

#### 1. Python 설치
Python 3.8 이상이 설치되어 있어야 합니다.
https://www.python.org/downloads/

#### 2. 의존성 패키지 설치
```bash
cd ulc-finder
pip install -r requirements.txt
```

또는 수동으로:
```bash
pip install PyQt5>=5.15.0 pyserial>=3.5
```

#### 3. 프로그램 실행
```bash
python main.py
```

## 사용 방법

### 1. 프로그램 실행

**uv 사용:**
```bash
uv run main.py
```

**기존 Python 사용:**
```bash
python main.py
```

### 2. 리더기 연결
1. COM 포트 드롭다운에서 리더기가 연결된 포트 선택
2. "연결" 버튼 클릭
3. 연결 성공 시 상태가 "연결됨"으로 변경

### 3. 키 스캔 시작
1. 시작 키 입력 (Hex 형식, 16바이트)
   - 예: `00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00`
2. "시작" 버튼 클릭
3. 진행률 및 속도 모니터링
4. 인증 성공 시 결과창에 키 표시

### 4. 스캔 중지
- "정지" 버튼 클릭하여 언제든지 스캔 중단 가능

## 프로토콜

### 스캔 루프 순서
```
1. Card Power ON (PC_to_RDR_IccPowerOn 0x62)
   - 카드를 활성화하고 ATR 수신

2. Get UID (FF CA 00 00 00)
   - 카드의 고유 식별자(UID) 읽기

3. Load 16-byte key to reader (INS_LOAD_AUTH 0x82)
   - 시도할 키를 리더기의 KeyStore Slot 3에 로드

4. Authenticate (General Authenticate 0x86)
   - FF 86 00 00 05 01 00 04 60 03: 3DES authentication

5. Check authentication result
   - Success (bStatus=0x00, SW1 SW2 = 90 00): Display key and stop
   - Fail: Increment key and continue

6. Repeat from step 1 with next key
```

### 통신 설정
- **Baud Rate**: 57600 bps (고정)
- **Data Format**: 8N1 (8 data bits, No parity, 1 stop bit)
- **프로토콜**: USB CCID 1.1 메시지 포맷

## 프로젝트 구조

```
ulc-finder/
├── main.py                     # 애플리케이션 진입점
├── PRD.md                      # 제품 요구사항 문서
├── README.md                   # 본 문서
├── requirements.txt            # 의존성 패키지
├── doc/
│   └── protocol.md            # 프로토콜 문서
├── gui/
│   ├── __init__.py
│   └── main_window.py         # 메인 윈도우
├── core/
│   ├── __init__.py
│   ├── serial_manager.py      # 시리얼 포트 관리
│   ├── ccid_protocol.py       # CCID 프로토콜 처리
│   ├── ulc_scanner.py         # ULC 키 스캔 로직
│   └── key_generator.py       # 키 생성 및 증가
├── utils/
│   └── __init__.py
├── logs/                       # 로그 디렉토리
└── results/                    # 결과 저장 디렉토리
```

## 기본 제조사 키

Mifare Ultralight C의 기본 제조사 키:
```
Hex: 49 45 4D 4B 41 45 52 42 21 4E 41 43 55 4F 59 46
ASCII: "IEMKAERB!NACUOYF" ("BREAKMEIFYOUCAN!" 역순)
```

## 주의사항

### 스캔 시간
- **전체 키 공간**: 2^128 = 3.4 × 10^38 keys
- **스캔 속도**: ~50 keys/sec (하드웨어에 따라 다름)
- **전체 스캔 시간**: 비현실적으로 긴 시간

### 현실적 사용 시나리오
1. **부분 키 알려진 경우**: 일부 바이트만 스캔
2. **제조사 기본 키**: 알려진 기본 키 우선 시도
3. **키 패턴 추정**: 특정 패턴의 키만 시도

## 법적 고려사항

⚠️ **중요**: 이 도구는 다음 목적으로만 사용해야 합니다:
- 본인 소유 카드의 분실 키 복구
- 보안 연구 및 교육 목적
- 승인된 펜테스팅 및 보안 감사
- CTF 챌린지

**금지 사항**:
- 타인 소유 카드의 무단 접근
- 불법적인 목적으로 사용
- 상업적 불법 복제

## 트러블슈팅

### 시리얼 포트 진단 도구

연결 문제가 있을 때 먼저 진단 도구를 실행하세요:

```bash
# uv 사용
uv run test_serial.py

# 기존 Python 사용
python test_serial.py
```

진단 도구는 다음을 확인합니다:
- 사용 가능한 COM 포트 목록
- 선택한 포트 연결 테스트
- CCID 프로토콜 통신 테스트
- 카드 UID 읽기 테스트

### 연결 실패 해결방법

#### 1. COM 포트를 찾을 수 없음
**증상**: "No ports found" 메시지 표시

**해결방법**:
- Windows 장치 관리자에서 COM 포트 확인
  1. Win + X → 장치 관리자
  2. "포트(COM & LPT)" 섹션 확인
  3. 리더기가 표시되는지 확인
- USB 케이블을 다른 포트에 연결
- USB 드라이버 재설치
- 리더기 전원 재연결

#### 2. 포트 연결 실패
**증상**: "연결에 실패했습니다" 에러

**해결방법**:
- **다른 프로그램이 포트 사용 중**
  - Arduino IDE, PuTTY, Tera Term 등 시리얼 프로그램 종료
  - 작업 관리자에서 python.exe 프로세스 확인 및 종료
- **권한 문제**
  - 관리자 권한으로 프로그램 실행
  - 우클릭 → 관리자 권한으로 실행
- **잘못된 포트 선택**
  - 장치 관리자에서 실제 포트 번호 확인
  - 다른 COM 포트 시도

#### 3. 리더기 통신 실패
**증상**: "리더기와 통신할 수 없습니다" 에러

**해결방법**:
- **리더기 전원 확인**
  - 리더기 LED가 켜져 있는지 확인
  - USB 전원 공급 확인
  - 외부 전원이 필요한 경우 연결
- **Baud Rate 확인**
  - 리더기가 57600 baud를 지원하는지 확인
  - 리더기 설정/펌웨어 확인
- **프로토콜 호환성**
  - 리더기가 CCID 프로토콜을 지원하는지 확인
  - PN512 기반 리더기인지 확인
- **케이블 문제**
  - USB 케이블 교체
  - 데이터 전송 지원 케이블 사용 (충전 전용 케이블 X)

#### 4. 카드 인식 실패
**증상**: UID를 읽을 수 없거나 인증 실패

**해결방법**:
- **카드 위치**
  - 카드를 리더기 안테나 중앙에 배치
  - 카드와 리더기 간격 조절 (너무 가깝거나 멀지 않게)
- **카드 타입 확인**
  - Mifare Ultralight C 카드인지 확인
  - 다른 카드 타입은 지원하지 않음
- **카드 상태**
  - 카드 손상 여부 확인
  - 다른 카드로 테스트

### 디버그 모드

더 자세한 로그를 보려면 콘솔에서 실행하세요:

```bash
uv run main.py
```

콘솔 창에 다음 정보가 표시됩니다:
- 시리얼 포트 연결 상태
- CCID 명령/응답 로그
- 에러 메시지 상세 정보

### 자주 묻는 질문 (FAQ)

**Q: "Access is denied" 에러가 발생합니다**
A: 다른 프로그램이 포트를 사용 중입니다. 모든 시리얼 프로그램을 종료하고 재시도하세요.

**Q: 포트는 연결되지만 리더기와 통신이 안 됩니다**
A: Baud rate가 맞지 않거나 리더기가 CCID 프로토콜을 지원하지 않을 수 있습니다. 리더기 사양을 확인하세요.

**Q: 스캔 속도가 너무 느립니다**
A: USB 2.0 포트 사용, 다른 프로그램 종료, 시작 키 범위 축소를 시도하세요.

## 라이선스

교육 및 연구 목적으로 제공됩니다.

## 기여

버그 리포트 및 기능 제안은 Issues를 통해 제출해주세요.

## 참고 문서

- [PRD.md](PRD.md) - 제품 요구사항 문서
- [doc/protocol.md](doc/protocol.md) - PN512 프로토콜 문서
- [CCID Specification 1.1](https://www.usb.org/sites/default/files/DWG_Smart-Card_CCID_Rev110.pdf)
- [Mifare Ultralight C Datasheet](https://www.nxp.com/docs/en/data-sheet/MF0ICU2.pdf)

---

**Version**: 1.0
**Last Updated**: 2025-12-12



30 30 30 30 30 30 30 30 30 30 30 30 30 30 30 30
49 45 4D 4B 41 45 52 42 21 4E 41 43 55 4F 59 46
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00


6F050000000002000000FFB0000510