import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Tuple, Optional

import numpy as np
import cv2

class FFMPEGVideoWriter:
	def __init__(self, path, framerate: int = 30, encoding_preset: str = "medium", resolution: Tuple[int, int] = (1920, 1080)):
		
		ffmpeg_command = [
			"ffmpeg",
			"-y",
			"-f", "rawvideo",
			"-vcodec", "rawvideo",
			"-s", f"{resolution[0]}x{resolution[1]}",
			"-pix_fmt", "bgr24",
			"-r", str(framerate),
			"-i", "-",
			"-an",
			"-vcodec", "libx264",
			"-preset", encoding_preset,
			path
		]
		
		self._ffmpeg_process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE)
		
	def write_frame(self, frame:np.ndarray):
		"""
		Write a frame to the video file (must be in BGR format)

		:param frame:
		:return:
		"""
		self._ffmpeg_process.stdin.write(frame.tobytes())
		
	def close(self):
		self._ffmpeg_process.stdin.close()
		self._ffmpeg_process.wait()
	
	def __del__(self):
		self.close()
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		self.close()
