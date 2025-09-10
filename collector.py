from __future__ import annotations

bl_info = {
    "name": "Collector V1.2",
    "author": "Were Sankofa",
    "version": (1, 2, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Collector",
    "description": (
        "Automatically organizes cameras into 'Cameras' and lights into 'Lights' collections "
        "on load or when new objects are added. Renames them sequentially for clean organization. "
        "Includes exportable organization report. Adds a quick button to set the active camera."
    ),
    "warning": "",
    "doc_url": "",
    "category": "Object",
}

import bpy
from bpy.app.handlers import persistent
from bpy.types import Operator, Panel
from bpy.props import BoolProperty
import re
import os
import datetime

HANDLERS_REGISTERED = False
TRACKED_OBJECT_IDS: set[int] = set()

TARGET_OBJECT_TYPES = {"CAMERA", "LIGHT"}
CAMERAS_COLLECTION_NAME = "Cameras"
LIGHTS_COLLECTION_NAME = "Lights"


def is_auto_enabled(scene: bpy.types.Scene | None) -> bool:
    if scene is None:
        return False
    return bool(getattr(scene, "collector_enable_auto", False))


def find_or_create_collection(name: str, scene: bpy.types.Scene) -> bpy.types.Collection:
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
    root = scene.collection
    if collection.name not in root.children.keys():
        try:
            root.children.link(collection)
        except RuntimeError:
            pass
    return collection


def move_object_exclusively_to_collection(obj: bpy.types.Object, target: bpy.types.Collection) -> None:
    if target not in obj.users_collection:
        try:
            target.objects.link(obj)
        except RuntimeError:
            pass

    for col in list(obj.users_collection):
        if col is not target:
            try:
                col.objects.unlink(obj)
            except RuntimeError:
                pass


def rename_objects_sequentially_of_type(obj_type: str) -> None:
    """
    Rename all existing objects of the given type ('CAMERA' or 'LIGHT') 
    sequentially like 'Camera 1', 'Camera 2', or 'Light 1', 'Light 2'.
    """
    type_name = "Camera" if obj_type == "CAMERA" else "Light" if obj_type == "LIGHT" else None
    if type_name is None:
        return

    objs = [o for o in bpy.data.objects if o.type == obj_type]
    objs.sort(key=lambda o: o.name.lower())

    for i, obj in enumerate(objs, start=1):
        new_name = f"{type_name} {i}"
        obj.name = new_name


def organize_scene_objects(scene: bpy.types.Scene) -> None:
    cameras_col = find_or_create_collection(CAMERAS_COLLECTION_NAME, scene)
    lights_col = find_or_create_collection(LIGHTS_COLLECTION_NAME, scene)

    rename_objects_sequentially_of_type("CAMERA")
    rename_objects_sequentially_of_type("LIGHT")

    for obj in scene.objects:
        if obj.type == "CAMERA":
            move_object_exclusively_to_collection(obj, cameras_col)
        elif obj.type == "LIGHT":
            move_object_exclusively_to_collection(obj, lights_col)


def rebuild_tracked_ids(scene: bpy.types.Scene) -> None:
    global TRACKED_OBJECT_IDS
    TRACKED_OBJECT_IDS = {id(obj) for obj in scene.objects if obj.type in TARGET_OBJECT_TYPES}


def rename_object_sequentially(obj: bpy.types.Object) -> None:
    type_name = "Camera" if obj.type == "CAMERA" else "Light" if obj.type == "LIGHT" else None
    if type_name is None:
        return

    pattern = re.compile(rf"^{type_name} (\d+)$")
    numbers = set()

    for o in bpy.data.objects:
        if o.type == obj.type:
            match = pattern.match(o.name)
            if match:
                try:
                    numbers.add(int(match.group(1)))
                except ValueError:
                    pass

    new_number = 1
    while new_number in numbers:
        new_number += 1

    obj.name = f"{type_name} {new_number}"


def organize_new_objects(scene: bpy.types.Scene) -> None:
    cameras_col = find_or_create_collection(CAMERAS_COLLECTION_NAME, scene)
    lights_col = find_or_create_collection(LIGHTS_COLLECTION_NAME, scene)

    new_objects = [
        obj for obj in scene.objects
        if obj.type in TARGET_OBJECT_TYPES and id(obj) not in TRACKED_OBJECT_IDS
    ]

    for obj in new_objects:
        rename_object_sequentially(obj)

        if obj.type == "CAMERA":
            move_object_exclusively_to_collection(obj, cameras_col)
        elif obj.type == "LIGHT":
            move_object_exclusively_to_collection(obj, lights_col)

    rebuild_tracked_ids(scene)


# New operator: Export Organization Report

class OBJECT_OT_collector_export_report(Operator):
    bl_idname = "object.collector_export_report"
    bl_label = "Export Organization Report"
    bl_description = "Export a text report of Cameras and Lights collections and their objects"
    bl_options = {"REGISTER"}

    def execute(self, context: bpy.types.Context):
        report_lines = []

        def write_collection_report(col_name):
            col = bpy.data.collections.get(col_name)
            if col is None:
                report_lines.append(f"Collection '{col_name}' not found.\n")
                return
            report_lines.append(f"Collection '{col_name}':")
            for obj in col.objects:
                report_lines.append(f"  - {obj.name} (Type: {obj.type})")
            report_lines.append("")  # blank line

        write_collection_report(CAMERAS_COLLECTION_NAME)
        write_collection_report(LIGHTS_COLLECTION_NAME)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"collector_report_{timestamp}.txt"
        filepath = os.path.join(bpy.app.tempdir, filename)

        try:
            with open(filepath, "w") as f:
                f.write("\n".join(report_lines))
            self.report({'INFO'}, f"Collector report saved to: {filepath}")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to write report: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}


