"""메인 윈도우 모듈"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QMessageBox,
    QDesktopWidget, QShortcut
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QKeySequence

from ..core.factories.detector_factory import DefectDetectorFactory, VisionConfig
from ..core.factories.monitor_factory import PrinterMonitorFactory, MonitorConfig
from ..core.image_processor import ImageProcessor
from ..ui.video_widget import VideoDisplayWidget
from ..ui.control_panel import ControlPanel
from ..constants.settings import (
    VISION_CONFIG,
    NETWORK_CONFIG,
    DEFAULT_URLS,
    EventType,
    PrinterStatus,
    ERROR_MESSAGES
)


class MainWindow(QMainWindow):
    """메인 윈도우 클래스"""

    def __init__(self):
        super().__init__()
        # 속성 초기화
        self.printer_monitor = None
        self.defect_detector = None
        self.image_processor = None
        self.video_widget = None
        self.control_panel = None
        self.detection_timer = None
        self.preview_timer = None

        # 모니터링 상태
        self.monitoring = False
        self.defect_detected = False
        self.defect_logged = False
        self.monitoring_start_time = None

        # UI 및 컴포넌트 초기화
        try:
            self.init_ui()
            self.init_core_components()
            self.setup_timers()
            self.setup_connections()
            self.setup_event_handlers()
            self.setup_shortcuts()
        except Exception as e:
            self.show_error_message("초기화 실패", str(e))

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("3D Printer Monitoring System - Nopaghetti")
        self.setMinimumSize(1024, 768)

        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 컨트롤 패널 (설정 + 버튼 + 로그)
        self.control_panel = ControlPanel()

        # 비디오 디스플레이 (웹캠 + Vision)
        self.video_widget = VideoDisplayWidget()

        # 레이아웃 배치: 설정 → 비디오 → 상태/제어
        # control_panel의 설정 그룹을 상단에 배치
        main_layout.addWidget(self.control_panel.create_settings_group())
        main_layout.addWidget(self.video_widget, stretch=1)
        main_layout.addWidget(self.control_panel.create_status_control_group())

        # 상태바
        self.statusBar().showMessage('준비됨')

        # 창 가운데 배치
        self.center_window()

    def center_window(self):
        """창을 화면 가운데로"""
        screen = QDesktopWidget().screenGeometry()
        window = self.geometry()
        x = (screen.width() - window.width()) // 2
        y = (screen.height() - window.height()) // 2
        self.move(x, y)

    def init_core_components(self):
        """코어 컴포넌트 초기화"""
        try:
            detector_factory = DefectDetectorFactory()
            monitor_factory = PrinterMonitorFactory()

            # 환경 변수 기반 초기화 시도
            try:
                self.printer_monitor = monitor_factory.create_from_env()
                self.defect_detector = detector_factory.create_from_env()
            except Exception:
                # 실패 시 기본 설정으로 초기화
                monitor_config = MonitorConfig(
                    base_url=NETWORK_CONFIG['BASE_URL'],
                    timeout=NETWORK_CONFIG['REQUEST_TIMEOUT'],
                    max_retries=NETWORK_CONFIG['MAX_RETRIES']
                )
                self.printer_monitor = monitor_factory.create_monitor(monitor_config)

                vision_config = VisionConfig(
                    prediction_key=VISION_CONFIG['PREDICTION_KEY'],
                    project_id=VISION_CONFIG['PROJECT_ID'],
                    iteration_name=VISION_CONFIG['ITERATION_NAME'],
                    api_endpoint=VISION_CONFIG['API_ENDPOINT']
                )
                self.defect_detector = detector_factory.create_detector(vision_config)

            self.image_processor = ImageProcessor()

        except Exception as e:
            self.control_panel.log_message(f"컴포넌트 초기화 실패: {str(e)}", 'error')

    def setup_timers(self):
        """타이머 설정"""
        self.detection_timer = QTimer()
        self.detection_timer.timeout.connect(self.process_frame)

        self.preview_timer = QTimer()
        self.preview_timer.timeout.connect(self.update_preview)

    def setup_connections(self):
        """시그널/슬롯 연결"""
        self.control_panel.monitoring_start_button.clicked.connect(self.start_monitoring)
        self.control_panel.monitoring_stop_button.clicked.connect(self.stop_monitoring)
        self.control_panel.pause_button.clicked.connect(self.pause_print)
        self.control_panel.resume_button.clicked.connect(self.resume_print)

        self.control_panel.webcam_apply_btn.clicked.connect(self.apply_webcam_url)
        self.control_panel.moonraker_apply_btn.clicked.connect(self.apply_moonraker_url)

    def setup_event_handlers(self):
        """이벤트 핸들러 설정"""
        if not all([self.printer_monitor, self.defect_detector, self.image_processor]):
            return

        self.printer_monitor.on(EventType.STATUS_CHANGED, self.handle_status_change)
        self.printer_monitor.on(EventType.ERROR_OCCURRED, self.handle_event_error)
        self.defect_detector.on(EventType.DEFECT_DETECTED, self.handle_defect_event)
        self.defect_detector.on(EventType.ERROR_OCCURRED, self.handle_event_error)
        self.image_processor.on(EventType.ERROR_OCCURRED, self.handle_event_error)

    def setup_shortcuts(self):
        """키보드 단축키 설정"""
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.start_monitoring)
        QShortcut(QKeySequence("Ctrl+X"), self).activated.connect(self.stop_monitoring)
        QShortcut(QKeySequence("Space"), self).activated.connect(self.toggle_pause_resume)

    # ──────────────────── 모니터링 제어 ────────────────────

    def start_monitoring(self):
        """모니터링 시작"""
        try:
            self.monitoring = True
            self.defect_detected = False
            self.defect_logged = False

            # 이미지 프로세서 모니터링 시작
            self.image_processor.start_monitoring()
            self.monitoring_start_time = self.image_processor.monitoring_start_time

            # 타이머 시작 (1초 간격)
            self.detection_timer.start(1000)
            self.preview_timer.start(1000)

            self.control_panel.update_monitoring_status(True)
            self.control_panel.log_message("모니터링을 시작했습니다.")
            self.statusBar().showMessage('모니터링 중...')

        except Exception as e:
            self.control_panel.log_message(f"시작 오류: {str(e)}", 'error')
            QMessageBox.critical(self, "오류", f"모니터링 시작 실패: {str(e)}")

    def stop_monitoring(self):
        """모니터링 중지"""
        try:
            self.monitoring = False
            self.defect_detected = False
            self.defect_logged = False
            self.monitoring_start_time = None

            self.detection_timer.stop()
            self.preview_timer.stop()

            self.image_processor.stop_monitoring()
            self.video_widget.clear_displays()

            self.control_panel.update_monitoring_status(False)
            self.control_panel.log_message("모니터링을 중지했습니다.")
            self.statusBar().showMessage('준비됨')

        except Exception as e:
            self.control_panel.log_message(f"중지 오류: {str(e)}", 'error')

    # ──────────────────── 프레임 처리 ────────────────────

    def process_frame(self):
        """결함 검사를 위한 프레임 처리"""
        if not self.monitoring:
            return

        try:
            webcam_url = self.control_panel.webcam_url_input.text()
            frame = self.image_processor.capture_frame(webcam_url)
            if frame is None:
                return

            # 프레임 처리 (크롭)
            processed = self.image_processor.process_frame(frame)
            cropped_frame = processed['cropped']

            if cropped_frame is None:
                return

            # 결함 감지
            defects, image_with_boxes = self.defect_detector.detect_defect(cropped_frame)

            if defects and not self.defect_logged:
                self.defect_detected = True
                self.defect_logged = True

                # 결함 정보 로그
                top_defect = max(defects, key=lambda d: d['probability'])
                self.control_panel.log_message(
                    f"결함 감지됨: {top_defect['tag']} "
                    f"({top_defect['probability']*100:.1f}% 신뢰도)",
                    'defect'
                )

                # 결함 이미지 저장
                if image_with_boxes is not None:
                    save_path = self.defect_detector.save_defect_image(image_with_boxes)
                    self.control_panel.log_message(f"결함 이미지 저장됨: {save_path}")

                # 프린터 일시정지
                self.pause_print()
                self.control_panel.log_message(
                    "결함이 감지되어 프린터를 일시정지합니다", 'warning'
                )

            # Vision 디스플레이 업데이트
            display_image = image_with_boxes if image_with_boxes is not None else cropped_frame
            self.video_widget.update_vision_display(display_image)

        except Exception as e:
            self.control_panel.log_message(f"결함 검사 오류: {str(e)}", 'error')

    def update_preview(self):
        """프리뷰 화면 업데이트"""
        if not self.monitoring:
            return

        try:
            webcam_url = self.control_panel.webcam_url_input.text()
            frame = self.image_processor.capture_frame(webcam_url)
            if frame is not None:
                self.video_widget.update_webcam_display(frame)

        except Exception as e:
            self.control_panel.log_message(f"프리뷰 업데이트 오류: {str(e)}", 'error')

    # ──────────────────── 프린터 제어 ────────────────────

    def pause_print(self):
        """프린트 일시정지"""
        try:
            if self.printer_monitor:
                try:
                    self.printer_monitor.pause_print()
                except Exception as e:
                    self.control_panel.log_message(
                        f"프린터 API 일시정지 요청 실패: {str(e)}", 'warning'
                    )
            self.control_panel.update_printer_status(PrinterStatus.PAUSED)
            self.control_panel.log_message("프린터가 일시정지되었습니다")
            self.statusBar().showMessage('프린터 상태: 일시정지됨')
        except Exception as e:
            self.control_panel.log_message(f"일시정지 실패: {str(e)}", 'error')

    def resume_print(self):
        """프린트 재개"""
        try:
            if self.printer_monitor:
                try:
                    self.printer_monitor.resume_print()
                except Exception as e:
                    self.control_panel.log_message(
                        f"프린터 API 재개 요청 실패: {str(e)}", 'warning'
                    )
            # 결함 상태 초기화하여 재모니터링 가능
            self.defect_detected = False
            self.defect_logged = False
            self.control_panel.update_printer_status(PrinterStatus.PRINTING)
            self.control_panel.log_message("프린팅이 재개되었습니다")
            self.statusBar().showMessage('프린터 상태: 프린팅 중')
        except Exception as e:
            self.control_panel.log_message(f"재개 실패: {str(e)}", 'error')

    def toggle_pause_resume(self):
        """일시정지/재개 토글"""
        if self.control_panel.pause_button.isEnabled():
            self.pause_print()
        elif self.control_panel.resume_button.isEnabled():
            self.resume_print()

    # ──────────────────── URL 적용 ────────────────────

    def apply_webcam_url(self):
        """웹캠 URL 적용"""
        if self.control_panel.show_consent_dialog():
            new_url = self.control_panel.webcam_url_input.text()
            self.control_panel.log_message(f"웹캠 URL이 적용되었습니다: {new_url}")
        else:
            self.control_panel.log_message("웹캠 URL 적용이 취소되었습니다.")

    def apply_moonraker_url(self):
        """Moonraker URL 적용"""
        if self.control_panel.show_consent_dialog():
            new_url = self.control_panel.moonraker_url_input.text()
            self.control_panel.log_message(f"Moonraker URL이 적용되었습니다: {new_url}")
        else:
            self.control_panel.log_message("Moonraker URL 적용이 취소되었습니다.")

    # ──────────────────── 이벤트 핸들러 ────────────────────

    def handle_status_change(self, event_data: dict):
        """프린터 상태 변경 이벤트 처리"""
        try:
            data = event_data.get('data', {})
            new_status = data.get('new_status', PrinterStatus.IDLE)
            self.control_panel.update_printer_status(new_status)
            self.control_panel.log_message(f"프린터 상태 변경: {new_status}")
        except Exception as e:
            self.control_panel.log_message(f"상태 변경 처리 실패: {str(e)}", 'error')

    def handle_defect_event(self, event_data: dict):
        """결함 감지 이벤트 처리"""
        try:
            data = event_data.get('data', {})
            defects = data.get('defects', [])
            if defects:
                self.control_panel.log_message(
                    f"이벤트: {len(defects)}개 결함 감지됨", 'defect'
                )
        except Exception as e:
            self.control_panel.log_message(f"결함 이벤트 처리 실패: {str(e)}", 'error')

    def handle_event_error(self, event_data: dict):
        """에러 이벤트 처리"""
        try:
            data = event_data.get('data', {})
            error = data.get('error', {})
            message = error.get('message', str(error)) if isinstance(error, dict) else str(error)
            self.control_panel.log_message(f"오류: {message}", 'error')
        except Exception:
            pass

    # ──────────────────── 기타 ────────────────────

    def show_error_message(self, title: str, message: str):
        """에러 메시지 표시"""
        QMessageBox.critical(self, title, message)

    def resizeEvent(self, event):
        """창 크기 변경 이벤트"""
        super().resizeEvent(event)

    def closeEvent(self, event):
        """창 닫기 이벤트"""
        if self.monitoring:
            self.stop_monitoring()
        event.accept()
