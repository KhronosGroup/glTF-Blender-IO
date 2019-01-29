# Setup
* Make sure the submodule at `draco-exporter/draco` is initialized and up to date
* Open a command line at `draco-exporter` and execute the following commands

## Linux
```
mkdir cmake-build-draco
cd cmake-build-draco
cmake ..
make -j 8
sudo cp libblender-draco-exporter.so /usr/lib/
```

## Windows
**TODO**

# Usage
If the setup worked correctly, your should see the draco mesh compression options in the exporter settings.