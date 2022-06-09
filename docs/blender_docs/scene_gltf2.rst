
********
glTF 2.0
********

.. reference::

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
- Extensions (listed below)
- Extras (custom properties)
- Animation (keyframe, shape key, and skinning)


Meshes
======

glTF's internal structure mimics the memory buffers commonly used by graphics chips
when rendering in real-time, such that assets can be delivered to desktop, web, or mobile clients
and be promptly displayed with minimal processing. As a result, quads and n-gons
are automatically converted to triangles when exporting to glTF.
Discontinuous UVs and flat-shaded edges may result in moderately higher vertex counts in glTF
compared to Blender, as such vertices are separated for export.
Likewise, curves and other non-mesh data are not preserved,
and must be converted to meshes prior to export.


Materials
=========

The core material system in glTF supports a metal/rough :abbr:`PBR (Physically Based Rendering)` workflow
with the following channels of information:

- Base Color
- Metallic
- Roughness
- Baked Ambient Occlusion
- Normal Map (tangent space, +Y up)
- Emissive

Some additional material properties or types of materials can be expressed using glTF extensions. The complete is can be found in _Extensions_ part of this documentation.

.. figure:: /images/addons_import-export_scene-gltf2_material-channels.jpg

   An example of the various image maps available in the glTF 2.0 core format. This is
   the `water bottle sample model <https://github.com/KhronosGroup/glTF-Sample-Models/tree/master/2.0/WaterBottle>`__
   shown alongside slices of its various image maps.


Imported Materials
------------------

The glTF material system is different from Blender's own materials. When a glTF file is imported,
the add-on will construct a set of Blender nodes to replicate each glTF material as closely as possible.

The importer supports Metal/Rough PBR (core glTF), Spec/Gloss PBR (``KHR_materials_pbrSpecularGlossiness``)
and some extension materials. The complete is can be found in _Extensions_ part of this documentation.

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


Base Color
^^^^^^^^^^

The glTF base color is determined by looking for a Base Color input on a Principled BSDF node.
If the input is unconnected, the input's default color (the color field next to the unconnected socket)
is used as the Base Color for the glTF material.

.. figure:: /images/addons_import-export_scene-gltf2_material-base-color-solid-green.png

   A solid base color can be specified directly on the node.

If an Image Texture node is found to be connected to the Base Color input,
that image will be used as the glTF base color.

.. figure:: /images/addons_import-export_scene-gltf2_material-base-color-image-hookup.png

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

.. figure:: /images/addons_import-export_scene-gltf2_material-metal-rough.png

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

.. figure:: /images/addons_import-export_scene-gltf2_material-occlusion-only.png

   A pre-baked ambient occlusion map, connected to a node that doesn't render but will export to glTF.

.. tip::

   The easiest way to create the custom node group is to import an existing glTF model
   that contains an occlusion map, such as
   the `water bottle <https://github.com/KhronosGroup/glTF-Sample-Models/tree/master/2.0/WaterBottle>`__
   or another existing model. A manually created custom node group can also be used.

glTF stores occlusion in the red (``R``) channel, allowing it to optionally share
the same image with the roughness and metallic channels.

.. figure:: /images/addons_import-export_scene-gltf2_material-orm-hookup.png

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

.. figure:: /images/addons_import-export_scene-gltf2_material-normal.png

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

An Image Texture node can be connected to the Emission input on the Principled BSDF node
to include an emissive map with the glTF material. Alternatively, the Image Texture node
can be connected to an Emission shader node, and optionally combined with properties
from a Principled BSDF node by way of an Add Shader node.

If the emissive map is alone in the material, it is best to set the Base Color default
to black, and the Roughness default to 1.0. This minimizes the influence of the other
channels if they are not needed.

.. figure:: /images/addons_import-export_scene-gltf2_material-emissive.png

   This arrangement is supported for backwards compatibility. It is simpler to use
   the Principled BSDF node directly.

If any component of emissiveFactor is > 1.0, ``KHR_materials_emissive_strength`` extension will be used.


Clearcoat
^^^^^^^^^

When the *Clearcoat* input on the Principled BSDF node has a nonzero default value or
Image Texture node connected, the ``KHR_materials_clearcoat`` glTF extension will be
included in the export. This extension will also include a value or Image Texture
from the *Clearcoat Roughness* input if available.

If Image Textures are used, glTF requires that the clearcoat values be written to
the red (``R``) channel, and *Clearcoat Roughness* to the green (``G``) channel.
If monochrome images are connected, the exporter will remap them to these color channels.

