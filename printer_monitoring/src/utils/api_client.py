"""프린터 API 통신을 담당하는 모듈"""

from typing import Optional, Dict, Any, Union, Callable
import requests
import json
import time
from dataclasses import dataclass
from datetime import datetime
from requests.exceptions import RequestException, HTTPError, ConnectionError, Timeout
from ..constants.settings import (
    NETWORK_CONFIG,
    EventType,
    ERROR_MESSAGES,
    APIEndpoints
)

@dataclass
class APIResponse:
    """API 응답 데이터"""
    success: bool
    data: Dict[str, Any]
    status_code: int
    timestamp: str

@dataclass
class RetryConfig:
    """재시도 설정"""
    max_retries: int
    retry_delay: int
    timeout: int

class APIError(Exception):
    """API 관련 커스텀 예외"""
    def __init__(
        self,
        message: str,
        error_type: str,
        status_code: Optional[int] = None,
        details: Optional[Dict] = None
    ):
        super().__init__(message)
        self.error_type = error_type
        self.status_code = status_code
        self.details = details or {}

class APIClient:
    """프린터 API 통신을 담당하는 클래스"""
    
    def __init__(
        self,
        base_url: str,
        retry_config: Optional[RetryConfig] = None,
        session: Optional[requests.Session] = None
    ):
        """
        API 클라이언트 초기화
        Args:
            base_url: API 기본 URL
            retry_config: 재시도 설정
            session: 외부에서 주입할 세션
        """
        self.base_url = base_url.rstrip('/')
        self._retry_config = retry_config or RetryConfig(
            max_retries=NETWORK_CONFIG['MAX_RETRIES'],
            retry_delay=NETWORK_CONFIG['RETRY_DELAY'],
            timeout=NETWORK_CONFIG['REQUEST_TIMEOUT']
        )
        self._session = session or self._init_session()
        self._event_handlers = {
            EventType.ERROR_OCCURRED: [],
            'request_completed': [],
            'retry_attempted': []
        }

    def _init_session(self) -> requests.Session:
        """HTTP 세션 초기화"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'PrinterMonitor/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        return session

    def on(self, event_type: str, handler: Callable) -> None:
        """이벤트 핸들러 등록"""
        if event_type in self._event_handlers:
            self._event_handlers[event_type].append(handler)

    def _emit(self, event_type: str, data: Optional[Dict] = None) -> None:
        """이벤트 발생"""
        if event_type in self._event_handlers:
            event_data = {
                'type': event_type,
                'timestamp': datetime.now().isoformat(),
                'data': data or {}
            }
            for handler in self._event_handlers[event_type]:
                handler(event_data)

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        files: Optional[Dict] = None
    ) -> APIResponse:
        """
        API 요청 수행
        Args:
            method: HTTP 메서드
            endpoint: API 엔드포인트
            data: 요청 데이터
            params: 쿼리 파라미터
            headers: 추가 헤더
            files: 파일 데이터
        Returns:
            API 응답
        Raises:
            APIError: 요청 실패 시
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        retries = 0
        last_error = None

        while retries < self._retry_config.max_retries:
            try:
                response = self._session.request(
                    method=method,
                    url=url,
                    json=data if files is None else None,
                    data=data if files is not None else None,
                    params=params,
                    headers=headers,
                    files=files,
                    timeout=self._retry_config.timeout
                )
                
                self._validate_response(response)
                result = response.json() if response.content else {}
                
                api_response = APIResponse(
                    success=True,
                    data=result,
                    status_code=response.status_code,
                    timestamp=datetime.now().isoformat()
                )
                
                self._emit('request_completed', api_response.__dict__)
                return api_response

            except (ConnectionError, Timeout) as e:
                retries += 1
                last_error = e
                
                if retries < self._retry_config.max_retries:
                    self._emit('retry_attempted', {
                        'attempt': retries,
                        'max_retries': self._retry_config.max_retries,
                        'error': str(e)
                    })
                    time.sleep(self._retry_config.retry_delay)
                else:
                    self._handle_error(e, "connection_error")
                    
            except json.JSONDecodeError as e:
                self._handle_error(e, "invalid_response")
                
            except Exception as e:
                self._handle_error(e, "request_failed")

        self._handle_error(last_error, "max_retries_exceeded")

    def _validate_response(self, response: requests.Response) -> None:
        """
        응답 상태 코드 검증
        Args:
            response: API 응답
        Raises:
            APIError: 응답이 실패 상태일 때
        """
        if response.status_code >= 500:
            raise APIError(
                ERROR_MESSAGES['API_ERROR'],
                "server_error",
                response.status_code,
                {'response': response.text}
            )
        elif response.status_code >= 400:
            raise APIError(
                ERROR_MESSAGES['API_ERROR'],
                "client_error",
                response.status_code,
                {'response': response.text}
            )

    def _handle_error(self, error: Exception, error_type: str) -> None:
        """
        에러 처리 및 이벤트 발생
        Args:
            error: 발생한 예외
            error_type: 에러 타입
        Raises:
            APIError: 래핑된 에러
        """
        api_error = APIError(
            str(error),
            error_type,
            details={'original_error': str(error)}
        )
        self._emit(EventType.ERROR_OCCURRED, {'error': api_error.__dict__})
        raise api_error

    def get_printer_status(self) -> Dict[str, Any]:
        """프린터 상태 조회"""
        response = self._make_request('GET', APIEndpoints.PRINTER_INFO)
        return response.data

    def pause_print(self) -> Dict[str, Any]:
        """프린팅 일시 정지"""
        response = self._make_request('POST', APIEndpoints.PRINT_PAUSE)
        return response.data

    def resume_print(self) -> Dict[str, Any]:
        """프린팅 재개"""
        response = self._make_request('POST', APIEndpoints.PRINT_RESUME)
        return response.data

    def stop_print(self) -> Dict[str, Any]:
        """프린팅 중지"""
        response = self._make_request('POST', APIEndpoints.PRINT_CANCEL)
        return response.data

    def get_temperature_data(self) -> Dict[str, Any]:
        """온도 데이터 조회"""
        response = self._make_request('GET', APIEndpoints.TEMPERATURE)
        return response.data

    def get_print_progress(self) -> Dict[str, Any]:
        """프린팅 진행률 조회"""
        response = self._make_request('GET', APIEndpoints.PROGRESS)
        return response.data

    def upload_file(
        self,
        file_path: str,
        file_data: bytes,
        file_type: str = 'gcode'
    ) -> Dict[str, Any]:
        """
        파일 업로드
        Args:
            file_path: 파일 경로
            file_data: 파일 데이터
            file_type: 파일 타입
        Returns:
            업로드 결과
        """
        files = {
            'file': (file_path, file_data, f'application/{file_type}')
        }
        response = self._make_request(
            'POST',
            APIEndpoints.FILES_UPLOAD,
            files=files
        )
        return response.data

    def verify_connection(self) -> bool:
        """
        API 연결 상태 확인
        Returns:
            연결 성공 여부
        """
        try:
            self.get_printer_status()
            return True
        except APIError:
            return False

    def close(self) -> None:
        """세션 종료"""
        if self._session:
            self._session.close()

    def __enter__(self) -> 'APIClient':
        """컨텍스트 매니저 진입"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """컨텍스트 매니저 종료"""
        self.close()