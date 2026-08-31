"""프린터 제어 패널 UI 모듈"""

from typing import Optional, Dict, List
from PyQt5.QtWidgets import (
    QWidget, QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QDialog,
    QCheckBox, QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor
from datetime import datetime
from dataclasses import dataclass
from ..constants.settings import DEFAULT_URLS

@dataclass
class UrlConfig:
    """URL 설정 정보"""
    webcam_url: str
    moonraker_url: str

class LogManager:
    """로그 관리 클래스"""
    
    def __init__(self, max_lines: int = 50):
        self.max_lines = max_lines
        self._log_levels = {
            'info': '→',
            'warning': '⚠',
            'error': '❌',
            'defect': '🔍'
        }

    def format_log(self, message: str, level: str = 'info') -> str:
        """로그 메시지 포맷팅"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        icon = self._log_levels.get(level, '→')
        return f"[{timestamp}] {icon} {message}"

    def get_log_icon(self, level: str) -> str:
        """로그 레벨별 아이콘 반환"""
        return self._log_levels.get(level, '→')

class ControlPanel(QWidget):
    """프린터 제어 패널 위젯"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        제어 패널 초기화
        Args:
            parent: 부모 위젯
        """
        super().__init__(parent)
        self.log_manager = LogManager()
        self.init_variables()
        self._settings_group = None
        self._status_control_group = None

    def init_variables(self) -> None:
        """변수 초기화"""
        self.monitoring = False
        self.printer_status = "idle"
        self.url_inputs: Dict[str, tuple] = {}
        self.control_buttons: Dict[str, QPushButton] = {}

    def create_settings_group(self) -> QGroupBox:
        """설정 그룹 생성 (한번만 생성, 이후 캐시 반환)"""
        if self._settings_group is not None:
            return self._settings_group

        settings_group = QGroupBox("모니터링 설정")
        settings_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        settings_layout = QGridLayout()
        settings_layout.setColumnStretch(1, 1)

        # URL 입력 필드 생성
        self.url_inputs = self._create_url_inputs()
        for row, (label, input_field, button) in enumerate(self.url_inputs.values()):
            settings_layout.addWidget(label, row, 0)
            settings_layout.addWidget(input_field, row, 1)
            settings_layout.addWidget(button, row, 2)

        settings_group.setLayout(settings_layout)
        self._settings_group = settings_group
        return settings_group

    def _create_url_inputs(self) -> Dict[str, tuple]:
        """URL 입력 필드 생성"""
        webcam_input = self._create_url_input(DEFAULT_URLS['WEBCAM_URL'])
        webcam_input.setText(DEFAULT_URLS['WEBCAM_URL'])
        webcam_btn = self._create_button("적용", "primary")

        moonraker_input = self._create_url_input(DEFAULT_URLS['MOONRAKER_BASE'])
        moonraker_input.setText(DEFAULT_URLS['MOONRAKER_BASE'])
        moonraker_btn = self._create_button("적용", "primary")

        return {
            'webcam': (
                QLabel("Webcam URL:"),
                webcam_input,
                webcam_btn,
            ),
            'moonraker': (
                QLabel("Moonraker URL:"),
                moonraker_input,
                moonraker_btn,
            )
        }

    def _create_url_input(self, placeholder: str) -> QLineEdit:
        """URL 입력 필드 생성"""
        input_field = QLineEdit()
        input_field.setPlaceholderText(placeholder)
        return input_field

    def create_status_control_group(self) -> QGroupBox:
        """상태 및 제어 그룹 생성 (한번만 생성, 이후 캐시 반환)"""
        if self._status_control_group is not None:
            return self._status_control_group

        control_group = QGroupBox("상태 및 제어")
        control_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        control_layout = QVBoxLayout()

        self.status_text = self._create_status_text()
        control_layout.addWidget(self.status_text)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.control_buttons = self._create_control_buttons()

        button_layout.addStretch()
        for button in self.control_buttons.values():
            button_layout.addWidget(button)
        button_layout.addStretch()

        control_layout.addLayout(button_layout)
        control_group.setLayout(control_layout)

        self.setup_style()
        self._status_control_group = control_group
        return control_group

    def _create_status_text(self) -> QTextEdit:
        """상태 텍스트 영역 생성"""
        status_text = QTextEdit()
        status_text.setReadOnly(True)
        status_text.setMaximumHeight(100)
        return status_text

    def _create_control_buttons(self) -> Dict[str, QPushButton]:
        """제어 버튼 생성"""
        return {
            'start': self._create_button("모니터링 시작", "success", True),
            'stop': self._create_button("모니터링 중지", "success", False),
            'pause': self._create_button("일시정지", "warning", False),
            'resume': self._create_button("재개", "primary", False)
        }

    def _create_button(
        self,
        text: str,
        style: str = "primary",
        enabled: bool = True
    ) -> QPushButton:
        """버튼 생성"""
        button = QPushButton(text)
        button.setEnabled(enabled)
        button.setMinimumWidth(100)
        self._apply_button_style(button, style)
        return button

    def _apply_button_style(self, button: QPushButton, style: str) -> None:
        """버튼 스타일 적용"""
        colors = {
            'primary': '#007bff',
            'success': '#28a745',
            'warning': '#ffc107',
            'danger': '#dc3545'
        }
        color = colors.get(style, colors['primary'])
        
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self._darken_color(color)};
            }}
            QPushButton:pressed {{
                background-color: {self._darken_color(color, 0.2)};
            }}
            QPushButton:disabled {{
                background-color: #CCCCCC;
                color: #666666;
            }}
        """)

    def setup_style(self) -> None:
        """전체 스타일 설정"""
        self.status_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 5px;
                font-family: monospace;
            }
        """)

    def show_consent_dialog(self) -> bool:
        """개인정보 수집 동의 다이얼로그"""
        dialog = QDialog(self)
        dialog.setWindowTitle("개인정보 수집 동의")
        dialog.setModal(True)
        dialog.setFixedSize(400, 300)

        layout = QVBoxLayout()

        info_text = QLabel(
            "본 서비스는 3D 프린터 모니터링을 위해\n"
            "다음과 같은 정보를 수집합니다:\n\n"
            "• 프린터 연결 URL\n"
            "• 웹캠 영상 데이터\n"
            "• 프린팅 상태 정보\n\n"
            "수집된 정보는 모니터링 용도로만 사용되며,\n"
            "서버에 별도로 저장되지 않습니다."
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("QLabel { line-height: 150%; }")
        layout.addWidget(info_text)

        consent_check = QCheckBox("개인정보 수집 및 이용에 동의합니다")
        layout.addWidget(consent_check)

        button_layout = QHBoxLayout()
        cancel_button = QPushButton("취소")
        confirm_button = QPushButton("확인")
        confirm_button.setEnabled(False)
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(confirm_button)
        layout.addLayout(button_layout)

        dialog.setLayout(layout)

        consent_check.stateChanged.connect(
            lambda state: confirm_button.setEnabled(state == Qt.Checked)
        )
        cancel_button.clicked.connect(dialog.reject)
        confirm_button.clicked.connect(dialog.accept)

        return dialog.exec_() == QDialog.Accepted

    def log_message(self, message: str, level: str = 'info') -> None:
        """로그 메시지 추가"""
        formatted_message = self.log_manager.format_log(message, level)
        self.status_text.append(formatted_message)
        self._limit_log_lines()
        self._scroll_to_bottom()

    def _limit_log_lines(self) -> None:
        """로그 라인 수 제한"""
        doc = self.status_text.document()
        while doc.lineCount() > self.log_manager.max_lines:
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()

    def _scroll_to_bottom(self) -> None:
        """스크롤을 최신 메시지로"""
        self.status_text.verticalScrollBar().setValue(
            self.status_text.verticalScrollBar().maximum()
        )

    def update_monitoring_status(self, is_monitoring: bool) -> None:
        """모니터링 상태 업데이트"""
        self.monitoring = is_monitoring
        self.control_buttons['start'].setEnabled(not is_monitoring)
        self.control_buttons['stop'].setEnabled(is_monitoring)
        self.control_buttons['pause'].setEnabled(is_monitoring)

    def update_printer_status(self, status: str) -> None:
        """프린터 상태 업데이트"""
        self.printer_status = status
        
        if status == "printing":
            self.control_buttons['pause'].setEnabled(True)
            self.control_buttons['resume'].setEnabled(False)
        elif status == "paused":
            self.control_buttons['pause'].setEnabled(False)
            self.control_buttons['resume'].setEnabled(True)
        else:  # idle or other states
            self.control_buttons['pause'].setEnabled(False)
            self.control_buttons['resume'].setEnabled(False)

    # -- 편의 프로퍼티: main_window에서 직접 접근 --
    @property
    def monitoring_start_button(self) -> QPushButton:
        return self.control_buttons['start']

    @property
    def monitoring_stop_button(self) -> QPushButton:
        return self.control_buttons['stop']

    @property
    def pause_button(self) -> QPushButton:
        return self.control_buttons['pause']

    @property
    def resume_button(self) -> QPushButton:
        return self.control_buttons['resume']

    @property
    def webcam_url_input(self) -> QLineEdit:
        return self.url_inputs['webcam'][1]

    @property
    def moonraker_url_input(self) -> QLineEdit:
        return self.url_inputs['moonraker'][1]

    @property
    def webcam_apply_btn(self) -> QPushButton:
        return self.url_inputs['webcam'][2]

    @property
    def moonraker_apply_btn(self) -> QPushButton:
        return self.url_inputs['moonraker'][2]

    def get_url_config(self) -> UrlConfig:
        """현재 URL 설정 반환"""
        return UrlConfig(
            webcam_url=self.url_inputs['webcam'][1].text(),
            moonraker_url=self.url_inputs['moonraker'][1].text()
        )

    @staticmethod
    def _darken_color(hex_color: str, factor: float = 0.1) -> str:
        """색상을 어둡게 만드는 헬퍼 함수"""
        # HEX to RGB
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        # RGB값을 어둡게
        darkened = [int(val * (1 - factor)) for val in rgb]
        
        # RGB to HEX
        return '#{:02x}{:02x}{:02x}'.format(*darkened)