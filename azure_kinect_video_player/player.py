import typer
import cv2
from pathlib import Path
from azure_kinect_video_player.playback_wrapper import AzureKinectPlaybackWrapper
import time
import sys

app = typer.Typer()


@app.command()
def app_main(video_filename: Path = typer.Argument(..., help="The video filename"),
			 realtime_wait: bool = typer.Option(True, help="Wait for the next frame to be displayed")):

	# Get the video filename from the command line
	video_filename = Path(video_filename)

	# Create the playback wrapper
	playback_wrapper = AzureKinectPlaybackWrapper(video_filename, realtime_wait=realtime_wait, auto_start=False)

	# Create windows for the colour, depth, and ir images
	cv2.namedWindow("Colour", cv2.WINDOW_NORMAL)
	cv2.namedWindow("Depth", cv2.WINDOW_NORMAL)
	cv2.namedWindow("IR", cv2.WINDOW_NORMAL)

	# Start timer
	start_time = time.time()
	playback_wrapper.start()

	# Loop through the frames
	for colour_image, depth_image, ir_image in playback_wrapper.grab_frame():

		# Check that the frame is not empty
		if colour_image is None:
			break

		# Display the colour, depth, and ir images
		cv2.imshow("Colour", colour_image)
		cv2.imshow("Depth", depth_image)
		cv2.imshow("IR", ir_image)

		# Wait for key press
		key = cv2.waitKey(1)

		# If q or ESC is pressed, break
		if key == ord("q") or key == 27:
			break

	# Stop timer
	end_time = time.time()

	# Print the time taken
	print("Time taken: {}s".format(end_time - start_time))

	# Close the windows
	cv2.destroyAllWindows()

	# Stop the playback wrapper
	playback_wrapper.stop()

	return 0


if __name__ == "__main__":
	sys.exit(app())
