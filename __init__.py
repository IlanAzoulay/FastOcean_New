# -*- coding: utf-8 -*-

# # BEGIN GPL LICENSE BLOCK #
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# # END GPL LICENSE BLOCK #

bl_info = {
    "name": "Fast Landscape",
    "author": "Laurent Laget (modified by Ilan Azoulay)",
    "version": (1, 0),
    "blender": (2, 78, 0),
    "location": "Add > Mesh",
    "description": "Terrain, grass and water generators",
    "warning": "",
    "wiki_url": "",
    "category": "Add Mesh",
    }

import bpy

"""
MODIFICATIONS:
- Added execute(self, context) methods to operators. This allows them to be called by command line
    > command line to call an operator: "bpy.ops." + bl_idname + "()"
        > Example: to call fastocean: bpy.ops.create.fastocean()
- Fixed sky creation so it works regardless of the pre-existing world settings
- Changed bl_idname of operators so they wouldn't be in a pre-existing attribute of bpy.ops
- Respecting PEP8
- Some less significant synthax changes here and there that don't change the outcome
"""


# PANELS =================================


class panelsky(bpy.types.Panel):
    """ce panel fait des courbes"""
    bl_label = "Fast Landscape"
    bl_idname = "OBJECT_PT_fast"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = "Fast Landscape"

    def draw(self, context):
        layout = self.layout

        layout.row().operator("create.fastterrain", icon='MESH_GRID')
        layout.row().operator("create.fastocean", icon='MOD_WAVE')
        layout.row().operator("add.collider_ocean", icon='MOD_OCEAN')
        layout.row().operator("create.fastsky", icon='WORLD_DATA')

        # TODO: pick values of sky
#        transition = pick_world.node_tree.nodes['transition_node'].inputs[1]
#        col.prop(bgp, "Transition", text="transition")


# ====================================================
#    OPERATORS
# ====================================================

