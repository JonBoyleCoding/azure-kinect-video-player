# Azure Kinect Playback Wrapper

This project contains a wrapper and a simple player for playing back Azure Kinect recordings. This project does not use the official Azure Kinect SDK, it simply reads the mkv containers recorded by the example application within the SDK.

## Installation instructions

You can either install the package [into your system](#install-the-player-and-the-module-into-your-system) and use it from there, or [include it in your project](#include-as-a-package-into-your-projct).

### Install the player and the module into your system

You can install this directly from git into your local user by the following command:

``` sh
pip install --upgrade git+https://github.com/JonBoyleCoding/python-azure-kinect-video-player.git@v0.2.0
```

(Note: the `--upgrade` flag is provided to ensure that if you upgrade to a newer version it actually does so)

### Include as a package into your project

The following example is for the `poetry` package manager.

``` sh
poetry add git+https://github.com/JonBoyleCoding/python-azure-kinect-video-player.git#v0.2.0
```

To update to a newer version, it is best to remove the package first and reinstall due to an outstanding issue with updating git repositories in `poetry`.

``` sh
poetry remove azure-kinect-video-player
poetry add git+https://github.com/JonBoyleCoding/python-azure-kinect-video-player.git#v0.2.0
```
