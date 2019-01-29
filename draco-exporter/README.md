# Setup
* Make sure `cmake` is installed
* Make sure the submodule at `draco-exporter/draco` is initialized and up to date
* Open a command line at `draco-exporter` and execute the following commands

## Linux/MacOS
```bash
mkdir cmake-build-draco
cd cmake-build-draco
cmake ..
make -j 8
mkdir -p ~/.local/lib/blender2.80
sudo cp libblender-draco-exporter.* ~/.local/lib/blender2.80/
```

## Windows
```bash
mkdir cmake-build-draco
cd cmake-build-draco
cmake .. -G "Visual Studio 15 2017 Win64"
cmake --build . --config Release
```

Copy `Release/blender-draco-exporter.dll` to `C:/Windows/`.

# Usage
If the setup worked correctly, your should see the draco mesh compression options in the exporter settings.
