import math
import os

import numpy as np
from scipy.spatial.distance import cdist
import bpy
from bpy.props import *
import os
from mathutils import Vector


def no_flyover(mesh):
    """
    Compute a static camera position

    Parameters
    ----------
    mesh        (obj) A DTMRenderContext (terrible class name) object
    """
    #Gets the boundaries of the mesh and target the middle
    minextents = np.asarray(mesh.dtm_min_v)
    maxextents = np.asarray(mesh.dtm_max_v)
    center = mesh.basedem.pixelcenter
    zcenterelevation = mesh.basedem.arr[mesh.basedem.pixelcenter[1],
                                    mesh.basedem.pixelcenter[0]]

    camera_target = (0,0,zcenterelevation)  #Since we center the DTM, set the camera to the origin
    #Set the position of the camera - center to the long 'edge'
    if maxextents[0] > maxextents[1]:
        #Larger in the x direction
        xcamera = 0.0
        ycamera = maxextents[1] - ((maxextents[1] - minextents[1]/ 2))
    else:
        ycamera = 0.0
        xcamera = minextents[0] - ((maxextents[0] - minextents[0]) / 1.5)
    zcamera = camera_target[2] + 400
    camera_point = (xcamera, ycamera, zcamera)
    #Final camera location.
    #camera_point = (boundaries_list[3][0] - camera_point_x, boundaries_list[3][1] - camera_point_y, camera_point_z)
    #Create both the target and camera, with the camera looking at the target.
    make_camera_and_target(camera_point, camera_target)
    #Selecting our camera.
    camera = None
    for item in bpy.data.objects:
        if item.type == 'CAMERA':
            camera = item
    #Simple error checking to ensure a camera is selected.
    if camera is None:
        print("Problem with selecting the camera in no_flyover.")
        return
    #Setting our FOV and Distance because we are looking at the mesh from far away.
    camera.data.lens = 23
    camera.data.clip_start = 0.1
    camera.data.clip_end = 1250.0
    return

def getcamera_target(minextents, maxextents):
    """
    Compute the center of the DTM in pixel space

    Parameters
    -----------
    minextents      (tuple) (xmin, ymin, zmin)
    maxextents      (tuple) (xmax, ymax, zmax)

    Returns
    --------
    center          (tuple) (xcenter, ycenter, zcenter)
    """
    xcenter = (maxextents[0] - minextents[0]) / 2.0
    ycenter = (maxextents[1] - minextents[1]) / 2.0
    zcenter = (maxextents[2] - minextents[2]) / 2.0

    return xcenter, ycenter, zcenter

def linear_pattern(mesh):
    linear_pattern_main(mesh)
    set_environment()
    return


def linear_pattern_main(mesh):
    print("LinearMAIN")
    waypoints = getlinear_path(mesh)
    #waypoints = check_height(waypoints, mesh)
    cameraobj = make_path("Curve", "Linear", waypoints)
    print("MAKING CAM")
    make_camera(waypoints[0])
    #Select the camera for additional setting adjustments.
    camera = None
    for item in bpy.data.objects:
        if item.type == 'CAMERA':
            camera = item
    #Simple error checking to ensure a camera is selected.
    if camera is None:
        print("Problem with selecting the camera in linear pattern main.")
        return

    camera.data.lens = 10
    camera.data.clip_end = 1250
    return


