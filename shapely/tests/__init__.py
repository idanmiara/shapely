import os
import sys
import unittest  # NOQA

if os.name == "nt" and sys.version_info[1] >= 8:
    geos_path = os.environ.get("GEOS_INSTALL")
    if geos_path:
        os.add_dll_directory(geos_path + r"\bin")


import numpy
import pytest

from shapely.geos import geos_version_string

# Show some diagnostic information; handy for CI
print("Python version: " + sys.version.replace("\n", " "))
print("GEOS version: " + geos_version_string)
print("Numpy version: " + numpy.version.version)


shapely20_deprecated = pytest.mark.filterwarnings(
    "ignore::shapely.errors.ShapelyDeprecationWarning"
)
