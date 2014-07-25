# ##### BEGIN GPL LICENSE BLOCK #####
#
#	This program is free software; you can redistribute it and/or
#	modify it under the terms of the GNU General Public License
#	as published by the Free Software Foundation; either version 2
#	of the License, or (at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with this program; if not, write to the Free Software Foundation,
#	Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import os
from sys import platform as _platform

import numpy as np

import bpy
import bmesh
from bpy.ops import *

from . import flyover_module as flyover
from . import gdalio

flyovers = {'linear':'LinearPattern'}

def placeobj(mesh, objname):
    """
    Place an object into the scene

    Parameters
    -----------
    mesh    (bmesh) Blender mesh object
    objname (str) Name of the object

    Returns
    -------
    obj     (obj) The object added to the scene
    """
    bpy.ops.object.select_all(action='DESELECT')
    mesh = bpy.data.objects.new(objname, mesh)
    bpy.context.scene.objects.link(mesh)
    bpy.context.scene.update()
    bpy.context.scene.objects.active = mesh
    mesh.select = True
    return mesh

class DTMViewerRenderContext:
    """
     This clears the scene and creates:
       1 DTM Mesh (using the hirise_dtm_importer class above)
       1 Lamp (Sun)
       1 Camera
       1 Empty (CameraTarget)
    """
    render_save_path = ''

    def __init__(self, filepath, dtm_resolution, dtm_stars, dtm_mist,
                 dtm_texture=None, dtm_flyover=None,
                 image_sample = 1.0,
                 interp_method = None,
                 zscale = 1.0,
                 importmode='DTM',
                 drapetarget=None):

        self.filepath = filepath
        self.texture = dtm_texture
        self.__resolution = dtm_resolution
        self.__stars = dtm_stars
        self.__mist = dtm_mist
        self.__flyover = dtm_flyover
        self.getflyover()
        self.image_sample = image_sample
        self.interp_method = interp_method
        self.zscale = zscale
        self.import_mode = importmode
        self.obj = drapetarget

        print(self.__flyover)

    def getflyover(self):
        if self.__flyover in flyovers.keys():
            self.__flyover = flyovers[self.__flyover]


    def createDefaultContext(self):
        ''' clears the current scene and fills it with a DTM '''
        if self.import_mode == 'DTM':
            self.clearScene()
            self.addDTM()
            self.setupRender(self.__resolution)
            self.setupLightSource()
            self.cleanupView()
            self.create_flyover_path()
        else:
            self.addSkin()

    # Clear the scene by removing all objects/materials
    def clearScene(self):
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()
        for mat in bpy.data.materials:
            bpy.data.materials.remove(mat)

    def setupLightSource(self):
        # The default "SUN" points straight down, which is fine for our needs
        bpy.ops.object.lamp_add(type='SUN')
        sun = bpy.data.objects['Sun']
        print(self.dtm_min_v, self.dtm_max_v)
        sun.location = (self.dtm_min_v[0]+self.delta_v[0]/2, self.dtm_min_v[1]+self.delta_v[1]/2, self.dtm_max_v[2]+1000)

    # Set the rendering defaults
    # Set up render in all popular 16:9 Formats and then a low resolution setting for testing
    def setupRender(self, resolution):
        """
        Set the render defaults

        Parameters
        -----------
        Resolution      (str) 16:9 resolution (180p, 360p, 480p, 720p, 1080p)
        """
        render = bpy.context.scene.render
        # Don't bother raytracing since we will likely put a real image on the
        # mesh that already contains shadows
        render.use_raytrace = False
        #default resolution is 1080p
        render.resolution_x = 1920
        render.resolution_y = 1080

        if resolution == '720p':
            render.resolution_x = 1280
            render.resolution_y = 720
        if resolution == '480p':
            render.resolution_x = 854
            render.resolution_y = 480
        if resolution == '360p':
            render.resolution_x = 640
            render.resolution_y = 360
        if resolution == '180p':
            render.resolution_x = 320
            render.resolution_y = 180

        render.resolution_percentage = 100

    def addSkin(self):
        """
        Drape an image over a DTM mesh

        TODO: Drape an ortho over the mesh
        """
        print("Preparing to drape image")
        #Replace the previous drape
        scn = bpy.context.scene
        obj = scn.objects[self.obj]
        obj.select = True
        scn.objects.active = obj
        boy.ops.object.transform_apply(rotation=True, scale=True)
        loc = obj.location
        mesh = obj.data

        previousmap = mesh.uv_textures.active
        uvtxtlayer = mesh.uv_textures.new('DTMskin')

        drapeimg = gdalio.ReadGDAL(self.filepath)

        #Lay the image over the existing mesh faces
        for i, face in enumerate(mesh.polygons):
            uvtxtlayer.data[i].image = img

        uvlooplayer = mesh.uv_layers.active
        for i in mesh.polygons:
            for j in i.loop_indices:
                vertidx = mesh.loops[j]
                pt = list(mesh.vertices[vertidx].co)
                pt = None

    def addDTM(self):
        print("Extracting vertices and faces from the supplied DTM")

        bpy.ops.object.transform_apply(rotation=True, scale=True)

        self.basedem = gdalio.ReadGDAL(self.filepath)
        self.basedem.resize(percentage_reduction=self.image_sample,
                              interpolation=self.interp_method)

        #Setup the mesh
        meshname = self.basedem.name
        bm = bmesh.new()
        mesh = bpy.data.meshes.new(meshname)

        #Create a material and texture
        material = bpy.data.materials.new(name="DTMSurface")
        material.specular_intensity = 0.0
        material.diffuse_intensity = 0.0
        material.use_shadeless = True

        if self.texture is not None:
            texture = bpy.data.textures.new(name="DTMTexture", type='IMAGE')
            try:
                bpy.ops.file.make_paths_absolute()
                bpy.ops.file.pack_all()
                texture.image = bpy.data.images.load(self.texture)
                bpy.ops.image.pack()
            except:
                raise NameError("Could not load the texture (image)", self.texture)
        else:
            texture = bpy.data.textures.new(name='DTMTexture', type='BLEND')

        meshtexture = material.texture_slots.add()
        meshtexture.texture = texture
        meshtexture.color=(0.0, 0.0, 0.0)
        #Process the DTM to extract vertices and generate faces
        #Setup the xy grid
        xsize = self.basedem.arr.shape[1]
        ysize = self.basedem.arr.shape[0]

        #Scaling information
        xscale = abs(self.basedem.worldfile['xpixelsize'])
        yscale = abs(self.basedem.worldfile['ypixelsize'])
        xyzratio = 1 / xscale  # Hard coded to z is in meter units
        xyzratio *= self.image_sample

        #x, y, z vectors stacked to 3d arr
        x,y = np.meshgrid((np.arange(xsize)), (np.arange(ysize)))

        #Exaggerate the z
        self.basedem.scale(self.zscale)
        z = self.basedem.arr
        z *= xyzratio
        z = np.flipud(z)
        #Scale the z to match the xy ratio
        #z *= (1 / (xscale * self.image_scale))

        zmin = np.nanmin(z)
        zmax = np.nanmax(z)

        #Shift the points to center the image on the blender origin (0,0,0)
        self.basedem.getpixelextent(x, y)
        self.basedem.getpixelcenter()
        center = self.basedem.pixelcenter

        self.blender_xoffset = center[0]
        self.blender_yoffset = center[1]


        x -= self.blender_xoffset
        y -= self.blender_yoffset
        z -= center[2]
        self.basedem.pixelcenter[2] = np.nanmean(z)


        verts_ar = np.hstack((x.reshape(-1,1),
                              y.reshape(-1,1),
                              z.reshape(-1,1)))

        verts = verts_ar.tolist()
        #generate the faces
        vertcount = xsize * ysize
        idx_ar = np.arange((ysize-1)*(xsize))
        idx_truth = (idx_ar + 1) % xsize != 0
        v_idx = idx_ar[idx_truth].reshape(-1, 1)

        faces_ar = np.hstack((v_idx + xsize,
                        v_idx + xsize + 1,
                        v_idx + 1,
                        v_idx))
        faces = faces_ar.tolist()

        #Create the mesh from the verts and faces
        mesh.from_pydata(verts, [], faces)
        mesh.update(calc_edges=True)

        #Capture the min and max values to position the sun
        self.dtm_min_v = (np.nanmin(x), np.nanmin(y), np.nanmin(z))
        self.dtm_max_v = (np.nanmax(x), np.nanmax(y), np.nanmax(z))
        self.delta_v = tuple(map(lambda a, b: a - b, self.dtm_max_v, self.dtm_min_v))

        #self.set_latlon_bounds(self.basedem)

        #Place the mesh in the scene and add the texture
        mesh = placeobj(mesh, meshname)
        bpy.ops.object.select_pattern(pattern=meshname)
        mesh.data.materials.append(material)

        #Adjust the view
        self.adjustview(self.basedem)

        return {"FINISHED"}

    def adjustview(self, rasterimporter):
        """
        Adjust the view to center on the georeferenced image

        Parameters
        ----------
        rasterimporter (obj) A gdalio object
        """
        ri = rasterimporter
        bnds = map
        maxdistance = round(max(map(abs, [ri.minlat, ri.minlon,
                                          ri.maxlat, ri.maxlon]))) * 2
        nbdig = len(str(maxdistance))
        scale = 10 ** (nbdig - 2)
        nblines = round(maxdistance / scale)

        targetdistance = nblines * scale
        areas = bpy.context.screen.areas
        for area in areas:
            if area.type == 'VIEW_3D':
                space = area.spaces.active
                if space.grid_lines * space.grid_scale < targetdistance:
                    space.grid_lines = nblines
                    space.grid_scale = scale
                    space.clip_end = targetdistance * 10

    def set_latlon_bounds(self, rasterimporter):
        """
        Using the georeferencing information, compute the bounds
        of the scene

        Parameters
        ----------
        rasterimporter  (obj) A gdalio object
        """
        scene = bpy.context.scene
        if not 'latitude' in scene.keys():
            ri = rasterimporter
            scene['latitude'] = (ri.minlat - ri.maxlat) / 2.0
            scene['longitude'] = (ri.minlon - ri.maxlon) / 2.0
        else:
            return

    def createStars(self):
        """
        Add stars to the background.
        """
        print("Adding stars to background...")
        world = bpy.context.scene.world
        #Set the background to black
        world.horizon_color = (0.0, 0.0, 0.0)
        #Set Zenith to gray
        world.zenith_color = (0.040, 0.040, 0.040)
        world.use_sky_paper = True
        world.use_sky_blend = True
        world.use_sky_real = True
        #Adjust the size of the stars and turn them on
        world.star_settings.size = 0.25
        world.star_settings.use_stars = True
        print("Stars applied successfully")

    def createMist(self):
        """
        Add mist over the DTM surface
        """
        print("Applying mist...")
        #set general colors for background and mist
        world = bpy.context.scene.world
        world.horizon_color = (0.0, 0.0, 0.0)
        world.zenith_color = (0.040, 0.040, 0.040)
        world.use_sky_paper = True
        world.use_sky_blend = True
        world.use_sky_real = True

        mist = bpy.context.scene.world.mist_settings
        mist.use_mist = True
        mist.start = 1.0
        mist.depth = 100 - min(abs(self.__dtm_min_v[0]-self.__dtm_max_v[0])/2,
                               abs(self.__dtm_min_v[1]-self.__dtm_max_v[1])/2)
        mist.height = max(self.__dtm_max_v[2] - 5, 0)
        mist.intensity = 0.15
        print("Mist applied successfully")

    def create_flyover_path(self):
        """
        Create the FlyOver path for the camera
        """
        if self.__flyover == "NoFlyover":
            print("Skipping flyover")
            flyover.no_flyover(self)
        elif self.__flyover == "CirclePattern":
            print("Creating circular flyover pattern...")
            flyover.circle_pattern(self)
            print("Circular flyover pattern created")
        elif self.__flyover == "DiamondPattern":
            print("Creating diamond flyover pattern...")
            flyover.diamond_pattern()
            print("Diamond flyover pattern created")
        elif self.__flyover == "LinearPattern":
            print("Creating linear flyover pattern...")
            flyover.linear_pattern(self)
            print("Linear flyover pattern created")

    def auto_render(self, animation, resolution='1080p'):
        """
        Called when the function is used via the commandline to automate the
        flyover generation process.

        Parameters
        ----------
        animation       (boolean?)
        resolution      (str) 16:9 resolution
        """
        #This assumes only one camera in the scene.
        bpy.context.scene.camera = bpy.data.objects['Camera']
        self.setupRender(resolution)
        if animation:
            bpy.data.scenes["Scene"].render.filepath = os.getcwd()+'/'+\
                DTMViewerRenderContext.render_save_path[0]
            bpy.ops.render.render(animation=True)
        else:
            bpy.data.scenes["Scene"].render.filepath = os.getcwd()+'/'+\
                DTMViewerRenderContext.render_save_path[0]
            bpy.ops.render.render(animation=False, write_still=True)

    def cleanupView(self):
        ## Can't align view because there is no pane to apply the view
        #bpy.ops.view3d.view_all(center=True)
        bpy.ops.object.select_pattern(pattern=self.basedem.name)


    def saveAs(self, path):
        bpy.ops.wm.save_as_mainfile(filepath=path, check_existing=False)


