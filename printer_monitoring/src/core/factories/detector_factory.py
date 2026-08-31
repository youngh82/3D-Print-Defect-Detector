"""결함 감지기 객체 생성을 담당하는 팩토리 모듈"""

from typing import Optional
from dataclasses import dataclass
import requests
from ..defect_detector import DefectDetector

@dataclass
class VisionConfig:
    """Vision API 설정"""
    prediction_key: str
    project_id: str
    iteration_name: str
    api_endpoint: str
    detection_threshold: float = 0.7

class DefectDetectorFactory:
    """결함 감지기 객체 생성을 담당하는 팩토리 클래스"""

    @staticmethod
    def create_detector(
        config: VisionConfig,
        session: Optional[requests.Session] = None
    ) -> DefectDetector:
        """
        결함 감지기 인스턴스 생성
        
        Args:
            config: Vision API 설정
            session: HTTP 세션 (선택사항)
            
        Returns:
            DefectDetector 인스턴스
        """
        return DefectDetector(
            prediction_key=config.prediction_key,
            project_id=config.project_id,
            iteration_name=config.iteration_name,
            detection_threshold=config.detection_threshold,
            session=session
        )

    @classmethod
    def create_from_env(cls) -> DefectDetector:
        """
        환경 변수에서 설정을 읽어 결함 감지기 생성
        
        Returns:
            DefectDetector 인스턴스
        """
        from ...utils.env_loader import load_env_vars
        
        env = load_env_vars()
        config = VisionConfig(
            prediction_key=env['VISION_PREDICTION_KEY'],
            project_id=env['VISION_PROJECT_ID'],
            iteration_name=env['VISION_ITERATION_NAME'],
            api_endpoint=env['VISION_API_ENDPOINT'],
            detection_threshold=env['DETECTION_THRESHOLD']
        )
        
        # Custom Vision API용 세션 설정
        session = requests.Session()
        session.headers.update({
            'Prediction-Key': config.prediction_key,
            'Content-Type': 'application/octet-stream'
        })
        
        return cls.create_detector(config, session)

    @classmethod
    def create_test_detector(
        cls,
        mock_predictions: bool = False
    ) -> DefectDetector:
        """
        테스트용 결함 감지기 생성
        
        Args:
            mock_predictions: 예측 결과 모의 여부
            
        Returns:
            DefectDetector 인스턴스
        """
        config = VisionConfig(
            prediction_key="test_key",
            project_id="test_project",
            iteration_name="test_iteration",
            api_endpoint="http://test.local/vision",
            detection_threshold=0.5
        )
        
        # 테스트용 세션 설정
        session = requests.Session()
        session.verify = False  # SSL 검증 비활성화
        
        if mock_predictions:
            # 테스트용 예측 결과 설정
            session.mount(
                'http://',
                MockVisionAdapter(
                    predictions=[
                        {
                            'tagName': 'test_defect',
                            'probability': 0.8,
                            'boundingBox': {
                                'left': 0.1,
                                'top': 0.1,
                                'width': 0.2,
                                'height': 0.2
                            }
                        }
                    ]
                )
            )
        
        return cls.create_detector(config, session)

class MockVisionAdapter(requests.adapters.BaseAdapter):
    """테스트용 Custom Vision API 응답 모의 어댑터"""
    
    def __init__(self, predictions: list):
        """
        모의 어댑터 초기화
        
        Args:
            predictions: 모의 예측 결과 목록
        """
        super().__init__()
        self.predictions = predictions

    def send(self, request, **kwargs):
        """
        모의 응답 생성
        
        Args:
            request: HTTP 요청
            **kwargs: 추가 인자
            
        Returns:
            모의 HTTP 응답
        """
        response = requests.Response()
        response.status_code = 200
        response._content = (
            '{"predictions":' + str(self.predictions) + '}'
        ).encode('utf-8')
        return response

    def close(self):
        """어댑터 정리"""
        pass