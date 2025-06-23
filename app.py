import json
import dash
from dash import html, dcc, callback_context
from dash.dependencies import Input, Output, State, ALL
import dash_bootstrap_components as dbc
from dash_draggable import ResponsiveGridLayout
from dash.exceptions import PreventUpdate

CANVAS_BASE_STYLE = {
    "position": "absolute",
    "top": "136px",
    "left": 0,
    "width": "100%",
    "height": "calc(100vh - 136px)",
    "overflow": "hidden",
    "backgroundColor": "transparent",
}

# ----------------------------------------------------------------------------- 
# App setup
# ----------------------------------------------------------------------------- 
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.MATERIA])
server = app.server

# ----------------------------------------------------------------------------- 
# UI COMPONENTS
# ----------------------------------------------------------------------------- 
def create_navbar():
    return dbc.NavbarSimple(
        brand="Neural-Viz",
        color="light",
        light=True,
        fixed="top",
        style={"height": "60px"},
    )

def create_tabbar():
    return dbc.Tabs(
        id="type-tabs",
        active_tab="DataSource",
        children=[
            dbc.Tab(label="Data Source", tab_id="DataSource"),
            # … other tabs …
        ],
        style={
            "position": "fixed",
            "top": "60px",
            "width": "100%",
            "zIndex": 1,
            "backgroundColor": "#f8f9fa",
        },
    )

def create_tab_content():
    return html.Div(
        id="tab-content",
        style={
            "position": "fixed",
            "top": "96px",
            "left": 0,
            "right": 0,
            "padding": "8px",
            "whiteSpace": "nowrap",
            "overflowX": "auto",
            "zIndex": 1,
            "backgroundColor": "#f8f9fa",
        },
    )

def create_sidebar():
    return dbc.Collapse(
        dbc.Card(
            [
                dbc.CardHeader("Node Options"),
                dbc.CardBody(
                    html.Div(id="sidebar-content", children=["Select a node to configure."])
                ),
            ],
            className="mt-3",
        ),
        id="sidebar-collapse",
        is_open=False,
        style={
            "position": "fixed",
            "top": "136px",
            "left": 0,
            "width": "20%",
            "height": "calc(100% - 136px)",
            "overflowY": "auto",
            "padding": "1rem",
            "backgroundColor": "#f8f9fa",
            "zIndex": 1,
        },
    )

def create_canvas():
    """Responsive grid that accepts external drops."""
    return ResponsiveGridLayout(
        id="canvas-layout",
        children=[],
        layouts={bp: [] for bp in ["lg","md","sm","xs","xxs"]},
        clearSavedLayout=True,
        save=False,
        resizeHandles=[],           # no resize grips
        isDraggable=True,
        isResizable=False,
        isDroppable=True,           # enable HTML5 drops
        droppingItem={"i": "__new__", "w": 1, "h": 1},
        compactType=None,
        preventCollision=True,
        verticalCompact=False,
        containerPadding=[0, 0],
        margin=[0, 0],
        gridCols={                # 36 cells across
            "lg":36, "md":36, "sm":36, "xs":36, "xxs":36
        },
        style=CANVAS_BASE_STYLE,
    )


# ----------------------------------------------------------------------------- 
# App layout
# ----------------------------------------------------------------------------- 
app.layout = html.Div([
    create_navbar(),
    create_tabbar(),
    create_tab_content(),
    create_sidebar(),
    create_canvas(),
    dcc.Store(id="nodes-store", data=[]),
])


# ----------------------------------------------------------------------------- 
# Helpers
# ----------------------------------------------------------------------------- 
def find_next_position(nodes, start_x, start_y, cols=36):
    occupied = {(n["layout"]["x"], n["layout"]["y"]) for n in nodes}
    for y in range(start_y, start_y + 100):
        for x in range(0, cols):
            if (x, y) not in occupied:
                return x, y
    return start_x, start_y


