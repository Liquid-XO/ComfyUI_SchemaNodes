import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

const ROLE_STYLES = {
    input: { color: "#355e3b", bgcolor: "#243f29", prefix: "IN" },
    output: { color: "#375a7f", bgcolor: "#24384e", prefix: "OUT" },
};

function getWidget(node, name) {
    return node.widgets?.find((widget) => widget.name === name);
}

function applyRoleStyle(node) {
    const roleWidget = getWidget(node, "io_kind");
    if (!roleWidget) {
        return;
    }

    const role = roleWidget.value || "input";
    const style = ROLE_STYLES[role] || ROLE_STYLES.input;

    node.properties = node.properties || {};
    if (!node.properties.schemaBaseTitle) {
        node.properties.schemaBaseTitle = (node.title || node.type || "").replace(/^\[(IN|OUT)\]\s+/, "");
    }

    node.color = style.color;
    node.bgcolor = style.bgcolor;
    node.title = `[${style.prefix}] ${node.properties.schemaBaseTitle}`;
    node.setDirtyCanvas?.(true, true);
}

function attachRoleWatcher(node) {
    const roleWidget = getWidget(node, "io_kind");
    if (!roleWidget || roleWidget.__schemaWatcherAttached) {
        applyRoleStyle(node);
        return;
    }

    const previous = roleWidget.callback;
    roleWidget.callback = function (...args) {
        previous?.apply(this, args);
        applyRoleStyle(node);
    };
    roleWidget.__schemaWatcherAttached = true;
    applyRoleStyle(node);
}

app.registerExtension({
    name: "inout.workflowSchema",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (!nodeData?.category?.startsWith("inout/schema")) {
            return;
        }

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            attachRoleWatcher(this);
            return result;
        };

        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            const result = onConfigure?.apply(this, arguments);
            attachRoleWatcher(this);
            return result;
        };
    },
});
