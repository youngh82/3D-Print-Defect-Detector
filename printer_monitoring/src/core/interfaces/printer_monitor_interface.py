"""프린터 모니터 인터페이스 정의"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable

class PrinterMonitorInterface(ABC):
    """프린터 모니터 인터페이스"""
    
    @abstractmethod
    def get_printer_status(self) -> Dict[str, Any]:
        """
        프린터의 현재 상태 조회
        
        Returns:
            프린터 상태 정보
        """
        pass

    @abstractmethod
    def pause_print(self) -> bool:
        """
        프린팅 일시 정지
        
        Returns:
            성공 여부
        """
        pass

    @abstractmethod
    def resume_print(self) -> bool:
        """
        프린팅 재개
        
        Returns:
            성공 여부
        """
        pass

    @abstractmethod
    def stop_print(self) -> bool:
        """
        프린팅 중지
        
        Returns:
            성공 여부
        """
        pass

    @abstractmethod
    def on(self, event_type: str, handler: Callable) -> None:
        """
        이벤트 핸들러 등록
        
        Args:
            event_type: 이벤트 타입
            handler: 이벤트 핸들러 함수
        """
        pass

    @abstractmethod
    def get_temperature_data(self) -> Dict[str, Any]:
        """
        온도 데이터 조회
        
        Returns:
            온도 정보
        """
        pass

    @abstractmethod
    def get_print_progress(self) -> Dict[str, Any]:
        """
        프린팅 진행률 조회
        
        Returns:
            진행률 정보
        """
        pass