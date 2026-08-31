# 3D Printer Monitoring System – Technical Report

## Executive Overview

- PyQt5 기반 데스크톱 애플리케이션으로 실시간 3D 프린터 상태를 추적하고, Azure Custom Vision으로 결함을 자동 감지합니다.
- 카메라 스트리밍, 프린터 원격 제어, 결함 발생 시 자동 일시정지 및 로그/이미지 기록까지 한 번에 처리하는 통합 솔루션입니다.
- 코드베이스는 UI, 비즈니스 로직, 인프라 유틸리티를 분리해 테스트 가능성과 유지보수성을 확보했습니다.

## 핵심 제공 가치

- **실시간 모니터링**: 웹캠 프레임을 1초 단위로 갱신하고 프린터 상태를 원격 API로 폴링.
- **결함 감지 자동화**: Azure Custom Vision Detect API를 호출해 70% 이상 확률의 이상을 식별하고 시각적 오버레이 및 이미지 저장.
- **자동 대응**: 결함 발생 시 프린터를 즉시 일시정지하도록 Moonraker API를 호출.
- **사용자 피드백 강화**: GUI 로그, 상태바, 동의 다이얼로그 등 사용자 경험 요소를 세심하게 설계.

## 시스템 아키텍처

```
printer_monitoring/
├── main.py                # 앱 진입점
├── src/
│   ├── ui/                # PyQt5 UI 레이어
│   ├── core/              # 비즈니스 로직 (결함 감지, 이미지 처리, 프린터 제어)
│   ├── utils/             # API 클라이언트, 설정/검증 유틸
│   └── constants/         # 환경 기반 상수 및 이벤트 정의
└── tests/                 # (향후 테스트용) 플레이스홀더
```

- **UI 레이어**(`src/ui`): 컨트롤 패널과 영상 위젯으로 사용자 상호작용과 시각화를 담당.
- **Core 레이어**(`src/core`): 이미지 전처리, 결함 검출, 프린터 상태 제어 등 도메인 로직 구현.
- **Utils & Constants**: API 통신, 환경 변수 로딩, 검증, 로깅 등 공통 기능을 제공.
- **환경 설정**: `.env` 파일로 API 키와 네트워크 파라미터를 주입하고 `settings.py`에서 일관되게 노출.

## 실행 흐름

1. `main.py`에서 `MainWindow`를 생성하면서 UI, 팩토리, 타이머를 초기화.
2. 사용자가 모니터링을 시작하면 `MainWindow.start_monitoring()`이 웹캠 프레임 캡처 및 결함 감지 타이머를 동작시킴.
3. `ImageProcessor.capture_frame()`이 최신 프레임을 가져와 동적 크롭을 수행.
4. 크롭된 프레임은 `DefectDetector.detect_defect()`를 통해 Custom Vision API로 전송되어 예측 결과를 획득.
5. 결함 발견 시 `PrinterMonitor.pause_print()`가 Moonraker API에 일시정지 요청을 보내고 UI에 로그가 표시됨.
6. 모든 주요 단계는 이벤트 핸들러(`EventType`)와 로그 시스템으로 사용자에게 피드백을 제공.

## 주요 모듈 분석

### 1. 메인 윈도우 & UI 조립 (`src/ui/main_window.py`)

팩토리 패턴으로 핵심 객체를 주입받고, UI 구성 요소와 타이머를 설정합니다. 신호-슬롯 연결로 사용자 인터랙션을 명확히 분리했습니다.

```python
# src/ui/main_window.py
self.control_panel.monitoring_start_button.clicked.connect(self.start_monitoring)
self.control_panel.monitoring_stop_button.clicked.connect(self.stop_monitoring)
self.control_panel.pause_button.clicked.connect(self.pause_print)
self.control_panel.resume_button.clicked.connect(self.resume_print)
```

에러 처리도 중앙집중화하여 어떤 컴포넌트에서 문제가 발생하든 동일한 UX를 제공합니다.

### 2. 동적 영역 추출 & 이미지 파이프라인 (`src/core/image_processor.py`)

모니터링 경과 시간에 따라 관심 영역을 확장하는 크롭 로직으로, 초반엔 프린팅 베드의 중심부만 집중하고 시간이 흐르면 범위를 넓혀 안정성과 성능을 모두 잡았습니다.

```python
# src/core/image_processor.py
width_ratio = min(
    CROP_CONFIG['initial_width_ratio'] +
    (CROP_CONFIG['width_growth_rate'] * elapsed_minutes),
    CROP_CONFIG['max_width_ratio']
)
```

또한 `capture_frame()`에서 캐시 우회를 위해 타임스탬프를 붙이고 네트워크 타임아웃, 리트라이 등 안정성을 확보했습니다.

### 3. Azure Custom Vision 결함 감지 (`src/core/defect_detector.py`)

Raw 이미지를 RGB로 변환해 JPEG 스트림으로 압축 후 Custom Vision Detect API에 전달합니다. 감지된 바운딩 박스를 시각적으로 강조할 뿐 아니라 `EventType.DEFECT_DETECTED` 이벤트로 상위 레이어에 알립니다.

