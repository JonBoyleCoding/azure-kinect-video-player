# Python Azure Kinect Video Player Release notes

## 0.2.2

- Fixed OpenCV window display of combination viewer (created 2 windows by accident)
- Some minor readme updates and fixes

## 0.2.1

- Added information on installation and usage to the readme

## 0.2.0

- Updated project executable name from `azure-kinect-video-player` -> `python-azure-kinect-video-player`
- Added pre-commit for YAPF (and YAPF'd the files)
- Added in a combined visualiser with normalisation options, and video writer for visualisation
- Added check for end of video, and getter for frame rate
- Added allows selection of which streams to load

## 0.1.0

- Initial version that displays a Kinect `.mkv` file with each image displayed raw in a separate window.