# ----------------------------------------------------------------------------- 
# Callbacks
# ----------------------------------------------------------------------------- 
@app.callback(
    Output("tab-content", "children"),
    Input("type-tabs", "active_tab"),
)
def render_tab_content(active_tab):
    icons = []
    if active_tab == "DataSource":
        data_icons = [
            {"id": "browse",  "label": "Browse",      "src": "/assets/inputdata.svg"},
            {"id": "input",   "label": "Input Data",  "src": "/assets/inputdata.svg"},
            # … other icons …
        ]
        for item in data_icons:
            icons.append(
                html.Div(
                    html.Img(
                        src=item["src"],
                        style={"width": "40px", "height": "40px"},
                    ),
                    id={"type": "source-icon", "source": item["id"]},
                    n_clicks=0,
                    **{
                        "draggable": True,
                        "data-node-type": item["id"],
                        "onDragStart":
                          "event.dataTransfer.setData('nodeType', event.target.getAttribute('data-node-type'));"
                    },
                    title=item["label"],
                    style={
                        "display":"inline-block",
                        "marginRight":"12px",
                        "cursor":"grab",
                        "textAlign":"center",
                    },
                )
            )
    return icons

@app.callback(
    Output("nodes-store", "data"),
    Input({"type": "source-icon", "source": ALL}, "n_clicks"),
    State("nodes-store", "data"),
    prevent_initial_call=True,
)
def add_source_node(n_clicks, data):
    # fallback if someone still clicks instead of drag/drop
    if not any(n_clicks):
        raise PreventUpdate
    triggered = callback_context.triggered[0]["prop_id"].split('.')[0]
    source = json.loads(triggered)["source"]
    idx = len(data)
    x, y = find_next_position(data, 0, 0, cols=36)
    return data + [{
        "id": f"node-{idx+1}",
        "type": source,
        "layout": {"x": x, "y": y, "w":1, "h":1},
    }]

@app.callback(
    Output("nodes-store", "data"),
    Input("canvas-layout", "droppingItem"),
    State("nodes-store", "data"),
    prevent_initial_call=True,
)
def handle_drop(dropping, nodes):
    # dropping is a dict: {'x':…, 'y':…, …}
    if not dropping or "x" not in dropping:
        raise PreventUpdate
    # what we packed in dataTransfer
    node_type = dropping.get("nodeType") or dropping.get("i")
    # compute a free spot
    dx, dy = find_next_position(nodes, dropping["x"], dropping["y"], cols=36)
    idx = len(nodes)
    nodes.append({
        "id": f"node-{idx+1}",
        "type": node_type,
        "layout": {"x": dx, "y": dy, "w":1, "h":1},
    })
    return nodes

@app.callback(
    Output("canvas-layout", "children"),
    Output("canvas-layout", "layouts"),
    Input("nodes-store", "data"),
)
def render_nodes(nodes):
    children = []
    layouts = {bp: [] for bp in ["lg","md","sm","xs","xxs"]}
    for node in nodes:
        if node["type"] == "browse":
            el = html.Img(
                src="/assets/inputdata.svg",
                style={"width":"40px","height":"40px","objectFit":"contain"},
            )
        else:
            el = html.I(
                className="fas fa-database",
                style={"fontSize":"40px"}
            )
        children.append(
            html.Div(
                el,
                id={"type":"canvas-node","pid":node["id"]},
                n_clicks=0,
                style={
                    "display":"flex",
                    "alignItems":"center",
                    "justifyContent":"center",
                    "overflow":"hidden",
                    "padding":0,
                    "margin":0,
                    "backgroundColor":"transparent",
                },
            )
        )
        for bp in layouts:
            layouts[bp].append({**node["layout"], "i": node["id"]})
    return children, layouts

@app.callback(
    Output("sidebar-collapse", "is_open"),
    Output("canvas-layout", "style"),
    Input({"type":"canvas-node","pid":ALL}, "n_clicks"),
    State("sidebar-collapse", "is_open"),
    prevent_initial_call=True,
)
def toggle_sidebar(n_clicks, is_open):
    if not any(n_clicks):
        raise PreventUpdate
    new_state = not is_open
    style = CANVAS_BASE_STYLE.copy()
    if new_state:
        style["left"] = "20%"
    return new_state, style

# ----------------------------------------------------------------------------- 
# Run
# ----------------------------------------------------------------------------- 
if __name__ == "__main__":
    app.run_server(debug=True)
