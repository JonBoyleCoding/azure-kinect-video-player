# Azure Kinect Playback Wrapper

This project contains a wrapper and a simple player for playing back Azure Kinect recordings. This project does not use the official Azure Kinect SDK, it simply reads the mkv containers recorded by the example application within the SDK.

## Installation Instructions

You can either install the package [into your system](#install-the-player-and-the-module-into-your-system) and use it from there, or [include it in your project](#include-as-a-package-into-your-project).

### Install the Player and the Module into your System

You can install this directly from git into your local user by the following command:

``` sh
pip install --upgrade git+https://github.com/JonBoyleCoding/python-azure-kinect-video-player.git@v0.2.1
```

(Note: the `--upgrade` flag is provided to ensure that if you upgrade to a newer version it actually does so)

### Include as a Package into your Project

The following example is for the `poetry` package manager.

``` sh
poetry add git+https://github.com/JonBoyleCoding/python-azure-kinect-video-player.git#v0.2.1
```

To update to a newer version, it is best to remove the package first and reinstall due to an outstanding issue with updating git repositories in `poetry`.

``` sh
poetry remove azure-kinect-video-player
poetry add git+https://github.com/JonBoyleCoding/python-azure-kinect-video-player.git#v0.2.1
```

## Using the Player

`python-azure-kinect-player [OPTIONS] VIDEO_FILENAME`

Arguments:
- `VIDEO_FILENAME`: The video filename (required)

Options:
- `--realtime-wait`/`--no-realtime-wait`: Wait for the next frame to be displayed (default: realtime-wait)
- `--rgb`/`--no-rgb`: Display RGB image (default: rgb)
- `--depth`/`--no-depth`: Display depth image (default: depth)
- `--ir`/`--no-ir`: Display IR image (default: ir)
- `--depth-min INTEGER`: Minimum depth value to display
- `--depth-max INTEGER`: Maximum depth value to display
- `--ir-min INTEGER`: Minimum IR value to display
- `--ir-max INTEGER`: Maximum IR value to display
- `--save-video PATH`: Save combined video to file (specify .mp4 filename)
- `--display-separate-windows`/`--no-display-separate-windows`: Display separate windows for RGB, depth, and IR images (default: no-display-separate-windows)
- `--install-completion [bash|zsh|fish|powershell|pwsh]`: Install completion for the specified shell.
- `--show-completion [bash|zsh|fish|powershell|pwsh]`: Show completion for the specified shell, to copy it or customize the installation.
- `--help`: Show this message and exit.

## Using the Wrapper

This section has the following subsections:

- [Playback Wrapper](#playback-wrapper)
- [Scaling 16-bit Images](#scaling-16-bit-images)

### Playback Wrapper

The wrapper itself can be included as follows:

``` python
from azure_kinect_video_player.playback_wrapper import AzureKinectPlaybackWrapper
```

It contains the following parameters upon construction:

- `video_filename`: The Kinect video filename
- `auto_start`: Automatically start the playback wrapper (otherwise, call start() to start)
- `realtime_wait`: Wait for the next frame to be displayed, or skip frames if processing is too slow
- `rgb`: Whether to load the RGB image
- `depth`: Whether to load the depth image
- `ir`: Whether to load the IR image


Once started (either by `auto-start` parameter or calling `.start()`), the wrapper will open up the video. If `realtime_wait` is `True` then the wrapper will start the timer at that point and present frames with regards to real time passed.

When `.grab_frame()` is called, it will read RGB, DEPTH, and IR images and return them as a tuple in that order. If any of rgb/depth/ir durint construction are `False`, then `None` will be returned instead.

This can be used as follows:

``` python
for colour_image, depth_image, ir_image in playback_wrapper.grab_frame():

    # If all images are None, break (probably reached the end of the video)
    if colour_image is None and depth_image is None and ir_image is None:
        break
```

The provided images are in the following format:

- RGB - is actually loaded as BGR to be compatible with OpenCV
- DEPTH - 16-bit unsigned integer representing millimeter distance of a pixel from the sensor
- IR - 16-bit image from the IR sensor

### Scaling 16-bit Images

If you wish to visualise the results, then you may need to convert the 16-bit images to 8-bit and scale the values to a useful range. This module provides a method for this:

``` python
from azure_kinect_video_player.image_scaler import map_uint16_to_uint8
```

This function takes the following parameters:

- `image`: `numpy.ndarray[np.uint16]` - the image that should be mapped
- `lower_bound`: `int`, optional - the lower bound of the range that should be mapped to `[0, 255]`; value must be in the range `[0, 65535]` and smaller than `upper_bound` (defaults to `numpy.min(image)`)
- `upper_bound`: `int`, optional - the upper bound of the range that should be mapped to `[0, 255]`; value must be in the range `[0, 65535]` and larger than `lower_bound` (defaults to `numpy.max(image)`)

And returns a `numpy.ndarray[uint8]`
