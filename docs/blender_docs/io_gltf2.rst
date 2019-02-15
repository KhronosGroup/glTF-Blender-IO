
********
glTF 2.0
********

:Name: glTF 2.0 format
:Location: :menuselection:`File --> Import/Export --> glTF 2.0 (.glb, .gltf)`
:Version: 0.0.1
:Blender: 2.80
:Category: Import-Export
:Authors: Julien Duroure, Norbert Nopper, Urs Hanselmann, Moritz Becher, Benjamin Schmithüsen, Khronos Group, Mozilla


Usage
=====

glTF™ (GL Transmission Format) is used for transmission and loading of 3D models
in web and native applications. glTF reduces the size of 3D models and
the runtime processing needed to unpack and render those models.
This format is commonly used on the web, and has upcoming support in native 3D engines
such as Unity3D and Unreal Engine 4.

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
when rendering in real-time, such that assets can be delivered to desktop, web, or mobile
clients and be promptly displayed with minimal processing.  As a result, quads and N-gons
(faces with more than 3 edges) are automatically converted to triangles when
exporting to glTF.  Likewise, curves and and other non-mesh data are not preserved,
and must be converted to meshes prior to export.

Materials
---------

The core material system in glTF supports a metal/rough PBR workflow with the following
channels of information:

- Base Color
- Metallic
- Roughness
- Baked Ambient Occlusion
- Normal Map
- Emissive

Imported Materials
------------------

The glTF material system is different from Blender's own materials.  When a glTF file
is imported, this addon will construct a set of Blender nodes to replicate each glTF material
as closely as possible.

The importer supports Metal/Rough PBR (core glTF), Spec/Gloss PBR (``KHR_materials_pbrSpecularGlossiness``)
and Shadeless (``KHR_materials_unlit``) materials.

.. tip::

   Examining the result of the material import process is a good way to see examples of the
   types of material nodes and settings that can be exported to glTF.


Exported Materials
------------------

The exporter supports Metal/Rough PBR (core glTF) and Shadeless (``KHR_materials_unlit``) materials.  It
will construct a glTF material based on the nodes it recognizes in the Blender material.

.. tip::

   To create Shadeless (Unlit) materials, use the Background material type.

The material export process handles the following settings:

- `Base Color`_
- `Metallic and Roughness`_
- `Baked Ambient Occlusion`_
- `Normal Map`_
- `Emissive`_
- `Double Sided`_
- `Blend Modes`_
- `UV Mapping`_
- `Factors`_

See also: `Putting it All Together`_

.. note::

   When image textures are used by materials, glTF requires that images be in PNG or JPEG format.
   This addon will automatically convert images from other formats, increasing export time.

Base Color
^^^^^^^^^^

The glTF base color is determined by looking for a Base Color input on a
"Principled BSDF" node.  If the input is disconnected, the input's default color
(the color swatch next to the disconnected input) is used as the Base Color for
the glTF material.

If an "Image Texture" node is found to be connected to the Base Color input, that
image will be used as the glTF base color.

Metallic and Roughness
^^^^^^^^^^^^^^^^^^^^^^

These values are read from the "Principled BSDF" node.  If both of these inputs
are disconnected, the node will display sliders to control their respective
values between 0.0 and 1.0, and these values will be copied into the glTF.

When using an image, glTF expects the metallic values to be encoded in the
Blue (``B``) channel, and roughness to be encoded in the Green (``G``) channel of the
same image.  If images are connected to the Blender node in a manner that
does not follow this convention, this addon may attempt to adapt the image
to the correct form during export, increasing export time.

In the Blender node graph, it is recommended to use a "Separate RGB" node
to separate the channels from an "Image Texture" node, and connect the
Green (``G``) channel to Roughness, and Blue (``B``) to Metallic.  The glTF exporter
will recognize this arrangement as matching the glTF standard, and that will
allow it to simply copy the image texture into the glTF file during export.

The Image Texture node for this should have its "Colorspace" setting
configured to "Non-Color Data".

.. figure:: /images/addons_io-gltf2-material-metalRough.png
   :alt: A metallic-roughness image connected in a manner consistent
         with the glTF standard, allowing it to be used verbatim inside
         an exported glTF file.

   A metallic/roughness image connected in a manner consistent
   with the glTF standard, allowing it to be used verbatim inside
   an exported glTF file.

Baked Ambient Occlusion
^^^^^^^^^^^^^^^^^^^^^^^