def getlinear_path(mesh):
    """
    Compute the start and stop points for a linear traversal

    Parameters
    -----------
    mesh        (obj) gdalio dtm object

    Returns
    -------
    path        (list)  [startpt, endpt], where each is [x,y,z]
    """
    boundary = mesh.basedem.pixelextent
    center = mesh.basedem.pixelcenter



    if distance_two_points(boundary['ul'], boundary['ur']) <=\
            distance_two_points(boundary['ul'], boundary['ll']):

        #Get the index and blender pixel space coordinates for the path
        startpixelx = (boundary['ll'][0] + boundary['lr'][0]) / 2
        startblenderx = ((boundary['ll'][0] - center[0]) + (boundary['lr'][0] - center[0])) / 2
        endpixelx = startpixelx
        endblenderx = startblenderx

        endpixely = boundary['ll'][1]
        endblendery = center[1] - endpixely
        ypixelextent = boundary['lr'][1]
        yblenderextent = ypixelextent - center[1]
        startpixely = ypixelextent  # Backoff 15% from the end
        startblendery = yblenderextent

        #Extract the topopgraphic profile
        topoprofile = mesh.basedem.arr[:,startpixelx]
        yidx = np.arange(topoprofile.shape[0])
        mask = np.isnan(topoprofile)
        startz = topoprofile[~mask][0]
        endz = topoprofile[~mask][1]

        validelev = topoprofile[~mask][::10]
        valididy = yidx[~mask][::10]

        centerz = mesh.basedem.pixelcenter[2]

        #Construct the start end end points
        xloc = endblenderx
        start = [xloc, endblendery, abs(centerz) + validelev[-1]]
        #end = [xloc, startblendery, abs(centerz) + validelev[0] + 100]

        path = [start]
        for i, v in enumerate(validelev):
            path.append([startblenderx, valididy[i] - center[1], (abs(centerz)) + v + 25 ])
        #path.append(end)
    else:
        startpixely = (boundary['ll'][1] + boundary['lr'][1] / 2)
        startblendery = ((boundary['ll'][1] - center[1]) + (boundary['lr'][1] - center[1])) / 2
        endpixely = startpixely
        endblendery = startblendery


        endpixelx = boundary['ll'][0]
        endblenderx = center[0] - endpixelx
        xpixelextent = boundary['lr'][0]
        xblenderextent = xpixelextent - center[0]
        startpixelx = int(xpixelextent - (xpixelextent * 0.15))  # Backoff 15% from the end
        startblenderx = int(xblenderextent - (xblenderextent * 0.15))

        #Extract the topopgraphic profile
        topoprofile = mesh.basedem.arr[startpixely]
        xidx = np.arange(topoprofile.shape[0])
        mask = np.isnan(topoprofile)
        startz = topoprofile[~mask][0]
        endz = topoprofile[~mask][1]

        validelev = topoprofile[~mask][::10]
        valididx = xidx[~mask][::10]

        centerz = mesh.basedem.pixelcenter[2]

        yloc = endblendery
        #TODO: Need a good, programmatic way to set a reasonable height +25 is a magic number...
        start = [endblenderx, yloc, abs(centerz) + validelev[-1]]
        end = [startblenderx, yloc, abs(centerz) + validelev[0]]


        path = [start]
        for i, v in enumerate(validelev):
            path.append([valididx[i] - center[0], yloc, (abs(centerz)) + v + 50  ])
        #path.append(end)
    path[0][2] = path[1][2]
    #path[-1][2] = path[-2][2]
    pathlength = len(path)
    pathlength = int(pathlength * 0.15)
    return path[:-pathlength]


def circle_pattern(mesh):
    circle_pattern_main()
    set_environment()
    return

def diamond_pattern():
    diamond_pattern_main()
    set_environment()
    return

def circle_pattern_main():
    #Get the boundaries and midpoint of the mesh.
    boundaries_list = get_dem_boundaries()
    midpoint_mesh = get_center(boundaries_list)
    #Create the circle around the mesh.
    bpy.ops.curve.primitive_bezier_circle_add()
    circle = bpy.data.objects['BezierCircle']
    circle.location = (midpoint_mesh[0], midpoint_mesh[1], midpoint_mesh[2]+25)
    radius = distance_two_points(boundaries_list[0], boundaries_list[1]) + 15
    circle.scale = (radius, radius, 1.0)
    #Define where the camera will be placed. Should be right on the circle.
    camera_point = (midpoint_mesh[0], midpoint_mesh[1] - radius, midpoint_mesh[2]+25)
    #Creat the camera.
    make_camera_and_target(camera_point, midpoint_mesh)
    #Select the camera for additional setting adjustments.
    camera = None
    for item in bpy.data.objects:
        if item.type == 'CAMERA':
            camera = item
    #Simple error checking to ensure a camera is selected.
    if camera is None:
        print("Problem with selecting the camera in circle pattern main.")
        return
    #Change the distance we can see with the camera because we are looking from far out.
    camera.data.clip_end = 300
    return

