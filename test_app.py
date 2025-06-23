import pytest
from dash_draggable import GridLayout
from app import create_canvas, add_input_node

def test_canvas_is_gridlayout():
    canvas = create_canvas()
    assert isinstance(canvas, GridLayout)
    assert canvas.id == "canvas-layout"
    assert "grid-canvas" in canvas.className

def test_add_input_node():
    # no clicks -> no nodes
    assert add_input_node(None, []) == []
    # first click -> one node
    data = add_input_node(1, [])
    assert len(data) == 1
    assert data[0]["layout"]["x"] == 0
    # second click -> two nodes
    data2 = add_input_node(2, data)
    assert len(data2) == 2
