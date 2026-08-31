"""결함 감지기 인터페이스 정의"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional, Callable
import numpy as np

class DefectDetectorInterface(ABC):
    """결함 감지기 인터페이스"""
    
    @abstractmethod
    def detect_defect(
        self,
        image: np.ndarray
    ) -> Tuple[List[Dict[str, Any]], Optional[np.ndarray]]:
        """
        이미지에서 결함을 감지
        
        Args:
            image (np.ndarray): 분석할 이미지

        Returns:
            Tuple[List[Dict[str, Any]], Optional[np.ndarray]]:
                - 감지된 결함 목록
                - 결함이 표시된 이미지 (옵션)
        """
        pass

    @abstractmethod
    def on(self, event_type: str, handler: Callable) -> None:
        """
        이벤트 핸들러 등록
        
        Args:
            event_type (str): 이벤트 타입
            handler (Callable): 이벤트 처리 함수
        """
        pass

    @abstractmethod
    def save_defect_image(self, image: np.ndarray, save_dir: str = "defects") -> str:
        """
        결함이 감지된 이미지 저장
        
        Args:
            image (np.ndarray): 저장할 이미지
            save_dir (str): 저장 디렉토리

        Returns:
            str: 저장된 파일 경로
        """
        pass