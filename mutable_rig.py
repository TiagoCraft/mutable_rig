import logging

from maya import cmds, utils

log = logging.getLogger("mutable_rig")
gui_log_handler = utils.MayaGuiLogHandler()
gui_log_handler.setFormatter(
    logging.Formatter(
        fmt="%(levelno)02d | %(asctime)s | %(pathname)s | %(lineno)s : %(message)s",
        datefmt="%Y-%m-%d %H.%M.%S",
    )
)
definition_index_attr = "definitionIndex"
definitions_attr = "definitions"
script_node_attr = "scriptNode"


def activate_rig(node: str):
    """Prepare a setup to live-update on time changes.

    Creates attributes to define the system, and a script node to life-update on time changes.
    Deletes previous script node if existing.

    Args:
        node: Maya node at the root of the setup (a rig or asset's root node).
    """
    # create node attributes if needed
    if not cmds.attributeQuery(definition_index_attr, node=node, exists=True):
        cmds.addAttr(node, longName=definition_index_attr, attributeType="long", keyable=True, min=0)
    if not cmds.attributeQuery(definitions_attr, node=node, exists=True):
        cmds.addAttr(node, longName=definitions_attr, dataType="string", multi=True)
    if not cmds.attributeQuery(script_node_attr, node=node, exists=True):
        cmds.addAttr(node, longName=script_node_attr, attributeType="message")

    # re/create script node
    if old_node := cmds.listConnections(f"{node}.{script_node_attr}", source=True):
        cmds.delete(old_node)
    script = cmds.scriptNode(
        beforeScript=f"cmds.evalDeferred(\"on_time_change('{node}')\")", scriptType=7, sourceType="python"
    )
    cmds.connectAttr(f"{script}.message", f"{node}.{script_node_attr}", force=True)


def connect_reference(ref_node: str):
    """Reconnect deformers to drivers from a loaded reference.

    Args:
        ref_node: Maya reference node name
    """
    deformers = cmds.listConnections("inXfs.dagSetMembers", source=True, destination=False)
    if constraints := cmds.listRelatives(deformers, type="constraint"):
        cmds.delete(constraints)

    out_set = cmds.ls(cmds.referenceQuery(ref_node, nodes=True), type="objectSet")[0]
    drivers = cmds.listConnections(f"{out_set}.dagSetMembers", source=True, destination=False)
    for driver, driven in zip(drivers, deformers):
        cmds.parentConstraint(driver, driven, mo=False)
    cmds.dgdirty(allPlugs=True)


def on_time_change(node: str):
    """Function to be called on time changes.

    Checks the rig definition for current frame.
    Loads and connects it's rig if needed and unloads any other rigs.

    Args:
        node: Maya node at the root of the setup (a rig or asset's root node).
    """
    definition_index = cmds.getAttr(f"{node}.{definition_index_attr}")
    base_attr = f"{node}.{definitions_attr}"
    attr = f"{base_attr}[{definition_index}]"
    inputs = cmds.listConnections(attr, source=True, destination=False)
    if inputs:
        # reference node exists
        ref_node = inputs[0]
        if cmds.referenceQuery(ref_node, isLoaded=True):
            log.info(f"Reference node {inputs[0]} already loaded. Nothing to do.")
            return  # Current rig is loaded. Nothing to do.

        # load reference
        cmds.file(loadReference=ref_node)
        connect_reference(ref_node)
        log.info(f"Switched to {inputs[0]}")
    else:
        # add reference node
        if not cmds.getAttr(attr):
            log.info(f"{attr} has no associated definition. Nothing to do.")
            return  # no definition at this index
        ref_node = cmds.file(
            cmds.file(
                cmds.getAttr(attr),
                reference=True,
                namespace=f"{node.replace('|', '_')}{definition_index}",
            ),
            query=True,
            referenceNode=True,
        )
        cmds.connectAttr(f"{ref_node}.message", attr, force=True)
        connect_reference(ref_node)
        log.info(f"Loaded and switched to {ref_node}")

    # unload other references
    all_indices = cmds.getAttr(base_attr, multiIndices=True)
    for index in all_indices or []:
        if index != definition_index:
            attr = f"{base_attr}[{index}]"
            inputs = cmds.listConnections(attr, source=True, destination=False)
            if inputs:
                ref_node = inputs[0]
                if cmds.referenceQuery(ref_node, isLoaded=True):
                    cmds.file(unloadReference=ref_node)
                    log.info(f"Unloaded {ref_node}")


# activate_rig("bob|rig")

