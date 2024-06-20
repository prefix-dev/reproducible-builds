if [[ $CONDA_BUILD_CROSS_COMPILATION == "1" ]]; then
    # Get an updated config.sub and config.guess
    cp $BUILD_PREFIX/share/gnuconfig/config.* .
fi
./configure --prefix=$PREFIX
make -j $CPU_COUNT
if [[ $CONDA_BUILD_CROSS_COMPILATION != "1" ]]; then
    make check
fi
make install
