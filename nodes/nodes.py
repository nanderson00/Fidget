import os
import bpy
from bpy.types import Operator, NodeTree, Node, NodeSocket
import nodeitems_utils
from nodeitems_utils import NodeCategory, NodeItem
from .. preferences import get_preferences
from bpy.props import *
from .. operators.drawing_mode import button

# node tree
class FidgetNodeTree(NodeTree):
    bl_idname = "FidgetNodeTree"
    bl_label = "Fidget Node Tree"
    bl_icon = "NODETREE"

## sockets ##

# eval socket
class FidgetEvalSocket(NodeSocket):
    bl_idname = "FidgetEvalSocket"
    bl_label = "Evaluate Socket"

    value = StringProperty(
        name = "Input Evaluation Value",
        description = "Command to execute",
        default = "")

    def draw(self, context, layout, node, text):
        if self.is_linked and not self.is_output:
            layout.label(text=text)
        elif node.bl_idname == "FidgetCommandNode":
            row = layout.row()
            row.scale_x = 5.0 # HACK: forces row to span width
            row.prop(self, "value", text="")
        elif self.is_output:
            layout.label(text="Output")
        else:
            row = layout.row()
            row.scale_x = 5.0
            row.prop(self, "value", text="")

    def draw_color(self, context, node):
        return (1.0, 0.4, 0.22, 1.0)

## nodes ##

# node mix-in
class FidgetTreeNode:

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "FidgetNodeTree"

# command
class FidgetCommandNode(Node, FidgetTreeNode):
    bl_idname = "FidgetCommandNode"
    bl_label = "Command"
    bl_width_min = 150

    def init(self, context):
        self.outputs.new("FidgetEvalSocket", "")

    def draw_buttons(self, context, layout):
        layout.separator()

# script
class FidgetScriptNode(Node, FidgetTreeNode):
    bl_idname = "FidgetScriptNode"
    bl_label = "Script"

    def init(self, context):
        self.outputs.new("FidgetEvalSocket", "")

    def draw_buttons(self, context, layout):
        layout.separator()

# is mode
class FidgetIsModeNode(Node, FidgetTreeNode):
    bl_idname = "FidgetIsModeNode"
    bl_label = "Is Mode"

    mode = EnumProperty(
        name = "Object Mode",
        description = "Mode requirements to allow executing",
        items = [
            ("PARTICLE_EDIT", "Particle Edit", ""),
            ("TEXTURE_PAINT", "Texture Paint", ""),
            ("WEIGHT_PAINT", "Weight Paint", ""),
            ("VERTEX_PAINT", "Vertex Paint", ""),
            ("SCULPT", "Sculpt", ""),
            ("EDIT", "Edit", ""),
            ("OBJECT", "Object", "")],
        default = "OBJECT")

    def init(self, context):
        self.outputs.new("NodeSocketBool", "")

    def draw_buttons(self, context, layout):
        layout.prop(self, 'mode', text="")

# switch
class FidgetSwitchNode(Node, FidgetTreeNode):
    bl_idname = "FidgetSwitchNode"
    bl_label = "Switch"

    def init(self, context):
        self.inputs.new("NodeSocketBool", "Use Last")
        self.inputs.new("FidgetEvalSocket", "")
        self.inputs.new("FidgetEvalSocket", "")
        self.outputs.new("FidgetEvalSocket", "")

# compare
class FidgetCompareNode(Node, FidgetTreeNode):
    bl_idname = "FidgetCompareNode"
    bl_label = "Compare"

    logic = EnumProperty(
        name = "Logic",
        description = "Type of logic to use for comparison",
        items = [
            ("XNOR", "Xnor", ""),
            ("XOR", "Xor", ""),
            ("NOR", "Nor", ""),
            ("NAND", "Nand", ""),
            ("OR", "Or", ""),
            ("AND", "And", "")],
        default = "AND")

    def init(self, context):
        self.inputs.new("NodeSocketBool", "Boolean")
        self.inputs.new("NodeSocketBool", "Boolean")
        self.outputs.new("NodeSocketBool", "")

    def draw_buttons(self, context, layout):
        layout.prop(self, "logic", text="")

