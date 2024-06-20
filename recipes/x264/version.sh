#!/bin/sh
# hmaarrfk -- July 2022
# Clone from source nad run the version script
# you will notice that there is a space in front
# of X264_VERSION
# Not sure why...
echo "#define X264_REV ${X264_REV}"
echo "#define X264_REV_DIFF 0"
echo "#define X264_VERSION \" ${X264_VERSION}\""
echo "#define X264_POINTVER \"${X264_POINTVER}\""
