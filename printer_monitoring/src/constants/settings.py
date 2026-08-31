"""프로젝트의 전역 상수 설정 파일"""
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from ..utils.env_loader import load_env_vars

# 환경 변수 로드
env = load_env_vars()

# 기본 URL 설정
DEFAULT_URLS: Final = {
    'MOONRAKER_BASE': env['MOONRAKER_BASE_URL'],
    'WEBCAM_URL': env['WEBCAM_URL'],
}

# Azure Custom Vision 설정
VISION_CONFIG: Final = {
    'PREDICTION_KEY': env['VISION_PREDICTION_KEY'],
    'PROJECT_ID': env['VISION_PROJECT_ID'],
    'ITERATION_NAME': env['VISION_ITERATION_NAME'],
    'API_ENDPOINT': env['VISION_API_ENDPOINT'],
}

# 네트워크 설정
NETWORK_CONFIG: Final = {
    'BASE_URL': env['MOONRAKER_BASE_URL'],
    'REQUEST_TIMEOUT': env['REQUEST_TIMEOUT'],
    'MAX_RETRIES': env['MAX_RETRIES'],
    'RETRY_DELAY': env['RETRY_DELAY'],
}

# 모니터링 설정
MONITORING_CONFIG: Final = {
    'DETECTION_THRESHOLD': env['DETECTION_THRESHOLD'],
    'FRAME_INTERVAL': env['FRAME_INTERVAL'],
    'PROCESSING_THRESHOLD': env['PROCESSING_THRESHOLD'],
    'FRAME_SKIP': env['FRAME_SKIP'],
}

# 이미지 처리 설정
IMAGE_PROCESSING: Final = {
    'MIN_IMAGE_SIZE': (env['MIN_IMAGE_WIDTH'], env['MIN_IMAGE_HEIGHT']),
    'MAX_IMAGE_SIZE': (env['MAX_IMAGE_WIDTH'], env['MAX_IMAGE_HEIGHT']),
    'JPEG_QUALITY': env['JPEG_QUALITY'],
}

# 크롭 설정
CROP_CONFIG: Final = {
    'initial_width_ratio': 0.45,
    'fixed_top_ratio': 0.4,
    'initial_bottom_ratio': 0.35,
    'max_width_ratio': 0.8,
    'max_bottom_ratio': 0.65,
    'width_growth_rate': 0.05,
    'bottom_growth_rate': 0.05,
}

# 파일 및 디렉토리 설정
PATHS: Final = {
    'BASE_DIR': Path(__file__).parent.parent.parent,
    'LOGS_DIR': 'logs',
    'DEFECTS_DIR': 'defects',
    'CONFIG_FILE': 'config.json',
}

# 상태 코드
class PrinterStatus:
    IDLE: Final = "idle"
    PRINTING: Final = "printing"
    PAUSED: Final = "paused"
    ERROR: Final = "error"

# 로그 레벨
class LogLevel:
    INFO: Final = "info"
    WARNING: Final = "warning"
    ERROR: Final = "error"
    DEFECT: Final = "defect"

# API 엔드포인트
class APIEndpoints:
    PRINTER_INFO: Final = "printer/info"
    PRINT_PAUSE: Final = "printer/print/pause"
    PRINT_RESUME: Final = "printer/print/resume"
    PRINT_CANCEL: Final = "printer/print/cancel"
    TEMPERATURE: Final = "printer/temperature"
    PROGRESS: Final = "printer/progress"
    FILES_UPLOAD: Final = "printer/files/upload"

# 에러 메시지
ERROR_MESSAGES: Final = {
    'CONNECTION_ERROR': '프린터 연결 실패: 네트워크 또는 서버 접속 오류',
    'TIMEOUT_ERROR': '요청 시간 초과',
    'AUTH_ERROR': '인증 실패',
    'API_ERROR': 'API 요청 실패',
    'INVALID_RESPONSE': '잘못된 응답 형식',
    'PRINTER_ERROR': '프린터 오류',
    'CAMERA_ERROR': '카메라 연결 실패',
    'VISION_API_ERROR': 'Custom Vision API 오류',
}

# 버튼 텍스트
BUTTON_TEXT: Final = {
    'START_MONITORING': '모니터링 시작',
    'STOP_MONITORING': '모니터링 중지',
    'PAUSE': '일시정지',
    'RESUME': '재개',
    'APPLY': '적용',
}

# 이벤트 타입
class EventType:
    DEFECT_DETECTED: Final = "defect_detected"
    STATUS_CHANGED: Final = "status_changed"
    MONITORING_STARTED: Final = "monitoring_started"
    MONITORING_STOPPED: Final = "monitoring_stopped"
    ERROR_OCCURRED: Final = "error_occurred"