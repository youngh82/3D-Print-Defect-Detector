from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QGroupBox, QGridLayout, QLineEdit, QPushButton, QLabel, QTextEdit, QSizePolicy, QDesktopWidget, QStyle, QFrame, QDialog, QScrollArea, QCheckBox, QHBoxLayout
from PyQt5.QtCore import Qt, QDateTime, QTimer, QSize
from PyQt5.QtGui import QFont
from styles import Styles, Colors
import sys
import re

class PrintMonitorUI(QMainWindow):
    def __init__(self):
        super().__init__()
        # 기본 윈도우 설정
        self.setMinimumSize(1200, 800)
        self.setWindowTitle("3D 프린터 모니터링 시스템")
        
        # 폰트 설정 - Mac OS 호환성 개선
        font = QFont()
        # Mac OS에서 사용 가능한 기본 폰트 설정
        if sys.platform == 'darwin':  # Mac OS
            font.setFamily("AppleGothic")  # 한글 지원 Mac 기본 폰트
        else:  # Windows 및 기타 OS
            font.setFamily("맑은 고딕")
            # 대체 폰트 설정 (Qt 버전이 지원하는 경우에만)
            try:
                font.setFallbackFamilies(["Malgun Gothic", "MS Gothic", "Arial"])
            except AttributeError:
                pass  # 지원하지 않는 경우 무시
        
        font.setPointSize(9)
        QApplication.setFont(font)
        
        # 멤버 변수 초기화
        self.monitoring_active = False
        self.is_paused = False
        self.success_timer = None
        self.webcam_stream = None
        self.moonraker_connection = None
        
        # 스타일 적용
        self.setStyleSheet(Styles.get_main_window_style())
        
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # UI 구성요소 초기화
        self.init_settings_group(main_layout)
        self.init_video_container(main_layout)
        self.init_bottom_container(main_layout)
        
        # 상태바 초기화
        self.status_bar = self.statusBar()
        self.status_bar.showMessage(u'시스템 준비 완료')
        
        # 윈도우 위치 조정
        self.centerWindow()
        
        # 초기 동의 다이얼로그 표시
        if not self.show_consent_dialog():
            sys.exit()

    def init_settings_group(self, main_layout):
        """설정 그룹 초기화"""
        settings_group = QGroupBox("모니터링 설정")
        settings_layout = QGridLayout()
        settings_group.setLayout(settings_layout)
        
        settings_layout.setColumnStretch(1, 1)
        settings_layout.setSpacing(15)
        
        # URL 입력 필드
        self.webcam_url_input = QLineEdit()
        self.webcam_url_input.setPlaceholderText("http://your-webcam-url:port")
        self.webcam_url_input.setStyleSheet(Styles.get_url_input_style())
        self.webcam_url_input.textChanged.connect(self.validate_url)
        
        self.moonraker_url_input = QLineEdit()
        self.moonraker_url_input.setPlaceholderText("http://your-moonraker-url:port")
        self.moonraker_url_input.setStyleSheet(Styles.get_url_input_style())
        self.moonraker_url_input.textChanged.connect(self.validate_url)
        
        # 버튼 초기화
        self.webcam_apply_btn = self.create_styled_button("웹캠 URL 적용", Colors.SUCCESS)
        self.moonraker_apply_btn = self.create_styled_button("Moonraker URL 적용", Colors.SUCCESS)
        
        self.webcam_apply_btn.clicked.connect(self.apply_webcam_url)
        self.moonraker_apply_btn.clicked.connect(self.apply_moonraker_url)
        
        # 초기 버튼 상태 설정
        self.webcam_apply_btn.setEnabled(False)
        self.moonraker_apply_btn.setEnabled(False)
        
        # 레이블 설정
        label_style = f"QLabel {{ color: {Colors.TEXT}; font-weight: bold; }}"
        webcam_label = QLabel("웹캠 URL:")
        moonraker_label = QLabel("Moonraker URL:")
        webcam_label.setStyleSheet(label_style)
        moonraker_label.setStyleSheet(label_style)
        
        # 레이아웃 배치
        settings_layout.addWidget(webcam_label, 0, 0)
        settings_layout.addWidget(self.webcam_url_input, 0, 1)
        settings_layout.addWidget(self.webcam_apply_btn, 0, 2)
        settings_layout.addWidget(moonraker_label, 1, 0)
        settings_layout.addWidget(self.moonraker_url_input, 1, 1)
        settings_layout.addWidget(self.moonraker_apply_btn, 1, 2)
        
        main_layout.addWidget(settings_group)

    def init_video_container(self, main_layout):
            """비디오 표시 영역 초기화"""
            video_container = QGroupBox("실시간 모니터링")
            video_layout = QHBoxLayout()
            video_container.setLayout(video_layout)
            
            # 여백 및 간격 조정
            video_layout.setContentsMargins(15, 25, 15, 15)  # 상단 여백 증가
            video_layout.setSpacing(20)
            
            # 왼쪽: 실시간 웹캠
            left_group = QGroupBox("실시간 웹캠")
            left_layout = QVBoxLayout()
            left_group.setLayout(left_layout)
            
            # 레이아웃 여백 조정
            left_layout.setContentsMargins(10, 25, 10, 10)  # 상단 여백 증가
            left_layout.setSpacing(10)
            
            self.webcam_label = QLabel()
            self.webcam_label.setStyleSheet("""
                QLabel {
                    background-color: #f8f9fa;
                    border: 2px solid #e0e0e0;
                    border-radius: 8px;
                    padding: 10px;
                    min-height: 400px;
                }
            """)
            self.webcam_label.setMinimumSize(480, 400)
            self.webcam_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.webcam_label.setAlignment(Qt.AlignCenter)
            self.webcam_label.setText("카메라 연결 대기 중...")
            
            left_layout.addWidget(self.webcam_label)
            
            # 오른쪽: Custom Vision 검사 영역
            right_group = QGroupBox("Custom Vision 검사 영역")
            right_layout = QVBoxLayout()
            right_group.setLayout(right_layout)
            
            # 레이아웃 여백 조정
            right_layout.setContentsMargins(10, 25, 10, 10)  # 상단 여백 증가
            right_layout.setSpacing(10)
            
            self.vision_label = QLabel()
            self.vision_label.setStyleSheet("""
                QLabel {
                    background-color: #f8f9fa;
                    border: 2px solid #e0e0e0;
                    border-radius: 8px;
                    padding: 10px;
                    min-height: 400px;
                }
            """)
            self.vision_label.setMinimumSize(480, 400)
            self.vision_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.vision_label.setAlignment(Qt.AlignCenter)
            self.vision_label.setText("Vision 분석 대기 중...")
            
            right_layout.addWidget(self.vision_label)
            
            # 레이아웃에 그룹 추가
            video_layout.addWidget(left_group)
            video_layout.addWidget(right_group)
            
            # 비디오 컨테이너 크기 정책 설정
            video_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            left_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            right_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            
            # 메인 레이아웃에 비디오 컨테이너 추가
            main_layout.addWidget(video_container)

    def init_bottom_container(self, main_layout):
        """하단 영역 초기화 (로그 + 버튼)"""
        bottom_container = QGroupBox("상태 및 제어")
        bottom_layout = QVBoxLayout()
        bottom_container.setLayout(bottom_layout)
        bottom_layout.setSpacing(15)
        
        # 로그 영역
        log_container = QWidget()
        log_layout = QVBoxLayout()
        log_container.setLayout(log_layout)
        
        log_label = QLabel("시스템 로그")
        log_label.setStyleSheet(Styles.get_log_label_style())
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMinimumHeight(150)
        self.status_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.status_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.status_text.setStyleSheet(Styles.get_log_text_style())
        
        log_layout.addWidget(log_label)
        log_layout.addWidget(self.status_text)
        
        bottom_layout.addWidget(log_container)
        
        # 버튼 컨테이너
        button_container = QWidget()
        button_layout = QHBoxLayout()
        button_container.setLayout(button_layout)
        button_layout.setSpacing(15)
        
        # 버튼 생성
        self.monitoring_start_button = self.create_styled_button("모니터링 시작", Colors.PRIMARY)
        self.monitoring_stop_button = self.create_styled_button("모니터링 중지", Colors.DANGER)
        self.pause_button = self.create_styled_button("일시정지", Colors.WARNING)
        self.resume_button = self.create_styled_button("재개", Colors.SUCCESS)
        
        # 버튼 아이콘 추가
        self.add_button_icon(self.monitoring_start_button, QStyle.SP_MediaPlay)
        self.add_button_icon(self.monitoring_stop_button, QStyle.SP_MediaStop)
        self.add_button_icon(self.pause_button, QStyle.SP_MediaPause)
        self.add_button_icon(self.resume_button, QStyle.SP_MediaPlay)
        
        # 버튼 이벤트 연결
        self.monitoring_start_button.clicked.connect(self.start_monitoring)
        self.monitoring_stop_button.clicked.connect(self.stop_monitoring)
        self.pause_button.clicked.connect(self.pause_monitoring)
        self.resume_button.clicked.connect(self.resume_monitoring)
        
        # 초기 버튼 상태 설정
        self.monitoring_stop_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        
        # 버튼 레이아웃 구성
        button_layout.addStretch()
        for button in [self.monitoring_start_button, self.monitoring_stop_button, 
                      self.pause_button, self.resume_button]:
            button_layout.addWidget(button)
        button_layout.addStretch()
        
        button_container.setFixedHeight(60)
        bottom_layout.addWidget(button_container)
        
        bottom_container.setMinimumHeight(250)
        main_layout.addWidget(bottom_container)

    def create_styled_button(self, text, base_color):
        """스타일이 적용된 버튼 생성"""
        button = QPushButton(text)
        button.setStyleSheet(Styles.get_button_style(base_color))
        return button

    def add_button_icon(self, button, icon_type):
        """버튼에 아이콘 추가"""
        icon = self.style().standardIcon(icon_type)
        button.setIcon(icon)
        button.setIconSize(QSize(20, 20))

    def centerWindow(self):
        """윈도우를 화면 중앙에 배치"""
        screen = QDesktopWidget().screenGeometry()
        window_size = self.geometry()
        x = (screen.width() - window_size.width()) // 2
        y = (screen.height() - window_size.height()) // 2
        self.move(x, y)

    def validate_url(self):
        """URL 유효성 검사"""
        sender = self.sender()
        url = sender.text().strip()
        
        # URL 유효성 검사를 위한 정규식 패턴
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ip address
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        is_valid = bool(url_pattern.match(url))
        
        if sender == self.webcam_url_input:
            self.webcam_apply_btn.setEnabled(is_valid)
        else:
            self.moonraker_apply_btn.setEnabled(is_valid)
        
        return is_valid

    def apply_webcam_url(self):
        """웹캠 URL 적용"""
        url = self.webcam_url_input.text().strip()
        if self.validate_url():
            self.log_message(f"웹캠 URL이 설정되었습니다: {url}")
            self.show_success_message("웹캠 URL이 성공적으로 설정되었습니다.")
        else:
            self.log_message("잘못된 웹캠 URL 형식입니다.", error=True)

    def apply_moonraker_url(self):
        """Moonraker URL 적용"""
        url = self.moonraker_url_input.text().strip()
        if self.validate_url():
            self.log_message(f"Moonraker URL이 설정되었습니다: {url}")
            self.show_success_message("Moonraker URL이 성공적으로 설정되었습니다.")
        else:
            self.log_message("잘못된 Moonraker URL 형식입니다.", error=True)

    def start_monitoring(self):
        """모니터링 시작"""
        if not self.validate_settings():
            return
        
        self.monitoring_active = True
        self.monitoring_start_button.setEnabled(False)
        self.monitoring_stop_button.setEnabled(True)
        self.pause_button.setEnabled(True)
        self.log_message("모니터링이 시작되었습니다.")
        self.show_success_message("모니터링이 시작되었습니다.")

    def stop_monitoring(self):
        """모니터링 중지"""
        self.monitoring_active = False
        self.is_paused = False
        self.monitoring_start_button.setEnabled(True)
        self.monitoring_stop_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.log_message("모니터링이 중지되었습니다.")
        self.show_success_message("모니터링이 중지되었습니다.")

    def pause_monitoring(self):
            """모니터링 일시정지"""
            self.is_paused = True
            self.pause_button.setEnabled(False)
            self.resume_button.setEnabled(True)
            self.log_message("모니터링이 일시정지되었습니다.")
            self.show_success_message("모니터링이 일시정지되었습니다.")

    def resume_monitoring(self):
        """모니터링 재개"""
        self.is_paused = False
        self.pause_button.setEnabled(True)
        self.resume_button.setEnabled(False)
        self.log_message("모니터링이 재개되었습니다.")
        self.show_success_message("모니터링이 재개되었습니다.")

    def validate_settings(self):
        """설정 유효성 검사"""
        if not self.webcam_url_input.text().strip():
            self.log_message("웹캠 URL이 설정되지 않았습니다.", error=True)
            return False
        
        if not self.moonraker_url_input.text().strip():
            self.log_message("Moonraker URL이 설정되지 않았습니다.", error=True)
            return False
            
        return True

    def log_message(self, message, error=False):
        """로그 메시지 추가"""
        timestamp = QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm:ss')
        log_level = "ERROR" if error else "INFO"
        formatted_message = f"[{timestamp}] [{log_level}] {message}"
        
        # 텍스트 색상 설정
        color = "#e74c3c" if error else "#2c3e50"
        self.status_text.append(f'<span style="color: {color}">{formatted_message}</span>')
        
        # 스크롤을 항상 최하단으로 이동
        scrollbar = self.status_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def show_success_message(self, message):
        """성공 메시지 표시"""
        if self.success_timer is not None:
            self.success_timer.stop()
            self.success_timer = None
        
        success_banner = QFrame(self)
        success_banner.setStyleSheet(Styles.get_success_banner_style())
        
        layout = QHBoxLayout()
        success_banner.setLayout(layout)
        layout.setContentsMargins(15, 10, 15, 10)
        
        label = QLabel(message)
        layout.addWidget(label)
        
        success_banner.setFixedHeight(50)
        success_banner.setGeometry(
            (self.width() - 300) // 2,
            10,
            300,
            50
        )
        success_banner.show()
        
        self.success_timer = QTimer()
        self.success_timer.timeout.connect(lambda: self.cleanup_success_banner(success_banner))
        self.success_timer.start(3000)

    def cleanup_success_banner(self, banner):
        """성공 메시지 배너 정리"""
        banner.deleteLater()
        if self.success_timer is not None:
            self.success_timer.stop()
            self.success_timer = None

    def show_consent_dialog(self):
            """개인정보 수집 동의 다이얼로그 표시"""
            dialog = QDialog(self)
            dialog.setWindowTitle("개인정보 수집 동의")
            dialog.setFixedSize(450, 400)  # 높이 증가
            dialog.setStyleSheet(Styles.get_main_window_style())
            
            layout = QVBoxLayout()
            layout.setSpacing(15)
            layout.setContentsMargins(20, 20, 20, 20)
            
            # 제목
            title_label = QLabel("개인정보 수집 안내")
            title_label.setStyleSheet("""
                QLabel#title {
                    font-size: 16px;
                    font-weight: bold;
                    color: #2c3e50;
                    margin-bottom: 10px;
                }
            """)
            title_label.setObjectName("title")
            layout.addWidget(title_label)
            
            # 스크롤 영역 생성
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setStyleSheet("""
                QScrollArea {
                    border: none;
                    background-color: transparent;
                }
                QScrollBar:vertical {
                    border: none;
                    background: #f0f0f0;
                    width: 10px;
                    margin: 0;
                }
                QScrollBar::handle:vertical {
                    background-color: #c0c0c0;
                    min-height: 30px;
                    border-radius: 5px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #a0a0a0;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    border: none;
                    background: none;
                }
            """)
            
            # 내용을 담을 위젯
            content_widget = QWidget()
            content_layout = QVBoxLayout()
            
            # 설명 프레임
            info_frame = QFrame()
            info_frame.setStyleSheet("""
                QFrame {
                    background-color: #f8f9fa;
                    border-radius: 8px;
                    padding: 15px;
                }
            """)
            info_layout = QVBoxLayout()
            
            description = QLabel(
                "본 서비스는 3D 프린터 모니터링을 위해\n"
                "다음과 같은 정보를 수집 및 이용합니다:\n\n"
                "1. 수집하는 개인정보 항목\n"
                "• 프린터 연결 정보 (IP 주소, 포트)\n"
                "• 웹캠 스트리밍 데이터\n"
                "• 프린팅 상태 정보\n"
                "• 결함 감지 이미지\n\n"
                "2. 개인정보의 수집 및 이용 목적\n"
                "• 3D 프린터 실시간 모니터링 서비스 제공\n"
                "• 프린팅 품질 관리 및 결함 감지\n"
                "• 서비스 개선 및 통계 분석\n\n"
                "3. 개인정보의 보유 및 이용 기간\n"
                "• 서비스 이용 기간 동안 보관\n"
                "• 서비스 종료 시 즉시 파기\n\n"
                "4. 동의를 거부할 권리 및 동의 거부에 따른 불이익\n"
                "• 개인정보 수집 동의를 거부할 권리가 있음\n"
                "• 동의 거부 시 서비스 이용이 제한될 수 있음\n\n"
                "5. 개인정보의 파기 절차 및 방법\n"
                "• 수집된 정보는 서비스 종료 시 자동으로 파기\n"
                "• 별도의 데이터베이스에 옮겨져 내부 방침에 따라 안전하게 처리\n"
            )
            description.setStyleSheet("""
                QLabel#description {
                    color: #34495e;
                    line-height: 1.6;
                }
            """)
            description.setObjectName("description")
            description.setWordWrap(True)
            info_layout.addWidget(description)
            info_frame.setLayout(info_layout)
            
            content_layout.addWidget(info_frame)
            content_layout.addStretch()
            content_widget.setLayout(content_layout)
            
            # 스크롤 영역에 컨텐츠 위젯 설정
            scroll.setWidget(content_widget)
            layout.addWidget(scroll)
            
            # 체크박스
            checkbox_frame = QFrame()
            checkbox_layout = QVBoxLayout()
            checkbox_layout.setSpacing(10)
            
            consent_checkbox = QCheckBox("개인정보 수집 및 이용에 동의합니다")
            consent_checkbox.setStyleSheet("""
                QCheckBox {
                    color: #2c3e50;
                    font-size: 13px;
                }
            """)
            
            security_checkbox = QCheckBox("보안 정책을 이해하고 동의합니다")
            security_checkbox.setStyleSheet("""
                QCheckBox {
                    color: #2c3e50;
                    font-size: 13px;
                }
            """)
            
            checkbox_layout.addWidget(consent_checkbox)
            checkbox_layout.addWidget(security_checkbox)
            checkbox_frame.setLayout(checkbox_layout)
            layout.addWidget(checkbox_frame)
            
            # 버튼
            button_frame = QFrame()
            button_layout = QHBoxLayout()
            button_layout.setSpacing(10)
            
            cancel_button = QPushButton("취소")
            cancel_button.setStyleSheet(Styles.get_button_style(Colors.GRAY))
            cancel_button.setFixedWidth(100)
            
            confirm_button = QPushButton("확인")
            confirm_button.setStyleSheet(Styles.get_button_style(Colors.PRIMARY))
            confirm_button.setEnabled(False)
            confirm_button.setFixedWidth(100)
            
            button_layout.addStretch()
            button_layout.addWidget(cancel_button)
            button_layout.addWidget(confirm_button)
            button_frame.setLayout(button_layout)
            layout.addWidget(button_frame)
            
            # 레이아웃 설정
            dialog.setLayout(layout)
            
            # 이벤트 핸들러
            def update_confirm_button():
                confirm_button.setEnabled(
                    consent_checkbox.isChecked() and 
                    security_checkbox.isChecked()
                )
            
            consent_checkbox.stateChanged.connect(update_confirm_button)
            security_checkbox.stateChanged.connect(update_confirm_button)
            cancel_button.clicked.connect(dialog.reject)
            confirm_button.clicked.connect(dialog.accept)
            
            # 다이얼로그 실행
            result = dialog.exec_()
            
            if result == QDialog.Accepted:
                self.show_success_message("설정이 성공적으로 적용되었습니다.")
            
            return result == QDialog.Accepted

    def closeEvent(self, event):
        """앱 종료 시 정리"""
        # 모니터링 중지
        if self.monitoring_active:
            self.stop_monitoring()
        
        # 타이머 정리
        if self.success_timer is not None:
            self.success_timer.stop()
            self.success_timer = None
        
        # 웹캠 스트림 정리
        if self.webcam_stream is not None:
            self.webcam_stream = None
        
        # Moonraker 연결 정리
        if self.moonraker_connection is not None:
            self.moonraker_connection = None
        
        # 로그에 종료 메시지 추가
        self.log_message("프로그램이 종료됩니다.")
        
        # 기본 종료 이벤트 처리
        super().closeEvent(event)

def main():
    # DPI 설정
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    window = PrintMonitorUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()