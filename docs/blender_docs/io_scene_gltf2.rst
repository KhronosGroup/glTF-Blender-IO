
********
glTF 2.0
********

.. admonition:: Reference
   :class: refbox

   :Category:  Import-Export
   :Menu:      :menuselection:`File --> Import/Export --> glTF 2.0 (.glb, .gltf)`


Usage
=====

glTF™ (GL Transmission Format) is used for transmission and loading of 3D models
in web and native applications. glTF reduces the size of 3D models and
the runtime processing needed to unpack and render those models.
This format is commonly used on the web, and has support in various 3D engines
such as Unity3D, Unreal Engine 4, and Godot.

This importer/exporter supports the following glTF 2.0 features:

- Meshes
- Materials (Principled BSDF) and Shadeless (Unlit)
- Textures
- Cameras
- Punctual lights (point, spot, and directional)
- Animation (keyframe, shape key, and skinning)


Meshes
------

glTF's internal structure mimics the memory buffers commonly used by graphics chips
when rendering in real-time, such that assets can be delivered to desktop, web, or mobile clients
and be promptly displayed with minimal processing. As a result, quads and n-gons
are automatically converted to triangles when exporting to glTF.
Discontinuous UVs and flat-shaded edges may result in moderately higher vertex counts in glTF
compared to Blender, as such vertices are separated for export.
Likewise, curves and other non-mesh data are not preserved,
and must be converted to meshes prior to export.


Materials
---------

The core material system in glTF supports a metal/rough :abbr:`PBR (Physically Based Rendering)` workflow
with the following channels of information:

- Base Color
- Metallic
- Roughness
- Baked Ambient Occlusion
- Normal Map
- Emissive

.. figure:: /images/addons_io-gltf2_material-channels.jpg

   An example of the various image maps available in the glTF 2.0 core format. This is
   the `water bottle sample model <https://github.com/KhronosGroup/glTF-Sample-Models/tree/master/2.0/WaterBottle>`__
   shown alongside slices of its various image maps.


Imported Materials
------------------

The glTF material system is different from Blender's own materials. When a glTF file is imported,
the add-on will construct a set of Blender nodes to replicate each glTF material as closely as possible.

The importer supports Metal/Rough PBR (core glTF), Spec/Gloss PBR (``KHR_materials_pbrSpecularGlossiness``)
and Shadeless (``KHR_materials_unlit``) materials.

.. tip::

   Examining the result of the material import process is a good way to see examples of
   the types of material nodes and settings that can be exported to glTF.


Exported Materials
------------------

The exporter supports Metal/Rough PBR (core glTF) and Shadeless (``KHR_materials_unlit``) materials.
It will construct a glTF material based on the nodes it recognizes in the Blender material.
The material export process handles the settings described below.

.. note::

   When image textures are used by materials, glTF requires that images be in PNG or JPEG format.
   The add-on will automatically convert images from other formats, increasing export time.

.. tip::

   To create Shadeless (Unlit) materials, use the Background material type.


Base Color
^^^^^^^^^^

The glTF base color is determined by looking for a Base Color input on a Principled BSDF node.
If the input is unconnected, the input's default color (the color field next to the unconnected socket)
is used as the Base Color for the glTF material.

.. figure:: /images/addons_io-gltf2_material-baseColor-solidGreen.png

   A solid base color can be specified directly on the node.

If an Image Texture node is found to be connected to the Base Color input,
that image will be used as the glTF base color.

.. figure:: /images/addons_io-gltf2_material-baseColor-imageHookup.png

   An image is used as the glTF base color.


Metallic and Roughness
^^^^^^^^^^^^^^^^^^^^^^

These values are read from the Principled BSDF node. If both of these inputs are unconnected,
the node will display sliders to control their respective values between 0.0 and 1.0,
and these values will be copied into the glTF.

