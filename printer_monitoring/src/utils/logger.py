import logging
import os
from datetime import datetime
from typing import Optional
from logging.handlers import RotatingFileHandler

class Logger:
    """로깅을 담당하는 클래스"""
    
    def __init__(self, log_dir: str = "logs", max_size: int = 1024*1024, backup_count: int = 5):
        """
        로거 초기화
        Args:
            log_dir (str): 로그 파일 저장 디렉토리
            max_size (int): 로그 파일 최대 크기 (바이트)
            backup_count (int): 보관할 백업 파일 수
        """
        self.log_dir = log_dir
        self.max_size = max_size
        self.backup_count = backup_count
        self._setup_logger()

    def _setup_logger(self):
        """로거 설정"""
        # 로그 디렉토리 생성
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 로그 파일명 설정
        current_date = datetime.now().strftime("%Y%m%d")
        log_file = os.path.join(self.log_dir, f"printer_monitor_{current_date}.log")
        
        # 로거 생성
        self.logger = logging.getLogger("PrinterMonitor")
        self.logger.setLevel(logging.DEBUG)
        
        # 포맷터 설정
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 파일 핸들러 설정
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=self.max_size,
            backupCount=self.backup_count
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        # 스트림 핸들러 설정
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(formatter)
        
        # 핸들러 추가
        self.logger.addHandler(file_handler)
        self.logger.addHandler(stream_handler)

    def info(self, message: str, extra: Optional[dict] = None):
        """정보 레벨 로그"""
        self.logger.info(message, extra=extra)

    def warning(self, message: str, extra: Optional[dict] = None):
        """경고 레벨 로그"""
        self.logger.warning(message, extra=extra)

    def error(self, message: str, extra: Optional[dict] = None):
        """에러 레벨 로그"""
        self.logger.error(message, extra=extra)

    def debug(self, message: str, extra: Optional[dict] = None):
        """디버그 레벨 로그"""
        self.logger.debug(message, extra=extra)

    def critical(self, message: str, extra: Optional[dict] = None):
        """치명적 에러 레벨 로그"""
        self.logger.critical(message, extra=extra)

    def log_defect(self, defect_info: dict):
        """결함 감지 로그"""
        self.logger.warning(
            "결함 감지",
            extra={
                'defect_type': defect_info.get('tag', 'unknown'),
                'confidence': defect_info.get('probability', 0),
                'timestamp': datetime.now().isoformat()
            }
        )

    def log_printer_status(self, status: str, details: Optional[dict] = None):
        """프린터 상태 변경 로그"""
        self.logger.info(
            f"프린터 상태 변경: {status}",
            extra={
                'status': status,
                'details': details or {},
                'timestamp': datetime.now().isoformat()
            }
        )

    def log_monitoring_event(self, event_type: str, details: Optional[dict] = None):
        """모니터링 이벤트 로그"""
        self.logger.info(
            f"모니터링 이벤트: {event_type}",
            extra={
                'event_type': event_type,
                'details': details or {},
                'timestamp': datetime.now().isoformat()
            }
        )

    def log_error_event(self, error_type: str, error_message: str, stack_trace: Optional[str] = None):
        """에러 이벤트 로그"""
        self.logger.error(
            f"에러 발생: {error_type}",
            extra={
                'error_type': error_type,
                'error_message': error_message,
                'stack_trace': stack_trace,
                'timestamp': datetime.now().isoformat()
            }
        )

    def get_recent_logs(self, count: int = 100) -> list:
        """최근 로그 조회"""
        logs = []
        if os.path.exists(self._get_current_log_file()):
            with open(self._get_current_log_file(), 'r') as f:
                logs = f.readlines()[-count:]
        return logs

    def _get_current_log_file(self) -> str:
        """현재 로그 파일 경로 반환"""
        current_date = datetime.now().strftime("%Y%m%d")
        return os.path.join(self.log_dir, f"printer_monitor_{current_date}.log")