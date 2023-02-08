import sys
import time
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy
import typer

from azure_kinect_video_player.playback_wrapper import AzureKinectPlaybackWrapper
from azure_kinect_video_player.image_scaler import map_uint16_to_uint8
from azure_kinect_video_player.ffmpeg_video_writer import FFMPEGVideoWriter

app = typer.Typer()


@app.command()
def app_main(video_filename: Path = typer.Argument(..., help="The video filename"),
             realtime_wait: bool = typer.Option(True, help="Wait for the next frame to be displayed"),
             rgb: bool = typer.Option(True, help="Display RGB image"),
             depth: bool = typer.Option(True, help="Display depth image"),
             ir: bool = typer.Option(True, help="Display IR image"),
             depth_min: Optional[int] = typer.Option(None, help="Minimum depth value to display"),
             depth_max: Optional[int] = typer.Option(None, help="Maximum depth value to display"),
             ir_min: Optional[int] = typer.Option(None, help="Minimum IR value to display"),
             ir_max: Optional[int] = typer.Option(None, help="Maximum IR value to display"),
             save_video: Optional[Path] = typer.Option(None, help="Save video to file (specify filename)"),
             display_separate_windows: bool = typer.Option(
                 False, help="Display separate windows for RGB, depth, and IR images")):

	# Get the video filename from the command line
	video_filename = Path(video_filename)

	# Create the playback wrapper
	playback_wrapper = AzureKinectPlaybackWrapper(video_filename,
	                                              realtime_wait=realtime_wait,
	                                              auto_start=False,
	                                              rgb=rgb,
	                                              depth=depth,
	                                              ir=ir)

	# Create windows for the colour, depth, and ir images
	if display_separate_windows:
		if rgb:
			cv2.namedWindow("Colour", cv2.WINDOW_NORMAL)
		if depth:
			cv2.namedWindow("Depth", cv2.WINDOW_NORMAL)
		if ir:
			cv2.namedWindow("IR", cv2.WINDOW_NORMAL)

	# Create a window for the combined images
	cv2.namedWindow(f"Combined Kinect Video: [{video_filename.name}]", cv2.WINDOW_NORMAL)

	# Start timer
	start_time = time.time()
	playback_wrapper.start()

	# Set the min/max values
	visualisation_depth_min_max = (depth_min, depth_max)
	visualisation_ir_min_max = (ir_min, ir_max)

	# If mins/maxes are not specified, determine them from the video
	determine_depth_min = visualisation_depth_min_max[0] is None
	determine_depth_max = visualisation_depth_min_max[1] is None
	determine_ir_min = visualisation_ir_min_max[0] is None
	determine_ir_max = visualisation_ir_min_max[1] is None

	print(f"Auto-determine depth min/max: {determine_depth_min}/{determine_depth_max}")
	print(f"Auto-determine IR min/max: {determine_ir_min}/{determine_ir_max}")

	# If any value is None, set mins to 0 and maxes to 65535
	if visualisation_depth_min_max[0] is None:
		visualisation_depth_min_max = (0, visualisation_depth_min_max[1])
	if visualisation_depth_min_max[1] is None:
		visualisation_depth_min_max = (visualisation_depth_min_max[0], 65535)
	if visualisation_ir_min_max[0] is None:
		visualisation_ir_min_max = (0, visualisation_ir_min_max[1])
	if visualisation_ir_min_max[1] is None:
		visualisation_ir_min_max = (visualisation_ir_min_max[0], 65535)

	# Set the calculated mins/maxes to 0
	calculated_depth_min_max = (65535, 0)
	calculated_ir_min_max = (65535, 0)

	video_writer = None

	try:
		# Loop through the frames
		for colour_image, depth_image, ir_image in playback_wrapper.grab_frame():

			# If we're saving the video, create the video writer
			if save_video is not None and video_writer is None:
				video_writer = initialise_video_writer(save_video, playback_wrapper.get_frame_rate(), colour_image,
				                                       depth_image, ir_image)

			# If all images are None, break (probably reached the end of the video)
			if colour_image is None and depth_image is None and ir_image is None:
				break

			# Determine the min and max values for the depth and ir images (store in calculated_depth_min_max and calculated_ir_min_max)
			# and update the visual min/max values (store in depth_min_max and ir_min_max)
			if depth_image is not None:
				calculated_depth_min_max = update_min_max(depth_image, calculated_depth_min_max)

				visualisation_depth_min_max = update_visual_min_max("Depth", calculated_depth_min_max,
				                                                    visualisation_depth_min_max, determine_depth_min,
				                                                    determine_depth_max)

			if ir_image is not None:
				calculated_ir_min_max = update_min_max(ir_image, calculated_ir_min_max)

				visualisation_ir_min_max = update_visual_min_max("IR", calculated_ir_min_max, visualisation_ir_min_max,
				                                                 determine_ir_min, determine_ir_max)

			# Combine the images
			combined_image = combine_images(colour_image,
			                                depth_image,
			                                ir_image,
			                                depth_min_max=visualisation_depth_min_max,
			                                ir_min_max=visualisation_ir_min_max)
			cv2.imshow(f"Combined Kinect Video: [{video_filename.name}]", combined_image)

			if video_writer is not None:
				video_writer.write_frame(combined_image)

			# Display the colour, depth, and ir images
			if display_separate_windows:
				if rgb and colour_image is not None:
					cv2.imshow("Colour", colour_image)

				if depth and depth_image is not None:
					cv2.imshow("Depth", depth_image)

				if ir and ir_image is not None:
					cv2.imshow("IR", ir_image)

			# Wait for key press
			key = cv2.waitKey(1)

			# If q or ESC is pressed, break
			if key == ord("q") or key == 27:
				break
	except KeyboardInterrupt:
		pass

	# Stop timer
	end_time = time.time()

	# Stop the video writer
	if video_writer is not None:
		video_writer.close()

	# Print the time taken
	print("Time taken: {}s".format(end_time - start_time))

	# Print the min and max values for the depth and ir images
	if visualisation_depth_min_max is not None:
		print("Depth min: {}, max: {}".format(calculated_depth_min_max[0], calculated_depth_min_max[1]))
	if visualisation_ir_min_max is not None:
		print("IR min: {}, max: {}".format(calculated_ir_min_max[0], calculated_ir_min_max[1]))

	# Close the windows
	cv2.destroyAllWindows()

	# Stop the playback wrapper
	playback_wrapper.stop()

	return 0