When using an image, glTF expects the metallic values to be encoded in the blue (``B``) channel,
and roughness to be encoded in the green (``G``) channel of the same image.
If images are connected to the Blender node in a manner that does not follow this convention,
the add-on may attempt to adapt the image to the correct form during exporting (with an increased export time).

In the Blender node tree, it is recommended to use a Separate RGB node
to separate the channels from an Image Texture node, and
connect the green (``G``) channel to Roughness, and blue (``B``) to Metallic.
The glTF exporter will recognize this arrangement as matching the glTF standard, and
that will allow it to simply copy the image texture into the glTF file during export.

The Image Texture node for this should have its *Color Space* set to Non-Color.

.. figure:: /images/addons_io-gltf2_material-metalRough.png

   A metallic/roughness image connected in a manner consistent with the glTF standard,
   allowing it to be used verbatim inside an exported glTF file.


Baked Ambient Occlusion
^^^^^^^^^^^^^^^^^^^^^^^

glTF is capable of storing a baked ambient occlusion map.
Currently there is no arrangement of nodes that causes Blender
to use such a map in exactly the same way as intended in glTF.
However, if the exporter finds a custom node group by the name of ``glTF Settings``, and
finds an input named ``Occlusion`` on that node group,
it will look for an Image Texture attached there to use as the occlusion map in glTF.
The effect need not be shown in Blender, as Blender has other ways of showing ambient occlusion,
but this method will allow the exporter to write an occlusion image to the glTF.
This can be useful to real-time glTF viewers, particularly on platforms where there
may not be spare power for computing such things at render time.

.. figure:: /images/addons_io-gltf2_material-occlusionOnly.png

   A pre-baked ambient occlusion map, connected to a node that doesn't render but will export to glTF.

.. tip::

   The easiest way to create the custom node group is to import an existing glTF model
   that contains an occlusion map, such as
   the `water bottle <https://github.com/KhronosGroup/glTF-Sample-Models/tree/master/2.0/WaterBottle>`__
   or another existing model. A manually created custom node group can also be used.

glTF stores occlusion in the red (``R``) channel, allowing it to optionally share
the same image with the roughness and metallic channels.

.. figure:: /images/addons_io-gltf2_material-orm-hookup.png

   This combination of nodes mimics the way glTF packs occlusion, roughness, and
   metallic values into a single image.

.. tip::

   The Cycles render engine has a Bake panel that can be used to bake
   ambient occlusion maps. The resulting image can be saved and connected
   directly to the ``glTF Settings`` node.


Normal Map
^^^^^^^^^^

To use a normal map in glTF, connect an Image Texture node's color output
to a Normal Map node's color input, and then connect the Normal Map normal output to
the Principled BSDF node's normal input. The Image Texture node
for this should have its *Color Space* property set to Non-Color.

The Normal Map node must remain on its default property of Tangent Space as
this is the only type of normal map currently supported by glTF.
The strength of the normal map can be adjusted on this node.
The exporter is not exporting these nodes directly, but will use them to locate
the correct image and will copy the strength setting into the glTF.

.. figure:: /images/addons_io-gltf2_material-normal.png

   A normal map image connected such that the exporter will find it and copy it
   to the glTF file.

.. tip::

   The Cycles render engine has a Bake panel that can be used to bake
   tangent-space normal maps from almost any other arrangement of normal vector nodes.
   Switch the Bake type to Normal. Keep the default space settings
   (space: Tangent, R: +X, G: +Y, B: +Z) when using this bake panel for glTF.
   The resulting baked image can be saved and plugged into to a new material using
   the Normal Map node as described above, allowing it to export correctly.

   See: :doc:`Cycles Render Baking </render/cycles/baking>`


Emissive
^^^^^^^^

An Image Texture node can be connected to an Emission shader node, and
optionally combined with properties from a Principled BSDF node by way of an Add shader node.

If the glTF exporter finds an image connected to the Emission shader node,
it will export that image as the glTF material's emissive texture.

.. figure:: /images/addons_io-gltf2_material-emissive.png

   An Emission node can be added to existing nodes.