The *Clearcoat Normal* input accepts the same kinds of inputs as the base Normal input,
specifically a tangent-space normal map with +Y up, and a user-defined strength.
This input can reuse the same normal map that the base material is using,
or can be assigned its own normal map, or can be left disconnected for a smooth coating.

All Image Texture nodes used for clearcoat shading should have their *Color Space* set to Non-Color.

.. figure:: /images/addons_import-export_scene-gltf2_material-clearcoat.png

   An example of a complex clearcoat application that will export correctly to glTF.
   A much simpler, smooth coating can be applied from just the Principled BSDF node alone.


Transmission
^^^^^^^^^^^^

When the Transmission input on the Principled BSDF node has a nonzero default value or
Image Texture node connected, the ``KHR_materials_transmission`` glTF extension will be
included in the export. When a texture is used, glTF stores the values in the red (``R``) channel.
The *Color Space* should be set to Non-Color.

Transmission is different from alpha blending, because transmission allows full-strength specular reflections.
In glTF, alpha blending is intended to represent physical materials that are partially missing from
the specified geometry, such as medical gauze wrap. Transmission is intended to represent physical materials
that are solid but allow non-specularly-reflected light to transmit through the material, like glass.

glTF does not offer a separate "Transmission Roughness", but the material's base roughness
can be used to blur the transmission, like frosted glass.

.. tip::

   Typically the alpha blend mode of a transmissive material should remain "Opaque",
   the default setting, unless the material only partially covers the specified geometry.

.. note::

   In real-time engines where transmission is supported, various technical limitations in
   the engine may determine which parts of the scene are visible through the transmissive surface.
   In particular, transmissive materials may not be visible behind other transmissive materials.
   These limitations affect physically-based transmission, but not alpha-blended non-transmissive materials.

.. warning::

   Transmission is complex for real-time rendering engines to implement,
   and support for the ``KHR_materials_transmission`` glTF extension is not yet widespread.

IOR
^^^

At import, there are two different situation:

- if ``KHR_materials_ior`` is not set, IOR value of Principled BSDF node is set to 1.5, that is the glTF default value of IOR.
- If set, the ``KHR_materials_ior`` is used to set the IOR value of Principled BSDF.

At export, IOR is included in the export only if one of these extensions are also used:

- ``KHR_materials_transmission``
- ``KHR_materials_volume``
- ``KHR_materials_specular``

IOR of 1.5 are not included in the export, because this is the default glTF IOR value.

Volume
^^^^^^

Volume can be exported using a Volume Absorption node, linked to Volume socket of Output node.
Data will be exported using the ``KHR_materials_volume`` extension.
For volume to be exported, some _transmission_ must be set on Principled BSDF node.
Color of Volume Absorption node is used as glTF attenuation color. No texture is allowed for this property.
Density of Volume Absorption node is used as inverse of glTF attenuation distance.
Thickess can be plugged into the Thickess socket of custom group node ``glTF Settings``. 
If a texture is used for thickness, it must be plugged on (``G``) Green channel of the image.

.. figure:: /images/addons_import-export_scene-gltf2_material-volume.png


Double-Sided / Backface Culling
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For materials where only the front faces will be visible, turn on *Backface Culling* in
the *Settings* panel of an Eevee material. When using other engines (Cycles, Workbench)
you can temporarily switch to Eevee to configure this setting, then switch back.

Leave this box unchecked for double-sided materials.

.. figure:: /images/addons_import-export_scene-gltf2_material-backface-culling.png

   The inverse of this setting controls glTF's ``DoubleSided`` flag.


Blend Modes
^^^^^^^^^^^

The Base Color input can optionally supply alpha values.
How these values are treated by glTF depends on the selected blend mode.

With the Eevee render engine selected, each material has a Blend Mode on
the material settings panel. Use this setting to define how alpha values from
the Base Color channel are treated in glTF. Three settings are supported by glTF:

Opaque
   Alpha values are ignored.
Alpha Blend
   Lower alpha values cause blending with background objects.
Alpha Clip
   Alpha values below the *Clip Threshold* setting will cause portions
   of the material to not be rendered at all. Everything else is rendered as opaque.

.. figure:: /images/addons_import-export_scene-gltf2_material-alpha-blend.png

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

.. figure:: /images/addons_import-export_scene-gltf2_material-mapping.png

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

.. figure:: /images/addons_import-export_scene-gltf2_material-principled.png

   A Principled BSDF material with an emissive texture.


