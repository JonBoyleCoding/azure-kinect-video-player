import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Tuple, Optional

import numpy as np


class AzureKinectPlaybackWrapper:
	def __init__(self, video_filename: Path, auto_start: bool = True, realtime_wait: bool = True,
		         rgb: bool = True, depth: bool = True, ir:bool = True):
		"""
		Playback wrapper for the Azure Kinect video files

		:param video_filename: The Kinect video filename
		:param auto_start: Automatically start the playback wrapper (otherwise, call start() to start)
		:param realtime_wait: Wait for the next frame to be displayed, or skip frames if processing is too slow
		"""

		##################################################
		# Check that ffmpeg is installed and in the path #
		##################################################

		# If windows, use where
		if platform.system() == "Windows":
			ffmpeg_path = subprocess.run(["where", "ffmpeg"], stdout=subprocess.PIPE).stdout.decode("utf-8").strip()

		# If linux or mac, use which
		elif platform.system() == "Linux" or platform.system() == "Darwin":
			ffmpeg_path = subprocess.run(["which", "ffmpeg"], stdout=subprocess.PIPE).stdout.decode("utf-8").strip()

		# If not windows, linux, or mac, raise an error
		else:
			raise RuntimeError("Unknown platform: {}".format(platform.system()))

		# If ffmpeg is not found, raise an error
		if not os.path.exists(ffmpeg_path):
			raise RuntimeError("Unable to find ffmpeg in the path. Please install ffmpeg and add it to the path.")

		#########################################################
		# Check that video_filename exists and is an 'mkv' file #
		#########################################################

		if not video_filename.exists():
			raise RuntimeError("Unable to find video file: {}".format(video_filename))

		if video_filename.suffix != ".mkv":
			raise RuntimeError("Video file must be an mkv file: {}".format(video_filename))

		self._video_filename = video_filename

		###############################################
		# Extract the stream info from the video file #
		###############################################

		# Get the stream info
		self._stream_info = _get_stream_info(self._video_filename)

		# Check if there are (at least) 3 streams
		if len(self._stream_info["streams"]) < 3:
			raise RuntimeError("Video file must contain at least 3 streams: {}".format(self._video_filename))

		# Get COLOR, DEPTH, and IR width and height
		self._colour_size = (int(self._stream_info["streams"][0]["width"]), int(self._stream_info["streams"][0]["height"]), 3)
		self._depth_size = (int(self._stream_info["streams"][1]["width"]), int(self._stream_info["streams"][1]["height"]))
		self._ir_size = (int(self._stream_info["streams"][2]["width"]), int(self._stream_info["streams"][2]["height"]))

		# Get the frame rate
		self._frame_rate = float(self._stream_info["streams"][0]["r_frame_rate"].split("/")[0])

		##########################################
		# Calculate the byte size of each stream #
		##########################################

		self._colour_byte_size = self._colour_size[0] * self._colour_size[1] * 3
		self._depth_byte_size = self._depth_size[0] * self._depth_size[1] * 2
		self._ir_byte_size = self._ir_size[0] * self._ir_size[1] * 2

		###################################
		# Create other internal variables #
		###################################

		self._procs = None  # The ffmpeg processes
		self._ready_to_start = True  # Whether the wrapper is ready to start (i.e. the ffmpeg processes have not been created yet)
		self._start_time = None  # The time the wrapper was started
		self._current_frame = 0  # The current frame number

		# Whether to wait for the next frame to be displayed, or skip frames if processing is too slow
		self._realtime_wait = realtime_wait

		# Whether to return the RGB, depth, and IR streams
		self._run_rgb = rgb
		self._run_depth = depth
		self._run_ir = ir

		# If auto_start, start the wrapper
		if auto_start:
			self.start()

	def start(self):
		"""
		Start reading the video file
		"""

		if self._ready_to_start:
			# Create 3 ffmpeg processes for each stream, and store them in self.procs
			# self._procs = [
			# 	subprocess.Popen(
			# 		["ffmpeg", "-i", str(self._video_filename), "-map", "0:0", "-f", "image2pipe", "-pix_fmt", "bgr24",
			# 		 "-vcodec", "rawvideo", "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
			# 		bufsize=self._colour_byte_size),
			# 	subprocess.Popen(
			# 		["ffmpeg", "-i", str(self._video_filename), "-map", "0:1", "-f", "image2pipe", "-pix_fmt",
			# 		 "gray16le", "-vcodec", "rawvideo", "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
			# 		bufsize=self._depth_byte_size),
			# 	subprocess.Popen(
			# 		["ffmpeg", "-i", str(self._video_filename), "-map", "0:2", "-f", "image2pipe", "-pix_fmt",
			# 		 "gray16le", "-vcodec", "rawvideo", "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
			# 		bufsize=self._ir_byte_size)
			# ]

			self._procs = []
			if self._run_rgb:
				self._procs.append(subprocess.Popen(
					["ffmpeg", "-i", str(self._video_filename), "-map", "0:0", "-f", "image2pipe", "-pix_fmt", "bgr24",
					 "-vcodec", "rawvideo", "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
					bufsize=self._colour_byte_size))
			else:
				self._procs.append(None)

			if self._run_depth:
				self._procs.append(subprocess.Popen(
					["ffmpeg", "-i", str(self._video_filename), "-map", "0:1", "-f", "image2pipe", "-pix_fmt",
					 "gray16le", "-vcodec", "rawvideo", "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
					bufsize=self._depth_byte_size))
			else:
				self._procs.append(None)

			if self._run_ir:
				self._procs.append(subprocess.Popen(
					["ffmpeg", "-i", str(self._video_filename), "-map", "0:2", "-f", "image2pipe", "-pix_fmt",
					 "gray16le", "-vcodec", "rawvideo", "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
					bufsize=self._ir_byte_size))
			else:
				self._procs.append(None)

			# Set ready_to_start to False
			self._ready_to_start = False

			# Set start_time to the current time
			self._start_time = time.time()

			# Set frame_count to 0
			self._current_frame = 0

	def grab_frame(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
		"""
		Grab the next frame from the video file

		:return: A tuple containing the colour, depth, and IR frames (in that order) as numpy arrays. If the end of the video file has been reached, all frames will be None.
		"""

		##########################################
		# Check if the wrapper is ready to start #
		##########################################

		# Check that start() has been called
		if self._ready_to_start:
			raise RuntimeError("Must call start() before grab_frame()")

		###########################
		# Start processing frames #
		###########################

		while True:

			def read_frame() -> Tuple[bytes, bytes, bytes]:
				"""
				Read the next frame from the video file

				:return: A tuple containing the colour, depth, and IR frames (in that order) as bytes
				"""

				colour_data = self._procs[0].stdout.read(self._colour_byte_size) if self._run_rgb else None
				depth_data = self._procs[1].stdout.read(self._depth_byte_size) if self._run_depth else None
				ir_data = self._procs[2].stdout.read(self._ir_byte_size) if self._run_ir else None

				return colour_data, depth_data, ir_data

			if self._realtime_wait:
				###########################################################################################
				# If realtime_wait is True, either wait for the next frame, or skip frames if catching up #
				###########################################################################################

				# Calculate the time that the next frame should be displayed
				next_frame_time = self._start_time + (self._current_frame / self._frame_rate)

				# Calculate the current time
				current_time = time.time()

				# Do we need to wait?
				if current_time < next_frame_time:
					# Wait for the next frame
					time.sleep(next_frame_time - current_time)
					colour_data, depth_data, ir_data = read_frame()
					self._current_frame += 1

				# Do we need to skip frames?
				elif current_time > next_frame_time:
					# Skip frames until we are caught up
					while current_time > next_frame_time:
						colour_data, depth_data, ir_data = read_frame()
						self._current_frame += 1
						next_frame_time = self._start_time + (self._current_frame / self._frame_rate)

						# Update current_time
						current_time = time.time()
				else:
					colour_data, depth_data, ir_data = read_frame()
					self._current_frame += 1
			else:
				#######################################################
				# If realtime_wait is False, just read the next frame #
				#######################################################

				colour_data, depth_data, ir_data = read_frame()
				self._current_frame += 1

			##################
			# Error checking #
			##################

			# Check if the data is the correct size
			if (self._run_rgb and len(colour_data) != self._colour_byte_size) or \
					(self._run_depth and len(depth_data) != self._depth_byte_size) or \
					(self._run_ir and len(ir_data) != self._ir_byte_size):

				print("Error: The streamed data is not the correct size. This is likely due to a corrupted video file. Aborting...")
				break

			#################################################
			# Extract the data from the bytes, and yield it #
			#################################################

			# Convert the data to numpy arrays

			colour_image = np.frombuffer(colour_data, dtype=np.uint8).reshape((self._colour_size[1], self._colour_size[0], self._colour_size[2])) if self._run_rgb else None
			depth_image = np.frombuffer(depth_data, dtype=np.uint16).reshape((self._depth_size[1], self._depth_size[0])) if self._run_depth else None
			ir_image = np.frombuffer(ir_data, dtype=np.uint16).reshape((self._ir_size[1], self._ir_size[0])) if self._run_ir else None

			# Return the colour, depth, and ir images
			yield colour_image, depth_image, ir_image

		# Kill the process
		self.stop()

		# Return Empty
		return None, None, None

	def stop(self):
		"""
		Stop the video stream
		"""

		# Check that start() has been called
		if self._ready_to_start:
			return

		# Close the streams and kill the processes
		for proc in self._procs:
			if proc is not None:
				proc.stdout.close()
				proc.kill()

		# Set ready_to_start to True
		self._ready_to_start = True

	def __del__(self):
		"""
		Stop the video stream when the object is deleted
		"""
		self.stop()

	def get_current_frame_number(self):
		"""
		Get the current frame number
		"""
		return self._current_frame


def _get_stream_info(video_filename: Path) -> dict:
	# Get the stream info
	stream_info = subprocess.run(
		["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(video_filename)],
		stdout=subprocess.PIPE).stdout.decode("utf-8")

	# Convert the stream info to a dictionary
	stream_info = json.loads(stream_info)

	return stream_info