.. note::

   The *Emission* input of the Principled BSDF node is not yet supported by this exporter.
   This may change in a future version.


Double Sided / Backface Culling
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For materials where only the front faces will be visible, turn on *Backface Culling* in
the *Settings* panel of an Eevee material. When using other engines (Cycles, Workbench)
you can temporarily switch to Eevee to configure this setting, then switch back.

Leave this box un-checked for double-sided materials.

.. figure:: /images/addons_io-gltf2_material-backfaceCulling.png

   The inverse of this setting controls glTF's ``DoubleSided`` flag.


Blend Modes
^^^^^^^^^^^

The Base Color input can optionally supply alpha values.
How these values are treated by glTF depends on the selected blend mode.

With the Eevee render engine selected, each material has a Blend Mode on
the material settings panel. Use this setting to define how alpha values from
the Base Color channel are treated in glTF. Three settings are supported by glTF:

Opaque
   Alpha values are ignored (the default).
Alpha Blend
   Lower alpha values cause blending with background objects.
Alpha Clip
   Alpha values below the *Clip Threshold* setting will cause portions
   of the material to not be rendered at all. Everything else is rendered as opaque.

.. figure:: /images/addons_io-gltf2_material-alphaBlend.png

   With the Eevee engine selected, a material's blend modes are configurable.

.. note::

   Be aware that transparency (or *Alpha Blend* mode) is complex for real-time engines
   to render, and may behave in unexpected ways after export. Where possible,
   use *Alpha Clip* mode instead, or place *Opaque* polygons behind only
   a single layer of *Alpha Blend* polygons.


UV Mapping
^^^^^^^^^^

Control over UV map selection and transformations is available by connecting a UV Map node
and a Mapping node to any Image Texture node.

Settings from the Mapping node are exported using a glTF extension named ``KHR_texture_transform``.
There is a mapping type selector across the top. *Point* is the recommended type for export.
*Texture* and *Vector* are also supported. The supported offsets are:

- *Location* - X and Y
- *Rotation* - Z only
- *Scale* - X and Y

For the *Texture* type, *Scale* X and Y must be equal (uniform scaling).

.. figure:: /images/addons_io-gltf2_material-mapping.png

   A deliberate choice of UV mapping.

.. tip::

   These nodes are optional. Not all glTF readers support multiple UV maps or texture transforms.


Factors
^^^^^^^

Any Image Texture nodes may optionally be multiplied with a constant color or scalar.
These will be written as factors in the glTF file, which are numbers that are multiplied
with the specified image textures. These are not common.


Example
^^^^^^^

A single material may use all of the above at the same time, if desired. This figure shows
a typical node structure when several of the above options are applied at once:

.. figure:: /images/addons_io-gltf2_material-principled.png

   A Principled BSDF material with an emissive texture.


Extensions
----------

The core glTF 2.0 format can be extended with extra information, using glTF extensions.
This allows the file format to hold details that were not considered universal at the time of first publication.
Not all glTF readers support all extensions, but some are fairly common.

Certain Blender features can only be exported to glTF via these extensions.
The following `glTF 2.0 extensions <https://github.com/KhronosGroup/glTF/tree/master/extensions>`__
are supported directly by this add-on:


.. rubric:: Import

- ``KHR_materials_pbrSpecularGlossiness``
- ``KHR_lights_punctual``
- ``KHR_materials_unlit``
- ``KHR_texture_transform``


.. rubric:: Export

- ``KHR_draco_mesh_compression``
- ``KHR_lights_punctual``
- ``KHR_materials_unlit``
- ``KHR_texture_transform``


Animation
---------

glTF allows multiple animations per file, with animations targeted to
particular objects at time of export. To ensure that an animation is included,
either (a) make it the active Action on the object, (b) create a single-strip NLA track,
or (c) stash the action.


.. rubric:: Supported

Only certain types of animation are supported:

- Keyframe (translation, rotation, scale)
- Shape keys
- Armatures / skinning

