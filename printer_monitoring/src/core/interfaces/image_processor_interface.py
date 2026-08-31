"""이미지 프로세서 인터페이스 정의"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
import numpy as np

class ImageProcessorInterface(ABC):
    """이미지 프로세서 인터페이스"""
    
    @abstractmethod
    def capture_frame(self, webcam_url: str) -> np.ndarray:
        """
        웹캠에서 프레임 캡처
        
        Args:
            webcam_url: 웹캠 URL
            
        Returns:
            캡처된 프레임
        """
        pass

    @abstractmethod
    def process_frame(
        self,
        frame: np.ndarray,
        monitoring_start_time: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        프레임 처리 및 분석
        
        Args:
            frame: 처리할 프레임
            monitoring_start_time: 모니터링 시작 시간
            
        Returns:
            처리된 이미지 정보
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