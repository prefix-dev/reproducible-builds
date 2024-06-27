#!/bin/bash
# Get an updated config.sub and config.guess
set -exo pipefail

if [[ ! $target_platform =~ .*win.* ]]; then
    cp $BUILD_PREFIX/share/gnuconfig/config.* ./tools
fi

export

if [[ ${CONDA_BUILD_CROSS_COMPILATION:-0} == 1 ]]; then
    export r_cv_header_zlib_h=yes
    export r_cv_have_bzlib=yes
    export r_cv_have_lzma=yes
    export r_cv_have_pcre2utf=yes
    export r_cv_have_pcre832=yes
    export r_cv_have_curl722=yes
    export r_cv_have_curl728=yes
    export r_cv_have_curl_https=yes
    export r_cv_size_max=yes
    export r_cv_prog_fc_char_len_t=size_t
    if [[ "${target_platform}" == linux-* ]]; then
      export r_cv_kern_usrstack=no
      export r_cv_search_xdr='none required'
    else
      export r_cv_kern_usrstack=yes
      export r_cv_search_xdr=no
    fi
    export ac_cv_lib_icucore_ucol_open=yes
    export ac_cv_func_mmap_fixed_mapped=yes
    export r_cv_working_mktime=yes
    export r_cv_func_ctanh_works=yes
    export r_cv_prog_fc_cc_compat_complex=yes
    export r_cv_zdotu_is_usable=yes
    # Need to check for openmp simd...
    mkdir -p doc
    (
      export CFLAGS=""

      export CXXFLAGS=""
      export CC=$CC_FOR_BUILD
      export CXX=$CXX_FOR_BUILD
      export AR=$($CC_FOR_BUILD -print-prog-name=ar)
      export F77=${F77//$HOST/$BUILD}
      export F90=${F90//$HOST/$BUILD}
      export F95=${F95//$HOST/$BUILD}
      export FC=${FC//$HOST/$BUILD}
      export GFORTRAN=${FC//$HOST/$BUILD}
      export LD=${LD//$HOST/$BUILD}
      export FFLAGS=${FFLAGS//$PREFIX/$BUILD_PREFIX}
      export FORTRANFLAGS=${FORTRANFLAGS//$PREFIX/$BUILD_PREFIX}
      # Filter out -march=.* from F*FLAGS
      re='\-march\=[^[:space:]]*(.*)'
      if [[ "${FFLAGS}" =~ $re ]]; then
        export FFLAGS="${BASH_REMATCH[1]}${BASH_REMATCH[2]}"
      fi
      re='\-march\=[^[:space:]]*(.*)'
      if [[ "${FORTRANFLAGS}" =~ $re ]]; then
        export FORTRANFLAGS="${BASH_REMATCH[1]}${BASH_REMATCH[2]}"
      fi
      # Filter out -mtune=.* from F*FLAGS
      re='\-mtune\=[^[:space:]]*(.*)'
      if [[ "${FFLAGS}" =~ $re ]]; then
        export FFLAGS="${BASH_REMATCH[1]}${BASH_REMATCH[2]}"
      fi
      re='\-mtune\=[^[:space:]]*(.*)'
      if [[ "${FORTRANFLAGS}" =~ $re ]]; then
        export FORTRANFLAGS="${BASH_REMATCH[1]}${BASH_REMATCH[2]}"
      fi
      export LDFLAGS=${LDFLAGS//$PREFIX/$BUILD_PREFIX}
      export CPPFLAGS=${CPPFLAGS//$PREFIX/$BUILD_PREFIX}
      export NM=$($CC_FOR_BUILD -print-prog-name=nm)
      export PKG_CONFIG_PATH=${BUILD_PREFIX}/lib/pkgconfig
      export CONDA_BUILD_CROSS_COMPILATION=0
      export HOST=$BUILD
      export PREFIX=$BUILD_PREFIX
      export IS_MINIMAL_R_BUILD=1
      # Use the original script without the prepended activation commands.
      /bin/bash ${RECIPE_DIR}/build-r-base.sh
    )
fi

aclocal -I m4
autoconf

# Filter out -std=.* from CXXFLAGS as it disrupts checks for C++ language levels.
re='(.*[[:space:]])\-std\=[^[:space:]]*(.*)'
if [[ "${CXXFLAGS}" =~ $re ]]; then
  export CXXFLAGS="${BASH_REMATCH[1]}${BASH_REMATCH[2]}"
fi

re2='(.*[[:space:]])\-I.*[^[:space:]]*(.*)'
if [[ "${CPPFLAGS}" =~ $re2 ]]; then
  export CPPFLAGS="${BASH_REMATCH[1]}${BASH_REMATCH[2]}"
fi
# if [[ "${CFLAGS}" =~ $re2 ]]; then
#   export CFLAGS="${BASH_REMATCH[1]}${BASH_REMATCH[2]}"
# fi
re3='(.*[[:space:]])\-L.*[^[:space:]]*(.*)'
if [[ "${CPPFLAGS}" =~ $re3 ]]; then
  export CPPFLAGS="${BASH_REMATCH[1]}${BASH_REMATCH[2]}"
fi
# if [[ "${CFLAGS}" =~ $re3 ]]; then
#   export CFLAGS="${BASH_REMATCH[1]}${BASH_REMATCH[2]}"
# fi
# if [[ "${LDFLAGS}" =~ $re3 ]]; then
#   export LDFLAGS="${BASH_REMATCH[1]}${BASH_REMATCH[2]}"
# fi

# Without this, dependency scanning fails (but with it CDT libuuid / Xt fails to link
# which we hack around with config.site)

if [[ "$target_platform" == "win-"* ]]; then
  export CPPFLAGS="${CPPFLAGS} -I$PREFIX/Library/include"
else
  export CPPFLAGS="${CPPFLAGS} -I$PREFIX/include"
fi

export TCL_CONFIG=${PREFIX}/lib/tclConfig.sh
export TK_CONFIG=${PREFIX}/lib/tkConfig.sh
export TCL_LIBRARY=${PREFIX}/lib/tcl8.6
export TK_LIBRARY=${PREFIX}/lib/tk8.6
# BUILD_PREFIX does not get considered for prefix replacement.
[[ -n ${AR} ]] && export AR=$(basename ${AR})
[[ -n ${CC} ]] && export CC=$(basename ${CC})
[[ -n ${GCC} ]] && export GCC=$(basename ${GCC})
[[ -n ${CXX} ]] && export CXX=$(basename ${CXX})
[[ -n ${F77} ]] && export F77=$(basename ${F77})
[[ -n ${FC} ]] && export FC=$(basename ${FC})
[[ -n ${LD} ]] && export LD=$(basename ${LD})
[[ -n ${RANLIB} ]] && export RANLIB=$(basename ${RANLIB})
[[ -n ${STRIP} ]] && export STRIP=$(basename ${STRIP})
export OBJC=${CC}
INSTALL_NAME_TOOL=${INSTALL_NAME_TOOL:-install_name_tool}

Linux() {
    # If lib/R/etc/javaconf ends up with anything other than ~autodetect~
    # for any value (except JAVA_HOME) then 'R CMD javareconf' will never
    # change it, so we prevent configure from finding Java.  post-install
    # and activate scripts now call 'R CMD javareconf'.
    unset JAVA_HOME

    export CPPFLAGS="${CPPFLAGS} -Wl,-rpath-link,${PREFIX}/lib"

    # Make sure curl is found from PREFIX instead of BUILD_PREFIX
    rm -f "${BUILD_PREFIX}/bin/curl-config"

    mkdir -p ${PREFIX}/lib
    # Tricky libuuid resolution issues against CentOS6's libSM. I may need to add some symbols to our libuuid library.
    # Works for configure:
    # . /opt/conda/bin/activate /home/rdonnelly/r-base-bld/_build_env
    # x86_64-conda_cos6-linux-gnu-cc -o conftest -L/home/rdonnelly/r-base-bld/_build_env/x86_64-conda_cos6-linux-gnu/sysroot/usr/lib64 conftest.c -lXt -lX11 -lrt -ldl -lm -luuid -L$PREFIX/lib -licuuc -licui18n
    # if [[ ${ARCH} == 32 ]]; then
    #   export CPPFLAGS="-L${BUILD_PREFIX}/${HOST}/sysroot/usr/lib ${CPPFLAGS}"
    #   export CFLAGS="-I${BUILD_PREFIX}/${HOST}/sysroot/usr/lib ${CFLAGS}"
    #   export CXXFLAGS="-I${BUILD_PREFIX}/${HOST}/sysroot/usr/lib ${CXXFLAGS}"
    # else
    #   export CPPFLAGS="-L${BUILD_PREFIX}/${HOST}/sysroot/usr/lib64 ${CPPFLAGS}"
    #   export CFLAGS="-I${BUILD_PREFIX}/${HOST}/sysroot/usr/lib64 ${CFLAGS}"
    #   export CXXFLAGS="-I${BUILD_PREFIX}/${HOST}/sysroot/usr/lib64 ${CXXFLAGS}"
    # fi
    echo "ac_cv_lib_Xt_XtToolkitInitialize=yes" > config.site
    export CONFIG_SITE=${PWD}/config.site
    if [[ "${IS_MINIMAL_R_BUILD:-0}" == "1" ]]; then
	CONFIGURE_ARGS="--without-x --with-blas=-lblas --with-lapack=-llapack"
    else
	CONFIGURE_ARGS="--with-x --with-blas=-lblas --with-lapack=-llapack"
    fi
    ./configure --prefix=${PREFIX}               \
                --host=${HOST}                   \
                --build=${BUILD}                 \
                --enable-shared                  \
                --enable-R-shlib                 \
                --disable-prebuilt-html          \
                --enable-memory-profiling        \
                --with-tk-config=${TK_CONFIG}    \
                --with-tcl-config=${TCL_CONFIG}  \
                --with-pic                       \
                --with-cairo                     \
                --with-readline                  \
                --with-recommended-packages=no   \
                --without-libintl-prefix         \
		${CONFIGURE_ARGS}                \
		LIBnn=lib || (cat config.log; exit 1)

    if cat src/include/config.h | grep "undef HAVE_PANGOCAIRO"; then
        echo "Did not find pangocairo, refusing to continue"
        cat config.log | grep pango
        exit 1
    fi

    make clean
    make -j${CPU_COUNT} ${VERBOSE_AT}
    # echo "Running make check-all, this will take some time ..."
    # make check-all -j1 V=1 > $(uname)-make-check.log 2>&1 || make check-all -j1 V=1 > $(uname)-make-check.2.log 2>&1

    make install

    # fail if build did not use external BLAS/LAPACK
    if [[ -e ${PREFIX}/lib/R/lib/libRblas.so || -e ${PREFIX}/lib/R/lib/libRlapack.so ]]; then
      echo "Test failed: Detected generic R BLAS/LAPACK"
      exit 1
    fi
    
    # Prevent C and C++ extensions from linking to libgfortran.
    sed -i -r 's|(^LDFLAGS = .*)-lgfortran|\1|g' ${PREFIX}/lib/R/etc/Makeconf

    pushd ${PREFIX}/lib/R/etc
      # See: https://github.com/conda/conda/issues/6701
      chmod g+w Makeconf ldpaths
    popd

    # Remove hard coded paths to these commands in the build machine
    sed -i.bak 's/PAGER=.*/PAGER=${PAGER-less}/g' ${PREFIX}/lib/R/etc/Renviron
    sed -i.bak 's/TAR=.*/TAR=${TAR-tar}/g' ${PREFIX}/lib/R/etc/Renviron
    sed -i.bak 's/R_GZIPCMD=.*/R_GZIPCMD=${R_GZIPCMD-gzip}/g' ${PREFIX}/lib/R/etc/Renviron
    rm ${PREFIX}/lib/R/etc/Renviron.bak
}

# This was an attempt to see how far we could get with using Autotools as things
# stand. On 3.2.4, the build system attempts to compile the Unix code which works
# to an extent, finally falling over due to fd_set references in sys-std.c when
# it should be compiling sys-win32.c instead. Eventually it would be nice to fix
# the Autotools build framework so that can be used for Windows builds too.
Mingw_w64_autotools() {
    unset JAVA_HOME

    mkdir -p ${PREFIX}/lib
    export TCL_CONFIG=${PREFIX}/Library/mingw-w64/lib/tclConfig.sh
    export TK_CONFIG=${PREFIX}/Library/mingw-w64/lib/tkConfig.sh
    export TCL_LIBRARY=${PREFIX}/Library/mingw-w64/lib/tcl8.6
    export TK_LIBRARY=${PREFIX}/Library/mingw-w64/lib/tk8.6
    export CPPFLAGS="${CPPFLAGS} -I${SRC_DIR}/src/gnuwin32/fixed/h"
    if [[ "${ARCH}" == "64" ]]; then
        export CPPFLAGS="${CPPFLAGS} -DWIN=64 -DMULTI=64"
    fi
    ./configure --prefix=${PREFIX}              \
                --host=x86_64-w64-mingw32       \
                --enable-shared                 \
                --enable-R-shlib                \
                --disable-prebuilt-html         \
                --enable-memory-profiling       \
                --with-tk-config=$TK_CONFIG     \
                --with-tcl-config=$TCL_CONFIG   \
                --with-x=no                     \
                --with-readline=no              \
                --with-recommended-packages=no  \
                LIBnn=lib

    make -j${CPU_COUNT} ${VERBOSE_AT}
    # echo "Running make check-all, this will take some time ..."
    # make check-all -j1 V=1 > $(uname)-make-check.log 2>&1
    make install
}

# Use the hand-crafted makefiles.
Mingw_w64_makefiles() {
    local _use_msys2_mingw_w64_tcltk=yes
    local _debug=no

    # Instead of copying a MkRules.dist file to MkRules.local
    # just create one with the options we know our toolchains
    # support, and don't set any
    if [[ "${ARCH}" == "64" ]]; then
        CPU="x86-64"
        HOST="x86_64-w64-mingw32"
    else
        CPU="i686"
        HOST="i686-w64-mingw32"
    fi

    export CPATH=${PREFIX}/Library/include
    export LIBRARY_PATH=${PREFIX}/Library/lib

    # Some hints from https://www.r-bloggers.com/an-openblas-based-rblas-for-windows-64-step-by-step/
    echo "LEA_MALLOC = YES"                              > "${SRC_DIR}/src/gnuwin32/MkRules.local"
    echo "BINPREF = ${HOST}-"                           >> "${SRC_DIR}/src/gnuwin32/MkRules.local"
    echo "BINPREF64 = ${HOST}-"                         >> "${SRC_DIR}/src/gnuwin32/MkRules.local"
    echo "USE_ATLAS = YES"                              >> "${SRC_DIR}/src/gnuwin32/MkRules.local"
    echo "ATLAS_PATH = ${PREFIX}/Library/lib"           >> "${SRC_DIR}/src/gnuwin32/MkRules.local"
    sed -i.bak 's|-lf77blas -latlas|-llapack -lblas|g' src/extra/blas/Makefile.win
    echo "MULTI =   "                                   >> "${SRC_DIR}/src/gnuwin32/MkRules.local"
    # BUILD_HTML causes filenames with special characters to be created, see
    #   https://github.com/conda-forge/r-base-feedstock/pull/177#issuecomment-845279175
    # echo "BUILD_HTML = YES"                            >> "${SRC_DIR}/src/gnuwin32/MkRules.local"
    echo "WIN = ${ARCH}"                                >> "${SRC_DIR}/src/gnuwin32/MkRules.local"
    if [[ "${_debug}" == "yes" ]]; then
        echo "EOPTS = -march=${CPU} -mtune=generic -O0" >> "${SRC_DIR}/src/gnuwin32/MkRules.local"
        echo "DEBUG = 1"                                >> "${SRC_DIR}/src/gnuwin32/MkRules.local"
    else
        # -O3 is used by R by default. It might be sensible to adopt -O2 here instead?
        echo "EOPTS = -march=${CPU} -mtune=generic"     >> "${SRC_DIR}/src/gnuwin32/MkRules.local"
    fi
    echo "OPENMP = -fopenmp"                            >> "${SRC_DIR}/src/gnuwin32/MkRules.local"
    echo "PTHREAD = -pthread"                           >> "${SRC_DIR}/src/gnuwin32/MkRules.local"
    echo "COPY_RUNTIME_DLLS = 1"                        >> "${SRC_DIR}/src/gnuwin32/MkRules.local"
    echo "TEXI2ANY = texi2any"                          >> "${SRC_DIR}/src/gnuwin32/MkRules.local"
    echo "TCL_VERSION = 86"                             >> "${SRC_DIR}/src/gnuwin32/MkRules.local"
    echo "USE_CAIRO = YES"                              >> "${SRC_DIR}/src/gnuwin32/MkRules.local"
    echo "CAIRO_LIBS = \"-lcairo -lfontconfig\""        >> "${SRC_DIR}/src/gnuwin32/MkRules.local"
    echo "USE_LIBCURL = YES"                            >> "${SRC_DIR}/src/gnuwin32/MkRules.local"
    echo "CURL_LIBS = -lcurl"                           >> "${SRC_DIR}/src/gnuwin32/MkRules.local"
    echo "USE_ICU = YES"                                >> "${SRC_DIR}/src/gnuwin32/MkRules.local"
    echo "ICU_PATH = ${PREFIX}/Library/"                >> "${SRC_DIR}/src/gnuwin32/MkRules.local"
    echo "ICU_LIBS = -licuin -licuuc -licudt -L\"${PREFIX}/Library/lib\""        >> "${SRC_DIR}/src/gnuwin32/MkRules.local"
    # This won't take and we'll force the issue at the end of the build* It's not really clear
    # if this is the best way to achieve my goal here (shared libraries, libpng, curl etc) but
    # it seems fairly reasonable all options considered. On other OSes, it's for '/usr/local'
    echo "LOCAL_SOFT = ${PREFIX}/Library/" >> "${SRC_DIR}/src/gnuwin32/MkRules.local"
    sed -i 's|-lwebp ||g' "${SRC_DIR}/src/library/grDevices/src/Makefile.win"
    sed -i 's|-DCURL_STATICLIB ||g' "${SRC_DIR}/src/modules/internet/Makefile.win"
    sed -i 's|-DLZMA_API_STATIC ||g' "${SRC_DIR}/src/library/utils/src/Makefile.win"
    sed -i 's|-DLZMA_API_STATIC ||g' "${SRC_DIR}/src/main/Makefile.win"
    sed -i 's|-DPCRE2_STATIC ||g' "${SRC_DIR}/src/main/Makefile.win"
    # Allow overriding TCL_VERSION
    sed -i 's|TCL_VERSION = 86|TCL_VERSION = 86t|g' "${SRC_DIR}/src/gnuwin32/fixed/etc/Makeconf"

    # R_ARCH looks like an absolute path (e.g. "/x64"), so MSYS2 will convert it.
    # We need to prevent that from happening.
    export MSYS2_ARG_CONV_EXCL="R_ARCH"
    cd "${SRC_DIR}/src/gnuwin32"
    if [[ "${_use_msys2_mingw_w64_tcltk}" == "yes" ]]; then
        # rinstaller and crandir would come after manuals (if it worked with MSYS2/mingw-w64-{tcl,tk}, in which case we'd just use make distribution anyway)
        echo "***** R-${PACKAGE_VERSION} Build started *****"
        for _stage in all cairodevices vignettes manuals; do
            echo "***** R-${PACKAGE_VERSION} Stage started: ${_stage} *****"
            make R_PKGS_RECOMMENDED= ${_stage} -j${CPU_COUNT} || exit 1
        done
    else
        echo "***** R-${PACKAGE_VERSION} Stage started: distribution *****"
        # NOTE: If you want to build the "distribution" target, you have to handle Inno Setup.
        #       I.e., either patch out Inno Setup usage generally or, if that is not possible,
        #       reintroduce Inno Setup download, set ISDIR etc. as done in r-base=4.1.3 builds.
        make distribution -j${CPU_COUNT} || exit 1
    fi
    # The flakiness mentioned below can be seen if the values are hacked to:
    # supremum error =  0.022  with p-value= 1e-04
    #  FAILED
    # Error in dkwtest("beta", shape1 = 0.2, shape2 = 0.2) : dkwtest failed
    # Execution halted
    # .. and testsuite execution is forced with:
    # pushd /c/Users/${USER}/mc3/conda-bld/work/R-revised/tests
    # ~/mc3/conda-bld/work/R-revised/bin/x64/R CMD BATCH --vanilla --no-timing ~/mc3/conda-bld/work/R-revised/tests/p-r-random-tests.R ~/gd/r-language/mingw-w64-p-r-random-tests.R.win.out
    # .. I need to see if this can be repeated on other systems and reported upstream or investigated more, it is very rare and I don't think warrants holding things up.
    # echo "Running make check-all (up to 3 times, there is some flakiness in p-r-random-tests.R), this will take some time ..."
    # make check-all -j1 > make-check.log 2>&1 || make check-all -j1 > make-check.2.log 2>&1 || make check-all -j1 > make-check.3.log 2>&1
    cd installer
    make R_PKGS_RECOMMENDED= imagedir

    # Copied to ${PREFIX}/lib to mirror the unix layout so we can use "noarch: generic" packages for any that do not require compilation.
    mkdir -p "${PREFIX}"/lib
    cp -Rf R-${PKG_VERSION}/. "${PREFIX}"/lib/R

    # We are not using rtools
    for _makeconf in $(find "${PREFIX}"/lib/R -name Makeconf); do
        sed -i 's|R_INSTALLER_BUILD = yes|R_INSTALLER_BUILD = no|g' ${_makeconf}
    done

    return 0
}

Darwin() {
    unset JAVA_HOME
    # Ensure the shared library extension on macOS is also .so
    # for better compatibility with pre-compiled binary macOS packages (similar to wheels in python).
    unset SHLIB_EXT

    # May want to strip these from Makeconf at the end.
    CFLAGS="-isysroot ${CONDA_BUILD_SYSROOT} "${CFLAGS}
    LDFLAGS="-Wl,-dead_strip_dylibs -isysroot ${CONDA_BUILD_SYSROOT} "${LDFLAGS}
    CPPFLAGS="-isysroot ${CONDA_BUILD_SYSROOT} "${CPPFLAGS}

    # Our libuuid causes problems:
    # In file included from qdPDF.c:29:
    # In file included from ./qdPDF.h:3:
    # In file included from ../../../../include/R_ext/QuartzDevice.h:103:
    # In file included from /opt/MacOSX10.9.sdk/System/Library/Frameworks/ApplicationServices.framework/Headers/ApplicationServices.h:23:
    # In file included from /opt/MacOSX10.9.sdk/System/Library/Frameworks/CoreServices.framework/Headers/CoreServices.h:23:
    # In file included from /opt/MacOSX10.9.sdk/System/Library/Frameworks/CoreServices.framework/Frameworks/AE.framework/Headers/AE.h:20:
    # In file included from /opt/MacOSX10.9.sdk/System/Library/Frameworks/CoreServices.framework/Frameworks/CarbonCore.framework/Headers/CarbonCore.h:208:
    # In file included from /opt/MacOSX10.9.sdk/System/Library/Frameworks/CoreServices.framework/Frameworks/CarbonCore.framework/Headers/HFSVolumes.h:25:
    # .. apart from this issue there seems to be a segfault:
    # https://rt.cpan.org/Public/Bug/Display.html?id=104394
    # http://openradar.appspot.com/radar?id=6069753579831296
    # .. anyway, uuid is part of libc on Darwin, so let's just try to use that.
    rm -f "${PREFIX}"/include/uuid/uuid.h

    # Make sure curl is found from PREFIX instead of BUILD_PREFIX
    rm -f "${BUILD_PREFIX}/bin/curl-config"

    ./configure --prefix=${PREFIX}                  \
                --host=${HOST}                      \
                --build=${BUILD}                    \
                --with-sysroot=${CONDA_BUILD_SYSROOT}  \
                --enable-shared                     \
                --enable-R-shlib                    \
                --with-tk-config=${TK_CONFIG}       \
                --with-tcl-config=${TCL_CONFIG}     \
                --with-blas=-lblas                  \
                --with-lapack=-llapack              \
                --enable-R-shlib                    \
                --enable-memory-profiling           \
                --without-x                         \
                --enable-R-framework=no             \
                --with-included-gettext=yes         \
                --with-recommended-packages=no || (cat config.log; false)

    # Horrendous hack to make up for what seems to be bugs (or over-cautiousness?) in ld64's -dead_strip_dylibs (and/or -no_implicit_dylibs)
    sed -i'.bak' 's|-lgobject-2.0 -lglib-2.0 -lintl||g' src/library/grDevices/src/cairo/Makefile
    rm src/library/grDevices/src/cairo/Makefile.bak

    make clean
    if [[ ${CONDA_BUILD_CROSS_COMPILATION:-0} == 1 ]]; then
      cp $BUILD_PREFIX/lib/R/doc/NEWS.rds doc/
      cp $BUILD_PREFIX/lib/R/doc/NEWS.2.rds doc/
      cp $BUILD_PREFIX/lib/R/doc/NEWS.3.rds doc/
      cp $BUILD_PREFIX/share/man/man1/R.1 doc/
      EXTRA_MAKE_ARGS="R_EXE=echo"
    fi
    make -j${CPU_COUNT} ${VERBOSE_AT} ${EXTRA_MAKE_ARGS}
    # echo "Running make check-all, this will take some time ..."
    # make check-all -j1 V=1 > $(uname)-make-check.log 2>&1
    make install ${EXTRA_MAKE_ARGS}

    # fail if build did not use external BLAS/LAPACK
    if [[ -e ${PREFIX}/lib/R/lib/libRblas.dylib || -e ${PREFIX}/lib/R/lib/libRlapack.dylib ]]; then
      echo "Test failed: Detected generic R BLAS/LAPACK"
      exit 1
    fi

    if [[ "$target_platform" == "osx-arm64" ]]; then
      # For backwards compatibility
      ln -sf ${PREFIX}/lib/libblas.dylib ${PREFIX}/lib/R/lib/libRblas.dylib
      ln -sf ${PREFIX}/lib/liblapack.dylib ${PREFIX}/lib/R/lib/libRlapack.dylib
    fi

    pushd ${PREFIX}/lib/R/etc
      sed -i'.bak' -r "s|-isysroot ${CONDA_BUILD_SYSROOT}||g" Makeconf
      sed -i'.bak' -r "s|$BUILD_PREFIX/lib/gcc|$PREFIX/lib/gcc|g" Makeconf
      sed -i'.bak' -r "s|-lemutls_w||g" Makeconf
      rm Makeconf.bak
      # See: https://github.com/conda/conda/issues/6701
      chmod g+w Makeconf ldpaths
    popd
}

if [[ $target_platform =~ .*osx.* ]]; then
  Darwin
  mkdir -p ${PREFIX}/etc/conda/activate.d
  cp "${RECIPE_DIR}"/activate-${PKG_NAME}.sh ${PREFIX}/etc/conda/activate.d/activate-${PKG_NAME}.sh
  mkdir -p ${PREFIX}/etc/conda/deactivate.d
  cp "${RECIPE_DIR}"/deactivate-${PKG_NAME}.sh ${PREFIX}/etc/conda/deactivate.d/deactivate-${PKG_NAME}.sh
elif [[ $target_platform =~ .*linux.* ]]; then
  Linux
  mkdir -p ${PREFIX}/etc/conda/activate.d
  cp "${RECIPE_DIR}"/activate-${PKG_NAME}.sh ${PREFIX}/etc/conda/activate.d/activate-${PKG_NAME}.sh
  mkdir -p ${PREFIX}/etc/conda/deactivate.d
  cp "${RECIPE_DIR}"/deactivate-${PKG_NAME}.sh ${PREFIX}/etc/conda/deactivate.d/deactivate-${PKG_NAME}.sh
elif [[ $target_platform =~ .*win.* ]]; then
  # Mingw_w64_autotools
  Mingw_w64_makefiles
fi

if [[ "$CONDA_BUILD_CROSS_COMPILATION" == "1" ]]; then
  pushd $BUILD_PREFIX/lib/R
  for f in $(find . -type f); do
    if [[ ! -f $PREFIX/lib/R/$f ]]; then
      mkdir -p $PREFIX/lib/R/$(dirname $f)
      cp $f $PREFIX/lib/R/$f
    fi
  done
fi

if [[ -f $PREFIX/lib/R/etc/Makeconf ]]; then
  mv $PREFIX/lib/R/etc/Makeconf .
  echo "R_HOME=$PREFIX/lib/R"   > $PREFIX/lib/R/etc/Makeconf
  cat Makeconf                 >> $PREFIX/lib/R/etc/Makeconf
fi
