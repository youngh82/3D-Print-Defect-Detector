# print_monitor_detection.py
import cv2
import numpy as np
import requests
from PIL import Image
import io
from datetime import datetime
import os
import logging
from pathlib import Path
from typing import Optional, Tuple, List, Dict

class PrintMonitorDetection:
    def __init__(self, ui, printer_control, detection_config):
        """
        결함 감지 모듈 초기화
        
        Args:
            ui: UI 컴포넌트 참조
            printer_control: 프린터 제어 컴포넌트 참조
            detection_config: 결함 감지 관련 설정
        """
        # 컴포넌트 참조 저장
        self.ui = ui
        self.printer_control = printer_control
        self.config = detection_config
        
        # 로거 설정
        self.logger = logging.getLogger(__name__)
        
        # 결함 감지 상태 초기화
        self.defect_detected = False
        self.defect_logged = False
        
        # API 세션 초기화
        self.session = requests.Session()
        
        # 작업 디렉토리 설정
        self.defects_dir = Path(self.config.defects_dir)
        self.defects_dir.mkdir(exist_ok=True)
        
        self.logger.info("결함 감지 모듈이 초기화되었습니다.")

    def detect_defect(self, image: np.ndarray) -> Tuple[List[Dict], Optional[np.ndarray]]:
        """
        이미지에서 결함을 감지하는 메서드
        
        Args:
            image: OpenCV 이미지 배열
            
        Returns:
            튜플: (결함 목록, 바운딩 박스가 그려진 이미지)
        """
        try:
            # 이미지 전처리
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image_pil = Image.fromarray(image_rgb)
            
            # 이미지를 바이트 스트림으로 변환
            img_byte_arr = io.BytesIO()
            image_pil.save(img_byte_arr, format='JPEG', quality=95)
            img_byte_arr = img_byte_arr.getvalue()
            
            # API 요청 헤더 설정
            headers = {
                'Prediction-Key': self.config.prediction_key,
                'Content-Type': 'application/octet-stream'
            }
            
            # API 엔드포인트 URL 구성
            url = f"{self.config.api_base_url}/{self.config.project_id}/detect/iterations/{self.config.iteration_name}/image"
            
            # API 요청
            response = self.session.post(url, headers=headers, data=img_byte_arr)
            response.raise_for_status()
            
            if response.status_code != 200:
                self.log_message(f"Custom Vision API 오류 (상태 코드: {response.status_code})", 'error')
                return [], None
            
            # 결과 처리
            results = response.json()
            predictions = results.get('predictions', [])
            
            if not predictions:
                return [], None
            
            # 결함 정보 및 이미지 처리
            defects = []
            image_with_boxes = image.copy()
            
            # 임계값 이상인 예측만 필터링
            high_confidence_predictions = [
                p for p in predictions 
                if p['probability'] > self.config.detection_threshold
            ]
            
            if high_confidence_predictions:
                # 가장 높은 신뢰도를 가진 결함 찾기
                highest_confidence = max(p['probability'] for p in high_confidence_predictions)
                highest_confidence_tag = next(
                    p['tagName'] for p in high_confidence_predictions 
                    if p['probability'] == highest_confidence
                )
                
                # 첫 결함 발견 시에만 로그 출력
                if not self.defect_logged:
                    self.log_message(
                        f"결함 감지됨: {highest_confidence_tag} ({highest_confidence*100:.1f}% 신뢰도)", 
                        'defect'
                    )
                    # 결함 발견 시 프린터 일시정지
                    if self.printer_control.printer_status == "printing":
                        self.printer_control.pause_print()
                        self.log_message("결함이 감지되어 프린터를 일시정지합니다", 'warning')
                
                # 각 결함에 대한 시각화 처리
                for prediction in high_confidence_predictions:
                    defect_info = {
                        'tag': prediction['tagName'],
                        'probability': prediction['probability'],
                        'bbox': prediction['boundingBox']
                    }
                    defects.append(defect_info)
                    self.visualize_defect(image_with_boxes, prediction)
                
                # 결함 이미지 저장
                if not self.defect_logged and self.config.save_detected_images:
                    self.save_defect_image(image_with_boxes)
                    self.defect_logged = True
                    self.defect_detected = True
            
            return defects, image_with_boxes
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API 요청 중 오류 발생: {str(e)}")
            self.log_message("API 요청 중 오류가 발생했습니다", 'error')
            return [], None
        except Exception as e:
            self.logger.error(f"결함 감지 처리 중 오류 발생: {str(e)}")
            self.log_message(f"결함 감지 처리 중 오류 발생: {str(e)}", 'error')
            return [], None

    def visualize_defect(self, image: np.ndarray, prediction: Dict) -> None:
        """결함 시각화 처리"""
        try:
            h, w = image.shape[:2]
            box = prediction['boundingBox']
            
            # 바운딩 박스 좌표 계산
            x = int(box['left'] * w)
            y = int(box['top'] * h)
            box_w = int(box['width'] * w)
            box_h = int(box['height'] * h)
            
            # 반투명 오버레이 생성
            overlay = image.copy()
            cv2.rectangle(
                overlay,
                (x, y),
                (x + box_w, y + box_h),
                (0, 0, 255),
                -1
            )
            
            # 반투명 효과 적용
            cv2.addWeighted(overlay, 0.3, image, 0.7, 0, image)
            
            # 실선 테두리 그리기
            cv2.rectangle(
                image,
                (x, y),
                (x + box_w, y + box_h),
                (0, 0, 255),
                3
            )
            
            # 텍스트 정보 준비
            text = f"{prediction['tagName']}: {prediction['probability']*100:.1f}%"
            font = cv2.FONT_HERSHEY_DUPLEX
            font_scale = 0.8
            thickness = 2
            
            # 텍스트 크기 계산
            (text_w, text_h), baseline = cv2.getTextSize(
                text,
                font,
                font_scale,
                thickness
            )
            
            # 텍스트 배경 영역 계산
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
            
            # 높은 신뢰도 표시
            if prediction['probability'] > 0.9:
                marker_size = 20
                cv2.drawMarker(
                    image,
                    (x + box_w - marker_size, y + marker_size),
                    (0, 255, 0),
                    cv2.MARKER_STAR,
                    marker_size,
                    2
                )
                
        except Exception as e:
            self.logger.error(f"결함 시각화 중 오류 발생: {str(e)}")
            self.log_message(f"결함 시각화 중 오류 발생: {str(e)}", 'error')

    def save_defect_image(self, image: np.ndarray) -> None:
        """결함 이미지 저장"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = self.defects_dir / f"defect_{timestamp}.jpg"
            cv2.imwrite(str(save_path), image)
            self.log_message(f"결함 이미지 저장됨: {save_path}")
        except Exception as e:
            self.logger.error(f"이미지 저장 오류: {str(e)}")
            self.log_message(f"이미지 저장 오류: {str(e)}", 'error')

    def reset_detection_status(self) -> None:
        """결함 감지 상태 초기화"""
        self.defect_detected = False
        self.defect_logged = False

    def get_detection_status(self) -> Dict[str, bool]:
        """현재 결함 감지 상태 반환"""
        return {
            'defect_detected': self.defect_detected,
            'defect_logged': self.defect_logged
        }

    def log_message(self, message: str, level: str = 'info') -> None:
        """로그 메시지 출력"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            'info': '→',
            'warning': '⚠',
            'error': '❌',
            'defect': '🔍'
        }.get(level, '→')
        
        formatted_message = f"[{timestamp}] {prefix} {message}"
        self.ui.status_text.append(formatted_message)
        
        # 로거에도 기록
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.log(log_level, message)