def initialise_video_writer(video_filename: Path, framerate: int, rgb_image: Optional[numpy.ndarray],
                            depth_image: Optional[numpy.ndarray],
                            ir_image: Optional[numpy.ndarray]) -> FFMPEGVideoWriter:
	width = 0
	height = 0

	# If all images are present
	if rgb_image is not None and depth_image is not None and ir_image is not None:
		# Set the width to max of rgb or combined depth/ir
		width = max(rgb_image.shape[1], depth_image.shape[1] + ir_image.shape[1])

		# Set the height to combined height of rgb and one of depth/ir
		height = rgb_image.shape[0] + max(depth_image.shape[0], ir_image.shape[0])

	# If only rgb and (depth or ir) are present
	elif rgb_image is not None and (depth_image is not None or ir_image is not None):
		used_image = depth_image if depth_image is not None else ir_image

		# Width is rgb width
		width = rgb_image.shape[1]

		# Height is rgb height + depth/ir height
		height = rgb_image.shape[0] + used_image.shape[0]
	# If only depth and ir are present
	elif depth_image is not None and ir_image is not None:
		# Width is combined depth/ir width
		width = depth_image.shape[1] + ir_image.shape[1]

		# Height is depth/ir height
		height = depth_image.shape[0]
	# If only one image is present
	else:
		used_image = rgb_image if rgb_image is not None else depth_image if depth_image is not None else ir_image

		# Width is image width
		width = used_image.shape[1]

		# Height is image height
		height = used_image.shape[0]

	# Create the video writer
	video_writer = FFMPEGVideoWriter(video_filename, framerate=framerate, resolution=(width, height))

	return video_writer


def update_min_max(image: numpy.ndarray, min_max: Tuple[int, int]) -> Tuple[int, int]:
	"""
	Update the min and max values for the image

	:param image:
	:param min_max:
	:return:
	"""

	# Copy the min_max tuple
	min_max = (min_max[0], min_max[1])

	# If the image is None, return the min_max
	if image is None:
		return min_max

	# Get the min and max values for the image
	image_min = numpy.min(image)
	image_max = numpy.max(image)

	# If the image min is less than the current min, update the min
	if image_min < min_max[0]:
		min_max = (image_min, min_max[1])

	# If the image max is greater than the current max, update the max
	if image_max > min_max[1]:
		min_max = (min_max[0], image_max)

	return min_max


def update_visual_min_max(output_str: str, calculated_min_max: Tuple[int, int], min_max: Tuple[int, int],
                          determine_min: bool, determine_max: bool) -> Tuple[int, int]:
	"""
	Update the min and max values for the visualisation

	:param output_str:
	:param calculated_min_max:
	:param min_max:
	:param determine_min:
	:param determine_max:
	:return:
	"""

	# Copy the min_max tuple
	min_max = (min_max[0], min_max[1])

	# Determine if the min and max values have changed
	if determine_min and calculated_min_max[0] != min_max[0]:
		print(f"{output_str} min: {calculated_min_max[0]}")
		min_max = (calculated_min_max[0], min_max[1])
	if determine_max and calculated_min_max[1] != min_max[1]:
		print(f"{output_str} max: {calculated_min_max[1]}")
		min_max = (min_max[0], calculated_min_max[1])

	return min_max