# Bouton fastterrain
class fastterrain(bpy.types.Operator):
    """description"""
    bl_idname = "create.fastterrain"
    bl_label = "Fast Terrain"
    # bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        self.invoke(context, None)
        return {'FINISHED'}

    def invoke(self, context, event):
        # set cycles
        context.scene.render.engine = 'CYCLES'

        # set view material
        context.space_data.viewport_shade = 'MATERIAL'

        # creation plane
        bpy.ops.mesh.primitive_plane_add(radius=1)
        context.object.name = "terrain"
        t = context.object.name

        # initial scale and subdivision
        bpy.ops.object.editmode_toggle()
        bpy.ops.transform.resize(value=(2, 2, 2), constraint_axis=(False, False, False),
                                 constraint_orientation='GLOBAL', mirror=False, proportional='DISABLED',
                                 proportional_edit_falloff='SMOOTH', proportional_size=1)
        bpy.ops.mesh.subdivide(number_cuts=10, smoothness=0)
        bpy.ops.mesh.subdivide(number_cuts=10, smoothness=0)
        bpy.ops.object.editmode_toggle()

        bpy.ops.object.shade_smooth()

        # Hair setup
        bpy.ops.object.particle_system_add()
        context.object.particle_systems["ParticleSystem"].name = "grass_particles"

        terrain = bpy.data.objects[t]
        par_set = bpy.data.particles['ParticleSettings']
        terrain.particle_systems['grass_particles'].settings = par_set

        bpy.data.particles["ParticleSettings"].use_modifier_stack = True
        bpy.data.particles["ParticleSettings"].type = 'HAIR'
        bpy.data.particles["ParticleSettings"].hair_length = 0.08
        bpy.data.particles["ParticleSettings"].count = 1250
        bpy.data.particles["ParticleSettings"].child_type = 'INTERPOLATED'
        bpy.data.particles['ParticleSettings'].cycles.root_width = 0.1
        bpy.ops.object.vertex_group_add()
        context.object.particle_systems["grass_particles"].vertex_group_density = "Group"

        # sculpt mode
        bpy.ops.sculpt.sculptmode_toggle()
        obj = context.active_object

        # creation material
        mat_name = "M_terrain"
        materials = bpy.data.materials
        mat = materials.get(mat_name) or materials.new(mat_name)

        if mat is None:
            mat = bpy.data.materials.new(name="M_terrain")

        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

        # creation shader
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        mat = materials.get(mat_name) or materials.new(mat_name)

        for node in nodes:
            nodes.remove(node)

        # geometry and position node
        node_geo = nodes.new('ShaderNodeNewGeometry')
        node_geo.location = (-1100, 100)

        # separate xyz node
        node_xyz = nodes.new('ShaderNodeSeparateXYZ')
        node_xyz.location = (-900, 100)

        # gradient altitude
        gradient_alt = nodes.new(type='ShaderNodeValToRGB')
        gradient_alt.location = (-700, 0)
        gradient_alt.color_ramp.elements[0].color = (1, 1, 1, 1)
        gradient_alt.color_ramp.elements[1].color = (0, 0, 0, 1)

        # shader low altitude
        node = nodes.new('ShaderNodeBsdfDiffuse')
        node.location = (50, -200)
        node.inputs[0].default_value = (0.05, 0.013, 0.008, 1)

        # noise low altitude
        noise_node = nodes.new(type='ShaderNodeTexNoise')
        noise_node.location = -400, -200
        noise_node.inputs[1].default_value = (100)

        # gradient low altitude
        gradient_node = nodes.new(type='ShaderNodeValToRGB')
        gradient_node.location = -230, -200
        gradient_node.color_ramp.elements[0].color = (0.04, 0.005, 0.003, 1)
        gradient_node.color_ramp.elements[1].color = (0.09, 0.011, 0.007, 1)

        # shader high altitude
        node_high = nodes.new('ShaderNodeBsdfGlossy')
        node_high.location = (-150, 150)
        node_high.inputs[0].default_value = (0.9, 0.9, 0.9, 1)
        node_high.inputs[1].default_value = (0.8)

        # shader green
        node_green = nodes.new('ShaderNodeBsdfDiffuse')
        node_green.location = (-150, 300)
        node_green.inputs[0].default_value = (0.06, 0.3, 0.08, 1)

        # mix high and green
        node_mg = nodes.new('ShaderNodeMixShader')
        node_mg.location = (50, 225)

        # mix low and high
        node_mix = nodes.new('ShaderNodeMixShader')
        node_mix.location = (250, -30)

        # node_divider
        node_div = nodes.new('ShaderNodeMath')
        node_div.location = (40, 0)
        node_div.operation = ('DIVIDE')
        node_div.inputs[1].default_value = 1.05

        # node_bump
        node_bump = nodes.new('ShaderNodeBump')
        node_bump.location = (-180, -450)

        # output
        node_output = nodes.new(type='ShaderNodeOutputMaterial')
        node_output.location = 500, 100

        # LINKS
        mat.node_tree.links.new(node.outputs['BSDF'], node_mix.inputs[2])
        mat.node_tree.links.new(node_high.outputs['BSDF'], node_mg.inputs[2])
        mat.node_tree.links.new(node_green.outputs['BSDF'], node_mg.inputs[1])
        mat.node_tree.links.new(gradient_alt.outputs[0], node_div.inputs[0])
        mat.node_tree.links.new(node_div.outputs[0], node_mix.inputs[0])
        mat.node_tree.links.new(node_xyz.outputs[2], node_mg.inputs[0])
        mat.node_tree.links.new(node_mg.outputs[0], node_mix.inputs[1])
        mat.node_tree.links.new(noise_node.outputs[0], gradient_node.inputs[0])
        mat.node_tree.links.new(gradient_node.outputs[0], node.inputs[0])
        mat.node_tree.links.new(node_geo.outputs[0], node_xyz.inputs[0])
        mat.node_tree.links.new(node_xyz.outputs[2], gradient_alt.inputs[0])
        mat.node_tree.links.new(noise_node.outputs[0], node_bump.inputs[2])
        mat.node_tree.links.new(node_bump.outputs[0], node.inputs[2])
        mat.node_tree.links.new(node_bump.outputs[0], node_high.inputs[2])
        mat.node_tree.links.new(node_mix.outputs[0], node_output.inputs['Surface'])

        bpy.ops.object.mode_set(mode='OBJECT')

        return {'FINISHED'}


