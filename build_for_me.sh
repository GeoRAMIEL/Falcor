# helper script for generating and building Falcor projects
# only use linux-gcc preset

if [ ! -d build ]; then
    mkdir build
fi
# only generate if the build folder for the preset does not exist
if [ ! -d build/linux-gcc ]; then
    cmake --preset linux-gcc
fi

cmake --build --preset linux-gcc-release