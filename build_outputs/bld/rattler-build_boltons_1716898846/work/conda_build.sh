
## Start of bash preamble
if [ -z ${CONDA_BUILD+x} ]; then
    source /Users/graf/projects/oss/reproducible-builds/build_outputs/bld/rattler-build_boltons_1716898846/work/build_env.sh
fi
# enable debug mode for the rest of the script
set -x
## End of preamble

python -m pip install . --no-deps -vv