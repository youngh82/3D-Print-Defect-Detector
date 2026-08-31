"""공통 데코레이터 모듈"""

import time
import logging
from typing import Any, Callable, Optional, Dict, TypeVar
from functools import wraps
from datetime import datetime

# 제네릭 타입 변수
T = TypeVar('T')

def log_execution(logger: Optional[logging.Logger] = None) -> Callable:
    """
    함수 실행을 로깅하는 데코레이터
    Args:
        logger: 로거 인스턴스 (없으면 기본 로거 사용)
    Returns:
        데코레이터 함수
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            used_logger = logger or logging.getLogger(func.__module__)
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                used_logger.debug(
                    f"{func.__name__} completed in {time.time() - start_time:.3f}s"
                )
                return result
            except Exception as e:
                used_logger.error(
                    f"Error in {func.__name__}: {str(e)}",
                    exc_info=True
                )
                raise

        return wrapper
    return decorator

def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    함수 실행 재시도 데코레이터
    Args:
        max_attempts: 최대 시도 횟수
        delay: 재시도 간 대기 시간
        exceptions: 재시도할 예외 목록
    Returns:
        데코레이터 함수
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay)

            raise last_exception

        return wrapper
    return decorator

def validate_input(**validators: Callable) -> Callable:
    """
    입력 값 검증 데코레이터
    Args:
        **validators: 파라미터별 검증 함수
    Returns:
        데코레이터 함수
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for param_name, validator in validators.items():
                if param_name in kwargs:
                    value = kwargs[param_name]
                    if not validator(value):
                        raise ValueError(
                            f"Invalid value for {param_name}: {value}"
                        )
            return func(*args, **kwargs)

        return wrapper
    return decorator

def event_emitter(event_type: str) -> Callable:
    """
    이벤트 발생 데코레이터
    Args:
        event_type: 이벤트 타입
    Returns:
        데코레이터 함수
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args: Any, **kwargs: Any) -> Any:
            try:
                result = func(self, *args, **kwargs)

                # 이벤트 발생 (_emit 메서드가 있는 경우)
                if hasattr(self, '_emit'):
                    self._emit(event_type, {
                        'timestamp': datetime.now().isoformat(),
                        'result': result
                    })

                return result
            except Exception as e:
                if hasattr(self, '_emit'):
                    self._emit('error', {
                        'timestamp': datetime.now().isoformat(),
                        'error': str(e),
                        'event_type': event_type
                    })
                raise

        return wrapper
    return decorator

def measure_time() -> Callable:
    """
    실행 시간 측정 데코레이터
    Returns:
        데코레이터 함수
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()

            print(f"{func.__name__} execution time: {end_time - start_time:.3f}s")
            return result

        return wrapper
    return decorator