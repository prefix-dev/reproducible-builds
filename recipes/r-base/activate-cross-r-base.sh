if [[ "$CONDA_BUILD" == "" ]]; then
  echo "This package can only be used in conda-build"
  exit 1
fi

if [[ "$CONDA_BUILD_STATE" != "TEST" && "$build_platform" != "$target_platform" ]]; then
  export R=$BUILD_PREFIX/bin/R
  export R_ARGS="--library=$PREFIX/lib/R/library --no-test-load"
  echo "R_HOME=$PREFIX/lib/R"     > $BUILD_PREFIX/lib/R/etc/Makeconf
  cat $PREFIX/lib/R/etc/Makeconf >> $BUILD_PREFIX/lib/R/etc/Makeconf
  if [[ -d $BUILD_PREFIX/lib/R/library ]]; then
    rsync -a -I $BUILD_PREFIX/lib/R/library/ $PREFIX/lib/R/library/
  fi
fi
