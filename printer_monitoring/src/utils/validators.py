"""공통 유효성 검증 유틸리티"""

import re
from typing import Any, Optional, Dict, List, Tuple
import cv2
import numpy as np
from dataclasses import dataclass
from ..constants.settings import IMAGE_PROCESSING

@dataclass
class ValidationResult:
    """검증 결과"""
    is_valid: bool
    errors: List[str]
    details: Optional[Dict[str, Any]] = None

class ImageValidator:
    """이미지 관련 검증"""

    @staticmethod
    def validate_image_size(
        image: np.ndarray,
        min_size: Optional[Tuple[int, int]] = None,
        max_size: Optional[Tuple[int, int]] = None
    ) -> ValidationResult:
        """
        이미지 크기 검증
        
        Args:
            image: OpenCV 이미지
            min_size: 최소 크기 (너비, 높이)
            max_size: 최대 크기 (너비, 높이)
            
        Returns:
            검증 결과
        """
        if image is None or image.size == 0:
            return ValidationResult(
                is_valid=False,
                errors=["유효하지 않은 이미지"],
                details={"error_type": "invalid_image"}
            )

        height, width = image.shape[:2]
        errors = []
        
        min_size = min_size or IMAGE_PROCESSING['MIN_IMAGE_SIZE']
        max_size = max_size or IMAGE_PROCESSING['MAX_IMAGE_SIZE']
        
        if width < min_size[0] or height < min_size[1]:
            errors.append(f"이미지 크기가 너무 작습니다. 최소 크기: {min_size}")
            
        if width > max_size[0] or height > max_size[1]:
            errors.append(f"이미지 크기가 너무 큽니다. 최대 크기: {max_size}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            details={
                "current_size": (width, height),
                "min_size": min_size,
                "max_size": max_size
            }
        )

    @staticmethod
    def validate_image_format(image: np.ndarray) -> ValidationResult:
        """
        이미지 형식 검증
        
        Args:
            image: OpenCV 이미지
            
        Returns:
            검증 결과
        """
        errors = []
        
        if image is None:
            errors.append("이미지가 None입니다")
            return ValidationResult(
                is_valid=False,
                errors=errors
            )
            
        if len(image.shape) != 3:
            errors.append("이미지가 3채널이 아닙니다")
            
        if image.dtype != np.uint8:
            errors.append("이미지 타입이 uint8이 아닙니다")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            details={"shape": image.shape, "dtype": str(image.dtype)}
        )

class URLValidator:
    """URL 관련 검증"""

    @staticmethod
    def validate_url(url: str) -> ValidationResult:
        """
        URL 형식 검증
        
        Args:
            url: 검증할 URL
            
        Returns:
            검증 결과
        """
        errors = []
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE
        )
        
        if not url:
            errors.append("URL이 비어있습니다")
        elif not url_pattern.match(url):
            errors.append("유효하지 않은 URL 형식입니다")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            details={"url": url}
        )

class PrinterStatusValidator:
    """프린터 상태 관련 검증"""

    @staticmethod
    def validate_temperature(
        temperature: Dict[str, float],
        min_temp: float = 0.0,
        max_temp: float = 300.0
    ) -> ValidationResult:
        """
        온도 데이터 검증
        
        Args:
            temperature: 온도 데이터
            min_temp: 최소 허용 온도
            max_temp: 최대 허용 온도
            
        Returns:
            검증 결과
        """
        errors = []
        
        for key, value in temperature.items():
            if not isinstance(value, (int, float)):
                errors.append(f"{key}: 온도가 숫자가 아닙니다")
            elif value < min_temp:
                errors.append(f"{key}: 온도가 너무 낮습니다 ({value})")
            elif value > max_temp:
                errors.append(f"{key}: 온도가 너무 높습니다 ({value})")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            details={
                "temperature": temperature,
                "limits": {"min": min_temp, "max": max_temp}
            }
        )

    @staticmethod
    def validate_progress(progress: float) -> ValidationResult:
        """
        진행률 검증
        
        Args:
            progress: 진행률 (0-100)
            
        Returns:
            검증 결과
        """
        errors = []
        
        if not isinstance(progress, (int, float)):
            errors.append("진행률이 숫자가 아닙니다")
        elif progress < 0 or progress > 100:
            errors.append(f"진행률이 유효범위를 벗어났습니다 ({progress})")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            details={"progress": progress}
        )

class ConfigValidator:
    """설정 관련 검증"""

    @staticmethod
    def validate_api_keys(
        keys: Dict[str, str],
        required_keys: List[str]
    ) -> ValidationResult:
        """
        API 키 검증
        
        Args:
            keys: API 키 목록
            required_keys: 필수 키 목록
            
        Returns:
            검증 결과
        """
        errors = []
        missing_keys = [key for key in required_keys if not keys.get(key)]
        
        if missing_keys:
            errors.append(f"필수 API 키가 없습니다: {', '.join(missing_keys)}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            details={"missing_keys": missing_keys}
        )