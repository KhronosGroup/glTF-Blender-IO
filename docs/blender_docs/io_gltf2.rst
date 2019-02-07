
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


.. rubric:: Supported

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


Materials
---------

Import
^^^^^^

Supports Metal/Rough PBR (Principled BSDF), Spec/Gloss PBR and Shadeless (Unlit) materials.


Export
^^^^^^

Supports Metal/Rough PBR (Principled BSDF) and Shadeless (Unlit) materials.


.. rubric:: Supported

Only certain properties of the Principled BSDF material are supported:

- Base Color
- Metallic (``B`` channel)
- Roughness (``G`` channel)
- Normal
- Tangent
- Blend Mode (Opaque, Alpha Blend, Alpha Clip)

.. note::

   To create Shadeless (Unlit) materials, use the Background material type.

Complex nodes cannot be exported. For best results when using nodes, prefer
the following structure:

.. figure:: /images/addons_io-gltf2-material-principled.png
   :alt: A Principled BSDF node uses multiple Image Texture inputs.
         Each texture takes a Mapping Vector, with a UV Map as its input.
         Roughness must use the ``G`` channel of its texture, and
         Metalness must use the ``B`` channel. The output of the Principled BSDF node
         is added to an Emission node, and the sum is connected to the Material Output node.

   A Principled BSDF material with an emissive texture.

Image Texture nodes may be multiplied with a constant color or scalar.


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


Properties
==========

Import
------

Log Level
   Set level of log to display.
Pack Images
   Pack all images into the blend-file.
Shading
   How normals are computed during import.


Export
------

General
^^^^^^^

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
   Apply modifiers to mesh objects.
Y Up
   Export using glTF convention, +Y up.
Custom Properties
   Export custom properties as glTF extras.
Remember Export Settings
   Store export settings in the Blender file, so they will be recalled next time
   the file is opened.
Copyright
   Legal rights and conditions for the model.


Meshes
^^^^^^

UVs
   Export UVs (texture coordinates) with meshes.
Normals
   Export vertex normals with meshes.
Tangents
   Export vertex tangents with meshes.
Vertex Colors
   Export vertex colors with meshes.


Objects
^^^^^^^

Cameras
   Export cameras.
Punctual Lights
   Export directional, point, and spot lights. Uses the ``KHR_lights_punctual`` glTF extension.


Materials
^^^^^^^^^

Materials
   Export materials.
Texture Transforms
   Export texture or UV position, rotation, and scale. Uses the ``KHR_texture_transform`` glTF extension.


Animation
^^^^^^^^^

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

glTF 2.0 is a relatively new file format. Discussion and development of the format
occur on the Khronos Group `GitHub repository <https://github.com/KhronosGroup/glTF>`__,
and feedback there is welcome. This importer/exporter is developed through
the `Blender glTF IO repository <https://github.com/KhronosGroup/glTF-Blender-IO>`__,
where you can file bug reports, submit feature requests, or contribute code.