Animation of other properties, like lights or materials, will be ignored.


Custom Properties
-----------------

Custom properties on most objects are preserved in glTF export/import, and
may be used for user-specific purposes.


File Format Variations
======================

The glTF specification identifies different ways the data can be stored.
The importer handles all of these ways. The exporter will ask the user to
select one of the following forms:


glTF Binary (``.glb``)
----------------------

This produces a single ``.glb`` file with all mesh data, image textures, and
related information packed into a single binary file.

.. tip::

   Using a single file makes it easy to share or copy the model to other systems and services.


glTF Separate (``.gltf`` + ``.bin`` + textures)
-----------------------------------------------

This produces a JSON text-based ``.gltf`` file describing the overall structure,
along with a ``.bin`` file containing mesh and vector data, and
optionally a number of ``.png`` or ``.jpg`` files containing image textures
referenced by the ``.gltf`` file.

.. tip::

   Having an assortment of separate files makes it much easier for a user to
   go back and edit any JSON or images after the export has completed.

.. note::

   Be aware that sharing this format requires sharing all of these separate files
   together as a group.


glTF Embedded (``.gltf``)
-------------------------

This produces a JSON text-based ``.gltf`` file, with all mesh data and
image data encoded (using Base64) within the file. This form is useful if
the asset must be shared over a plain-text-only connection.

.. warning::

   This is the least efficient of the available forms, and should only be used when required.


Properties
==========

Import
------

Pack Images
   Pack all images into the blend-file.
Shading
   How normals are computed during import.


Export
------

General Tab
^^^^^^^^^^^

Format
   See: `File Format Variations`_
Selected Objects
   Export selected objects only.
Apply Modifiers
   Apply modifiers (excluding armatures) to mesh objects.
Y Up
   Export using glTF convention, +Y up.
Custom Properties
   Export custom properties as glTF extras.
Remember Export Settings
   Store export settings in the Blender file, so they will be recalled next time
   the file is opened.
Copyright
   Legal rights and conditions for the model.


Meshes Tab
^^^^^^^^^^

UVs
   Export UVs (texture coordinates) with meshes.
Normals
   Export vertex normals with meshes.
Tangents
   Export vertex tangents with meshes.
Vertex Colors
   Export vertex colors with meshes.
Materials
   Export materials.
Draco mesh compression
   Compress meshes using Google Draco.
Compression level
   Higher compression results in slower encoding and decoding.
Position quantization bits
   Higher values result in better compression rates.
Normal quantization bits
   Higher values result in better compression rates.
Texcoord quantization bits
   Higher values result in better compression rates.


Objects Tab
^^^^^^^^^^^

Cameras
   Export cameras.
Punctual Lights
   Export directional, point, and spot lights. Uses the ``KHR_lights_punctual`` glTF extension.


Animation Tab
^^^^^^^^^^^^^

Use Current Frame
   Export the scene in the current animation frame.
Animations
   Exports active actions and NLA tracks as glTF animations.
Limit to Playback Range
   Clips animations to selected playback range.
Sampling Rate
   How often to evaluate animated values (in frames).
Always Sample Animations
   Apply sampling to all animations.
Skinning
   Export skinning (armature) data.
Bake Skinning Constraints
   Apply skinning constraints to armatures.
Include All Bone Influences
   Allow >4 joint vertex influences. Models may appear incorrectly in many viewers.
Shape Keys
   Export shape keys (morph targets).
Shape Key Normals
   Export vertex normals with shape keys (morph targets).
Shape Key Tangents
   Export vertex tangents with shape keys (morph targets).


Contributing
============

This importer/exporter is developed through
the `glTF-Blender-IO repository <https://github.com/KhronosGroup/glTF-Blender-IO>`__,
where you can file bug reports, submit feature requests, or contribute code.

Discussion and development of the glTF 2.0 format itself takes place on
the Khronos Group `glTF GitHub repository <https://github.com/KhronosGroup/glTF>`__,
and feedback there is welcome.
