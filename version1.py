import sys
import cv2
import numpy as np
import requests
import time
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from azure.cognitiveservices.vision.customvision.prediction import CustomVisionPredictionClient
from msrest.authentication import ApiKeyCredentials
from PIL import Image
import io
import os
from datetime import datetime
from styles import Styles, Colors  # Styles와 Colors 클래스를 import

class PrintMonitorApp(QMainWindow):

#모든 UI 및 변수 초기화를 담당하는 생성자 메소드.
    def __init__(self):
        super().__init__()
        self.setStyleSheet(Styles.get_main_window_style())  # 기본 스타일 적용
        
        # URL 설정
        self.moonraker_base_url = "http://3dro.kr:3002"
        self.webcam_url = "http://3dro.kr:3002/webcam/"
        
        # 세션 재사용을 위한 requests 세션 초기화
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'image/jpeg, image/png, */*',
            'Referer': 'http://3dro.kr:3002/cam'
        })
        
        # Azure Custom Vision API 설정
        self.prediction_key = '71rDXXeueNkSZlK997Cq9BRLMgT6pDXqgR6aaymfYTBNkmnPFAC1JQQJ99AKACYeBjFXJ3w3AAAIACOGFGph'
        self.project_id = '224ff5eb-7998-4705-a4fe-10b7be2d3e4b' #03ad7aee-92b9-4dce-a262-0d3510987126
        self.iteration_name = 'Iteration3'
        
        # 프린터 상태 초기화
        self.printer_status = "idle"
        
        # 상태 플래그 초기화
        self.monitoring = False           # 모니터링 실행 상태
        self.defect_detected = False      # 결함 감지 상태
        self.defect_logged = False        # 결함 로그 출력 상태
        self.last_processed_time = 0      # 마지막 처리 시간
        self.processing_threshold = 0.5    # 처리 주기 (초)
        
        # 이미지 처리 관련 변수 초기화
        self.last_frame = None            # 마지막 프레임 저장
        self.defect_image = None          # 결함 이미지 저장
        self.current_webcam_image = None  # 현재 웹캠 이미지
        self.current_vision_image = None  # 현재 비전 이미지
        
        # 이미지 처리 설정
        self.detection_threshold = 0.7    # 결함 감지 임계값
        self.frame_skip = 2              # 프레임 스킵 수
        self.frame_count = 0             # 현재 프레임 카운트
        
        # 크롭 설정
        self.initial_width_ratio = 0.35   # 초기 너비 비율
        self.fixed_top_ratio = 0.2        # 고정된 상단 비율
        self.initial_bottom_ratio = 0.3   # 초기 하단 비율
        self.max_width_ratio = 0.7        # 최대 너비 비율
        self.max_bottom_ratio = 0.6       # 최대 하단 비율
        self.width_growth_per_minute = 0.05    # 분당 너비 성장률
        self.bottom_growth_per_minute = 0.05   # 분당 하단 성장률
        
        # UI 초기화
        self.initUI()
        
        # 타이머 설정
        self.timer = QTimer()             # 결함 검사용 타이머
        self.timer.timeout.connect(self.update_frame)
        
        self.preview_timer = QTimer()     # 프리뷰 업데이트용 타이머
        self.preview_timer.timeout.connect(self.update_preview)
        
        # 디버그 모드 설정
        self.debug_mode = False           # 디버그 모드 플래그
        self.debug_frame = None           # 디버그용 프레임
        
        # 윈도우 설정
        self.adjustSize()
        self.centerWindow()
        
        # 모니터링 시작 시간 초기화 (동적 크롭 영역 계산용)
        self.monitoring_start_time = None
        
        # 기본 윈도우 크기 설정
        self.setMinimumSize(1024, 768)    # 최소 윈도우 크기
        
        # 상태바 초기화
        self.statusBar().showMessage('준비됨')
        
        # 작업 디렉토리 생성
        self.defects_dir = "defects"
        os.makedirs(self.defects_dir, exist_ok=True)  # 결함 이미지 저장 디렉토리
        
        # 로그 설정
        self.max_log_lines = 50           # 최대 로그 라인 수
        
        # 에러 핸들링을 위한 재시도 설정
        self.max_retries = 3              # 최대 재시도 횟수
        self.retry_delay = 1              # 재시도 간 대기 시간(초)
        
        # 네트워크 타임아웃 설정
        self.request_timeout = 5          # 요청 타임아웃(초)
        
        try:
            # 초기 프린터 상태 확인
            self.update_printer_status("idle")
        except Exception as e:
            self.log_message(f"초기 프린터 상태 확인 실패: {str(e)}", 'error')
        
        # 키 이벤트 바인딩
        self.shortcut_start = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_start.activated.connect(self.start_monitoring)
        
        self.shortcut_stop = QShortcut(QKeySequence("Ctrl+X"), self)
        self.shortcut_stop.activated.connect(self.stop_monitoring)
        
        self.shortcut_pause = QShortcut(QKeySequence("Space"), self)
        self.shortcut_pause.activated.connect(self.toggle_pause_resume)

