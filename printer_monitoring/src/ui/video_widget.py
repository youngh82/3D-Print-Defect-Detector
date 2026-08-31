"""비디오 디스플레이를 위한 UI 모듈"""

import cv2
import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass
from PyQt5.QtWidgets import (
    QWidget,
    QGroupBox,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt

@dataclass
class DisplaySize:
    """디스플레이 크기 정보"""
    width: int
    height: int

class ImageConverter:
    """이미지 변환 유틸리티 클래스"""
    
    @staticmethod
    def frame_to_qimage(frame: np.ndarray) -> Optional[QImage]:
        """
        OpenCV 프레임을 QImage로 변환
        
        Args:
            frame: OpenCV 이미지 프레임
            
        Returns:
            변환된 QImage 또는 None
        """
        try:
            if frame is None:
                return None
                
            # BGR to RGB 변환
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            
            # QImage 생성
            bytes_per_line = ch * w
            return QImage(
                rgb_frame.data,
                w, h,
                bytes_per_line,
                QImage.Format_RGB888
            )
        except Exception as e:
            print(f"이미지 변환 실패: {str(e)}")
            return None

class VideoDisplayLabel(QLabel):
    """비디오 표시를 위한 레이블 위젯"""
    
    def __init__(
        self,
        min_size: DisplaySize = DisplaySize(480, 360),
        parent: Optional[QWidget] = None
    ):
        """
        비디오 디스플레이 레이블 초기화
        
        Args:
            min_size: 최소 디스플레이 크기
            parent: 부모 위젯
        """
        super().__init__(parent)
        self.setObjectName("videoLabel")
        self.setMinimumSize(min_size.width, min_size.height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAlignment(Qt.AlignCenter)
        self.setScaledContents(True)
        self.current_image: Optional[QImage] = None

    def update_display(self, image: Optional[QImage] = None) -> None:
        """
        디스플레이 업데이트
        
        Args:
            image: 표시할 QImage
        """
        if image:
            self.current_image = image
        if self.current_image:
            scaled_pixmap = QPixmap.fromImage(self.current_image).scaled(
                self.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.setPixmap(scaled_pixmap)

    def clear_display(self) -> None:
        """디스플레이 초기화"""
        self.clear()
        self.current_image = None

class VideoDisplayWidget(QWidget):
    """비디오 디스플레이를 위한 위젯"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        비디오 디스플레이 위젯 초기화
        
        Args:
            parent: 부모 위젯
        """
        super().__init__(parent)
        self.image_converter = ImageConverter()
        self.init_ui()

    def init_ui(self) -> None:
        """UI 초기화"""
        main_layout = QVBoxLayout(self)
        video_container = self._create_video_container()
        main_layout.addWidget(video_container)

    def _create_video_container(self) -> QGroupBox:
        """비디오 컨테이너 생성"""
        container = QGroupBox("실시간 모니터링")
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QHBoxLayout()

        # 왼쪽: 실시간 웹캠
        left_group = self._create_display_group(
            "실시간 웹캠",
            DisplaySize(480, 360)
        )
        self.webcam_label = left_group.findChild(VideoDisplayLabel)

        # 오른쪽: Custom Vision 검사
        right_group = self._create_display_group(
            "Custom Vision 검사 영역",
            DisplaySize(480, 360)
        )
        self.vision_label = right_group.findChild(VideoDisplayLabel)

        layout.addWidget(left_group)
        layout.addWidget(right_group)
        container.setLayout(layout)
        return container

    def _create_display_group(
        self,
        title: str,
        min_size: DisplaySize
    ) -> QGroupBox:
        """
        디스플레이 그룹 생성
        
        Args:
            title: 그룹 제목
            min_size: 최소 디스플레이 크기
        
        Returns:
            생성된 그룹박스
        """
        group = QGroupBox(title)
        layout = QVBoxLayout()
        display_label = VideoDisplayLabel(min_size)
        layout.addWidget(display_label)
        group.setLayout(layout)
        return group

    def update_webcam_display(self, frame: np.ndarray) -> None:
        """
        웹캠 디스플레이 업데이트
        
        Args:
            frame: OpenCV 이미지 프레임
        """
        try:
            qimage = self.image_converter.frame_to_qimage(frame)
            if qimage:
                self.webcam_label.update_display(qimage)
        except Exception as e:
            print(f"웹캠 디스플레이 업데이트 실패: {str(e)}")

    def update_vision_display(self, frame: np.ndarray) -> None:
        """
        Custom Vision 디스플레이 업데이트
        
        Args:
            frame: OpenCV 이미지 프레임
        """
        try:
            qimage = self.image_converter.frame_to_qimage(frame)
            if qimage:
                self.vision_label.update_display(qimage)
        except Exception as e:
            print(f"Vision 디스플레이 업데이트 실패: {str(e)}")

    def clear_displays(self) -> None:
        """모든 디스플레이 초기화"""
        self.webcam_label.clear_display()
        self.vision_label.clear_display()

    def resizeEvent(self, event) -> None:
        """
        창 크기 변경 이벤트
        
        Args:
            event: 리사이즈 이벤트
        """
        super().resizeEvent(event)
        self.webcam_label.update_display()
        self.vision_label.update_display()

    def get_display_sizes(self) -> Tuple[DisplaySize, DisplaySize]:
        """
        현재 디스플레이 크기 반환
        
        Returns:
            (웹캠 디스플레이 크기, Vision 디스플레이 크기)
        """
        return (
            DisplaySize(
                self.webcam_label.width(),
                self.webcam_label.height()
            ),
            DisplaySize(
                self.vision_label.width(),
                self.vision_label.height()
            )
        )