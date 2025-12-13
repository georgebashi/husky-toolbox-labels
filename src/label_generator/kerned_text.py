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
import tempfile


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

        # Create SVG path data for all glyphs, with each contour as a separate path
        svg_paths = []

        for glyph_name, x_pos, y_pos in shaped_glyphs:
            if glyph_name == '.notdef':
                continue

            # Use a custom pen to extract separate contours
            from fontTools.pens.recordingPen import RecordingPen
            rec_pen = RecordingPen()
            self.glyph_set[glyph_name].draw(rec_pen)

            # Split recording into separate contours (each moveTo...closePath sequence)
            contours = self._split_contours(rec_pen.value)

            for contour in contours:
                # Convert each contour to SVG path by manually replaying commands
                svg_pen = SVGPathPen(self.glyph_set)

                for cmd, args in contour:
                    if cmd == 'moveTo':
                        svg_pen.moveTo(args[0])
                    elif cmd == 'lineTo':
                        svg_pen.lineTo(args[0])
                    elif cmd == 'curveTo':
                        svg_pen.curveTo(*args)
                    elif cmd == 'qCurveTo':
                        svg_pen.qCurveTo(*args)
                    elif cmd == 'closePath':
                        svg_pen.closePath()

                path_data = svg_pen.getCommands()
                if path_data:
                    svg_paths.append({
                        'path': path_data,
                        'x': x_pos * scale_factor,
                        'y': y_pos * scale_factor
                    })

        if not svg_paths:
            raise ValueError(f"No glyphs could be rendered for text: {self.text}")

        # Create SVG file with all glyph paths
        svg_content = self._create_svg(svg_paths, scale_factor)

        # Write to temporary file and import
        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
            f.write(svg_content)
            svg_path = f.name

        try:
            # Import SVG using build123d
            shapes = import_svg(svg_path)

            if len(shapes) == 0:
                raise ValueError(f"No shapes imported from SVG for text: {self.text}")

            # Create a compound from all imported shapes
            from build123d import Face, Wire
            faces = []
            for shape in shapes:
                if isinstance(shape, Wire):
                    faces.append(Face(shape))
                elif isinstance(shape, Face):
                    faces.append(shape)

            if not faces:
                raise ValueError(f"No valid faces created from SVG for text: {self.text}")

            compound = Compound(faces) if len(faces) > 1 else faces[0]

            # Center the text at origin
            bbox = compound.bounding_box()
            center_x = (bbox.min.X + bbox.max.X) / 2
            center_y = (bbox.min.Y + bbox.max.Y) / 2

            centered = compound.translate((-center_x, -center_y, 0))

            return centered
        finally:
            # Clean up temp file
            import os
            try:
                os.unlink(svg_path)
            except:
                pass

    def _split_contours(self, recording: list) -> list:
        """
        Split a recording into separate contour sequences.

        Each contour is a moveTo...closePath sequence.

        Args:
            recording: RecordingPen value

        Returns:
            List of contour recordings
        """
        contours = []
        current = []

        for cmd, args in recording:
            current.append((cmd, args))
            if cmd == 'closePath':
                contours.append(current)
                current = []

        if current:  # Handle unclosed paths
            contours.append(current)

        return contours

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
            paths_svg.append(f'  <path d="{glyph["path"]}" transform="{transform}" fill="black"/>')

        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" version="1.1">
{chr(10).join(paths_svg)}
</svg>'''

        return svg