glTF is capable of storing a baked ambient occlusion map.  Currently there
is no arrangement of nodes that causes Blender to use such a map in exactly
the same way as glTF intends it to be used.  However, if the exporter finds
a custom node group by the name of ``glTF Metallic Roughness``, and finds an
input named ``Occlusion`` on that node group, it will look for an Image Texture
attached there to use as the occlusion map in glTF.  The effect need not be shown
in Blender, as Blender has other ways of showing ambient occlusion, but this
method will allow the exporter to write an occlusion image to the glTF.

glTF stores occlusion in the Red (``R``) channel, allowing it to optionally share
the same image with the Roughness and Metallic channels.

Normal Map
^^^^^^^^^^

To use a Normal Map in glTF, connect an "Image Texture" node's color output
to a "Normal Map" node's color input, and then connect the "Normal Map" normal
output to the "Principled BSDF" node's "Normal" input.  The Image Texture node
for this should have its "Colorspace" setting configured to "Non-Color Data".

The "Normal Map" node must remain on its default setting of "Tangent Space" as
this is the only type of normal map currently supported by glTF.  The strength
of the normal map can be adjusted on this node.  The exporter isn't exporting
these nodes directly, but will use them to locate the correct image and will
copy the strength setting into the glTF.

.. figure:: /images/addons_io-gltf2-material-normal.png
   :alt: A normal map image connected such that the exporter will find it and copy it
         to the glTF file.

   A normal map image connected such that the exporter will find it and copy it
   to the glTF file.

.. tip::

   Blender's "Cycles" rendering engine has a "Bake" panel that can be used to bake
   tangent-space normal maps from almost any other arrangement of normal vector
   nodes.  Switch the "Bake type" to "Normal".  Keep the default space settings
   (Space: Tangent, R: +X, G: +Y, B: +Z) when using this bake panel for glTF.
   The resulting baked image can be saved and hooked up to a new material using
   the Normal Map node as described above.

Emissive
^^^^^^^^

An "Image Texture" node can be connected to an "Emission" shader node, and optionally
combined with settings from a "Principled BSDF" node by way of an "Add" shader node.

If the glTF exporter finds an image connected to the Emission shader node, it will
export that image as the glTF material's emissive image.

Double Sided
^^^^^^^^^^^^