def diamond_pattern_main():
    #Get the boundaries of the mesh.
    boundaries_list = get_dem_boundaries()
    #Getting the midpoints of each side.
    side_one_midpoint = midpoint_two_points(boundaries_list[3], boundaries_list[1])
    side_two_midpoint = midpoint_two_points(boundaries_list[1], boundaries_list[2])
    side_three_midpoint = midpoint_two_points(boundaries_list[2], boundaries_list[0])
    side_four_midpoint = midpoint_two_points(boundaries_list[0], boundaries_list[3])
    #Depending on the orientation of the mesh, we move into the image by 5 in x and 5 in y.
    #Makes it so we don't run right to the edge every time.
    if side_one_midpoint[1] - side_three_midpoint[1] < 0:
        side_one_midpoint = (side_one_midpoint[0] + 5, side_one_midpoint[1] + 5, side_one_midpoint[2])
        side_two_midpoint = (side_two_midpoint[0] + 5, side_two_midpoint[1] - 5, side_two_midpoint[2])
        side_three_midpoint = (side_three_midpoint[0] - 5, side_three_midpoint[1] - 5, side_three_midpoint[2])
        side_four_midpoint = (side_four_midpoint[0] - 5, side_four_midpoint[1] + 5, side_four_midpoint[2])
    else:
        side_one_midpoint = (side_one_midpoint[0] + 5, side_one_midpoint[1] - 5, side_one_midpoint[2])
        side_two_midpoint = (side_two_midpoint[0] + 5, side_two_midpoint[1] + 5, side_two_midpoint[2])
        side_three_midpoint = (side_three_midpoint[0] - 5, side_three_midpoint[1] + 5, side_three_midpoint[2])
        side_four_midpoint = (side_four_midpoint[0] + 5, side_four_midpoint[1] + 5, side_four_midpoint[2])
    #Setting up the list for our 4 point diamond shape.
    point_list = [side_two_midpoint, side_three_midpoint, side_four_midpoint, side_one_midpoint, side_two_midpoint]
    #Make it so our points are above the mesh.
    point_list = check_height(point_list)
    #Create both the path and the camera.
    make_path("Curve", "Diamond", point_list)
    make_camera(side_two_midpoint)
    #Select the camera for additional setting adjustments.
    camera = None
    for item in bpy.data.objects:
        if item.type == 'CAMERA':
            camera = item
    #Simple error checking to ensure a camera is selected.
    if camera is None:
        print("Problem with selecting the camera in diamond pattern main.")
        return
    camera.data.clip_end = 300
    return

def check_height(waypoints, mesh):
    """
    Setup the flight height over the DTM using a simplistic, static offset

    Parameters
    ----------
    waypoints   (list) of lists with start / stop pairs for
                       each leg of a camera path
    """

    for w in waypoints:
        centerz = mesh.basedem.pixelcenter[2]
        w[2] = centerz * 5

    return waypoints

