import mathutils
import bpy
from bpy import context
import sys

model_path = MODEL_PATH


scene = bpy.data.scenes.new("OurScene")
camera_data = bpy.data.cameras.new("Camera")
camera = bpy.data.objects.new("Camera", camera_data)
camera.location = (-4.0*20, -5.0*20, -1.0*20)
scene.objects.link(camera)
scene.update()
scene.camera = camera
bpy.context.screen.scene = scene
bpy.data.cameras['Camera.001'].clip_end = 10000
bpy.ops.scene.new(type='LINK_OBJECTS')
bpy.context.scene.name = 'model.obj'
bpy.ops.import_mesh.stl(filepath=model_path)
bpy.ops.transform.resize(value=(0.01, 0.01, 0.01))
bpy.context.scene.camera = camera
bpy.context.scene.world = bpy.data.worlds['World']

# look at origin
loc_camera = camera.matrix_world.to_translation()
direction = mathutils.Vector((0., 0., 0.)) - loc_camera
# point the cameras '-Z' and use its 'Y' as up
rot_quat = direction.to_track_quat('-Z', 'Y')
# assume we're using euler rotation
camera.rotation_euler = rot_quat.to_euler()

bpy.data.worlds['World'].light_settings.use_environment_light = True

bpy.ops.view3d.camera_to_view_selected()
scene.camera.location.x = scene.camera.location.x*1.2
scene.camera.location.y = scene.camera.location.y*1.2
scene.camera.location.z = scene.camera.location.z*1.2

bpy.context.scene.render.filepath = OUTPUT_PATH
bpy.ops.render.render(write_still=True)