# New operator: Set Active Camera to Selected

class OBJECT_OT_collector_set_active_camera(Operator):
    bl_idname = "object.collector_set_active_camera"
    bl_label = "Set Active Camera to Selected"
    bl_description = "Set the scene's active camera to the currently selected camera"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        obj = context.object
        return obj is not None and obj.type == 'CAMERA'

    def execute(self, context: bpy.types.Context):
        scene = context.scene
        obj = context.object
        if obj is None or obj.type != 'CAMERA':
            self.report({'WARNING'}, "Select a camera object first")
            return {'CANCELLED'}
        scene.camera = obj
        # Ensure we enter the selected camera's view immediately for convenience
        switched = False
        try:
            win = context.window
            if win is not None:
                for area in win.screen.areas:
                    if area.type == 'VIEW_3D':
                        # Find a WINDOW region and a VIEW_3D space for correct override
                        region = next((r for r in area.regions if r.type == 'WINDOW'), None)
                        space = next((s for s in area.spaces if s.type == 'VIEW_3D'), None)
                        if region and space:
                            with context.temp_override(window=win, area=area, region=region, space_data=space, scene=scene, object=obj):
                                try:
                                    res = bpy.ops.view3d.object_as_camera()
                                    if res == {'FINISHED'}:
                                        switched = True
                                        break
                                except Exception:
                                    pass
                        # Fallback: set view perspective without operators
                        if not switched and hasattr(space, 'region_3d') and space.region_3d:
                            space.region_3d.view_perspective = 'CAMERA'
                            switched = True
                            break
        except Exception:
            pass
        # If we couldn't switch any 3D View, still succeed after setting the active camera
        self.report({'INFO'}, f"Active camera set to: {obj.name}")
        return {'FINISHED'}


@persistent
def handle_load_post(_dummy):
    scene = bpy.context.scene
    if is_auto_enabled(scene) and scene is not None:
        ensure_handlers_registered()
        organize_scene_objects(scene)
        rebuild_tracked_ids(scene)


@persistent
def handle_depsgraph_update(_depsgraph):
    scene = bpy.context.scene
    if scene is None or not is_auto_enabled(scene):
        return
    organize_new_objects(scene)


def ensure_handlers_registered() -> None:
    global HANDLERS_REGISTERED
    if HANDLERS_REGISTERED:
        return
    if handle_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(handle_load_post)
    if handle_depsgraph_update not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(handle_depsgraph_update)
    HANDLERS_REGISTERED = True


def ensure_handlers_unregistered() -> None:
    global HANDLERS_REGISTERED
    try:
        while handle_load_post in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.remove(handle_load_post)
    except Exception:
        pass
    try:
        while handle_depsgraph_update in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(handle_depsgraph_update)
    except Exception:
        pass
    HANDLERS_REGISTERED = False


def update_collector_auto(self: bpy.types.Scene, context: bpy.types.Context) -> None:
    scene = context.scene
    if getattr(self, "collector_enable_auto", False):
        ensure_handlers_registered()
        organize_scene_objects(scene)
        rebuild_tracked_ids(scene)
    else:
        ensure_handlers_unregistered()


class OBJECT_OT_collector_organize(Operator):
    bl_idname = "object.collector_organize"
    bl_label = "Organize Cameras & Lights"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: bpy.types.Context):
        scene = context.scene
        organize_scene_objects(scene)
        rebuild_tracked_ids(scene)
        self.report({'INFO'}, "Collector: Organized cameras and lights.")
        return {'FINISHED'}


class VIEW3D_PT_collector_panel(Panel):
    bl_label = "Collector"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Collector"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.scene is not None

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        scene = context.scene

        col = layout.column(align=True)
        col.prop(scene, "collector_enable_auto", text="Auto-Organize")
        col.operator(OBJECT_OT_collector_organize.bl_idname, icon="FILE_REFRESH")
        col.operator(OBJECT_OT_collector_export_report.bl_idname, icon="TEXT")
        col.separator()
        col.operator(OBJECT_OT_collector_set_active_camera.bl_idname, icon="CAMERA_DATA")


CLASSES = (
    OBJECT_OT_collector_organize,
    OBJECT_OT_collector_export_report,
    OBJECT_OT_collector_set_active_camera,
    VIEW3D_PT_collector_panel,
)


def delayed_init():
    scene = bpy.context.scene
    if scene and is_auto_enabled(scene):
        organize_scene_objects(scene)
        rebuild_tracked_ids(scene)
    return None


def register():
    bpy.types.Scene.collector_enable_auto = BoolProperty(
        name="Auto-Organize Cameras/Lights",
        description=(
            "When enabled, cameras are moved to the 'Cameras' collection and lights "
            "to the 'Lights' collection on file load and when new objects are added."
        ),
        default=True,
        update=update_collector_auto,
    )

    for cls in CLASSES:
        bpy.utils.register_class(cls)

    ensure_handlers_registered()

    bpy.app.timers.register(delayed_init)


def unregister():
    ensure_handlers_unregistered()

    for cls in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass

    if hasattr(bpy.types.Scene, "collector_enable_auto"):
        try:
            del bpy.types.Scene.collector_enable_auto
        except Exception:
            pass


if __name__ == "__main__":
    register()