def make_camera_and_target(point, target_point):
    #Creat both the camera and target.
    bpy.ops.object.camera_add(view_align=False, enter_editmode=False, location=point)
    bpy.ops.object.add(type='EMPTY')
    #Place the empty object variable as camera_target.
    camera_target = None
    for item in bpy.data.objects:
        if item.type == 'EMPTY':
            camera_target = item
    #Place the camera object variable as camera
    camera = None
    for item in bpy.data.objects:
        if item.type == 'CAMERA':
            camera = item
    #Simple error checking to ensure a camera and target are selected.
    if camera_target is None or camera is None:
        print("Problem selecting camera and target in make_camera_and_target.")
        return
    #Setting up the camera targets name and location.
    camera_target.name = 'CameraTarget'
    camera_target.location = target_point
    #Setting up the constraint on the camera.
    camera.select = True
    track_constraint = camera.constraints.new('TRACK_TO')
    track_constraint.target = camera_target
    track_constraint.track_axis = 'TRACK_NEGATIVE_Z'
    track_constraint.up_axis = 'UP_Y'
    #Adds both the camera and target to the path.
    attach_camera_to_path()
    add_target_to_path()
    return

def make_camera(point):
    #Creat both the camera and target.
    bpy.ops.object.camera_add(view_align=False, enter_editmode=False, location=point)
    #Place the empty object variable as camera_target.
    camera_target = None
    for item in bpy.data.objects:
        if item.type == 'CURVE':
            camera_target = item
    #Place the camera object variable as camera
    camera = None
    for item in bpy.data.objects:
        if item.type == 'CAMERA':
            camera = item
    print("CAM: ", camera)
    #Simple error checking to ensure a camera and curve are selected.
    if camera is None or camera_target is None:
        print("Problem selecting a camera and curve in make_camera.")
        return
    #Setting up the constraint on the camera.
    camera.select = True
    track_constraint = camera.constraints.new('TRACK_TO')
    track_constraint.target = camera_target
    track_constraint.track_axis = 'TRACK_Z'
    track_constraint.up_axis = 'UP_Y'
    #Adds the camera to the curve.
    attach_camera_to_path()
    return

def attach_camera_to_path():
    #Deselect all other objects.
    deselect_objects()
    #Select camera.
    camera = None
    for item in bpy.data.objects:
        if item.type == 'CAMERA':
            camera = item
    #Select the curve.
    curve = None
    for item in bpy.data.objects:
        if item.type == 'CURVE':
            curve = item
    #Simple error checking to see if either camera or curve is still none.
    if camera is None or curve is None:
        print("No path or camera to attach to one another in attach_camera_to_path.")
        return
    camera.select = True
    curve.select = True
    #Set the camera to follow the curve.
    bpy.context.scene.objects.active = curve
    bpy.ops.object.parent_set(type='FOLLOW')
    return

def add_target_to_path():
    print('Adding to path')
    #Deselect all other objects.
    deselect_objects()
    #Select the target.
    camera_target = None
    for item in bpy.data.objects:
        if item.type == 'EMPTY':
            camera_target = item
    #Select the curve.
    curve = None
    for item in bpy.data.objects:
        if item.type == 'CURVE':
            curve = item
    #Simple error checking to see if we have selected a target and curve.
    if camera_target is None or curve is None:
        print("No path or target to attach to one another in add_target_to_path.")
        return
    camera_target.select = True
    curve.select = True
    #Set the target to follow the path.
    bpy.ops.object.parent_set(type='FOLLOW')
    return

def deselect_objects():
    #Look through all objects and make sure they are deselected.
    for item in bpy.data.objects:
        item.select = False
    return

def make_path(object_name, curve_name, points):
    #Sets up or curve and object to be added to the scene.
    curve_data = bpy.data.curves.new(name=curve_name, type='CURVE')
    curve_data.dimensions = '3D'
    object_data = bpy.data.objects.new(object_name, curve_data)
    #Starting point of our curve. The first point in our input list.
    object_data.location = points[0]
    bpy.context.scene.objects.link(object_data)
    #Type of curve, POLY, and the number of points to be added.
    polyline = curve_data.splines.new('POLY')
    polyline.points.add(len(points)-1)
    #Need a holder for our origin.
    o_x, o_y, o_z = (0, 0, 0)
    for index in range(len(points)):
        if index == 0:
            #First iteration gives or holder the value of the curve origin.
            o_x, o_y, o_z = points[index]
        else:
            #Because the origin of the curve is different from (0, 0, 0),
            #we need to change the following points relative to our curve origin.
            #As if our curve origin is (0, 0, 0).
            x = points[index][0]
            y = points[index][1]
            z = points[index][2]
            polyline.points[index].co = ((x - o_x), (y - o_y), (z - o_z), 1)

    return object_data
