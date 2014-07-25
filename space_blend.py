#################################################################
###Pipeline script to automate flyover creation #################
###Run script on command line with the following command:
###blender -b -P space_blend.py <your_image>.IMG
###For help with commands type:
###blender - b -P space_blend.py --h
#################################################################
import os
from sys import platform as _platform

import bpy
from bpy.props import *
from bpy_extras.io_utils import ImportHelper
from SpaceBlender import blender_module
from SpaceBlender import gdal_module
from SpaceBlender import flyover_module


class SpaceBlender(object):


    def __init__(self, dtm, resolution, flyover_pattern, color_pattern,
                 xyscale, interp,zscale, stars, mist, texture):
        #Set up the default options for the pipeline
        self.filepath = dtm
        self.resolution = resolution
        self.flyover_pattern =  flyover_pattern
        self.color_pattern = color_pattern
        self.scale = xyscale
        self.interp = interp
        self.zscale = zscale
        self.animation = True
        self.stars = stars
        self.mist = mist
        self.texture = texture

        self.pipeline(bpy.types.Operator)

    def pipeline(self, context):
        input_DEM = self.filepath

        #if input_DEM != bpy.path.ensure_ext(input_DEM, ".IMG"):
            #return {'CANCELLED'}
        dtm_location = input_DEM

        texture_location = ''
        merge_location =''
        color_file = ''
        hill_shade = 'hillshade.tiff'
        color_relief = 'colorrelief.tiff'

        project_location = os.path.dirname(__file__)
        ################################################################################
        ## Use the GDAL tools to create hill-shade and color-relief and merge them with
        ## hsv_merge.py to use as a texture for the DTM. Creates DTM_TEXTURE.tiff
        ################################################################################
        if self.texture != None:
            texture_location = os.path.join(os.path.dirname(self.filepath), os.path.basename(self.texture))
        elif self.color_pattern == 'NoColorPattern':
            texture_location=None
        else:
            # If user selected a colr we are going to run the gdal and merge processes
            # We need to dtermine which OS is being used and set the location of color files
            # and the merge script accordingly
            if _platform == "linux" or _platform == "linux2":
            # linux
                    # Strip out the image name to set texture location and append color choice.
                texture_location = self.filepath.split('/')[-1:]
                texture_location = texture_location[0].split('.')[:1]
                texture_location = os.getcwd()+'/'+texture_location[0]+'_'+self.color_pattern+'.tiff'
                color_file = '/usr/share/blender/scripts/addons/SpaceBlender/color_maps/' + self.color_pattern + '.txt'
                merge_location = '/usr/share/blender/scripts/addons/SpaceBlender/hsv_merge.py'
            elif _platform == "darwin":
            # OS X
                        # Strip out the image name to set texture location and append color choice.
                texture_location = self.filepath.split('/')[-1:]
                texture_location = texture_location[0].split('.')[:1]
                texture_location = os.getcwd()+'/'+texture_location[0]+'_'+self.color_pattern+'.tiff'
                color_file = '/Applications/Blender/blender.app/Contents/MacOS/2.70/scripts/addons/SpaceBlender/color_maps/'\
                    + self.color_pattern + '.txt'
                merge_location = '/Applications/Blender/blender.app/Contents/MacOS/2.70/scripts/addons/SpaceBlender/hsv_merge.py'
            elif _platform == "win32":
            # Windows.
                # Strip out the image name to set texture location and append color choice.
                texture_location = self.filepath.split('\\')[-1:]
                texture_location = texture_location[0].split('.')[:1]
                texture_location = os.getcwd()+'\\'+texture_location[0]+'_'+self.color_pattern+'.tiff'
                color_file = '"'+'C:\\Program Files\\Blender Foundation\\Blender\\2.69\\scripts\\addons\\SpaceBlender\\color_maps\\'+self.color_pattern + '.txt'+'"'
                merge_location = '"'+'C:\\Program Files\\Blender Foundation\\Blender\\2.69\scripts\\addons\\SpaceBlender\\hsv_merge.py'+'"'

            gdal = gdal_module.GDALDriver(dtm_location)
            gdal.gdal_hillshade(hill_shade)
            gdal.gdal_color_relief(color_file, color_relief)
            gdal.hsv_merge(merge_location, hill_shade, color_relief, texture_location)

            print('\nSaving texture at: ' + texture_location)
            gdal.gdal_clean_up(hill_shade, color_relief)



        ################################################################################
        ####################Execute DEM Importer and Blender Module#####################
        blender_module.load(self, context,
                            filepath=self.filepath,
                            scale=self.zscale,
                            image_sample=self.scale,
                            interp_method = self.interp,
                            color_pattern=self.color_pattern,
                            flyover_pattern=self.flyover_pattern,
                            texture_location=texture_location,
                            cropVars=False,
                            resolution=self.resolution,
                            stars=self.stars,
                            mist=self.mist,
                            render=True,
                            animation=self.animation)

        return {'FINISHED'}


def main():
    import sys
    import argparse

    argv = sys.argv[4:]


    usage_text = "Run blender in background mode with this script:\n   blender -b -P " + __file__ + " -- [options]"

    parser = argparse.ArgumentParser(description=usage_text)
    parser.add_argument('dtm', help="The input DTM")
    parser.add_argument('-r', '--resolution', dest='resolution', default='720p', help="Output resolution:['180p', '360p', '480p', '720p', '1080p']")
    parser.add_argument('-s', '--scale', dest='scale', type=float, default=0.5, help='Percentage to scale the input image, e.g. 0.5 for 50')
    parser.add_argument('-i', '--interp', dest='interp', default='cubic', help="Interpolation method for xy sampling: ['nearest', 'linear', 'bicubic', 'cubic']")
    parser.add_argument('-z', '--zscale', dest='zscale', type=float, default=1.0, help='Percentage to scale the z dimensions, e.g. 0.5 for 50%')
    parser.add_argument('-f', '--flyover', dest='flyover', default='linear', help="Flyover pattern to use:['noflyover', 'linear', 'circle', 'diamond']")
    parser.add_argument('-c', '--color', dest='color', default='Rainbow_Saturated', help="Color ramp to use:['NoColorPattern','Rainbow_Saturated','Rainbow_Medium','Rainbow_Light','Blue_Steel','Earth','Diverging_BrownBlue','Diverging_RedGray','Diverging_BlueRed','Diverging_RedBrown','Diverging_RedBlue','Diverging_GreenRed','Sequential_Blue','Sequential_Green','Sequential_Red','Sequential_BlueGreen','Sequential_YellowBrown']")
    parser.add_argument('-m', '--mist', dest='mist', action='store_true', help='Render mist (Default: False)')
    parser.add_argument('-a', '--stars', dest='stars', action='store_true', help="Render stars (Default: False)")
    parser.add_argument('-t', '--texture', dest='texture', help='Apply a texture to the input image, e.g. an orthoimage')
    args = parser.parse_args(argv)

    #Render
    sp = SpaceBlender(args.dtm, args.resolution,args.flyover,
                      args.color, args.scale, args.interp, args.zscale,
                      args.stars, args.mist, args.texture)

if __name__ == "__main__":
    main()