Exporting a Shadeless (Unlit) Material
--------------------------------------

To export an unlit material, mix in a camera ray, and avoid using the Principled BSDF node.

.. figure:: /images/addons_import-export_scene-gltf2_material-unlit.png

   One of several similar node arrangements that will export
   ``KHR_materials_unlit`` and render shadeless in Blender.


Extensions
==========

The core glTF 2.0 format can be extended with extra information, using glTF extensions.
This allows the file format to hold details that were not considered universal at the time of first publication.
Not all glTF readers support all extensions, but some are fairly common.

Certain Blender features can only be exported to glTF via these extensions.
The following `glTF 2.0 extensions <https://github.com/KhronosGroup/glTF/tree/master/extensions>`__
are supported directly by this add-on:


.. rubric:: Import

- ``KHR_materials_pbrSpecularGlossiness``
- ``KHR_materials_clearcoat``
- ``KHR_materials_transmission``
- ``KHR_materials_unlit``
- ``KHR_materials_emissive_strength``
- ``KHR_materials_volume``
- ``KHR_materials_ior``
- ``KHR_lights_punctual``
- ``KHR_texture_transform``
- ``KHR_mesh_quantization``



.. rubric:: Export

- ``KHR_draco_mesh_compression``
- ``KHR_lights_punctual``
- ``KHR_materials_clearcoat``
- ``KHR_materials_transmission``
- ``KHR_materials_unlit``
- ``KHR_materials_emissive_strength``
- ``KHR_materials_ior``
- ``KHR_texture_transform``
- ``KHR_materials_volume``


Third-party glTF Extensions
---------------------------

It is possible for Python developers to add Blender support for additional glTF extensions by writing their
own third-party add-on, without modifying this glTF add-on. For more information, `see the example on GitHub
<https://github.com/KhronosGroup/glTF-Blender-IO/tree/master/example-addons/>`__ and if needed,
`register an extension prefix <https://github.com/KhronosGroup/glTF/blob/master/extensions/Prefixes.md>`__.


Custom Properties
=================

Custom properties are always imported, and will be exported from most objects
if the :menuselection:`Include --> Custom Properties` option is selected before export.
These are stored in the ``extras`` field on the corresponding object in the glTF file.

Unlike glTF extensions, custom properties (extras) have no defined namespace,
and may be used for any user-specific or application-specific purposes.


Animation
=========

A glTF animation changes the transforms of objects or pose bones, or the values of shape keys.
One animation can affect multiple objects, and there can be multiple animations in a glTF file.


Import
------

Imported models are set up so that the first animation in the file is playing automatically.
Scrub the Timeline to see it play.

When the file contains multiple animations, the rest will be organized using
the :doc:`Nonlinear Animation editor </editors/nla/tracks>`. Each animation
becomes an action stashed to an NLA track. The track name is the name of the glTF animation.
To make the animation within that track visible, click Solo (star icon) next to the track you want to play.

.. _fig-gltf-solo-track:

.. figure:: /images/addons_import-export_scene-gltf2_animation-solo-track.png

   This is the `fox sample model <https://github.com/KhronosGroup/glTF-Sample-Models/tree/master/2.0/Fox>`__
   showing its "Run" animation.

If an animation affects multiple objects, it will be broken up into multiple parts.
The part of the animation that affects one object becomes an action stashed on that object.
Use the track names to tell which actions are part of the same animation.
To play the whole animation, you need to enable Solo (star icon) for all its tracks.

.. note::

   There is currently no way to see the non-animated pose of a model that had animations.


Export
------

You can export animations by creating actions. How glTF animations are made from actions is controlled by
the :menuselection:`Animation --> Group by NLA Track` export option.


.. rubric:: Group by NLA Track on (default)

An action will be exported if it is the active action on an object, or it is stashed to an NLA track
(e.g. with the *Stash* or *Push Down* buttons in the :doc:`Action Editor </editors/dope_sheet/action>`).
Actions which are **not** associated with an object in one of these ways are **not exported**.
If you have multiple actions you want to export, make sure they are stashed!

A glTF animation can have a name, which is the action name by default. You can override it
by renaming its NLA track from ``NLATrack``/``[Action Stash]`` to the name you want to use.
For example, the Fig. :ref:`fox model <fig-gltf-solo-track>` will export with three animations,
"Survey", "Walk", and "Run".
If you rename two tracks on two different objects to the same name, they will become part
of the same glTF animation and will play together.

