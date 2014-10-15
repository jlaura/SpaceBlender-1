#SpaceBlender


Space Blender is a Blender plugin designed to generate flyover DTM videos from a 32-bit digital elevation model.

##Requirements
Space Blender has the following dependencies:

1. The Geospatial Data Abstraction Library (GDAL)
2. NumPy
3. SciPy

These dependencies must be installed within the blender shipped version of Python 3.3.  See the installation section for instructions on meeting these dependencies

##Command line Quick-Start
For this quickstart, we make the assumption that Blender is already installed and accessible via the command line as `blender`.  If this is not the case, see installation (below).


First, we will print the usage statement for the space blender command line tool:

`blender -b -P space_blend.py`

This will return:

```
usage: blender [-h] [-r RESOLUTION] [-s SCALE] [-i INTERP] [-z ZSCALE] [-f FLYOVER] [-c COLOR] [-m] [-a] [-t TEXTURE] dtm
```
where:

* `-h` Display the blender help documentation.
* `-r` The the output resolution select from: ['180p', '360p', '480p', '720p', '1080p'].  720p is the default.
* `-s` A scaling factor, between 0 and 1 used to scale the input image in the x and y directions.
* `-i` The interpolation method used if a scaling factor is defined.  Selected from ['nearest', 'linear', 'bicubic', 'cubic'] with the default being cubic.
* `-z' The z direction scaling factor as a floating point number, e.g. 1.5 for a one and a half time vertical exaggeration.
* `-f` The flyover type selection from: ['noflyover', 'linear', 'circle', 'diamond'].  Linear is the default.
* `-c` The colormap to use to colorize the DTM selected from: ['NoColorPattern','Rainbow_Saturated','Rainbow_Medium','Rainbow_Light','Blue_Steel','Earth','Diverging_BrownBlue','Diverging_RedGray','Diverging_BlueRed','Diverging_RedBrown','Diverging_RedBlue','Diverging_GreenRed','Sequential_Blue','Sequential_Green','Sequential_Red','Sequential_BlueGreen','Sequential_YellowBrown'].  The default is 'Rainbow_Saturated'
*  `-m` A boolean flag defining whether mist is rendered.
*  `-a` A boolean flag defining whether stars are rendered.
*  `-t` A texture applied to the input image, e.g. an orthoimage.

###Example usage:
While the usage examples all assume a mythical DEM 'inputdem.IMG', it is possible to use any GDAL support input data type.  The development team has tested Space Blender using `.IMG` and `.tif` file formats.

* Render a default flyover image at low spatial resolution and the lowest possible rendering resolution.  This is an ideal way to test your installation.

```
blender -b -P space_blend.py -s 0.1 -r 180p inputdem.IMG
```

* Render the same, but at full spatial and rendering resolution

```
blender -b -P space_blend.py -s inputdem.IMG
```

##Installation
The development team utilizes [Anaconda Python] (http://continuum.io/downloads) as their default python installation in part because of the ease of external package installation.  The installation described below makes use of Anaconda Python and replaces the python 3.3 that ships with Blender with an Anaconda installation.  This has been tested on Mac OS X and Scientific Linux.

* Download and install Anaconda Python.
*  At the time of the last update to this ReadMe, Blender was using Python version 3.3.5.  So, we will create a virutal environment that mirrors the Blender installation:

```
conda create -n blenderpython -p PATH_TO_INSTALL_DIRECTORY python=3.3 anaconda
```
where PATH\_TO\_INSTALL\_DIRECTORY is the location where the python 3.3 folder will be created.
* Activate the Python 3.3 environment and perform the necessary software installations.

```
source activate blenderpython
conda install gdal
```
* Navigate to the blender directory.  Within that directory, a subdirectory exists names as the version of Blender installed.  On OSX, one can open the blender application folder, `View Package Contents` on the blender application, then enter `MacOS > Version`.  Within thius directory is a directory called `python`.
* Rename the `python` directroy to `python_backup`.  This ensures that we can rollback from the changes to be made.
* Create a new directory named `python`.
* Copy the contents of the spaceblender python directory (created above) into the newly created python directory.  Top-level directories within the `python` directory should include: bin, conda-meta, docs, Examples, include, lib, share.