In glTF, double-sided is a property that is applied per-material, not per-viewport
or per-mesh, so it has no exact equivalent within Blender.  It can be thought of as
a combination of backface culling (in Blender's viewport) and double-sided lighting
(a Blender mesh property).

When ``false`` (the default), backface culling is used, and the backs of faces in
the glTF will not be visible in other software.  When ``true``, backface culling
is disabled, and double-sided lighting is used, automatically reversing the normal
vectors of any visible back faces.

To set this value to true, create a custom node group by the name of
``glTF Metallic Roughness``, add an input value named ``DoubleSided`` with a range
of 0.0 to 1.0, and set it to 1.0.  There will be no equivalent effect in Blender,
but the exporter will enable double-sided mode in glTF for this material.

Blend Modes
^^^^^^^^^^^

The Base Color input value, or Base Color image, can optionally supply alpha values.
How these values are treated by glTF depends on the selected blend mode.

With the "Eevee" rendering engine selected, each material has a "Blend Mode" on the
material settings panel.  Use this setting to govern how alpha values from the
Base Color channel are treated in glTF.  Three settings are supported by glTF:

- **Opaque** - Alpha values are ignored (the default).
- **Alpha Blend** - Lower alpha values cause blending with background objects.
- **Alpha Clip** - Alpha values below the **Clip Threshold** setting will cause portions
  of the material to not be rendered at all.  Everything else is rendered as opaque.

.. note::

   Be aware that transparency (or **Alpha Blend** mode) is complex for real-time engines
   to render, and may behave in unexpected ways after export. Where possible, use
   **Alpha Clip** mode instead, or place **Opaque** polygons behind only a single
   layer of **Alpha Blend** polygons.

UV Mapping
^^^^^^^^^^

Control over UV map selection and transformations is available by connecting a "UV Map"
node and a "Mapping" node to any "Image Texture" node.

Settings from the "Mapping" node are exported using a glTF extension named
``KHR_texture_transform``.  The supported mapping types from the selector across the
top of the node are **Texture** and **Point**.  The supported offsets are:

- **Location** - ``X`` and ``Y``
- **Rotation** - ``Z`` only
- **Scale** - ``X`` and ``Y``

.. figure:: /images/addons_io-gltf2-material-mapping.png
   :alt: A deliberate choice of UV mapping.

   A deliberate choice of UV mapping.

.. note::

   These nodes are optional.  Not all glTF readers support multiple UV maps or texture transforms.

Putting it All Together
^^^^^^^^^^^^^^^^^^^^^^^

A single material may use all of the above at the same time, if desired.  This figure shows
a typical node structure when several of the above options are applied at once:

.. figure:: /images/addons_io-gltf2-material-principled.png
   :alt: A Principled BSDF node uses multiple Image Texture inputs.
         Each texture takes a Mapping Vector, with a UV Map as its input.
         Roughness must use the ``G`` channel of its texture, and
         Metallic must use the ``B`` channel. The output of the Principled BSDF node
         is added to an Emission node, and the sum is connected to the Material Output node.

   A Principled BSDF material with an emissive texture.

Factors
^^^^^^^

Any Image Texture nodes may optionally be multiplied with a constant color or scalar.
These will be written as "factors" in the glTF file, which are numbers that multiply
with specified image textures.  These are not common.


Extensions
----------

Certain features require extensions to the core format specification. The following
`glTF 2.0 extensions <https://github.com/KhronosGroup/glTF/tree/master/extensions>`__
are supported:

**Import**

- ``KHR_materials_pbrSpecularGlossiness``
- ``KHR_lights_punctual``
- ``KHR_materials_unlit``

**Export**

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

The glTF specification identifies different ways the data can be stored.  The
importer handles all of these ways.  The exporter will ask the user to
select one of the following forms:

glTF Binary (``.glb``)
^^^^^^^^^^^^^^^^^^^^^^

This produces a single ``.glb`` file with all mesh data, image textures, and
related information packed into a single binary file.  This makes it easy to
share or copy the model to other systems and services.

This is the default.

glTF Separate (``.gltf`` + ``.bin`` + textures)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This produces a JSON text-based ``.gltf`` file describing the overall structure,
along with a ``.bin`` file containing mesh and vector data, and optionally a
number of ``.png`` or ``.jpg`` files containing image textures referenced by
the ``.gltf`` file.

Having an assortment of separate files makes it much easier for a user to
go back and edit any JSON or images after the export has completed.

Be aware that sharing this format requires sharing all of these separate files
together as a group.

glTF Embedded (``.gltf``)
^^^^^^^^^^^^^^^^^^^^^^^^^

This produces a JSON text-based ``.gltf`` file, with all mesh data and image
data encoded (using Base64) within the file.  This form is useful if the
asset must be shared over a plain-text-only connection.

This is the least efficient of the available forms, and should only be used
when required.


Properties
==========

Import Properties
-----------------

Log Level
   Set level of log to display.
Pack Images
   Pack all images into the blend-file.
Shading
   How normals are computed during import.


Export Properties
-----------------

Tab: General
^^^^^^^^^^^^

Format
   Output format and embedding options. Binary is most efficient,
   but JSON (embedded or separate) may be easier to edit later.

   glTF Binary (``.glb``)
      Exports a single file, with all data packed in binary form.
      Most efficient and portable, but more difficult to edit later.
   glTF Embedded (``.gltf``)
      Exports a single file, with all data packed in JSON.
      Less efficient than binary, but easier to edit later.
   glTF Separate (``.gltf`` + ``.bin`` + textures)
      Exports multiple files, with separate JSON, binary and texture data.
      Easiest to edit later.

Selected Objects
   Export selected objects only.
Apply Modifiers
   Apply modifiers (excluding Armatures) to mesh objects.
Y Up
   Export using glTF convention, +Y up.
Custom Properties
   Export custom properties as glTF extras.
Remember Export Settings
   Store export settings in the Blender file, so they will be recalled next time
   the file is opened.
Copyright
   Legal rights and conditions for the model.


Tab: Meshes
^^^^^^^^^^^

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


Tab: Objects
^^^^^^^^^^^^

Cameras
   Export cameras.
Punctual Lights
   Export directional, point, and spot lights. Uses the ``KHR_lights_punctual`` glTF extension.


Tab: Animation
^^^^^^^^^^^^^^

Animations
   Exports active actions and NLA tracks as glTF animations.
Limit to Playback Range
   Clips animations to selected playback range.
Sampling Rate
   How often to evaluate animated values (in frames).
Keyframes Start at 0
   Keyframes start at 0, instead of 1.
Always Sample Animations
   Apply sampling to all animations.
Use Current Frame
   Export the scene in the current animation frame.
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
