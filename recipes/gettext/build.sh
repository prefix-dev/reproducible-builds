#!/usr/bin/env bash

set -exuo pipefail

if [[ "$target_platform" == win* ]] ; then
    export PREFIX="$LIBRARY_PREFIX_U"
    export PATH="$PATH_OVERRIDE"
    export BUILD=x86_64-pc-mingw64
    export HOST=x86_64-pc-mingw64

    # Setup needed for autoreconf. Keep am_version sync'ed with meta.yaml.

    am_version=1.15
    export ACLOCAL=aclocal-$am_version
    export AUTOMAKE=automake-$am_version

    # Automake used to automatically deploy the "compile" wrapper script
    # that wrapped MSVC to help it work more like Unix compilers. As of
    # 0.21, we have to provide and use the script ourselves. Ditto for
    # "ar-lib".

    export AR="$RECIPE_DIR/ar-lib lib"
    export CC="$RECIPE_DIR/compile cl.exe -nologo"
    export CPP="cl.exe -nologo -E"
    export CXX="$RECIPE_DIR/compile cl.exe -nologo"
    export CXXCPP="cl.exe -nologo -E"
    export LD="link"
    export NM="dumpbin -symbols"
    export RANLIB=":"
    export STRIP=":"

    # We also need a custom wrapper for `cl -nologo -E` because the
    # invocation of the "windres"/"rc" tool can't handle preprocessor names
    # containing spaces. Windres also breaks if we don't use `--use-temp-file`
    # -- looks like the Cygwin popen() call might not work on Windows.

    export RC="windres --use-temp-file --preprocessor $RECIPE_DIR/msvcpp.sh"
    export WINDRES="windres --use-temp-file --preprocessor $RECIPE_DIR/msvcpp.sh"

    # We need to get the mingw stub libraries that let us link with system
    # DLLs. Stock gettext gets built on Windows so I'm not sure why it doesn't
    # have any needed Windows OS libraries specified anywhere, but it doesn't,
    # so we add them here too.

    export LDFLAGS="${LDFLAGS:-} -L/mingw-w64/x86_64-w64-mingw32/lib -L$PREFIX/lib"

    # We need the -MD flag ("link with MSVCRT.lib"); otherwise our executables
    # can crash with error -1073740791 = 0xC0000409 = STATUS_STACK_BUFFER_OVERRUN
    #
    # But -GL messes up Libtool's identification of how the linker works;
    # it parses dumpbin output and: https://stackoverflow.com/a/11850034/3760486

    export CFLAGS=$(echo "-MD ${CFLAGS:-} " |sed -e "s, [-/]GL ,,")
    export CXXFLAGS=$(echo "-MD ${CXXFLAGS:-} " |sed -e "s, [-/]GL ,,")

    autoreconf -vfi
else
    # Get an updated config.sub and config.guess
   cp $BUILD_PREFIX/share/libtool/build-aux/config.* build-aux/
   export CPP="$CC -E"
fi

./configure \
  --prefix=$PREFIX \
  --build=$BUILD \
  --host=$HOST \
  --disable-static \
  --disable-csharp \
  --disable-dependency-tracking \
  --disable-java \
  --disable-native-java \
  --disable-openmp \
  --enable-fast-install \
  --without-emacs || (cat config.log; cat gettext-runtime/config.log; exit 1)

make -j${CPU_COUNT}

find . -name '*.dll'
