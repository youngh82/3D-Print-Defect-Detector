# print_monitor_control.py
import requests
from datetime import datetime
import time
import logging
from typing import Optional
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMessageBox

class PrintMonitorControl:
    def __init__(self, ui, network_config):
        """
        프린터 제어 모듈 초기화
        
        Args:
            ui: UI 컴포넌트 참조
            network_config: 네트워크 관련 설정
        """
        # 컴포넌트 참조 저장
        self.ui = ui
        self.config = network_config
        
        # 로거 설정
        self.logger = logging.getLogger(__name__)
        
        # 프린터 상태 초기화
        self.printer_status = "idle"
        
        # 네트워크 세션 설정
        self.session = requests.Session()
        self.session.headers.update(self.config.default_headers or {})
        
        # 초기 프린터 상태 확인
        try:
            self.update_printer_status("idle")
        except Exception as e:
            self.logger.error(f"초기 프린터 상태 확인 실패: {str(e)}")
            self.log_message(f"초기 프린터 상태 확인 실패: {str(e)}", 'error')

    def apply_moonraker_url(self) -> None:
        """Moonraker URL 업데이트"""
        if self.ui.show_consent_dialog():
            moonraker_url = self.ui.moonraker_url_input.text()
            self.log_message(f"Moonraker URL이 적용되었습니다: {moonraker_url}")
            self.ui.moonraker_apply_btn.setStyleSheet("background-color: #4CAF50; color: white;")
            QTimer.singleShot(1000, lambda: self.ui.moonraker_apply_btn.setStyleSheet(""))
        else:
            self.log_message("Moonraker URL 적용이 취소되었습니다.")

    def pause_print(self) -> None:
        """프린터 일시정지"""
        try:
            url = f"{self.ui.moonraker_url_input.text()}/printer/print/pause"
            self.log_message(f"프린터 일시정지 요청: {url}")
            
            response = self.retry_operation(
                lambda: self.session.post(url, timeout=self.config.request_timeout)
            )
            
            if response and response.status_code == 200:
                # 프린터 상태 업데이트
                self.printer_status = "paused"
                self.log_message("프린터가 일시정지되었습니다")
                
                # 상태바 업데이트
                self.ui.statusBar().showMessage('프린터 상태: 일시정지됨')
                
                # 버튼 UI 업데이트
                self.ui.pause_button.setEnabled(False)
                self.ui.resume_button.setEnabled(True)
                
                # 모니터링 상태 유지
                self.ui.monitoring_start_button.setEnabled(False)
                self.ui.monitoring_stop_button.setEnabled(True)
                
            else:
                error_msg = f"프린터 일시정지 실패: HTTP {response.status_code if response else 'No Response'}"
                self.log_message(error_msg, 'error')
                QMessageBox.warning(self.ui, "일시정지 실패", error_msg)
                
        except requests.exceptions.ConnectionError:
            error_msg = "프린터 연결 실패: 네트워크 또는 서버 접속 오류"
            self.log_message(error_msg, 'error')
            QMessageBox.critical(self.ui, "연결 오류", error_msg)
            
        except Exception as e:
            error_msg = f"프린터 일시정지 중 오류 발생: {str(e)}"
            self.log_message(error_msg, 'error')
            QMessageBox.critical(self.ui, "오류", error_msg)

    def resume_print(self) -> None:
        """프린터 재개"""
        try:
            url = f"{self.ui.moonraker_url_input.text()}/printer/print/resume"
            self.log_message(f"프린터 재개 요청: {url}")
            
            response = self.retry_operation(
                lambda: self.session.post(url, timeout=self.config.request_timeout)
            )
            
            if response and response.status_code == 200:
                # 프린터 상태 업데이트
                self.printer_status = "printing"
                self.log_message("프린팅이 재개되었습니다")
                
                # 상태바 업데이트
                self.ui.statusBar().showMessage('프린터 상태: 프린팅 중')
                
                # 버튼 UI 업데이트
                self.ui.pause_button.setEnabled(True)
                self.ui.resume_button.setEnabled(False)
                
                # 모니터링 상태 유지
                self.ui.monitoring_start_button.setEnabled(False)
                self.ui.monitoring_stop_button.setEnabled(True)
                
            else:
                error_msg = f"프린터 재개 실패: HTTP {response.status_code if response else 'No Response'}"
                self.log_message(error_msg, 'error')
                QMessageBox.warning(self.ui, "재개 실패", error_msg)
                
        except requests.exceptions.ConnectionError:
            error_msg = "프린터 연결 실패: 네트워크 또는 서버 접속 오류"
            self.log_message(error_msg, 'error')
            QMessageBox.critical(self.ui, "연결 오류", error_msg)
            
        except Exception as e:
            error_msg = f"프린터 재개 중 오류 발생: {str(e)}"
            self.log_message(error_msg, 'error')
            QMessageBox.critical(self.ui, "오류", error_msg)

    def emergency_stop(self) -> None:
        """긴급 정지"""
        try:
            url = f"{self.ui.moonraker_url_input.text()}/printer/emergency_stop"
            self.log_message(f"긴급 정지 요청: {url}", 'warning')
            
            response = self.retry_operation(
                lambda: self.session.post(url, timeout=self.config.request_timeout)
            )
            
            if response and response.status_code == 200:
                self.printer_status = "idle"
                self.log_message("프린터가 긴급 정지되었습니다", 'warning')
                self.ui.statusBar().showMessage('프린터 상태: 긴급 정지됨')
                
                # UI 업데이트
                self.ui.pause_button.setEnabled(False)
                self.ui.resume_button.setEnabled(False)
                self.ui.monitoring_start_button.setEnabled(True)
                self.ui.monitoring_stop_button.setEnabled(False)
                
            else:
                error_msg = f"긴급 정지 실패: HTTP {response.status_code if response else 'No Response'}"
                self.log_message(error_msg, 'error')
                QMessageBox.critical(self.ui, "긴급 정지 실패", error_msg)
                
        except Exception as e:
            error_msg = f"긴급 정지 중 오류 발생: {str(e)}"
            self.log_message(error_msg, 'error')
            QMessageBox.critical(self.ui, "오류", error_msg)

    def update_printer_status(self, status: str) -> None:
        """프린터 상태 업데이트"""
        try:
            self.printer_status = status
            
            # 상태에 따른 버튼 활성화/비활성화
            if status == "idle":
                self.ui.pause_button.setEnabled(False)
                self.ui.resume_button.setEnabled(False)
                status_text = "대기 중"
                
            elif status == "printing":
                self.ui.pause_button.setEnabled(True)
                self.ui.resume_button.setEnabled(False)
                status_text = "프린팅 중"
                
            elif status == "paused":
                self.ui.pause_button.setEnabled(False)
                self.ui.resume_button.setEnabled(True)
                status_text = "일시정지됨"
                
            # 상태바 업데이트
            self.ui.statusBar().showMessage(f'프린터 상태: {status_text}')
            
            # 상태 로그 추가
            self.log_message(f"프린터 상태가 '{status_text}'(으)로 변경되었습니다")
            
        except Exception as e:
            self.logger.error(f"상태 업데이트 중 오류 발생: {str(e)}")
            self.log_message(f"상태 업데이트 중 오류 발생: {str(e)}", 'error')

    def get_printer_status(self) -> str:
        """프린터 상태 조회"""
        try:
            url = f"{self.ui.moonraker_url_input.text()}/printer/objects/query?print_stats"
            response = self.retry_operation(
                lambda: self.session.get(url, timeout=self.config.request_timeout)
            )
            
            if response and response.status_code == 200:
                data = response.json()
                status = data.get('result', {}).get('status', {}).get('print_stats', {}).get('state', 'idle')
                return status
            else:
                self.log_message(f"프린터 상태 조회 실패: HTTP {response.status_code if response else 'No Response'}", 'error')
                return "unknown"
                
        except Exception as e:
            self.logger.error(f"프린터 상태 조회 중 오류 발생: {str(e)}")
            self.log_message(f"프린터 상태 조회 중 오류 발생: {str(e)}", 'error')
            return "unknown"

    def check_connection(self) -> bool:
        """프린터 연결 상태 확인"""
        try:
            url = f"{self.ui.moonraker_url_input.text()}/printer/info"
            response = self.retry_operation(
                lambda: self.session.get(url, timeout=self.config.request_timeout)
            )
            
            if response and response.status_code == 200:
                self.log_message("프린터 연결 상태: 정상")
                return True
            else:
                self.log_message("프린터 연결 상태: 실패", 'error')
                return False
                
        except Exception as e:
            self.logger.error(f"프린터 연결 확인 중 오류 발생: {str(e)}")
            self.log_message(f"프린터 연결 확인 중 오류 발생: {str(e)}", 'error')
            return False

    def retry_operation(self, operation):
        """작업 재시도 래퍼 메서드"""
        for attempt in range(self.config.max_retries):
            try:
                return operation()
            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    raise e
                self.log_message(f"작업 실패, {attempt + 1}번째 재시도 중...", 'warning')
                time.sleep(self.config.retry_delay)

    def log_message(self, message: str, level: str = 'info') -> None:
        """로그 메시지 출력"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            'info': '→',
            'warning': '⚠',
            'error': '❌',
            'status': '🖨'
        }.get(level, '→')
        
        formatted_message = f"[{timestamp}] {prefix} {message}"
        self.ui.status_text.append(formatted_message)
        
        # 로거에도 기록
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.log(log_level, message)