from typing import Optional

import numpy as np


def map_uint16_to_uint8(image: np.ndarray, lower_bound: Optional[int] = 0, upper_bound: Optional[int] = 65535) -> np.ndarray:
	"""
	Map a 16-bit image trough a lookup table to convert it to 8-bit.

	Original code from: https://stackoverflow.com/a/36100507/791025
	Modified to fix bound checks and add type hints.

	Parameters
	----------
	image: numpy.ndarray[np.uint16]
		image that should be mapped
	lower_bound: int, optional
		lower bound of the range that should be mapped to ``[0, 255]``,
		value must be in the range ``[0, 65535]`` and smaller than `upper_bound`
		(defaults to ``numpy.min(image)``)
	upper_bound: int, optional
	   upper bound of the range that should be mapped to ``[0, 255]``,
	   value must be in the range ``[0, 65535]`` and larger than `lower_bound`
	   (defaults to ``numpy.max(image)``)

	Returns
	-------
	numpy.ndarray[uint8]
	"""
	
	# Check bounds are valid
	if lower_bound is not None and not(0 <= lower_bound < 2**16):
		raise ValueError(
			'"lower_bound" must be in the range [0, 65535]')
	if upper_bound is not None and not(0 <= upper_bound < 2**16):
		raise ValueError(
			'"upper_bound" must be in the range [0, 65535]')
	
	# Calculate bounds if necessary
	if lower_bound is None:
		lower_bound = np.min(image)
	if upper_bound is None:
		upper_bound = np.max(image)
	if lower_bound >= upper_bound:
		raise ValueError(
			'"lower_bound" must be smaller than "upper_bound"')
	
	# Convert the image
	lut = np.concatenate([
		np.zeros(lower_bound, dtype=np.uint16),
		np.linspace(0, 255, upper_bound - lower_bound).astype(np.uint16),
		np.ones(2**16 - upper_bound, dtype=np.uint16) * 255
	])
	
	return lut[image].astype(np.uint8)