```python
# src/core/defect_detector.py
response = self.session.post(self.api_endpoint, data=image_bytes)
response.raise_for_status()
results = response.json()
high_confidence_predictions = [
    p for p in results.get('predictions', [])
    if p['probability'] > self.detection_threshold
]
```

박스 영역은 반투명 오버레이와 확률 텍스트를 Overlay해 사용자가 즉시 인지할 수 있게 했습니다.

### 4. 프린터 원격 제어 (`src/core/printer_monitor.py`)

Moonraker API와 통신하는 `APIClient`를 감싼 래퍼입니다. 상태 변경 시 이벤트를 발행해 UI와 로거에서 동일한 정보를 공유합니다.

```python
# src/core/printer_monitor.py
response = self._api_client.pause_print()
if response.get('success', False):
    self._update_status(PrinterStatus.PAUSED)
```

`get_printer_status`, `get_temperature_data`, `get_print_progress` 등 모듈화된 메서드로 확장에 용이합니다.

### 5. 견고한 API 통신 (`src/utils/api_client.py`)

재시도, 타임아웃, 이벤트 발행을 한 곳에서 처리하는 재사용 가능한 HTTP 래퍼입니다.

```python
# src/utils/api_client.py
while retries < self._retry_config.max_retries:
    try:
        response = self._session.request(
            method=method,
            url=url,
            json=data if files is None else None,
            data=data if files is not None else None,
            timeout=self._retry_config.timeout
        )
        self._validate_response(response)
        return APIResponse(success=True, data=response.json(), ...)
    except (ConnectionError, Timeout) as e:
        retries += 1
        time.sleep(self._retry_config.retry_delay)
```

요청이 성공하든 실패하든 `request_completed`, `retry_attempted`, `EventType.ERROR_OCCURRED` 이벤트로 상위 레벨이 상황을 인지할 수 있습니다.

### 6. 설정/환경 관리

- `.env` → `src/utils/env_loader.py` → `src/constants/settings.py`의 체인을 통해 키와 파라미터를 로드.
- `Config` 클래스(`src/utils/config.py`)는 JSON 파일 기반의 사용자 설정 저장/로드/리셋을 담당.
- `pyproject.toml`에는 formatter(Black), linter(isort/pylint), 타입 검사(mypy), 커버리지 등 개발 품질 툴 설정을 정의했습니다.

## 사용자 경험 요소

- `ControlPanel`이 URL 입력, 모니터링 제어 버튼, 실시간 로그를 제공.
- `VideoDisplayWidget`이 웹캠/비전 화면을 나란히 렌더링하여 결함 인식 결과를 즉시 비교.
- 개인정보 동의 다이얼로그(`ControlPanel.show_consent_dialog`)로 실제 사용 환경에서의 컴플라이언스 고려.
- `styles.py`의 글로벌 스타일시트로 일관된 UI 룩앤필 부여.

## 레거시 스크립트 (`version1.py`)

초기 실험 버전인 `version1.py`는 단일 파일 구조로 동일한 기능을 구현했습니다. 클래스와 함수가 한곳에 모여 있어 빠른 프로토타입 작성에는 유리하지만, 현재 폴더 구조는 이를 모듈화하여 유지보수성을 크게 개선한 버전입니다. 이력서에선 “모놀리식 PoC → 계층화된 아키텍처”로 리팩터링한 경험을 강조할 수 있습니다.

## 기술 포인트 (Resume Highlight)

1. **이벤트 기반 아키텍처**: UI와 백엔드 로직 간 이벤트 버스를 설계해 느슨한 결합과 재사용성을 확보.
2. **컴퓨터 비전 통합**: Azure Custom Vision Detect API를 활용해 실시간 이상 징후를 시각화.
3. **동적 관심영역 추적**: 프린팅 진행도에 맞춰 관심영역을 확장하는 알고리즘으로 성능과 정확도의 균형 달성.
4. **안정적인 네트워크 계층**: 재시도, 타임아웃, 에러 래핑을 갖춘 API 클라이언트로 산업용 안정성을 확보.
5. **UX & 컴플라이언스 고려**: 실시간 로그, 상태바, 개인정보 동의 등 사용자 및 법적 요구사항 반영.

## 향후 확장 아이디어

- Custom Vision 결과를 누적/학습해 결함 유형별 통계 대시보드 제공.
- MQTT 등 실시간 프로토콜을 이용한 프린터 상태 스트리밍.
- 테스트 스위트를 추가해 시뮬레이션 프레임/프린터 응답을 검증.
- 다중 카메라/프린터 지원을 위한 멀티 세션 관리 레이어.

---

이 문서는 프로젝트 구조와 기술적 특징을 빠르게 이해하고 이력서/포트폴리오에 반영할 수 있도록 작성되었습니다. 추가로 강조하고 싶은 세부 영역이 있다면 알려주세요!
