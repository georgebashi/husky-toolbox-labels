"""
SVG Profile Import and Scaling

This module handles importing and scaling the SVG cross-section profile
that defines the clip shape for the toolbox label.
"""

from pathlib import Path
from build123d import import_svg, Face, Wire, scale, Axis


class ClipProfile:
    """Handles SVG cross-section import and scaling to real-world dimensions."""

    TARGET_HEIGHT = 28.86
    TARGET_DEPTH = 37.7

    def __init__(self, svg_path: Path):
        """
        Initialize the ClipProfile.

        Args:
            svg_path: Path to the SVG file containing the cross-section
        """
        self.svg_path = svg_path
        self.raw_shape = None
        self.scaled_face = None

    def load(self) -> 'ClipProfile':
        """
        Import SVG and convert to Face.

        Returns:
            Self for method chaining
        """
        shapes = import_svg(str(self.svg_path))

        if len(shapes) == 0:
            raise ValueError(f"No shapes found in {self.svg_path}")

        shape = shapes[0]

        if isinstance(shape, Wire):
            self.raw_shape = Face(shape)
        elif isinstance(shape, Face):
            self.raw_shape = shape
        else:
            raise TypeError(f"Expected Wire or Face, got {type(shape)}")

        return self

    def scale_to_dimensions(self) -> Face:
        """
        Scale from SVG units to real-world mm and orient in Y-Z plane.

        The SVG viewBox is 119 x 94 units, which maps to:
        - SVG X (119 units) -> Depth (Z-axis): 37.7mm
        - SVG Y (94 units) -> Height (Y-axis): 28.86mm

        Returns:
            Scaled Face in Y-Z plane ready for extrusion along X
        """
        if self.raw_shape is None:
            raise ValueError("Must call load() before scale_to_dimensions()")

        bbox = self.raw_shape.bounding_box()
        current_width = bbox.size.X
        current_height = bbox.size.Y

        scale_x = self.TARGET_DEPTH / current_width
        scale_y = self.TARGET_HEIGHT / current_height

        scaled = scale(self.raw_shape, by=(scale_x, scale_y, 1.0))

        rotated = scaled.rotate(Axis.Y, 90)

        self.scaled_face = rotated
        return self.scaled_face
