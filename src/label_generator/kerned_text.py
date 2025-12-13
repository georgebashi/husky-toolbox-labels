"""
Kerned Text Rendering

This module uses HarfBuzz for proper text shaping with kerning,
then converts the shaped glyphs to SVG and imports them using build123d.
"""

from pathlib import Path
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from build123d import import_svg, Compound
from typing import List, Tuple


class KernedText:
    """Renders text with proper kerning using HarfBuzz."""

    def __init__(self, text: str, font_path: Path, font_size: float):
        """
        Initialize KernedText.

        Args:
            text: The text string to render
            font_path: Path to the TTF font file
            font_size: Font size in mm
        """
        self.text = text
        self.font_path = font_path
        self.font_size = font_size

        with open(font_path, 'rb') as f:
            self.fontdata = f.read()

        self.ttfont = TTFont(font_path)
        self.glyph_set = self.ttfont.getGlyphSet()

        # Get units per em for scaling
        self.units_per_em = self.ttfont['head'].unitsPerEm

    def shape_text(self) -> List[Tuple[str, float, float]]:
        """
        Shape text using HarfBuzz to get glyph positions with kerning.

        Returns:
            List of (glyph_name, x_position, y_position) tuples
        """
        # Create HarfBuzz font
        face = hb.Face(self.fontdata)
        font = hb.Font(face)

        scale = int(self.units_per_em)
        font.scale = (scale, scale)

        buf = hb.Buffer()
        buf.add_str(self.text)
        buf.guess_segment_properties()

        hb.shape(font, buf)

        infos = buf.glyph_infos
        positions = buf.glyph_positions

        glyph_order = self.ttfont.getGlyphOrder()

        shaped_glyphs = []
        x_cursor = 0

        for info, pos in zip(infos, positions):
            glyph_name = glyph_order[info.codepoint]
            x_pos = x_cursor + pos.x_offset
            y_pos = pos.y_offset

            shaped_glyphs.append((glyph_name, x_pos, y_pos))

            x_cursor += pos.x_advance

        return shaped_glyphs

    def create_geometry(self) -> Compound:
        """
        Create build123d geometry from shaped text by rendering to SVG.

        Returns:
            Compound containing all glyph faces, centered at (0, 0)
        """
        shaped_glyphs = self.shape_text()
        scale_factor = self.font_size / self.units_per_em

        # Create SVG path data - one path per glyph with all contours
        svg_paths = []

        for glyph_name, x_pos, y_pos in shaped_glyphs:
            if glyph_name == '.notdef':
                continue

            # Create single path with all contours for this glyph
            pen = SVGPathPen(self.glyph_set)
            self.glyph_set[glyph_name].draw(pen)

            path_data = pen.getCommands()
            if not path_data:
                continue

            svg_paths.append({
                'path': path_data,
                'x': x_pos * scale_factor,
                'y': y_pos * scale_factor
            })

        if not svg_paths:
            raise ValueError(f"No glyphs could be rendered for text: {self.text}")

        # Create SVG file with all glyph paths
        svg_content = self._create_svg(svg_paths, scale_factor)

        # Save to debug file and import
        svg_path = 'debug_text.svg'
        with open(svg_path, 'w') as f:
            f.write(svg_content)

        # Import SVG using build123d
        shapes = import_svg(svg_path)

        if len(shapes) == 0:
            raise ValueError(f"No shapes imported from SVG for text: {self.text}")

        # SVG imports as Face with multiple wires
        # Convert multi-wire faces to properly unioned geometry
        from build123d import Face, Wire, make_face
        faces = []

        for shape in shapes:
            if isinstance(shape, Wire):
                faces.append(Face(shape))
            elif isinstance(shape, Face):
                # If face has multiple wires, they represent separate contours
                # that need to be unioned together
                wires = shape.wires()
                if len(wires) > 1:
                    # Create separate faces from each wire and union them
                    wire_faces = []
                    for wire in wires:
                        try:
                            wire_faces.append(make_face(wire))
                        except:
                            continue

                    if wire_faces:
                        # Union all wire faces together
                        unioned = wire_faces[0]
                        for wf in wire_faces[1:]:
                            unioned = unioned + wf
                        faces.append(unioned)
                else:
                    faces.append(shape)

        if not faces:
            raise ValueError(f"No valid faces created from SVG for text: {self.text}")

        result = Compound(faces) if len(faces) > 1 else faces[0]

        # Center the text at origin
        bbox = result.bounding_box()
        center_x = (bbox.min.X + bbox.max.X) / 2
        center_y = (bbox.min.Y + bbox.max.Y) / 2

        centered = result.translate((-center_x, -center_y, 0))

        return centered

    def _create_svg(self, svg_paths: list, scale_factor: float) -> str:
        """
        Create an SVG document with all glyph paths.

        Args:
            svg_paths: List of dicts with 'path', 'x', 'y' keys
            scale_factor: Scale factor from font units to mm

        Returns:
            SVG document as a string
        """
        # Calculate viewBox to encompass all glyphs
        # We'll use a generous viewBox and let build123d handle the bounds

        paths_svg = []
        for glyph in svg_paths:
            # SVG uses transform to position each glyph
            # Note: SVG Y-axis points down, font Y-axis points up
            # We flip Y by using negative scale
            transform = f"translate({glyph['x']:.3f}, {glyph['y']:.3f}) scale({scale_factor:.6f}, {-scale_factor:.6f})"
            # Use fill-rule="nonzero" which is standard for TrueType fonts
            paths_svg.append(f'  <path d="{glyph["path"]}" transform="{transform}" fill="black" fill-rule="nonzero"/>')

        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" version="1.1">
{chr(10).join(paths_svg)}
</svg>'''

        return svg