def set_environment():
    """
    Setup the Blender environment
    """
    bpy.data.scenes["Scene"].frame_end = 1440
    #Select the curve.
    curve = None
    for item in bpy.data.objects:
        if item.type == 'CURVE':
            curve = item
    #Simple error checking to see if either camera or curve is still none.
    if curve is None:
        print("Curve not found in set environment.")
        return
    curve.data.path_duration = 1440
    #Change the output to MPEG video with an MPEG-4 codec.
    bpy.data.scenes["Scene"].render.image_settings.file_format = 'FFMPEG'
    bpy.context.scene.render.ffmpeg.format = 'MPEG4'
    #Set the video to output to the current working directory
    bpy.data.scenes["Scene"].render.filepath = os.getcwd()+'/'
    return

def distance_two_points(pt1, pt2):
    """
    Compute the norm between two vectors
    """
    distance = math.sqrt((pt1[0] - pt2[0])**2 + (pt1[1] - pt2[1])**2)
    return distance

def computemidpoint(pt1, pt2):
    """
    Compute the midpoint between two points
    """
    if not isinstance(pt1, np.ndarray):
        pt1 = np.array(pt1)
        pt2 = np.array(pt2)
    return (pt1 + pt2) / 2


def get_dem_boundaries():
    """
    Old function to support cirular paths
    """
    #Simple value holders for getting our corners and highest point in the DEM.
    #Farthest NW corner of the DEM.
    x_max_point = (0, 0, 0)
    #Farthest SE corner of the DEM.
    x_min_point = (100, 0, 0)
    #Farthest NE corner of the DEM.
    y_max_point = (0, 0, 0)
    #Farthest SW corner of the DEM.
    y_min_point = (0, 100, 0)
    #Max height value of the DEM.
    z_max_value = -10
    #Return List
    return_list = []
    #Run through each object to find the MESH.
    for item in bpy.data.objects:
        if item.type == 'MESH':
            #Run through each vertex to get our data.
            for vertex in item.data.vertices:
                #Series of if statements to get the correct values for our value holders.
                if vertex.co.x >= x_max_point[0]:
                    x_max_point = (vertex.co.x, vertex.co.y, vertex.co.z)
                if vertex.co.x < x_min_point[0]:
                    x_min_point = (vertex.co.x, vertex.co.y, vertex.co.z)
                if vertex.co.y >= y_max_point[1]:
                    y_max_point = (vertex.co.x, vertex.co.y, vertex.co.z)
                if vertex.co.y < y_min_point[1]:
                    y_min_point = (vertex.co.x, vertex.co.y, vertex.co.z)
                if not np.isnan(vertex.co.z):
                    if vertex.co.z > z_max_value:
                        z_max_value = vertex.co.z
    return_list.append(x_max_point)
    return_list.append(x_min_point)
    return_list.append(y_max_point)
    return_list.append(y_min_point)
    return_list.append(z_max_value)
    return return_list

def get_center(input_list):
    """
    Old function to support circular paths
    """
    #Gets us the values midpoint of the mesh.
    x_cross_mid_p = midpoint_two_points(input_list[0], input_list[1])
    y_cross_mid_p = midpoint_two_points(input_list[2], input_list[3])
    return_value = midpoint_two_points(x_cross_mid_p, y_cross_mid_p)
    return_value = list(return_value)
    return_value[2] = input_list[4]
    return return_value

def midpoint_two_points(point_one, point_two):
    """
    Old function to support circular paths
    """
    return (point_one[0]+point_two[0])/2, (point_one[1]+point_two[1])/2, (point_one[2]+point_two[2])/2