# output
class FidgetOutputNode(Node, FidgetTreeNode):
    bl_idname = "FidgetOutputNode"
    bl_label = "Output"

    mode = EnumProperty(
        name = "Fidget Mode",
        description = "The fidget mode to target",
        items = [
            ("MODE3", "Mode 3", ""),
            ("MODE2", "Mode 2", ""),
            ("MODE1", "Mode 1", "")],
        default = "MODE1")

    button = EnumProperty(
        name = "Fidget Button",
        description = "The fidget button to target",
        items = [
            ("LEFT", "Left Button", ""),
            ("RIGHT", "Right Button", ""),
            ("TOP", "Top Button", "")],
        default = "TOP")

    # XXX: is there a need?
    # value = EnumProperty(
    #     name = "Event Value",
    #     description = "Event value",
    #     items = [
    #         ("PRESS", "Press", ""),
    #         ("RELEASE", "Release", "")],
    #     default = "PRESS")

    def init(self, context):
        self.inputs.new("FidgetEvalSocket", "")

    def draw_buttons(self, context, layout):
        layout.prop(self, "mode", text="")
        layout.prop(self, "button", text="")
        # layout.prop(self, "value", text="")

        row = layout.row(align=True)
        op = row.operator("node.fidget_update")
        op.output_id = str(self.toID())

        # TODO
        # row.operator("node.fidget_save", text="", icon="FILE_TICK")
        # row.operator("node.fidget_reset", text="", icon="LOAD_FACTORY")

# categories
class FidgetNodeCategory(NodeCategory):

    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == "FidgetNodeTree"

node_categories = [
    FidgetNodeCategory("FIDGETINPUT", "Input", items=[
        NodeItem("FidgetCommandNode"),
        NodeItem("FidgetScriptNode")]),
    FidgetNodeCategory("FIDGETLOGIC", "Logic", items=[
        NodeItem("FidgetIsModeNode"), NodeItem("FidgetSwitchNode"), NodeItem("FidgetCompareNode")]),
    FidgetNodeCategory("FIDGETOUTPUT", "Output", items=[
        NodeItem("FidgetOutputNode")]),
    FidgetNodeCategory("LAYOUT", "Layout", items=[
        NodeItem("NodeFrame"),
        NodeItem("NodeReroute")])]

# update
class FidgetUpdate(Operator):
    bl_idname = "node.fidget_update"
    bl_label = "Update"
    bl_description = "Update this fidget button"

    output_id = StringProperty()

    def execute(self, context):
        tree_name, output_name = eval(self.output_id)
        self.tree = bpy.data.node_groups[tree_name]

        output = self.tree.nodes[output_name]
        links = output.inputs[0].links

        if len(links):
            input = links[0].from_node

            # command
            if input.bl_idname == "FidgetCommandNode":
                pass

            # script
            elif input.bl_idname == "FidgetScriptNode":
                pass

            # switch
            elif input.bl_idname == "FidgetSwitchNode":
                pass

            # if not valid link
            else:
                self.report({'WARNING'}, "Invalid input")
                return {'CANCELLED'}

        # no inputs
        else:
            setattr(getattr(button, "{}".format(output.button.lower())), "{}".format(output.mode.lower()), getattr(getattr(assign, "{}".format(output.button.lower())), "{}".format(output.mode.lower())))

        return {'FINISHED'}

class assign:

    class top:

        def mode1(modal, context, event):
            print("replaced top mode 1")

        def mode2(modal, context, event):
            print("replaced top mode 2")

        def mode3(modal, context, event):
            print("replaced top mode 3")

    class right:

        def mode1(modal, context, event):
            print("replaced right mode 1")

        def mode2(modal, context, event):
            print("replaced right mode 2")

        def mode3(modal, context, event):
            print("replaced right mode 3")

    class left:

        def mode1(modal, context, event):
            print("replaced left mode 1")

        def mode2(modal, context, event):
            print("replaced left mode 2")

        def mode3(modal, context, event):
            print("replaced left mode 3")

# save
# class FidgetSave(Operator):
#     bl_idname = "node.fidget_save"
#     bl_label = "Save"
#     bl_description = "Permantly save this node behavior as the default for this fidget button"
#
#     def execute(self, context):
#         return {'FINISHED'}

# reset
# class FidgetReset(Operator):
#     bl_idname = "node.fidget_reset"
#     bl_label = "Reset"
#     bl_description = "Reset this fidget button to defaults"
#
#     def execute(self, context):
#         return {'FINISHED'}

def nodes_register():
    nodeitems_utils.register_node_categories("FIDGET_NODES", node_categories)

def nodes_unregister():
    nodeitems_utils.unregister_node_categories("FIDGET_NODES")