# classe fastocean
class fastocean(bpy.types.Operator):
    """Create a dynamic ocean"""
    bl_idname = "create.fastocean"
    bl_label = "Fast Ocean"
    # bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        self.invoke(context, None)
        return {'FINISHED'}

    def invoke(self, context, event):

        # NAMES
        name_ocean = "Ocean"
        name_mod_ocean = "mod_ocean"
        name_dpaint = "foam_paint"

        # set cycles
        context.scene.render.engine = 'CYCLES'
        context.scene.cycles.volume_bounces = 2

        # Create Ocean object
        bpy.ops.mesh.primitive_plane_add()
        ocean_obj = context.object
        ocean_obj.name = name_ocean

        # Create ground object
        bpy.ops.mesh.primitive_plane_add()
        ground_obj = context.object
        ground_obj.name = "Ground"

        # Tweak scale and location
        ocean_obj.location = [0, 0, 0]
        ground_obj.location = [0, 0, -25]
        ground_obj.dimensions = [120, 120, 0]

        ocean_obj.modifiers.new(name=name_mod_ocean, type="OCEAN")
        mod_ocean = ocean_obj.modifiers.get(name_mod_ocean)
        mod_ocean.wave_scale = 1

        # setup modifier ocean
        mod_ocean.repeat_x = 1
        mod_ocean.repeat_y = 1
        mod_ocean.resolution = 12
        mod_ocean.wave_scale = 2

        mod_ocean.use_normals = True
        mod_ocean.use_foam = True
        mod_ocean.foam_layer_name = "foam_layer"

        # creation material
        mat_name = "M_ocean"
        materials = bpy.data.materials
        mat = materials.get(mat_name) or materials.new(mat_name)

        if mat is None:
            mat = bpy.data.materials.new(name="M_ocean")

        if ocean_obj.data.materials:
            ocean_obj.data.materials[0] = mat
        else:
            ocean_obj.data.materials.append(mat)

        # create shader
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        mat = materials.get(mat_name) or materials.new(mat_name)

        for node in nodes:
            nodes.remove(node)

        # node blue water
        water_node = nodes.new('ShaderNodeBsdfGlass')
        water_node.location = (80, 50)
        water_node.distribution = ('MULTI_GGX')
        water_node.inputs[0].default_value = (0.11, 0.44, 0.8, 1)
        water_node.inputs[2].default_value = (1.330)
        water_node.label = ('Water Shader - Glass BSDF')

        # nodes for foam, attribute and noise

        # attribute node for wet map
        wet_node = nodes.new('ShaderNodeAttribute')
        wet_node.location = (-780, 790)
        wet_node.attribute_name = ('dp_wetmap')
        wet_node.label = ('Wet map attribute')

        # attribute node 2 for wet map
        wet_node2 = nodes.new('ShaderNodeAttribute')
        wet_node2.location = (-780, 920)
        wet_node2.attribute_name = ('dp_wetmap')
        wet_node2.label = ('Wet map attribute 2')

        # add texture coordinate
        ocean_texcoord_node = nodes.new('ShaderNodeTexCoord')
        ocean_texcoord_node.location = (-780, 620)

        # mixrgb add node
        mixrgb_add_node = nodes.new('ShaderNodeMixRGB')
        mixrgb_add_node.location = (-600, 920)
        mixrgb_add_node.use_clamp = True
        mixrgb_add_node.blend_type = ('ADD')

        # texture noise for first vector object
        noisevec1_node = nodes.new('ShaderNodeTexNoise')
        noisevec1_node.location = (-600, 730)
        noisevec1_node.inputs[1].default_value = (10)
        noisevec1_node.inputs[2].default_value = (5)

        # texture noise for second vector object
        noisevec2_node = nodes.new('ShaderNodeTexNoise')
        noisevec2_node.location = (-600, 550)
        noisevec2_node.inputs[1].default_value = (2)
        noisevec2_node.inputs[2].default_value = (5)
        noisevec2_node.inputs[3].default_value = (1)

        # mixrgb substract node
        mixrgb_substract_node = nodes.new('ShaderNodeMixRGB')
        mixrgb_substract_node.location = (-180, 920)
        mixrgb_substract_node.use_clamp = True
        mixrgb_substract_node.blend_type = ('SUBTRACT')

        # mixrgb substract node 2
        mixrgb_substract2_node = nodes.new('ShaderNodeMixRGB')
        mixrgb_substract2_node.location = (80, 920)
        mixrgb_substract2_node.use_clamp = True
        mixrgb_substract2_node.blend_type = ('SUBTRACT')
        mixrgb_substract2_node.label = ('Subtract 2')

        # multiply node for displacement
        multiply_displace_node = nodes.new('ShaderNodeMath')
        multiply_displace_node.operation = ('MULTIPLY')
        multiply_displace_node.inputs[0].default_value = (2)
        multiply_displace_node.location = (250, 920)

        # wet shader with attributes
        wetshader_node = nodes.new(type='ShaderNodeBsdfDiffuse')
        wetshader_node.location = (250, 700)
        wetshader_node.label = ('Wet Shader')

        # color ramp for noise texture for attribute section
        gradient_noise_node = nodes.new(type='ShaderNodeValToRGB')
        gradient_noise_node.location = (-180, 700)

        # color ramp 2 for noise texture for attribute section
        gradient_noise_node2 = nodes.new(type='ShaderNodeValToRGB')
        gradient_noise_node2.location = (-440, 750)

        # foam attribute for both shaders
        foam_node = nodes.new('ShaderNodeAttribute')
        foam_node.location = (-350, 300)
        foam_node.attribute_name = ('foam_layer')
        foam_node.label = ('Foam Attribute')

        # diffuse shader, half part of foam
        diffuse_foam_node = nodes.new(type='ShaderNodeBsdfDiffuse')
        diffuse_foam_node.location = (-180, 360)

        # glossy shader, half part of foam
        glossy_foam_node = nodes.new(type='ShaderNodeBsdfGlossy')
        glossy_foam_node.location = (-180, 220)

        # mix gloss and diffuse shader for foam node
        mix_foam_node = nodes.new('ShaderNodeMixShader')
        mix_foam_node.location = (0, 310)
        mix_foam_node.label = ('Mix Foam nodes')

        # mix attributes and foam shader
        mix_attribute_node = nodes.new('ShaderNodeMixShader')
        mix_attribute_node.location = (180, 310)
        mix_attribute_node.label = ('Mix attributes foam')

        # nodes for water, bump and volume

        # texture noise for bump
        noise_node = nodes.new('ShaderNodeTexNoise')
        noise_node.location = (-700, 50)

        # gradient water
        gradient_water_node = nodes.new(type='ShaderNodeValToRGB')
        gradient_water_node.location = (-530, 50)
        gradient_water_node.color_ramp.elements[0].color = (1, 1, 1, 1)
        gradient_water_node.color_ramp.elements[1].color = (0, 0, 0, 1)

        # vector bump node
        bump_water_node = nodes.new('ShaderNodeBump')
        bump_water_node.location = (-250, 50)

        # mix shader
        mix_node = nodes.new('ShaderNodeMixShader')
        mix_node.location = (350, 150)
        mix_node.label = ('Mix glass with attributes')

        # shader volume scatter
        volume_node = nodes.new('ShaderNodeVolumeScatter')
        volume_node.location = (80, -150)
        volume_node.inputs[0].default_value = (0.0863, 0.3681, 0.2131, 1)
        volume_node.inputs[1].default_value = (0.29)

        # shader volume absorption
        absorption_node = nodes.new('ShaderNodeVolumeAbsorption')
        absorption_node.location = (80, -300)
        absorption_node.inputs[0].default_value = (0.115, 0.5681, 0.1944, 1)
        absorption_node.inputs[1].default_value = (0.400)

        # mix volume shader
        volume_mix_node = nodes.new('ShaderNodeMixShader')
        volume_mix_node.location = (250, -200)
        volume_mix_node.label = ('mix volumes')

        # node output
        node_output = nodes.new(type='ShaderNodeOutputMaterial')
        node_output.location = 600, 100

        # LINKS
        mat.node_tree.links.new(water_node.outputs['BSDF'], mix_node.inputs[2])
        mat.node_tree.links.new(noise_node.outputs[0], gradient_water_node.inputs[0])
        mat.node_tree.links.new(gradient_water_node.outputs[0], bump_water_node.inputs[2])
        mat.node_tree.links.new(bump_water_node.outputs[0], water_node.inputs[3])
        mat.node_tree.links.new(volume_node.outputs[0], volume_mix_node.inputs[1])
        mat.node_tree.links.new(absorption_node.outputs[0], volume_mix_node.inputs[2])
        mat.node_tree.links.new(volume_mix_node.outputs[0], node_output.inputs['Volume'])
        mat.node_tree.links.new(mix_node.outputs[0], node_output.inputs['Surface'])
        mat.node_tree.links.new(wet_node2.outputs[0], mixrgb_add_node.inputs[1])
        mat.node_tree.links.new(wet_node.outputs[0], mixrgb_add_node.inputs[2])
        mat.node_tree.links.new(ocean_texcoord_node.outputs['Object'], noisevec1_node.inputs[0])
        mat.node_tree.links.new(ocean_texcoord_node.outputs['Object'], noisevec2_node.inputs[0])
        mat.node_tree.links.new(mixrgb_add_node.outputs[0], mixrgb_substract_node.inputs[1])
        mat.node_tree.links.new(noisevec1_node.outputs[0], gradient_noise_node2.inputs[0])
        mat.node_tree.links.new(noisevec2_node.outputs[0], gradient_noise_node.inputs[0])
        mat.node_tree.links.new(mixrgb_substract_node.outputs[0], mixrgb_substract2_node.inputs[1])
        mat.node_tree.links.new(gradient_noise_node.outputs[0], mixrgb_substract2_node.inputs[2])
        mat.node_tree.links.new(gradient_noise_node2.outputs[0], mixrgb_substract_node.inputs[2])
        mat.node_tree.links.new(mixrgb_substract2_node.outputs[0], wetshader_node.inputs[0])
        mat.node_tree.links.new(foam_node.outputs[0], diffuse_foam_node.inputs[0])
        mat.node_tree.links.new(foam_node.outputs[0], glossy_foam_node.inputs[0])
        mat.node_tree.links.new(diffuse_foam_node.outputs[0], mix_foam_node.inputs[1])
        mat.node_tree.links.new(glossy_foam_node.outputs[0], mix_foam_node.inputs[2])
        mat.node_tree.links.new(wetshader_node.outputs['BSDF'], mix_attribute_node.inputs[1])
        mat.node_tree.links.new(mix_foam_node.outputs[0], mix_attribute_node.inputs[2])
        mat.node_tree.links.new(mix_attribute_node.outputs[0], mix_node.inputs[0])
        mat.node_tree.links.new(mix_attribute_node.outputs[0], mix_node.inputs[1])
        mat.node_tree.links.new(mixrgb_substract2_node.outputs[0], multiply_displace_node.inputs[1])
        mat.node_tree.links.new(multiply_displace_node.outputs[0], node_output.inputs['Displacement'])

        # apply dynamic paint and setup the ocean as a canvas#
        ocean_obj.modifiers.new(name=name_dpaint, type="DYNAMIC_PAINT")
        mod_dpaint = ocean_obj.modifiers.get(name_dpaint)
        context.scene.objects.active = ocean_obj
        bpy.ops.dpaint.type_toggle(type='CANVAS')
        # bpy.ops.dpaint.surface_slot_add()
        # bpy.ops.dpaint.type_toggle(type='CANVAS')
        mod_dpaint.canvas_settings.canvas_surfaces["Surface"].preview_id = 'WETMAP'
        mod_dpaint.canvas_settings.canvas_surfaces["Surface"].use_dissolve = True
        bpy.ops.dpaint.output_toggle(output='A')
        bpy.ops.dpaint.output_toggle(output='B')
        mod_dpaint.canvas_settings.canvas_surfaces["Surface"].use_antialiasing = True

        # apply a second layer of dynamic paint with a wave effect
        bpy.ops.dpaint.surface_slot_add()
        mod_dpaint.canvas_settings.canvas_surfaces["Surface.001"].name = "onde"
        mod_dpaint.canvas_settings.canvas_surfaces["onde"].surface_type = 'WAVE'
        mod_dpaint.canvas_settings.canvas_surfaces["onde"].use_antialiasing = True
        mod_dpaint.canvas_settings.canvas_surfaces["onde"].use_wave_open_border = True

        ground_obj.parent = ocean_obj
        ground_obj.matrix_parent_inverse = ocean_obj.matrix_world.inverted()  # Keep transform

        return {'FINISHED'}