def load(operator, context, filepath, scale, image_sample, interp_method,
         color_pattern, flyover_pattern, texture_location, cropVars,
         resolution, stars, mist, render, animation):
    """
    Called by ui_module to fire off an import
    """
    print("Sampling Perc.: %s" % image_sample)
    print("Scale: %f" % scale)
    print("Color Mapping: %s" % color_pattern)
    print("Flyover Mode: %s" % flyover_pattern)

    #Strip out the image name for saving later as .blend file
    if _platform == "win32":
        save_path = filepath.split('\\')[-1:]
        save_path = save_path[0].split('.')[:1]
        DTMViewerRenderContext.render_save_path = save_path
        save_path = os.getcwd()+'\\'+save_path[0]+'.blend'
        print('Processing image, saving at: ' + save_path)
    else:
        save_path = filepath.split('/')[-1:]
        save_path = save_path[0].split('.')[:1]
        DTMViewerRenderContext.render_save_path = save_path
        save_path = os.getcwd()+'/'+save_path[0]+'.blend'
        print('Processing image, saving at: ' + save_path)

    newScene = DTMViewerRenderContext(filepath,resolution, stars, mist,
                                  dtm_texture = texture_location,
                                  dtm_flyover = flyover_pattern,
                                  image_sample = image_sample,
                                  interp_method = interp_method,
                                  zscale = scale)

    print('Processing image in Blender, please be patient...')
    newScene.createDefaultContext()

    if mist:
        newScene.createMist()
    if stars:
        newScene.createStars()

    #Try is for a pipeline call and except is for a GUI call?
    try:
        newScene.saveAs(save_path)
        print("Saved image at: ", save_path)
        print("  DTM_IMG:", filepath)
        print("  DTM_TEXTURE:", texture_location)
    except:
        print("Not saving blend file...")
        rasterimporter = gdalio.ReadGDAL(filepath)
        rasterimporter.resize(percentage_reduction=image_sample,
                              interpolation=interp_method)
        rasterimporter.scale(scale)

        #importer = hirise_dtm_importer(context, filepath)
        #importer.bin_mode(bin_mode)
        #importer.scale(scale)

        #if cropVars:
            #importer.crop(cropVars[0], cropVars[1], cropVars[2], cropVars[3] )
        #importer.execute()

        print("Loading %s" % filepath)

    if render:
        newScene.auto_render(animation, resolution)

    return
