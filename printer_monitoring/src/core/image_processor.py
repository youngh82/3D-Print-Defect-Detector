"""이미지 처리 및 전처리를 담당하는 모듈"""

import cv2
import numpy as np
import requests
import time
from typing import Optional, Dict, Any, Tuple, Callable
from datetime import datetime
from dataclasses import dataclass
from .interfaces.image_processor_interface import ImageProcessorInterface
from ..constants.settings import (
    CROP_CONFIG,
    IMAGE_PROCESSING,
    EventType,
    ERROR_MESSAGES,
    NETWORK_CONFIG
)

@dataclass
class ImageDimensions:
    """이미지 크기 정보"""
    width: int
    height: int

@dataclass
class CropRegion:
    """크롭 영역 정보"""
    x: int
    y: int
    width: int
    height: int
    width_ratio: float
    bottom_ratio: float

class ImageProcessingError(Exception):
    """이미지 처리 관련 예외"""
    def __init__(
        self,
        message: str,
        error_type: str,
        details: Optional[Dict] = None
    ):
        super().__init__(message)
        self.error_type = error_type
        self.details = details or {}

class ImageProcessor(ImageProcessorInterface):
    """이미지 처리 및 전처리를 담당하는 클래스"""
    
    def __init__(self, session: Optional[requests.Session] = None):
        """
        이미지 프로세서 초기화
        Args:
            session: 외부에서 주입할 HTTP 세션 (선택사항)
        """
        self.session = session or self._init_session()
        self._event_handlers = {
            EventType.ERROR_OCCURRED: [],
            'image_processed': [],
            'crop_updated': []
        }
        self.monitoring_start_time: Optional[float] = None

    def _init_session(self) -> requests.Session:
        """HTTP 세션 초기화"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'image/jpeg, image/png, */*'
        })
        return session

    def on(self, event_type: str, handler: Callable) -> None:
        """
        이벤트 핸들러 등록
        Args:
            event_type: 이벤트 타입
            handler: 이벤트 핸들러 함수
        """
        if event_type in self._event_handlers:
            self._event_handlers[event_type].append(handler)

    def _emit(self, event_type: str, data: Optional[Dict] = None) -> None:
        """
        이벤트 발생
        Args:
            event_type: 이벤트 타입
            data: 이벤트 데이터
        """
        if event_type in self._event_handlers:
            event_data = {
                'type': event_type,
                'timestamp': datetime.now().isoformat(),
                'data': data or {}
            }
            for handler in self._event_handlers[event_type]:
                handler(event_data)

    def capture_frame(self, webcam_url: str) -> np.ndarray:
        """
        웹캠에서 프레임 캡처
        Args:
            webcam_url: 웹캠 URL
        Returns:
            캡처된 프레임
        Raises:
            ImageProcessingError: 캡처 실패 시
        """
        try:
            timestamp = int(time.time() * 1000)
            url = f"{webcam_url}?action=snapshot&bypassCache={timestamp}"
            
            response = self.session.get(
                url,
                timeout=NETWORK_CONFIG['REQUEST_TIMEOUT']
            )
            response.raise_for_status()
            
            image_array = np.frombuffer(response.content, dtype=np.uint8)
            frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            
            if frame is None or frame.size == 0:
                raise ImageProcessingError(
                    "이미지 캡처 실패",
                    "capture_failed"
                )
            
            self._validate_image_size(frame)
            return frame
            
        except requests.exceptions.RequestException as e:
            error = ImageProcessingError(
                ERROR_MESSAGES['CAMERA_ERROR'],
                "network_error",
                {'original_error': str(e)}
            )
            self._emit(EventType.ERROR_OCCURRED, {'error': error.__dict__})
            raise error
        except Exception as e:
            error = ImageProcessingError(
                "프레임 캡처 실패",
                "capture_failed",
                {'original_error': str(e)}
            )
            self._emit(EventType.ERROR_OCCURRED, {'error': error.__dict__})
            raise error

    def process_frame(
        self,
        frame: np.ndarray,
        monitoring_start_time: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        프레임 처리 및 분석
        Args:
            frame: 처리할 프레임
            monitoring_start_time: 모니터링 시작 시간
        Returns:
            처리된 이미지 정보
        Raises:
            ImageProcessingError: 처리 실패 시
        """
        try:
            if frame is None or frame.size == 0:
                raise ImageProcessingError(
                    "유효하지 않은 프레임",
                    "invalid_frame"
                )
            
            if monitoring_start_time and not self.monitoring_start_time:
                self.monitoring_start_time = monitoring_start_time
            
            cropped_frame = self._crop_print_area(frame)
            
            result = {
                'original': frame,
                'cropped': cropped_frame,
                'timestamp': datetime.now().isoformat(),
                'dimensions': ImageDimensions(
                    width=frame.shape[1],
                    height=frame.shape[0]
                ).__dict__
            }
            
            self._emit('image_processed', result)
            return result
            
        except Exception as e:
            error = ImageProcessingError(
                "프레임 처리 실패",
                "processing_failed",
                {'original_error': str(e)}
            )
            self._emit(EventType.ERROR_OCCURRED, {'error': error.__dict__})
            raise error

    def _crop_print_area(self, frame: np.ndarray) -> np.ndarray:
        """
        프린팅 영역을 동적으로 크롭
        Args:
            frame: 원본 프레임
        Returns:
            크롭된 이미지
        """
        try:
            if frame is None:
                raise ImageProcessingError(
                    "유효하지 않은 프레임",
                    "invalid_frame"
                )

            height, width = frame.shape[:2]
            center_x = width // 2
            center_y = height // 2
            
            elapsed_minutes = self._get_elapsed_minutes()
            crop_region = self._calculate_crop_region(
                width, height, center_x, center_y, elapsed_minutes
            )
            
            self._emit('crop_updated', crop_region.__dict__)
            
            return frame[
                crop_region.y:crop_region.y + crop_region.height,
                crop_region.x:crop_region.x + crop_region.width
            ]
                
        except Exception as e:
            error = ImageProcessingError(
                "이미지 크롭 실패",
                "crop_failed",
                {'original_error': str(e)}
            )
            self._emit(EventType.ERROR_OCCURRED, {'error': error.__dict__})
            raise error

    def _get_elapsed_minutes(self) -> float:
        """모니터링 경과 시간(분) 계산"""
        return (time.time() - self.monitoring_start_time) / 60 if self.monitoring_start_time else 0

    def _calculate_crop_region(
        self,
        width: int,
        height: int,
        center_x: int,
        center_y: int,
        elapsed_minutes: float
    ) -> CropRegion:
        """
        크롭 영역 계산
        Args:
            width: 이미지 너비
            height: 이미지 높이
            center_x: 이미지 중심 x좌표
            center_y: 이미지 중심 y좌표
            elapsed_minutes: 경과 시간(분)
        Returns:
            크롭 영역 정보
        """
        width_ratio = min(
            CROP_CONFIG['initial_width_ratio'] + 
            (CROP_CONFIG['width_growth_rate'] * elapsed_minutes),
            CROP_CONFIG['max_width_ratio']
        )
        
        bottom_ratio = min(
            CROP_CONFIG['initial_bottom_ratio'] + 
            (CROP_CONFIG['bottom_growth_rate'] * elapsed_minutes),
            CROP_CONFIG['max_bottom_ratio']
        )
        
        crop_width = int(width * width_ratio)
        crop_top = int(height * CROP_CONFIG['fixed_top_ratio'])

        x = max(0, min(center_x - (crop_width // 2), width - crop_width))
        y = max(0, center_y - (crop_top // 2))
        crop_bottom = min(height, center_y + int(height * bottom_ratio))

        return CropRegion(
            x=x,
            y=y,
            width=crop_width,
            height=max(1, crop_bottom - y),
            width_ratio=width_ratio,
            bottom_ratio=bottom_ratio
        )

    def _validate_image_size(self, image: np.ndarray) -> None:
        """
        이미지 크기 검증
        Args:
            image: 검증할 이미지
        Raises:
            ImageProcessingError: 이미지 크기가 유효하지 않을 때
        """
        height, width = image.shape[:2]
        min_width, min_height = IMAGE_PROCESSING['MIN_IMAGE_SIZE']
        max_width, max_height = IMAGE_PROCESSING['MAX_IMAGE_SIZE']
        
        if width < min_width or height < min_height:
            raise ImageProcessingError(
                "이미지 크기가 너무 작습니다",
                "invalid_size",
                {
                    'current': {'width': width, 'height': height},
                    'minimum': {'width': min_width, 'height': min_height}
                }
            )
            
        if width > max_width or height > max_height:
            raise ImageProcessingError(
                "이미지 크기가 너무 큽니다",
                "invalid_size",
                {
                    'current': {'width': width, 'height': height},
                    'maximum': {'width': max_width, 'height': max_height}
                }
            )

    def start_monitoring(self) -> None:
        """모니터링 시작"""
        self.monitoring_start_time = time.time()

    def stop_monitoring(self) -> None:
        """모니터링 중지"""
        self.monitoring_start_time = None