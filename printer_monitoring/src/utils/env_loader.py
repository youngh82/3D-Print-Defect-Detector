"""환경 변수 로드 및 검증을 담당하는 모듈"""

import os
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv

class EnvironmentError(Exception):
    """환경 변수 관련 예외"""
    pass

def load_env_vars() -> Dict[str, Any]:
    """
    .env 파일에서 환경 변수를 로드하고 필수 값들을 검증
    Returns:
        Dict[str, Any]: 로드된 환경 변수들
    Raises:
        EnvironmentError: 필수 환경 변수가 없거나 잘못된 경우
    """
    # .env 파일 로드
    env_path = Path(__file__).parent.parent.parent / '.env'
    load_dotenv(env_path)

    # 필수 환경 변수 목록
    required_vars = [
        'VISION_PREDICTION_KEY',
        'VISION_PROJECT_ID',
        'VISION_ITERATION_NAME',
        'VISION_API_ENDPOINT',
        'MOONRAKER_BASE_URL',
        'WEBCAM_URL'
    ]

    # 환경 변수 검증
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

    # 숫자형 환경 변수 변환 및 검증
    try:
        env_vars = {
            # Azure Custom Vision 설정
            'VISION_PREDICTION_KEY': os.getenv('VISION_PREDICTION_KEY'),
            'VISION_PROJECT_ID': os.getenv('VISION_PROJECT_ID'),
            'VISION_ITERATION_NAME': os.getenv('VISION_ITERATION_NAME'),
            'VISION_API_ENDPOINT': os.getenv('VISION_API_ENDPOINT'),

            # URL 설정
            'MOONRAKER_BASE_URL': os.getenv('MOONRAKER_BASE_URL'),
            'WEBCAM_URL': os.getenv('WEBCAM_URL'),

            # 네트워크 설정
            'REQUEST_TIMEOUT': int(os.getenv('REQUEST_TIMEOUT', '5')),
            'MAX_RETRIES': int(os.getenv('MAX_RETRIES', '3')),
            'RETRY_DELAY': int(os.getenv('RETRY_DELAY', '1')),

            # 모니터링 설정
            'DETECTION_THRESHOLD': float(os.getenv('DETECTION_THRESHOLD', '0.7')),
            'FRAME_INTERVAL': float(os.getenv('FRAME_INTERVAL', '1.0')),
            'PROCESSING_THRESHOLD': float(os.getenv('PROCESSING_THRESHOLD', '0.5')),
            'FRAME_SKIP': int(os.getenv('FRAME_SKIP', '2')),

            # 이미지 처리 설정
            'JPEG_QUALITY': int(os.getenv('JPEG_QUALITY', '95')),
            'MIN_IMAGE_WIDTH': int(os.getenv('MIN_IMAGE_WIDTH', '640')),
            'MIN_IMAGE_HEIGHT': int(os.getenv('MIN_IMAGE_HEIGHT', '480')),
            'MAX_IMAGE_WIDTH': int(os.getenv('MAX_IMAGE_WIDTH', '1920')),
            'MAX_IMAGE_HEIGHT': int(os.getenv('MAX_IMAGE_HEIGHT', '1080'))
        }
    except ValueError as e:
        raise EnvironmentError(f"Invalid environment variable value: {str(e)}")

    return env_vars