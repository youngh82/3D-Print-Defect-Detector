"""프린터 상태 모니터링 및 제어 모듈"""

from typing import Optional, Dict, Any, Callable
from datetime import datetime
from dataclasses import dataclass
from .interfaces.printer_monitor_interface import PrinterMonitorInterface
from ..utils.api_client import APIClient
from ..constants.settings import PrinterStatus, EventType, ERROR_MESSAGES

@dataclass
class PrinterState:
    """프린터 상태 정보"""
    status: str
    temperature: Dict[str, float]
    progress: float
    timestamp: str

class PrinterMonitorError(Exception):
    """프린터 모니터링 관련 예외"""
    def __init__(
        self,
        message: str,
        error_type: str,
        details: Optional[Dict] = None
    ):
        super().__init__(message)
        self.error_type = error_type
        self.details = details or {}

class PrinterMonitor(PrinterMonitorInterface):
    """프린터 상태 모니터링 및 제어를 담당하는 클래스"""
    
    def __init__(self, api_client: APIClient):
        """
        프린터 모니터 초기화
        Args:
            api_client: API 클라이언트 인스턴스
        """
        self._api_client = api_client
        self._current_status = PrinterStatus.IDLE
        self._event_handlers = {
            EventType.STATUS_CHANGED: [],
            EventType.ERROR_OCCURRED: [],
            EventType.MONITORING_STARTED: [],
            EventType.MONITORING_STOPPED: []
        }

    @property
    def current_status(self) -> str:
        """현재 프린터 상태"""
        return self._current_status

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

    def get_printer_status(self) -> Dict[str, Any]:
        """
        프린터의 현재 상태 조회
        Returns:
            프린터 상태 정보
        Raises:
            PrinterMonitorError: 상태 조회 실패 시
        """
        try:
            response = self._api_client.get_printer_status()
            new_status = response.get('status', PrinterStatus.IDLE)
            self._update_status(new_status)
            
            state = PrinterState(
                status=new_status,
                temperature=self.get_temperature_data(),
                progress=self.get_print_progress().get('progress', 0.0),
                timestamp=datetime.now().isoformat()
            )
            
            return state.__dict__
            
        except Exception as e:
            error = PrinterMonitorError(
                ERROR_MESSAGES['PRINTER_ERROR'],
                'status_check_failed',
                {'original_error': str(e)}
            )
            self._emit(EventType.ERROR_OCCURRED, {'error': error.__dict__})
            raise error

    def pause_print(self) -> bool:
        """
        프린팅 일시 정지
        Returns:
            성공 여부
        Raises:
            PrinterMonitorError: 일시정지 실패 시
        """
        try:
            response = self._api_client.pause_print()
            if response.get('success', False):
                self._update_status(PrinterStatus.PAUSED)
                return True
            return False
            
        except Exception as e:
            error = PrinterMonitorError(
                ERROR_MESSAGES['PRINTER_ERROR'],
                'pause_failed',
                {'original_error': str(e)}
            )
            self._emit(EventType.ERROR_OCCURRED, {'error': error.__dict__})
            raise error

    def resume_print(self) -> bool:
        """
        프린팅 재개
        Returns:
            성공 여부
        Raises:
            PrinterMonitorError: 재개 실패 시
        """
        try:
            response = self._api_client.resume_print()
            if response.get('success', False):
                self._update_status(PrinterStatus.PRINTING)
                return True
            return False
            
        except Exception as e:
            error = PrinterMonitorError(
                ERROR_MESSAGES['PRINTER_ERROR'],
                'resume_failed',
                {'original_error': str(e)}
            )
            self._emit(EventType.ERROR_OCCURRED, {'error': error.__dict__})
            raise error

    def stop_print(self) -> bool:
        """
        프린팅 중지
        Returns:
            성공 여부
        Raises:
            PrinterMonitorError: 중지 실패 시
        """
        try:
            response = self._api_client.stop_print()
            if response.get('success', False):
                self._update_status(PrinterStatus.IDLE)
                return True
            return False
            
        except Exception as e:
            error = PrinterMonitorError(
                ERROR_MESSAGES['PRINTER_ERROR'],
                'stop_failed',
                {'original_error': str(e)}
            )
            self._emit(EventType.ERROR_OCCURRED, {'error': error.__dict__})
            raise error

    def get_temperature_data(self) -> Dict[str, Any]:
        """
        온도 데이터 조회
        Returns:
            온도 정보
        Raises:
            PrinterMonitorError: 조회 실패 시
        """
        try:
            return self._api_client.get_temperature_data()
            
        except Exception as e:
            error = PrinterMonitorError(
                ERROR_MESSAGES['PRINTER_ERROR'],
                'temperature_check_failed',
                {'original_error': str(e)}
            )
            self._emit(EventType.ERROR_OCCURRED, {'error': error.__dict__})
            raise error

    def get_print_progress(self) -> Dict[str, Any]:
        """
        프린팅 진행률 조회
        Returns:
            진행률 정보
        Raises:
            PrinterMonitorError: 조회 실패 시
        """
        try:
            return self._api_client.get_print_progress()
            
        except Exception as e:
            error = PrinterMonitorError(
                ERROR_MESSAGES['PRINTER_ERROR'],
                'progress_check_failed',
                {'original_error': str(e)}
            )
            self._emit(EventType.ERROR_OCCURRED, {'error': error.__dict__})
            raise error

    def _update_status(self, new_status: str) -> None:
        """
        프린터 상태 업데이트 및 이벤트 발생
        Args:
            new_status: 새로운 상태
        """
        if new_status != self._current_status:
            old_status = self._current_status
            self._current_status = new_status
            
            self._emit(EventType.STATUS_CHANGED, {
                'old_status': old_status,
                'new_status': new_status,
                'timestamp': datetime.now().isoformat()
            })

    def start_monitoring(self) -> None:
        """모니터링 시작"""
        try:
            initial_status = self.get_printer_status()
            self._emit(EventType.MONITORING_STARTED, {
                'initial_status': initial_status,
                'timestamp': datetime.now().isoformat()
            })
        except PrinterMonitorError:
            raise

    def stop_monitoring(self) -> None:
        """모니터링 중지"""
        try:
            final_status = self.get_printer_status()
            self._emit(EventType.MONITORING_STOPPED, {
                'final_status': final_status,
                'timestamp': datetime.now().isoformat()
            })
        except PrinterMonitorError:
            raise