class collider_ocean(bpy.types.Operator):
    """Transform the selected object easily into a collider that will generate foam"""
    bl_idname = "add.collider_ocean"
    bl_label = "Collider Ocean"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        self.invoke(context, None)
        return {'FINISHED'}

    def invoke(self, context, event):
        # apply dynamic paint, and setup the object as a brush
        bpy.ops.object.modifier_add(type='DYNAMIC_PAINT')
        modif = context.object.modifiers.get("Dynamic Paint")
        modif.ui_type = 'BRUSH'
        bpy.ops.dpaint.type_toggle(type='BRUSH')
        modif.brush_settings.paint_source = 'VOLUME_DISTANCE'
        modif.brush_settings.paint_distance = 3  # More visible this way
        modif.brush_settings.wave_factor = 2

        return {'FINISHED'}


class fastsky(bpy.types.Operator):
    """Create a realistic sky as background"""
    bl_idname = "create.fastsky"  # bl_idname = "world.fastsky"
    bl_label = "Fast Sky"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        self.invoke(context, None)
        return {'FINISHED'}

    def invoke(self, context, event):

        scn = context.scene
        scn.render.engine = 'CYCLES'
        sky = bpy.data.worlds.new("sky")
        scn.world = sky
        scn.world.use_nodes = True

        # select world node tree
        nt = bpy.data.worlds[sky.name].node_tree

        # create sky
        sky_node = nt.nodes.new(type="ShaderNodeTexSky")
        sky_node.location = (-1500, 450)

        # find location of Background node
        background_node = nt.nodes['Background']

        # connect color out of Grad node to Color in of Background node
        # sky_node_output = sky_node.outputs['Color']
        # sky_node_input = background_node.inputs['Color']
        # nt.links.new(sky_node_output, sky_node_input)

        # texture coordinate node
        coord_node = nt.nodes.new(type="ShaderNodeTexCoord")
        coord_node.location = (-2800, 0)

        # texture coordinate node
        map_node = nt.nodes.new(type="ShaderNodeMapping")
        map_node.location = (-2600, 0)
        map_node.scale = (0, 0, 1)

        # coloramp 1 horizon nuages
        ramp1_node = nt.nodes.new(type="ShaderNodeValToRGB")
        ramp1_node.location = (-2200, 0)
        ramp1_node.color_ramp.elements[0].color = (1, 1, 1, 1)
        ramp1_node.color_ramp.elements[1].color = (0, 0, 0, 1)
        ramp1_node.color_ramp.elements[1].position = (0.155)

        # multiply node
        mult1_node = nt.nodes.new(type="ShaderNodeMath")
        mult1_node.operation = 'MULTIPLY'
        mult1_node.inputs[1].default_value = (15)
        mult1_node.location = (-2200, 150)

        # noise texture for clouds
        clouds_node = nt.nodes.new(type="ShaderNodeTexNoise")
        clouds_node.inputs[2].default_value = (16)
        clouds_node.inputs[3].default_value = (0)
        clouds_node.label = ("Clouds")
        clouds_node.location = (-2000, 160)

        # coloramp 2 grayscale convertor
        ramp2_node = nt.nodes.new(type="ShaderNodeValToRGB")
        ramp2_node.location = (-1800, 160)
        ramp2_node.color_ramp.elements[0].color = (1, 1, 1, 1)
        ramp2_node.color_ramp.elements[1].color = (0, 0, 0, 1)
        ramp2_node.color_ramp.elements[1].position = (0.559)

        ramp2_node.label = ("Cloud color and brightness")
        ramp2_node.use_custom_color = True
        ramp2_node.color = (0.8, 0.8, 1)

        # mult 2 aka couverture nuageuse
        couv_node = nt.nodes.new(type="ShaderNodeMath")
        couv_node.operation = 'MULTIPLY'
        couv_node.inputs[1].default_value = (1)
        couv_node.location = (-1500, 150)
        couv_node.label = ("Clouds cover")

        couv_node.use_custom_color = True
        couv_node.color = (1, 1, 1)

        # mix_node 1
        mix1_node = nt.nodes.new(type="ShaderNodeMixRGB")
        mix1_node.location = (-1300, 150)
        mix1_node.label = ("mix horizon")
        mix1_node.inputs[2].default_value = (0, 0, 0, 1)

        # mix_node 2
        mix2_node = nt.nodes.new(type="ShaderNodeMixRGB")
        mix2_node.location = (-1000, 150)
        mix2_node.label = ("mix sky")

        # transition gamma node
        transition_node = nt.nodes.new(type="ShaderNodeGamma")
        transition_node.location = (-1300, 300)
        transition_node.label = ("Transition day night")
        transition_node.use_custom_color = True
        transition_node.color = (0.00223385, 0.0560615, 1)

        # mix sky plus stars
        mix3_node = nt.nodes.new(type="ShaderNodeMixRGB")
        mix3_node.location = (-800, 0)
        mix3_node.label = ("sky with stars")

        # noise texture for stars
        stars_node = nt.nodes.new(type="ShaderNodeTexNoise")
        stars_node.inputs[1].default_value = (500)
        stars_node.inputs[2].default_value = (2)
        stars_node.label = ("Stars")
        stars_node.location = (-2000, -320)

        # coloramp 3 grayscale convertor for stars
        ramp3_node = nt.nodes.new(type="ShaderNodeValToRGB")
        ramp3_node.location = (-1800, -320)

        ramp3_node.color_ramp.elements[0].color = (1, 1, 1, 1)
        ramp3_node.color_ramp.elements[1].color = (0, 0, 0, 1)
        ramp3_node.color_ramp.elements[1].position = (0.282)

        # mult 3 aka eclat etoile
        shine_node = nt.nodes.new(type="ShaderNodeMath")
        shine_node.operation = 'MULTIPLY'
        shine_node.inputs[1].default_value = (10)
        shine_node.location = (-1500, -320)
        shine_node.label = ("Shine star")

        shine_node.use_custom_color = True
        shine_node.color = (0.608, 0.51, 0)

        # mix horizon etoiles plus stars
        mix4_node = nt.nodes.new(type="ShaderNodeMixRGB")
        mix4_node.inputs[2].default_value = (0, 0, 0, 1)
        mix4_node.location = (-1300, -320)
        mix4_node.label = ("mix horizon with stars")

        # coloramp 4 grayscale convertor
        ramp4_node = nt.nodes.new(type="ShaderNodeValToRGB")
        ramp4_node.location = (-1300, -160)

        ramp4_node.color_ramp.elements[0].color = (1, 1, 1, 1)
        ramp4_node.color_ramp.elements[1].color = (0, 0, 0, 1)
        ramp4_node.color_ramp.elements[1].position = (0.559)

        # LINKS
        nt.links.new(coord_node.outputs[0], map_node.inputs[0])
        nt.links.new(map_node.outputs[0], ramp1_node.inputs[0])
        nt.links.new(map_node.outputs[0], mult1_node.inputs[0])
        nt.links.new(mult1_node.outputs[0], clouds_node.inputs[1])
        nt.links.new(clouds_node.outputs[0], ramp2_node.inputs[0])
        nt.links.new(ramp2_node.outputs[0], couv_node.inputs[0])
        nt.links.new(couv_node.outputs[0], mix1_node.inputs[1])
        nt.links.new(ramp1_node.outputs[0], mix1_node.inputs[0])
        nt.links.new(mix1_node.outputs[0], mix2_node.inputs[0])
        nt.links.new(ramp2_node.outputs[0], mix2_node.inputs[2])
        nt.links.new(transition_node.outputs[0], mix2_node.inputs[1])
        nt.links.new(sky_node.outputs[0], transition_node.inputs[0])
        nt.links.new(mix2_node.outputs[0], mix3_node.inputs[1])
        nt.links.new(stars_node.outputs[0], ramp3_node.inputs[0])
        nt.links.new(ramp3_node.outputs[0], shine_node.inputs[0])
        nt.links.new(shine_node.outputs[0], mix4_node.inputs[1])
        nt.links.new(mix4_node.outputs[0], mix3_node.inputs[2])
        nt.links.new(ramp1_node.outputs[0], mix4_node.inputs[0])
        nt.links.new(ramp4_node.outputs[0], mix3_node.inputs[0])
        nt.links.new(mix3_node.outputs[0], background_node.inputs[0])

        return {'FINISHED'}


def menu_item(self, context):
    self.layout.operator(fastterrain.bl_idname, text="Terrain - Fast Landscape", icon="MESH_GRID")
    self.layout.operator(fastocean.bl_idname, text="Water - Fast Landscape", icon='MOD_WAVE')
    self.layout.operator(collider_ocean.bl_idname, text="Collide with ocean - Fast Landscape", icon="MOD_OCEAN")

    self.layout.operator(fastsky.bl_idname, text="Sky - Fast Landscape", icon="WORLD_DATA")


def register():
    bpy.utils.register_class(panelsky)
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_mesh_add.append(menu_item)


def unregister():
    bpy.utils.unregister_class(panelsky)
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_mesh_add.remove(menu_item)

if __name__ == "__main__":
    register()