The importer organizes actions so they will be exported correctly with this mode.


.. rubric:: Group by NLA Track off

In this mode, the NLA organization is not used, and only one animation is exported using
the active actions on all objects.

.. note::

   For both modes, remember only certain types of animation are supported:

   - Object transform (location, rotation, scale)
   - Pose bones
   - Shape key values

   Animation of other properties, like physics, lights, or materials, will be ignored.

.. note::

   In order to sample shape key animations controlled by drivers using bone transformations,
   they must be on a mesh object that is a direct child of the bones' armature.


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
Guess Original Bind Pose
   Determines the pose for bones (and consequently, skinned meshes) in Edit Mode.
   When on, attempts to guess the pose that was used to compute the inverse bind matrices.
Bone Direction
   Changes the heuristic the importer uses to decide where to place bone tips.
   Note that the Fortune setting may cause inaccuracies in models that use non-uniform scaling.
   Otherwise this is purely aesthetic.


Export
------

Format
   See: `File Format Variations`_.
Textures
   Folder to place texture files in. Relative to the gltf-file.
Copyright
   Legal rights and conditions for the model.
Remember Export Settings
   Store export settings in the blend-file,
   so they will be recalled next time the file is opened.


Include
^^^^^^^

Selected Objects
   Export selected objects only.
Visible Objects
   Export visible objects only.
Renderable Objects
   Export renderable objects only.
Active Collection
   Export objects from active collection only.
Active Scene
   Export active scene only.
Custom Properties
   Export custom properties as glTF extras.
Cameras
   Export cameras.
Punctual Lights
   Export directional, point, and spot lights. Uses the ``KHR_lights_punctual`` glTF extension.


Transform
^^^^^^^^^

Y Up
   Export using glTF convention, +Y up.


Geometry
^^^^^^^^

Apply Modifiers
   Export objects using the evaluated mesh, meaning the resulting mesh after all
   :doc:`Modifiers </modeling/modifiers/index>` have been calculated.
UVs
   Export UVs (texture coordinates) with meshes.
Normals
   Export vertex normals with meshes.
Tangents
   Export vertex tangents with meshes.
Vertex Colors
   Export Color Attributes with meshes.
Loose Edges
   Export loose edges as lines, using the material from the first material slot.
Loose Points
   Export loose points as glTF points, using the material from the first material slot.
Materials
   Export full materials, only placeholders (all primitives but without materials), 
   or does not export materials. (In that last case, primitive are merged, lossing material slot information).
Images
   Output format for images. PNG is lossless and generally preferred, but JPEG might be preferable for
   web applications due to the smaller file size.
   If None is chosen, materials are exported without textures.


Compression
"""""""""""

Compress meshes using Google Draco.

Compression Level
   Higher compression results in slower encoding and decoding.
Quantization Position
   Higher values result in better compression rates.
Normal
   Higher values result in better compression rates.
Texture Coordinates
   Higher values result in better compression rates.
Color
   Higher values result in better compression rates.
Generic
   Higher values result in better compression rates.


Animation
^^^^^^^^^

Use Current Frame
   Export the scene in the current animation frame.
   For rigs, when off, rest pose is used as default pose for joints in glTF file.
   When on, the current frame is used as default pose for joints in glTF file.


Animation
"""""""""

Exports active actions and NLA tracks as glTF animations.

Limit to Playback Range
   Clips animations to selected playback range.
Sampling Rate
   How often to evaluate animated values (in frames).
Always Sample Animations
   Apply sampling to all animations.
Group by NLA Track
   Whether to export NLA strip animations.
Optimize Animation Size
   Reduce exported file-size by removing duplicate keyframes.
Export Deformation Bones Only
   Export deformation bones only.


Shape Keys
""""""""""

Export shape keys (morph targets).

Shape Key Normals
   Export vertex normals with shape keys (morph targets).
Shape Key Tangents
   Export vertex tangents with shape keys (morph targets).


Skinning
""""""""

Export skinning (armature) data.

Include All Bone Influences
   Allow more than 4 joint vertex influences. Models may appear incorrectly in many viewers.


Contributing
============

This importer/exporter is developed through
the `glTF-Blender-IO repository <https://github.com/KhronosGroup/glTF-Blender-IO>`__,
where you can file bug reports, submit feature requests, or contribute code.

Discussion and development of the glTF 2.0 format itself takes place on
the Khronos Group `glTF GitHub repository <https://github.com/KhronosGroup/glTF>`__,
and feedback there is welcome.
