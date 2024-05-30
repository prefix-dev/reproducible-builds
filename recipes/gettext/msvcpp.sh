#!/bin/sh
# Needed because "windres" can't handle a preprocesser whose invocation is
# more than one word.
exec cl -nologo -E -DRC_INVOKED "$@"
