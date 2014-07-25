import glob
import os

import bpy
from bpy.props import *
from bpy_extras.io_utils import ImportHelper
from . import blender_module
from . import gdal_module
from . import flyover_module





class UI_Driver(bpy.types.Operator, ImportHelper):
    bl_idname = "import_dem.img"
    bl_label  = "GDAL Importer"
    bl_options = {'UNDO'}



    extensions = ['*.img', '*.tif', '*.tiff', '*.cub', '*.jp2']
    extstring = ";".join(extensions)
    filter_glob = StringProperty(default=extstring, options={'HIDDEN'})


    def listObjects(self, context):
        baseextensions = ['img', 'tif', 'tiff', 'cub', 'jp2']
        #Function used to update the objects list (obj_list) used by the dropdown box.
        objs = [] #list containing tuples of each object
        if self.filepath:
            basepath = os.path.dirname(self.filepath)

            for i,f in enumerate(glob.glob(os.path.dirname(self.filepath) + '/*')):
                try:
                    ext = f.split('.')[1]
                except:
                    continue
                if ext in baseextensions:
                    objs.append((os.path.join(basepath, f), f, "Ortho Layer: {}".format(f)))
        return objs

    #Color Control consider an option to say if you have GDAL installed or not -- possibly detect GDAL
    # Colors to possibly add
    #('BrownAndRedColorPattern', "Brown & Red (Mars)", "Not colorblind friendly")
    #('GrayscaleColorPattern', "Grayscale (8-16 bit grays, Lunar)", "Colorblind friendly")
    #Haven't determined color blindness support
    color_pattern = EnumProperty(items=(
        ('NoColorPattern', "None", "Will skip GDAL execution"),
        ('Rainbow_Saturated', 'Rainbow Saturated', 'Colorblind friendly'),
        ('Rainbow_Medium', 'Rainbow Medium', 'Colorblind friendly'),
        ('Rainbow_Light', 'Rainbow Light', 'Colorblind friendly'),
        ('Blue_Steel', 'Blue Steel', 'Colorblind friendly'),
        ('Earth', 'Earth', 'Colorblind friendly'),
        ('Diverging_BrownBlue', 'Diverging Brown & Blue', 'Colorblind friendly'),
        ('Diverging_RedGray', 'Diverging Red & Gray', 'Colorblind friendly'),
        ('Diverging_BlueRed', 'Diverging Blue & Red', 'Colorblind friendly'),
        ('Diverging_RedBrown', 'Diverging Brown & Red (Mars)', 'Colorblind friendly'),
        ('Diverging_RedBlue', 'Diverging Red & Blue', 'Colorblind friendly'),
        ('Diverging_GreenRed', 'Diverging Green & Red', 'Colorblind friendly'),
        ('Sequential_Blue', 'Sequential Blue', 'Colorblind friendly'),
        ('Sequential_Green', 'Sequential Green', 'Colorblind friendly'),
        ('Sequential_Red', 'Sequential Red', 'Colorblind friendly'),
        ('Sequential_BlueGreen', 'Sequential Blue & Green', 'Colorblind friendly'),
        ('Sequential_YellowBrown', 'Sequential Yellow & Brown', 'Colorblind friendly')),
        name="Color", description="Import Color Texture", default='NoColorPattern')

    #Flyover Pattern Control. Flyover that haven't been implemented yet are commented out.
    flyover_pattern = EnumProperty(items=(
        ('NoFlyover', "No flyover", "Don't ceate a flyover"),
        # ('AlgorithmicPattern', "Algorithmic Pattern", "Automatically create a 'pretty' flyover"),
        ('CirclePattern', "Circle Pattern", "Create a generic circular flyover"),
        # ('OvalPattern', "Oval Pattern", "Create a generic ovular flyover"),
        # ('HourGlassPattern', "Hour Glass Pattern", "Create a generic X like flyover"),
        ('DiamondPattern', "Diamond Pattern", "Create a diagonal flyover"),
        ('LinearPattern', "Linear Pattern", "Create a linear flyover")),
        name="Flyover", description="Import Flyover", default='NoFlyover')


    #Option to add stars to the background of the image
    stars = BoolProperty(name="Apply Stars",
            description="Applies stars to the background",
            default=False
            )

    #Option to add mist to the image
    mist = BoolProperty(name="Apply Mist",
        description="Applies mist to the image",
        default=False
        )


    ortho = BoolProperty(name="Load Ortho",
                         description="Instead of a color, load an orthoimage as a skin",
                         default=False
                         )

    #Render Resolution Lower the resolution the faster the render
    #Listed all popular 16:9 Formats and then a low resolution setting for testing
    resolution = EnumProperty(items=(
        ('1080p', '1080p', '1920×1080p Resolution'),
        ('720p', '720p', '1280×720p Resolution'),
        ('480p', '480p', '854x480p Resolution'),
        ('360p', '360p', '640x360p Resolution'),
        ('180p', '180p', '320x180p Low Res good for testing')),
        name='Resolution', description='Render Resolution', default='720p')

    #Scaling Control
    scale = IntProperty(name="Exaggeration",
                          description="Z Exaggeration Factor",
                          min=1,
                          max=10,
                          soft_min=1,
                          soft_max=100,
                          default=1)

    image_sample = FloatProperty(name='Scale Image',
                              description='Sub (super) sample the image to a given percentage',
                              min= 0.01,
                              max= 2.0,
                              soft_min = 0.015,
                              soft_max = 2.1,
                              default=0.5)

    interp_method = EnumProperty(items=(
        ('Nearest', 'Nearest', 'Nearest Neighbor Interpolation'),
        ('Bilinear', 'Bilinear', 'Bilinear Interpolation'),
        ('Bicubic', 'Bicubic', 'Bicubic Interpolation'),
        ('Cubic', 'Cubic', 'Cubic Interpolation')),
        name='Interp.', description='Sampling Interpolation Method', default='Cubic')

    objectslist = EnumProperty(attr="obj_list", name="Objects", description="Choose object to edit", items=listObjects)

    def draw(self, context):
        """
        Draws and updates the panel in the blender import GUI
        """
        layout = self.layout
        modules = ['image_sample', 'interp_method', 'scale',
                   'color_pattern', 'ortho', 'objectslist',
                   'resolution','flyover_pattern', 'stars', 'mist']
        for m in modules:
            layout.prop(self, m)

    def execute(self, context):
        extensions = ['*.img', '*.tif', '*.tiff', '*.cub']
        input_DEM = self.filepath
        #TODO: This checker is not working for multiple file extensions.
        #for ext in extensions:
            #if input_DEM != bpy.path.ensure_ext(input_DEM, ext):
                #return {'CANCELLED'}
        dtm_location = self.filepath
        dtm_basepath = os.path.dirname(dtm_location)

        project_location = os.path.dirname(__file__)
        ################################################################################
        ## Use the GDAL tools to create hill-shade and color-relief and merge them with
        ## hsv_merge.py to use as a texture for the DTM. Creates DTM_TEXTURE.tiff
        ################################################################################
        if self.ortho == True:
            texture_location = self.objectslist
            print(texture_location)
        elif self.color_pattern == 'NoColorPattern':
            texture_location=None
            pass
        else:
            color_file = os.path.normpath("\"" + project_location + "/color_maps/" + self.color_pattern + ".txt\"")
            merge_location = os.path.normpath("\"" + project_location + "/hsv_merge.py\"")
            texture_location = os.path.normpath(dtm_location + ".tiff")
            hill_shade = os.path.normpath("\""+project_location+"/maps/hillshade.tiff\"")
            color_relief = os.path.normpath("\""+project_location+"/maps/colorrelief.tiff\"")

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
                            scale=self.scale,
                            image_sample=self.image_sample,
                            interp_method = self.interp_method,
                            color_pattern=self.color_pattern,
                            flyover_pattern=self.flyover_pattern,
                            texture_location=texture_location,
                            cropVars=False,
                            resolution=self.resolution,
                            stars=self.stars,
                            mist=self.mist,
                            render=False,
                            animation=False)
        return {'FINISHED'}
