"""3D 프린팅 결함 감지 모듈"""

import cv2
import numpy as np
from PIL import Image
import io
from datetime import datetime
import os
from typing import Optional, Dict, Any, Tuple, List, Callable
from dataclasses import dataclass
import requests
from ..constants.settings import (
    VISION_CONFIG,
    EventType,
    ERROR_MESSAGES,
    IMAGE_PROCESSING
)
from .interfaces.defect_detector_interface import DefectDetectorInterface

@dataclass
class DefectInfo:
    """결함 정보를 담는 데이터 클래스"""
    tag: str
    probability: float
    bbox: Dict[str, float]
    timestamp: str

class DefectDetectionError(Exception):
    """결함 감지 관련 예외"""
    def __init__(
        self, 
        message: str, 
        error_type: str, 
        details: Optional[Dict] = None
    ):
        super().__init__(message)
        self.error_type = error_type
        self.details = details or {}

class DefectDetector(DefectDetectorInterface):
    """3D 프린팅 결함 감지를 담당하는 클래스"""
    
    def __init__(
        self,
        prediction_key: str,
        project_id: str,
        iteration_name: str,
        detection_threshold: float = 0.7,
        session: Optional[requests.Session] = None
    ):
        """
        결함 감지기 초기화
        Args:
            prediction_key: Azure Custom Vision prediction key
            project_id: 프로젝트 ID
            iteration_name: 반복 학습 이름
            detection_threshold: 감지 임계값
            session: 외부 HTTP 세션 (선택사항)
        """
        self.prediction_key = prediction_key
        self.project_id = project_id
        self.iteration_name = iteration_name
        self.detection_threshold = detection_threshold
        self.api_endpoint = (
            f"{VISION_CONFIG['API_ENDPOINT']}/{project_id}/"
            f"detect/iterations/{iteration_name}/image"
        )
        
        # HTTP 세션 초기화 또는 주입
        self.session = session or self._create_session()
        
        # 이벤트 핸들러 초기화
        self._event_handlers = {
            EventType.DEFECT_DETECTED: [],
            EventType.ERROR_OCCURRED: []
        }

    def _create_session(self) -> requests.Session:
        """HTTP 세션 생성 및 설정"""
        session = requests.Session()
        session.headers.update({
            'Prediction-Key': self.prediction_key,
            'Content-Type': 'application/octet-stream'
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

    def detect_defect(
        self,
        image: np.ndarray
    ) -> Tuple[List[Dict[str, Any]], Optional[np.ndarray]]:
        """
        이미지에서 결함을 감지
        Args:
            image: OpenCV 이미지 배열
        Returns:
            결함 목록과 바운딩 박스가 그려진 이미지
        Raises:
            DefectDetectionError: 결함 감지 실패 시
        """
        try:
            # 이미지 유효성 검증
            if image is None or image.size == 0:
                raise DefectDetectionError(
                    "유효하지 않은 이미지",
                    "invalid_image"
                )

            # 이미지 전처리
            processed_image = self._preprocess_image(image)
            
            # API 요청 및 예측
            predictions = self._request_detection(processed_image)
            
            if not predictions:
                return [], None

            # 결함 정보 및 이미지 처리
            defects = []
            image_with_boxes = image.copy()
            
            # 신뢰도 기준값 이상인 예측만 필터링
            high_confidence_predictions = [
                p for p in predictions 
                if p['probability'] > self.detection_threshold
            ]
            
            if not high_confidence_predictions:
                return [], None

            # 각 결함에 대한 처리
            for prediction in high_confidence_predictions:
                defect_info = self._create_defect_info(prediction)
                defects.append(defect_info.__dict__)
                self._draw_bounding_box(image_with_boxes, prediction)
            
            # 결함 감지 이벤트 발생
            if defects:
                self._emit(EventType.DEFECT_DETECTED, {
                    'defects': defects,
                    'image_shape': image.shape[:2]
                })

            return defects, image_with_boxes
            
        except DefectDetectionError:
            raise
        except Exception as e:
            error = DefectDetectionError(
                ERROR_MESSAGES['VISION_API_ERROR'],
                "detection_failed",
                {'original_error': str(e)}
            )
            self._emit(EventType.ERROR_OCCURRED, {'error': error.__dict__})
            raise error

    def _preprocess_image(self, image: np.ndarray) -> bytes:
        """
        이미지 전처리
        Args:
            image: OpenCV 이미지
        Returns:
            전처리된 이미지 바이트
        """
        try:
            # BGR to RGB 변환
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image_pil = Image.fromarray(image_rgb)
            
            # 이미지를 바이트 스트림으로 변환
            img_byte_arr = io.BytesIO()
            image_pil.save(
                img_byte_arr,
                format='JPEG',
                quality=IMAGE_PROCESSING['JPEG_QUALITY']
            )
            return img_byte_arr.getvalue()
            
        except Exception as e:
            raise DefectDetectionError(
                "이미지 전처리 실패",
                "preprocessing_failed",
                {'original_error': str(e)}
            )

    def _request_detection(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Custom Vision API 요청
        Args:
            image_bytes: 이미지 바이트 데이터
        Returns:
            감지된 결함 목록
        """
        try:
            response = self.session.post(
                self.api_endpoint,
                data=image_bytes
            )
            response.raise_for_status()
            
            results = response.json()
            return results.get('predictions', [])
            
        except requests.exceptions.RequestException as e:
            raise DefectDetectionError(
                "API 요청 실패",
                "api_request_failed",
                {'original_error': str(e)}
            )

    def _create_defect_info(self, prediction: Dict[str, Any]) -> DefectInfo:
        """
        예측 결과로부터 결함 정보 생성
        Args:
            prediction: 예측 결과 딕셔너리
        Returns:
            결함 정보 객체
        """
        return DefectInfo(
            tag=prediction['tagName'],
            probability=prediction['probability'],
            bbox=prediction['boundingBox'],
            timestamp=datetime.now().isoformat()
        )

    def _draw_bounding_box(self, image: np.ndarray, prediction: Dict[str, Any]) -> None:
        """
        결함 영역에 바운딩 박스 그리기
        Args:
            image: 원본 이미지
            prediction: 예측 결과
        """
        try:
            h, w = image.shape[:2]
            box = prediction['boundingBox']
            
            # 좌표 계산
            x = int(box['left'] * w)
            y = int(box['top'] * h)
            box_w = int(box['width'] * w)
            box_h = int(box['height'] * h)
            
            # 반투명 박스 그리기
            overlay = image.copy()
            cv2.rectangle(
                overlay,
                (x, y),
                (x + box_w, y + box_h),
                (0, 0, 255),
                -1
            )
            cv2.addWeighted(overlay, 0.3, image, 0.7, 0, image)
            
            # 실선 테두리 그리기
            cv2.rectangle(
                image,
                (x, y),
                (x + box_w, y + box_h),
                (0, 0, 255),
                3
            )
            
            self._add_text_overlay(
                image,
                prediction['tagName'],
                prediction['probability'],
                x, y, box_w, box_h
            )
            
        except Exception as e:
            raise DefectDetectionError(
                "바운딩 박스 그리기 실패",
                "drawing_failed",
                {'original_error': str(e)}
            )

    def _add_text_overlay(
        self,
        image: np.ndarray,
        tag_name: str,
        probability: float,
        x: int,
        y: int,
        w: int,
        h: int
    ) -> None:
        """
        바운딩 박스에 텍스트 정보 추가
        Args:
            image: 대상 이미지
            tag_name: 결함 태그
            probability: 확률
            x, y, w, h: 박스 좌표
        """
        text = f"{tag_name}: {probability*100:.1f}%"
        font_scale = 0.8
        thickness = 2
        font = cv2.FONT_HERSHEY_DUPLEX
        
        # 텍스트 크기 계산
        (text_w, text_h), baseline = cv2.getTextSize(
            text, font, font_scale, thickness
        )
        
        # 텍스트 위치 및 배경
        padding = 5
        text_x = x
        text_y = max(y - 10, text_h + padding)
        
        # 텍스트 배경 그리기
        cv2.rectangle(
            image,
            (text_x, text_y - text_h - 2*padding),
            (text_x + text_w + 2*padding, text_y + padding),
            (0, 0, 255),
            -1
        )
        
        # 텍스트 그리기
        cv2.putText(
            image,
            text,
            (text_x + padding, text_y - padding),
            font,
            font_scale,
            (255, 255, 255),
            thickness,
            cv2.LINE_AA
        )

    def save_defect_image(self, image: np.ndarray, save_dir: str = "defects") -> str:
        """
        감지된 결함 이미지 저장
        Args:
            image: 저장할 이미지
            save_dir: 저장 디렉토리
        Returns:
            저장된 파일 경로
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            os.makedirs(save_dir, exist_ok=True)
            save_path = f"{save_dir}/defect_{timestamp}.jpg"
            
            # 이미지 저장
            cv2.imwrite(save_path, image)
            return save_path
            
        except Exception as e:
            raise DefectDetectionError(
                "이미지 저장 실패",
                "save_failed",
                {'original_error': str(e)}
            )