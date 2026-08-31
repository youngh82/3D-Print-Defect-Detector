"""프린터 모니터 객체 생성을 담당하는 팩토리 모듈"""

from typing import Optional
from dataclasses import dataclass
import requests
from ..printer_monitor import PrinterMonitor
from ...utils.api_client import APIClient, RetryConfig

@dataclass
class MonitorConfig:
    """모니터 설정"""
    base_url: str
    timeout: int = 5
    max_retries: int = 3
    retry_delay: int = 1

class PrinterMonitorFactory:
    """프린터 모니터 객체 생성을 담당하는 팩토리 클래스"""

    @staticmethod
    def create_monitor(
        config: MonitorConfig,
        session: Optional[requests.Session] = None
    ) -> PrinterMonitor:
        """
        프린터 모니터 인스턴스 생성
        
        Args:
            config: 모니터 설정
            session: HTTP 세션 (선택사항)
            
        Returns:
            PrinterMonitor 인스턴스
        """
        # API 클라이언트 설정
        retry_config = RetryConfig(
            max_retries=config.max_retries,
            retry_delay=config.retry_delay,
            timeout=config.timeout
        )

        # API 클라이언트 생성
        api_client = APIClient(
            base_url=config.base_url,
            retry_config=retry_config,
            session=session
        )

        # 프린터 모니터 생성
        return PrinterMonitor(api_client)

    @classmethod
    def create_from_env(cls) -> PrinterMonitor:
        """
        환경 변수에서 설정을 읽어 프린터 모니터 생성
        
        Returns:
            PrinterMonitor 인스턴스
        """
        from ...utils.env_loader import load_env_vars
        
        env = load_env_vars()
        config = MonitorConfig(
            base_url=env['MOONRAKER_BASE_URL'],
            timeout=env['REQUEST_TIMEOUT'],
            max_retries=env['MAX_RETRIES'],
            retry_delay=env['RETRY_DELAY']
        )
        
        return cls.create_monitor(config)

    @classmethod
    def create_test_monitor(cls) -> PrinterMonitor:
        """
        테스트용 프린터 모니터 생성
        
        Returns:
            PrinterMonitor 인스턴스
        """
        config = MonitorConfig(
            base_url="http://test.local",
            timeout=1,
            max_retries=1,
            retry_delay=0
        )
        
        # 테스트용 세션 생성
        session = requests.Session()
        session.verify = False  # SSL 검증 비활성화
        
        return cls.create_monitor(config, session)