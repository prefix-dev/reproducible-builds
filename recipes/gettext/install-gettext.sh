#!/bin/bash

set -euxo pipefail

make install

if [[ "${PKG_NAME}" != "gettext" ]]; then
  rm -rf ${PREFIX}/share/gettext/projects
  rm -rf ${PREFIX}/share/doc/libtextstyle
  rm -rf ${PREFIX}/share/doc/gettext/examples
  rm -rf ${PREFIX}/share/doc/gettext/javadoc2
fi

# This overlaps with readline:
rm -rf ${PREFIX}/share/info/dir

find $PREFIX -name '*.la' -delete
