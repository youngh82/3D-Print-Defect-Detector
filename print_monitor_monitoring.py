# print_monitor_monitoring.py
import cv2
import numpy as np
import requests
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap
from datetime import datetime
import time
import logging
from pathlib import Path
from typing import Optional, Tuple

class PrintMonitorMonitoring:
    def __init__(self, ui, defect_detection, monitoring_config):
        """
        모니터링 모듈 초기화
        
        Args:
            ui: UI 컴포넌트 참조
            defect_detection: 결함 감지 컴포넌트 참조
            monitoring_config: 모니터링 관련 설정
        """
        # 컴포넌트 참조 저장
        self.ui = ui
        self.defect_detection = defect_detection
        self.config = monitoring_config
        
        # 로거 설정
        self.logger = logging.getLogger(__name__)
        
        # 모니터링 상태 초기화
        self.monitoring = False
        self.last_processed_time = 0
        
        # 이미지 처리 관련 변수 초기화
        self.last_frame = None
        self.defect_image = None
        self.current_webcam_image = None
        self.current_vision_image = None
        
        # 세션 재사용을 위한 requests 세션 초기화
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'image/jpeg, image/png, */*'
        })
        
        # 타이머 설정
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        
        self.preview_timer = QTimer()
        self.preview_timer.timeout.connect(self.update_preview)
        
        # 모니터링 시작 시간 초기화
        self.monitoring_start_time = None
        
        self.logger.info("모니터링 모듈이 초기화되었습니다.")

    def start_monitoring(self) -> None:
        """모니터링 시작"""
        try:
            self.monitoring = True
            
            # 모니터링 시작 시간 초기화
            self.monitoring_start_time = time.time()
            self.last_processed_time = 0
            
            # 결함 감지 상태 초기화
            self.defect_detection.reset_detection_status()
            
            # 즉시 첫 검사 실행
            self.update_frame()
            
            # 타이머 시작
            self.timer.start(1000)  # 1초 간격
            self.preview_timer.start(1000)  # 1초 간격
            
            # UI 버튼 상태 업데이트
            self.ui.monitoring_start_button.setEnabled(False)
            self.ui.monitoring_stop_button.setEnabled(True)
            self.ui.pause_button.setEnabled(True)
            self.ui.resume_button.setEnabled(False)
            
            # 로그 메시지
            self.log_message("모니터링을 시작했습니다.")
            self.ui.statusBar().showMessage('모니터링 중...')
            
        except Exception as e:
            self.logger.error(f"모니터링 시작 중 오류 발생: {str(e)}")
            self.log_message(f"시작 오류: {str(e)}", 'error')

    def stop_monitoring(self) -> None:
        """모니터링 중지"""
        try:
            # 모니터링 상태 초기화
            self.monitoring = False
            self.monitoring_start_time = None
            
            # 결함 감지 상태 초기화
            self.defect_detection.reset_detection_status()
            
            # 타이머 중지
            self.timer.stop()
            self.preview_timer.stop()
            
            # UI 버튼 상태 업데이트
            self.ui.monitoring_start_button.setEnabled(True)
            self.ui.monitoring_stop_button.setEnabled(False)
            self.ui.pause_button.setEnabled(False)
            self.ui.resume_button.setEnabled(False)
            
            # Custom Vision 영역 초기화
            self.ui.vision_label.clear()
            self.current_vision_image = None
            
            # 로그 메시지
            self.log_message("모니터링을 중지했습니다.")
            self.ui.statusBar().showMessage('준비됨')
            
        except Exception as e:
            self.logger.error(f"모니터링 중지 중 오류 발생: {str(e)}")
            self.log_message(f"중지 오류: {str(e)}", 'error')

    def update_frame(self) -> None:
        """결함 검사를 위한 프레임 업데이트"""
        if not self.monitoring:
            return
            
        try:
            # 웹캠 이미지 캡처
            timestamp = int(time.time() * 1000)
            current_webcam_url = self.ui.webcam_url_input.text()
            url = f"{current_webcam_url}?action=snapshot&bypassCache={timestamp}"
            
            response = self.session.get(url)
            response.raise_for_status()
            
            image_array = np.frombuffer(response.content, dtype=np.uint8)
            frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            
            if frame is None or frame.size == 0:
                self.log_message("이미지 캡처 실패", 'error')
                return
            
            # 프린트 영역 크롭
            cropped_frame = self.crop_print_area(frame)
            
            if cropped_frame is not None:
                # 결함 감지 수행
                defects, image_with_boxes = self.defect_detection.detect_defect(cropped_frame)
                
                # 결함 감지 결과에 따른 이미지 표시
                if defects:
                    if image_with_boxes is not None:
                        self.update_vision_display(image_with_boxes)
                else:
                    self.update_vision_display(cropped_frame)
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"웹캠 연결 오류: {str(e)}")
            self.log_message("웹캠 연결에 실패했습니다", 'error')
        except Exception as e:
            self.logger.error(f"프레임 업데이트 중 오류 발생: {str(e)}")
            self.log_message(f"프레임 업데이트 오류: {str(e)}", 'error')

    def update_preview(self) -> None:
        """실시간 프리뷰 업데이트"""
        if not self.monitoring:
            return
            
        try:
            current_time = time.time()
            
            # 처리 주기 확인
            if current_time - self.last_processed_time < self.config.processing_interval:
                return
                
            timestamp = int(current_time * 1000)
            current_webcam_url = self.ui.webcam_url_input.text()
            url = f"{current_webcam_url}?action=snapshot&bypassCache={timestamp}"
            
            response = self.session.get(url)
            response.raise_for_status()
            
            image_array = np.frombuffer(response.content, dtype=np.uint8)
            frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            
            if frame is not None and frame.size > 0:
                self.update_webcam_display(frame)
                self.last_processed_time = current_time
                self.last_frame = frame
                
        except Exception as e:
            self.logger.error(f"프리뷰 업데이트 중 오류 발생: {str(e)}")
            self.log_message(f"프리뷰 업데이트 오류: {str(e)}", 'error')

    def crop_print_area(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """프린팅 영역 크롭"""
        try:
            if frame is None:
                return None
                
            height, width = frame.shape[:2]
            center_x = width // 2
            center_y = height // 2
            
            # 모니터링 시간 계산
            if self.monitoring_start_time is None:
                elapsed_minutes = 0
            else:
                elapsed_minutes = (time.time() - self.monitoring_start_time) / 60
            
            # 현재 크롭 비율 계산
            current_width_ratio = min(
                self.config.initial_width_ratio + (self.config.width_growth_per_minute * elapsed_minutes),
                self.config.max_width_ratio
            )
            
            current_bottom_ratio = min(
                self.config.initial_bottom_ratio + (self.config.bottom_growth_per_minute * elapsed_minutes),
                self.config.max_bottom_ratio
            )
            
            # 크롭 영역 계산
            crop_width = int(width * current_width_ratio)
            crop_top = int(height * self.config.fixed_top_ratio)
            crop_bottom = int(height * current_bottom_ratio)
            
            # 크롭 좌표 계산
            x = center_x - (crop_width // 2)
            y_top = center_y - (crop_top // 2)
            y_bottom = center_y + crop_bottom
            
            # 좌표 범위 조정
            x = max(0, min(x, width - crop_width))
            y_top = max(0, y_top)
            y_bottom = min(height, y_bottom)
            
            return frame[y_top:y_bottom, x:x+crop_width]
            
        except Exception as e:
            self.logger.error(f"이미지 크롭 중 오류 발생: {str(e)}")
            self.log_message(f"이미지 크롭 오류: {str(e)}", 'error')
            return frame

    def update_webcam_display(self, frame: np.ndarray) -> None:
        """웹캠 이미지 표시 업데이트"""
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            self.current_webcam_image = qt_image
            scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
                self.ui.webcam_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.ui.webcam_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            self.logger.error(f"웹캠 디스플레이 업데이트 중 오류 발생: {str(e)}")
            self.log_message(f"웹캠 디스플레이 업데이트 오류: {str(e)}", 'error')

    def update_vision_display(self, frame: np.ndarray) -> None:
        """Custom Vision 이미지 표시 업데이트"""
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            self.current_vision_image = qt_image
            scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
                self.ui.vision_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.ui.vision_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            self.logger.error(f"비전 디스플레이 업데이트 중 오류 발생: {str(e)}")
            self.log_message(f"비전 디스플레이 업데이트 오류: {str(e)}", 'error')

    def apply_webcam_url(self) -> None:
        """웹캠 URL 업데이트"""
        if self.ui.show_consent_dialog():
            self.log_message(f"웹캠 URL이 적용되었습니다: {self.ui.webcam_url_input.text()}")
            self.ui.webcam_apply_btn.setStyleSheet("background-color: #4CAF50; color: white;")
            QTimer.singleShot(1000, lambda: self.ui.webcam_apply_btn.setStyleSheet(""))
        else:
            self.log_message("웹캠 URL 적용이 취소되었습니다.")

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