def combine_images(rgb: Optional[numpy.ndarray],
                   depth: Optional[numpy.ndarray],
                   ir: Optional[numpy.ndarray],
                   depth_min_max: Optional[Tuple[int, int]] = None,
                   ir_min_max: Optional[Tuple[int, int]] = None) -> numpy.ndarray:
	"""
	Combine the RGB, depth, and IR images into one image

	:param rgb:
	:param depth:
	:param ir:
	:param depth_min_max:
	:param ir_min_max:
	:return:
	"""

	# Clone the images to ensure the originals are not modified
	if rgb is not None:
		rgb = rgb.copy()
	if depth is not None:
		depth = depth.copy()
	if ir is not None:
		ir = ir.copy()

	# If all images are None, throw an error
	if rgb is None and depth is None and ir is None:
		raise ValueError("All images are None")

	# If all 3 images are not None, combine them into one image with rgb on the top, and depth and ir on the bottom
	if rgb is not None and depth is not None and ir is not None:
		# Convert the depth and ir images to 8-bit (downscale from 16-bit) and convert to BGR
		depth = map_uint16_to_uint8(depth, depth_min_max[0], depth_min_max[1])
		depth = cv2.cvtColor(depth, cv2.COLOR_GRAY2BGR)

		ir = map_uint16_to_uint8(ir, ir_min_max[0], ir_min_max[1])
		ir = cv2.cvtColor(ir, cv2.COLOR_GRAY2BGR)

		# Determine the width of the image
		width = max(rgb.shape[1], depth.shape[1] + ir.shape[1])

		# Create a new image
		image = numpy.zeros((rgb.shape[0] + depth.shape[0], width, 3), dtype=numpy.uint8)

		# Copy the rgb image to the top of the image (centre it)
		image[:rgb.shape[0], (width - rgb.shape[1]) // 2:(width - rgb.shape[1]) // 2 + rgb.shape[1]] = rgb

		# Copy the depth image to the bottom left of the image
		image[rgb.shape[0]:, :depth.shape[1]] = depth

		# Copy the ir image to the bottom right of the image (if the width is more than both images, ensure a gap)
		image[rgb.shape[0]:, width - ir.shape[1]:] = ir

		return image

	# If rgb and one of depth or ir are not None, combine them into one image with rgb on the top, and depth or ir on the bottom (centred)
	if rgb is not None and (depth is not None or ir is not None):
		# Convert the depth or ir images to 8-bit (downscale from 16-bit) and convert to BGR
		if depth is not None:
			used_image = map_uint16_to_uint8(depth, depth_min_max[0], depth_min_max[1])
		else:
			used_image = map_uint16_to_uint8(ir, ir_min_max[0], ir_min_max[1])

		used_image = cv2.cvtColor(used_image, cv2.COLOR_GRAY2BGR)

		# Create a new image
		image = numpy.zeros((rgb.shape[0] + used_image.shape[0], max(rgb.shape[1], used_image.shape[1]), 3),
		                    dtype=numpy.uint8)

		# Copy the rgb image to the top of the image
		image[:rgb.shape[0],
		      (image.shape[1] - rgb.shape[1]) // 2:(image.shape[1] - rgb.shape[1]) // 2 + rgb.shape[1]] = rgb

		# Copy the depth or ir image to the bottom of the image
		image[rgb.shape[0]:, (image.shape[1] - used_image.shape[1]) // 2:(image.shape[1] - used_image.shape[1]) // 2 +
		      used_image.shape[1]] = used_image

		return image

	# If depth and ir are not None, combine them into one image with depth on the left, and ir on the right
	if depth is not None and ir is not None and rgb is None:
		# Convert the depth and ir images to 8-bit (downscale from 16-bit) and convert to BGR
		depth = map_uint16_to_uint8(depth, depth_min_max[0], depth_min_max[1])
		depth = cv2.cvtColor(depth, cv2.COLOR_GRAY2BGR)

		ir = map_uint16_to_uint8(ir, ir_min_max[0], ir_min_max[1])
		ir = cv2.cvtColor(ir, cv2.COLOR_GRAY2BGR)

		# Determine the width of the image
		width = depth.shape[1] + ir.shape[1]

		# Create a new image
		image = numpy.zeros((depth.shape[0], width, 3), dtype=numpy.uint8)

		# Copy the depth image to the left of the image
		image[:, :depth.shape[1]] = depth

		# Copy the ir image to the right of the image
		image[:, depth.shape[1]:] = ir

		return image

	# Otherwise (should only be one image), return that image
	if rgb is not None:
		return rgb
	if depth is not None:
		return depth
	if ir is not None:
		return ir


if __name__ == "__main__":
	sys.exit(app())