#UI 초기화:
    def initUI(self):
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 설정 그룹
        settings_group = QGroupBox("모니터링 설정")
        settings_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        settings_layout = QGridLayout()
        settings_layout.setColumnStretch(1, 1)
        
        # 웹캠 URL 입력 필드와 적용 버튼
        self.webcam_url_input = QLineEdit(self.webcam_url)
        self.webcam_apply_btn = QPushButton("적용")
        self.webcam_apply_btn.clicked.connect(self.apply_webcam_url)
        settings_layout.addWidget(QLabel("Webcam URL:"), 0, 0)
        settings_layout.addWidget(self.webcam_url_input, 0, 1)
        settings_layout.addWidget(self.webcam_apply_btn, 0, 2)
        
        # Moonraker URL 입력 필드와 적용 버튼
        self.moonraker_url_input = QLineEdit(self.moonraker_base_url)
        self.moonraker_apply_btn = QPushButton("적용")
        self.moonraker_apply_btn.clicked.connect(self.apply_moonraker_url)
        settings_layout.addWidget(QLabel("Moonraker URL:"), 1, 0)
        settings_layout.addWidget(self.moonraker_url_input, 1, 1)
        settings_layout.addWidget(self.moonraker_apply_btn, 1, 2)
        
        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)
        
        # 비디오 표시 영역 컨테이너 (두 개의 화면을 나란히 배치)
        video_container = QGroupBox("실시간 모니터링")
        video_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        video_layout = QHBoxLayout()  # 수평 레이아웃으로 변경
        
        # 왼쪽: 실시간 웹캠 화면
        left_group = QGroupBox("실시간 웹캠")
        left_layout = QVBoxLayout()
        self.webcam_label = QLabel()
        self.webcam_label.setObjectName("videoLabel")
        self.webcam_label.setMinimumSize(480, 360)
        self.webcam_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.webcam_label.setAlignment(Qt.AlignCenter)
        self.webcam_label.setScaledContents(True)
        left_layout.addWidget(self.webcam_label)
        left_group.setLayout(left_layout)
        
        # 오른쪽: Custom Vision 검사 영역
        right_group = QGroupBox("Custom Vision 검사 영역")
        right_layout = QVBoxLayout()
        self.vision_label = QLabel()
        self.vision_label.setObjectName("videoLabel")
        self.vision_label.setMinimumSize(480, 360)
        self.vision_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.vision_label.setAlignment(Qt.AlignCenter)
        self.vision_label.setScaledContents(True)
        right_layout.addWidget(self.vision_label)
        right_group.setLayout(right_layout)
        
        # 두 화면을 컨테이너에 추가
        video_layout.addWidget(left_group)
        video_layout.addWidget(right_group)
        video_container.setLayout(video_layout)
        main_layout.addWidget(video_container)
        
        # 하단 영역 (로그 + 버튼)
        bottom_container = QGroupBox("상태 및 제어")
        bottom_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        bottom_layout = QVBoxLayout()
        
        # 로그 영역
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(100)
        bottom_layout.addWidget(self.status_text)
        
        # 버튼 영역
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # 버튼 스타일 정의
        button_base_style = """
            QPushButton {
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                min-width: 100px;
                min-height: 30px;
                margin: 2px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """
        
        monitor_button_style = button_base_style + """
            QPushButton {
                background-color: #4CAF50;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """
        
        pause_button_style = button_base_style + """
            QPushButton {
                background-color: #ffa500;
            }
            QPushButton:hover {
                background-color: #ff8c00;
            }
            QPushButton:pressed {
                background-color: #d2691e;
            }
        """
        
        resume_button_style = button_base_style + """
            QPushButton {
                background-color: #28a745;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """
        
        # 버튼 생성 및 스타일 적용
        self.monitoring_start_button = QPushButton("모니터링 시작")
        self.monitoring_start_button.setStyleSheet(monitor_button_style)
        self.monitoring_start_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        
        self.monitoring_stop_button = QPushButton("모니터링 중지")
        self.monitoring_stop_button.setStyleSheet(monitor_button_style)
        self.monitoring_stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        
        self.pause_button = QPushButton("일시정지")
        self.pause_button.setStyleSheet(pause_button_style)
        self.pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        
        self.resume_button = QPushButton("재개")
        self.resume_button.setStyleSheet(resume_button_style)
        self.resume_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        
        # 초기 버튼 상태 설정
        self.monitoring_stop_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        
        # 버튼 이벤트 연결
        self.monitoring_start_button.clicked.connect(self.start_monitoring)
        self.monitoring_stop_button.clicked.connect(self.stop_monitoring)
        self.pause_button.clicked.connect(self.pause_print)
        self.resume_button.clicked.connect(self.resume_print)
        
        # 버튼 레이아웃에 추가
        button_layout.addStretch()
        button_layout.addWidget(self.monitoring_start_button)
        button_layout.addWidget(self.monitoring_stop_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.resume_button)
        button_layout.addStretch()
        
        bottom_layout.addLayout(button_layout)
        bottom_container.setLayout(bottom_layout)
        main_layout.addWidget(bottom_container)

    def display_webcam_image(self):
            """웹캠 이미지 표시"""
            if hasattr(self, 'current_webcam_image'):
                scaled_pixmap = QPixmap.fromImage(self.current_webcam_image).scaled(
                    self.webcam_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.webcam_label.setPixmap(scaled_pixmap)

    def display_vision_image(self):
        """Custom Vision 이미지 표시"""
        if hasattr(self, 'current_vision_image'):
            scaled_pixmap = QPixmap.fromImage(self.current_vision_image).scaled(
                self.vision_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.vision_label.setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        """창 크기 변경 이벤트"""
        super().resizeEvent(event)
        # 창 크기가 변경될 때만 이미지 리사이징
        self.display_webcam_image()
        self.display_vision_image()

    def centerWindow(self):
        screen = QDesktopWidget().screenGeometry()
        window_size = self.geometry()
        x = (screen.width() - window_size.width()) // 2
        y = (screen.height() - window_size.height()) // 2
        self.move(x, y)

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


#모니터링 기능 구현:
    def start_monitoring(self):
        """모니터링 시작 메소드"""
        try:
            # 모니터링 상태를 활성화
            self.monitoring = True
            # 결함 로깅 상태 초기화
            self.defect_logged = False
            # 결함 감지 상태 초기화
            self.defect_detected = False
            
            # 모니터링 시작 시간 초기화
            self.monitoring_start_time = time.time()
            # 마지막 처리 시간 초기화
            self.last_processed_time = 0
            
            # 즉시 첫 검사 실행
            self.update_frame()
            
            # 타이머 시작 (1초 간격으로 결함 검사)
            self.timer.start(1000)
            # 프리뷰 업데이트 타이머 시작 (1초 간격)
            self.preview_timer.start(1000)
            
            # 버튼 상태 업데이트
            self.monitoring_start_button.setEnabled(False)  # 모니터링 시작 버튼 비활성화
            self.monitoring_stop_button.setEnabled(True)    # 모니터링 중지 버튼 활성화
            self.pause_button.setEnabled(True)              # 일시 정지 버튼 활성화
            self.resume_button.setEnabled(False)            # 재개 버튼 비활성화
            
            # 로그 및 상태바 업데이트
            self.log_message("모니터링을 시작했습니다.")  # 로그 메시지 기록
            self.statusBar().showMessage('모니터링 중...')  # 상태바 메시지 업데이트
        
        except Exception as e:
            # 예외 발생 시 로그 메시지 기록 및 오류 메시지 박스 표시
            self.log_message(f"시작 오류: {str(e)}", 'error')
            QMessageBox.critical(self, "오류", f"모니터링 시작 실패: {str(e)}")

    def stop_monitoring(self):
        """모니터링 중지 메소드"""
        try:
            # 모니터링 상태 초기화
            self.monitoring = False
            self.defect_logged = False  # 결함 로깅 상태 초기화
            self.defect_detected = False  # 결함 감지 상태 초기화
            self.monitoring_start_time = None  # 시작 시간 초기화
            
            # 타이머 중지
            self.timer.stop()
            self.preview_timer.stop()
            
            # 버튼 상태 업데이트
            self.monitoring_start_button.setEnabled(True)
            self.monitoring_stop_button.setEnabled(False)
            self.pause_button.setEnabled(False)
            self.resume_button.setEnabled(False)
            
            # Custom Vision 영역 초기화
            if hasattr(self, 'current_vision_image'):
                self.vision_label.clear()
                self.current_vision_image = None
            
            # 로그 및 상태바 업데이트
            self.log_message("모니터링을 중지했습니다.")
            self.statusBar().showMessage('준비됨')
            
        except Exception as e:
            self.log_message(f"중지 오류: {str(e)}", 'error')
            QMessageBox.critical(self, "오류", f"모니터링 중지 실패: {str(e)}")

    def update_frame(self):
        """결함 검사를 위한 프레임 업데이트 메소드"""
        if not self.monitoring:
            return
                    
        try:
            # 웹캠 이미지 캡처
            timestamp = int(time.time() * 1000)
            current_webcam_url = self.webcam_url_input.text()
            url = f"{current_webcam_url}?action=snapshot&bypassCache={timestamp}"
            
            response = self.session.get(url)
            
            if response.status_code == 200:
                # 이미지 디코딩
                image_array = np.frombuffer(response.content, dtype=np.uint8)
                frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                
                if frame is None or frame.size == 0:
                    self.log_message("이미지 캡처 실패", 'error')
                    return
                
                # 프린트 영역 크롭 및 결함 검사
                cropped_frame = self.crop_print_area(frame)
                
                if cropped_frame is not None:
                    defects, image_with_boxes = self.detect_defect(cropped_frame)
                    
                    if defects and not self.defect_logged:
                        self.defect_detected = True
                        self.defect_logged = True
                        
                        if image_with_boxes is not None:
                            # 결함 이미지 저장 및 표시
                            self.defect_image = image_with_boxes
                            self.save_defect_image(image_with_boxes)
                            
                            # 결함 발견 시 프린터 일시정지
                            if self.printer_status == "printing":
                                self.pause_print()
                                self.log_message("결함이 감지되어 프린터를 일시정지합니다", 'warning')
                    
                    # 결함 감지 여부와 관계없이 항상 검사 영역 표시 업데이트
                    display_image = image_with_boxes if image_with_boxes is not None else cropped_frame
                    rgb_image = cv2.cvtColor(display_image, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb_image.shape
                    bytes_per_line = ch * w
                    self.current_vision_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    self.display_vision_image()
                        
            else:
                self.log_message(f"웹캠 연결 실패 (상태 코드: {response.status_code})", 'error')
                        
        except Exception as e:
            self.log_message(f"결함 검사 오류: {str(e)}", 'error')

    def update_preview(self):
        """프리뷰 업데이트 메서드"""
        if not hasattr(self, 'webcam_label'):
            return
                    
        try:
            current_time = time.time()
            
            # 최소 업데이트 간격을 1초로 설정
            if current_time - self.last_processed_time < 1.0:
                return
                        
            timestamp = int(current_time * 1000)
            current_webcam_url = self.webcam_url_input.text()
            url = f"{current_webcam_url}?action=snapshot&bypassCache={timestamp}"
            
            response = self.session.get(url)
            
            if response.status_code == 200:
                image_array = np.frombuffer(response.content, dtype=np.uint8)
                frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                
                if frame is None or frame.size == 0:
                    return
                        
                # 웹캠 화면 업데이트
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                self.current_webcam_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                self.display_webcam_image()
                
                # Custom Vision 검사 영역도 실시간 업데이트
                cropped_frame = self.crop_print_area(frame)
                if cropped_frame is not None and not self.defect_detected:
                    rgb_cropped = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb_cropped.shape
                    bytes_per_line = ch * w
                    self.current_vision_image = QImage(rgb_cropped.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    self.display_vision_image()
                
                self.last_processed_time = current_time
                self.last_frame = frame
                    
        except Exception as e:
            self.log_message(f"프리뷰 업데이트 중 오류 발생: {str(e)}")

#프린터 제어 기능구현:
    def pause_print(self):
        """프린터 일시정지 메소드"""
        try:
            url = f"{self.moonraker_url_input.text()}/printer/print/pause"
            self.log_message(f"프린터 일시정지 요청: {url}")
            
            response = self.session.post(url)
            
            if response.status_code == 200:
                # 프린터 상태 업데이트
                self.printer_status = "paused"
                self.log_message("프린터가 일시정지되었습니다")
                
                # 상태바 업데이트
                self.statusBar().showMessage('프린터 상태: 일시정지됨')
                
                # 버튼 UI 업데이트
                self.pause_button.setEnabled(False)
                self.resume_button.setEnabled(True)
                
                # 모니터링 상태 유지
                self.monitoring_start_button.setEnabled(False)
                self.monitoring_stop_button.setEnabled(True)
                
            else:
                error_msg = f"프린터 일시정지 실패: HTTP {response.status_code}"
                self.log_message(error_msg, 'error')
                QMessageBox.warning(self, "일시정지 실패", error_msg)
                
        except requests.exceptions.ConnectionError:
            error_msg = "프린터 연결 실패: 네트워크 또는 서버 접속 오류"
            self.log_message(error_msg, 'error')
            QMessageBox.critical(self, "연결 오류", error_msg)
            
        except Exception as e:
            error_msg = f"프린터 일시정지 중 오류 발생: {str(e)}"
            self.log_message(error_msg, 'error')
            QMessageBox.critical(self, "오류", error_msg)
        
    def resume_print(self):
        """프린터 재개 메소드"""
        try:
            url = f"{self.moonraker_url_input.text()}/printer/print/resume"
            self.log_message(f"프린터 재개 요청: {url}")
            
            response = self.session.post(url)
            
            if response.status_code == 200:
                # 프린터 상태 업데이트
                self.printer_status = "printing"
                self.log_message("프린팅이 재개되었습니다")
                
                # 상태바 업데이트
                self.statusBar().showMessage('프린터 상태: 프린팅 중')
                
                # 버튼 UI 업데이트
                self.pause_button.setEnabled(True)
                self.resume_button.setEnabled(False)
                
                # 모니터링 상태 유지
                self.monitoring_start_button.setEnabled(False)
                self.monitoring_stop_button.setEnabled(True)
                
            else:
                error_msg = f"프린터 재개 실패: HTTP {response.status_code}"
                self.log_message(error_msg, 'error')
                QMessageBox.warning(self, "재개 실패", error_msg)
                
        except requests.exceptions.ConnectionError:
            error_msg = "프린터 연결 실패: 네트워크 또는 서버 접속 오류"
            self.log_message(error_msg, 'error')
            QMessageBox.critical(self, "연결 오류", error_msg)
            
        except Exception as e:
            error_msg = f"프린터 재개 중 오류 발생: {str(e)}"
            self.log_message(error_msg, 'error')
            QMessageBox.critical(self, "오류", error_msg)

    def toggle_pause_resume(self):
        """일시정지/재개 토글 메소드"""
        if self.printer_status == "printing":
            self.pause_print()
        elif self.printer_status == "paused":
            self.resume_print()

    def update_printer_status(self, status):
        """프린터 상태 업데이트 및 UI 반영"""
        try:
            self.printer_status = status
            
            # 상태에 따른 버튼 활성화/비활성화 및 상태 텍스트 설정
            if status == "idle":
                self.pause_button.setEnabled(False)
                self.resume_button.setEnabled(False)
                status_text = "대기 중"
                
            elif status == "printing":
                self.pause_button.setEnabled(True)
                self.resume_button.setEnabled(False)
                status_text = "프린팅 중"
                
            elif status == "paused":
                self.pause_button.setEnabled(False)
                self.resume_button.setEnabled(True)
                status_text = "일시정지됨"
                
            # 상태바 업데이트
            self.statusBar().showMessage(f'프린터 상태: {status_text}')
            
            # 상태 로그 추가
            self.log_message(f"프린터 상태가 '{status_text}'(으)로 변경되었습니다")
            
        except Exception as e:
            self.log_message(f"상태 업데이트 중 오류 발생: {str(e)}", 'error')

    def detect_defect(self, image):
        """
        이미지에서 결함을 감지하는 메서드
        Args:
            image (numpy.ndarray): OpenCV 이미지 배열
            
        Returns:
            tuple: (결함 목록, 바운딩 박스가 그려진 이미지)
        """
        try:
            # 이미지 전처리
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image_pil = Image.fromarray(image_rgb)
            
            # 이미지를 바이트 스트림으로 변환
            img_byte_arr = io.BytesIO()
            image_pil.save(img_byte_arr, format='JPEG', quality=95)
            img_byte_arr = img_byte_arr.getvalue()
            
            # Azure Custom Vision API 설정
            headers = {
                'Prediction-Key': self.prediction_key,
                'Content-Type': 'application/octet-stream'
            }
            
            # API 엔드포인트 URL
            url = f"https://eastus.api.cognitive.microsoft.com/customvision/v3.0/Prediction/{self.project_id}/detect/iterations/{self.iteration_name}/image"
            
            # API 요청
            try:
                response = requests.post(url, headers=headers, data=img_byte_arr)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                self.log_message(f"API 요청 실패: {str(e)}", 'error')
                return [], None
                
            if response.status_code != 200:
                self.log_message(f"Custom Vision API 오류 (상태 코드: {response.status_code})", 'error')
                return [], None

            # 응답 처리
            results = response.json()
            predictions = results.get('predictions', [])
            
            if not predictions:
                return [], None
            
            # 결함 정보 및 이미지 처리
            defects = []
            image_with_boxes = image.copy()
            
            # 신뢰도 70% 이상인 예측만 필터링
            high_confidence_predictions = [p for p in predictions if p['probability'] > 0.7]
            
            if high_confidence_predictions:
                # 가장 높은 신뢰도를 가진 결함 찾기
                highest_confidence = max(p['probability'] for p in high_confidence_predictions)
                highest_confidence_tag = next(p['tagName'] for p in high_confidence_predictions 
                                        if p['probability'] == highest_confidence)
                
                # 첫 결함 발견 시에만 로그 출력
                if not self.defect_logged:
                    self.log_message(
                        f"결함 감지됨: {highest_confidence_tag} ({highest_confidence*100:.1f}% 신뢰도)", 
                        'defect'
                    )
                
                # 각 결함에 대한 처리
                for prediction in high_confidence_predictions:
                    # 결함 정보 저장
                    defect_info = {
                        'tag': prediction['tagName'],
                        'probability': prediction['probability'],
                        'bbox': prediction['boundingBox']
                    }
                    defects.append(defect_info)
                    
                    # 바운딩 박스 좌표 계산
                    h, w = image.shape[:2]
                    box = prediction['boundingBox']
                    x = int(box['left'] * w)
                    y = int(box['top'] * h)
                    box_w = int(box['width'] * w)
                    box_h = int(box['height'] * h)
                    
                    # 박스 그리기 - 두꺼운 테두리와 반투명 오버레이
                    overlay = image_with_boxes.copy()
                    # 반투명 박스 그리기
                    cv2.rectangle(
                        overlay,
                        (x, y),
                        (x + box_w, y + box_h),
                        (0, 0, 255),
                        -1  # 채우기
                    )
                    # 반투명 효과 적용
                    cv2.addWeighted(overlay, 0.3, image_with_boxes, 0.7, 0, image_with_boxes)
                    # 실선 테두리 그리기
                    cv2.rectangle(
                        image_with_boxes,
                        (x, y),
                        (x + box_w, y + box_h),
                        (0, 0, 255),
                        3  # 더 두꺼운 선
                    )
                    
                    # 텍스트 정보
                    text = f"{prediction['tagName']}: {prediction['probability']*100:.1f}%"
                    
                    # 텍스트 크기 계산
                    font_scale = 0.8  # 더 큰 폰트 크기
                    thickness = 2
                    font = cv2.FONT_HERSHEY_DUPLEX  # 더 선명한 폰트
                    (text_w, text_h), baseline = cv2.getTextSize(
                        text,
                        font,
                        font_scale,
                        thickness
                    )
                    
                    # 텍스트 배경 패딩
                    padding = 5
                    text_x = x
                    text_y = max(y - 10, text_h + padding)  # 텍스트가 이미지 위로 넘어가지 않도록
                    
                    # 텍스트 배경 그리기 (더 넓은 영역)
                    cv2.rectangle(
                        image_with_boxes,
                        (text_x, text_y - text_h - 2*padding),
                        (text_x + text_w + 2*padding, text_y + padding),
                        (0, 0, 255),
                        -1
                    )
                    
                    # 텍스트 그리기
                    cv2.putText(
                        image_with_boxes,
                        text,
                        (text_x + padding, text_y - padding),
                        font,
                        font_scale,
                        (255, 255, 255),  # 흰색
                        thickness,
                        cv2.LINE_AA  # 부드러운 텍스트 렌더링
                    )
                    
                    # 신뢰도에 따른 추가 표시 (선택적)
                    if prediction['probability'] > 0.9:  # 90% 이상의 신뢰도
                        # 고신뢰도 표시 (예: 모서리에 작은 마커)
                        marker_size = 20
                        cv2.drawMarker(
                            image_with_boxes,
                            (x + box_w - marker_size, y + marker_size),
                            (0, 255, 0),  # 녹색
                            cv2.MARKER_STAR,
                            marker_size,
                            2
                        )
            
            return defects, image_with_boxes
                        
        except Exception as e:
            self.log_message(f"결함 감지 처리 중 오류 발생: {str(e)}", 'error')
            return [], None

    def crop_print_area(self, frame):
        """
        프린팅 영역을 동적으로 크롭하는 메서드
        
        Args:
            frame (numpy.ndarray): 원본 프레임
            
        Returns:
            numpy.ndarray: 크롭된 이미지
        """
        try:
            if frame is None:
                return None
                
            height, width = frame.shape[:2]
            center_x = width // 2
            center_y = height // 2
            
            # 현재 시간과 모니터링 시작 시간의 차이 계산
            if self.monitoring_start_time is None:
                self.monitoring_start_time = time.time()
                elapsed_minutes = 0
            else:
                elapsed_minutes = (time.time() - self.monitoring_start_time) / 60
            
            # 기본 크롭 비율 설정 (초기 비율만 증가)
            initial_width_ratio = 0.45    # 0.35에서 0.45로 증가
            fixed_top_ratio = 0.4        # 0.2에서 0.15로 감소하여 더 위쪽부터 시작
            initial_bottom_ratio = 0.35   # 0.3에서 0.35로 증가
            
            # 최대 크롭 비율 설정 (증가)
            max_width_ratio = 0.8         # 0.7에서 0.8로 증가
            max_bottom_ratio = 0.65       # 0.6에서 0.65로 증가
            
            # 시간에 따른 성장률 (유지)
            width_growth_per_minute = 0.05    # 기존 값 유지
            bottom_growth_per_minute = 0.05   # 기존 값 유지
            
            # 현재 크롭 비율 계산
            current_width_ratio = min(
                initial_width_ratio + (width_growth_per_minute * elapsed_minutes),
                max_width_ratio
            )
            
            current_bottom_ratio = min(
                initial_bottom_ratio + (bottom_growth_per_minute * elapsed_minutes),
                max_bottom_ratio
            )
            
            # 크롭 영역 계산
            crop_width = int(width * current_width_ratio)
            crop_top = int(height * fixed_top_ratio)
            crop_bottom = int(height * current_bottom_ratio)
            
            # 크롭 좌표 계산
            x = center_x - (crop_width // 2)
            y_top = center_y - (crop_top // 2)
            y_bottom = center_y + crop_bottom
            
            # 좌표가 이미지 범위를 벗어나지 않도록 조정
            x = max(0, min(x, width - crop_width))
            y_top = max(0, y_top)
            y_bottom = min(height, y_bottom)
            
            # 이미지 크롭
            cropped = frame[y_top:y_bottom, x:x+crop_width]
            
            # 디버그용 시각화 (원본 이미지에 크롭 영역 표시)
            if hasattr(self, 'debug_frame'):
                self.debug_frame = frame.copy()
                cv2.rectangle(
                    self.debug_frame,
                    (x, y_top),
                    (x+crop_width, y_bottom),
                    (0, 255, 0),  # BGR 색상 (녹색)
                    2  # 선 두께
                )
            
            return cropped
                
        except Exception as e:
            self.log_message(f"이미지 크롭 오류: {str(e)}", 'error')
            return frame  # 에러 발생 시 원본 프레임 반환

    def save_defect_image(self, image):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = f"defects/defect_{timestamp}.jpg"
        os.makedirs("defects", exist_ok=True)
        cv2.imwrite(save_path, image)
        self.log_message(f"결함 이미지 저장됨: {save_path}")


#기타 유틸리티 메소드:
    def display_image(self, image, add_text=None):
        """이미지 표시를 위한 헬퍼 메소드"""
        if image is None:
            return
            
        # 이미지 크기 조정
        target_height = 480
        ratio = target_height / image.shape[0]
        resized_image = cv2.resize(image, 
            (int(image.shape[1] * ratio), target_height))
        
        # 텍스트 추가
        if add_text:
            cv2.putText(resized_image, add_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        # 이미지 표시
        rgb_image = cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.video_label.setPixmap(scaled_pixmap)
        self.current_frame = QPixmap.fromImage(qt_image)

    def updateVideoFrame(self):
        if hasattr(self, 'current_frame'):
            scaled_pixmap = self.current_frame.scaled(
                self.video_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.video_label.setPixmap(scaled_pixmap)

    def log_message(self, message, level='info'):
        """
        중요도에 따라 로그 메시지를 필터링하여 출력
        level: 'info', 'warning', 'error', 'defect'
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 로그 레벨에 따른 prefix 설정
        prefix = {
            'info': '→',
            'warning': '⚠',
            'error': '❌',
            'defect': '🔍'
        }.get(level, '→')
        
        formatted_message = f"[{timestamp}] {prefix} {message}"
        self.status_text.append(formatted_message)
        
        # 로그 최대 줄 수 제한
        if self.status_text.document().lineCount() > 50:
            cursor = self.status_text.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor, 10)
            cursor.removeSelectedText()

    def apply_webcam_url(self):
        """웹캠 URL 적용 (동의 절차 추가)"""
        if self.show_consent_dialog():
            self.webcam_url = self.webcam_url_input.text()
            self.log_message(f"웹캠 URL이 적용되었습니다: {self.webcam_url}")
            self.webcam_apply_btn.setStyleSheet("background-color: #4CAF50; color: white;")
            QTimer.singleShot(1000, lambda: self.webcam_apply_btn.setStyleSheet(""))
        else:
            self.log_message("웹캠 URL 적용이 취소되었습니다.")

    def apply_moonraker_url(self):
        """Moonraker URL 적용 (동의 절차 추가)"""
        if self.show_consent_dialog():
            self.moonraker_base_url = self.moonraker_url_input.text()
            self.log_message(f"Moonraker URL이 적용되었습니다: {self.moonraker_base_url}")
            self.moonraker_apply_btn.setStyleSheet("background-color: #4CAF50; color: white;")
            QTimer.singleShot(1000, lambda: self.moonraker_apply_btn.setStyleSheet(""))
        else:
            self.log_message("Moonraker URL 적용이 취소되었습니다.")

    def show_consent_dialog(self):
        """개인정보 수집 동의 다이얼로그 표시"""
        dialog = QDialog(self)
        dialog.setWindowTitle("개인정보 수집 동의")
        dialog.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        
        # 설명 텍스트
        info_text = QLabel(
            "본 서비스는 3D 프린터 모니터링을 위해\n다음과 같은 정보를 수집합니다:\n\n"
            "• 프린터 연결 URL\n"
            "• 웹캠 영상 데이터\n"
            "• 프린팅 상태 정보"
        )
        info_text.setWordWrap(True)
        layout.addWidget(info_text)
        
        # 체크박스
        consent_checkbox = QCheckBox("개인정보 수집 및 이용에 동의합니다")
        layout.addWidget(consent_checkbox)
        
        # 버튼 영역
        button_layout = QHBoxLayout()
        cancel_button = QPushButton("취소")
        confirm_button = QPushButton("확인")
        confirm_button.setEnabled(False)
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(confirm_button)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        # 이벤트 핸들러
        def on_checkbox_changed(state):
            confirm_button.setEnabled(state == Qt.Checked)
        
        consent_checkbox.stateChanged.connect(on_checkbox_changed)
        cancel_button.clicked.connect(dialog.reject)
        confirm_button.clicked.connect(dialog.accept)
        
        return dialog.exec_() == QDialog.Accepted

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'video_label'):
            self.updateVideoFrame()



if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = PrintMonitorApp()
    ex.show()
    sys.exit(app.exec_())