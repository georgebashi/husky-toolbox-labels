"""
Kerned Text Rendering

This module uses HarfBuzz for proper text shaping with kerning,
then converts the shaped glyphs to build123d geometry.
"""

from pathlib import Path
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from build123d import Wire, Face, Compound, Vector
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
        Create build123d geometry from shaped text.

        Returns:
            Compound containing all glyph faces
        """
        shaped_glyphs = self.shape_text()

        scale_factor = self.font_size / self.units_per_em

        faces = []

        for glyph_name, x_pos, y_pos in shaped_glyphs:
            if glyph_name == '.notdef':
                continue

            pen = RecordingPen()
            self.glyph_set[glyph_name].draw(pen)

            if not pen.value:
                continue

            try:
                glyph_face = self._recording_to_face(pen.value, x_pos, y_pos, scale_factor)
                if glyph_face:
                    faces.append(glyph_face)
            except Exception as e:
                print(f"Warning: Could not convert glyph '{glyph_name}': {e}")
                continue

        if not faces:
            raise ValueError(f"No glyphs could be rendered for text: {self.text}")

        return Compound(faces)

    def _recording_to_face(self, recording: list, x_offset: float, y_offset: float, scale: float) -> Face:
        """
        Convert fontTools recording pen data to build123d Face.

        Args:
            recording: Recording pen data
            x_offset: X offset for this glyph
            y_offset: Y offset for this glyph
            scale: Scale factor to apply

        Returns:
            Face representing the glyph
        """
        from build123d import Polyline, make_face

        contours = []
        current_contour = []

        for cmd, args in recording:
            if cmd == 'moveTo':
                if current_contour:
                    contours.append(current_contour)
                    current_contour = []
                x, y = args[0]
                x = (x + x_offset) * scale
                y = (y + y_offset) * scale
                current_contour.append((x, y))

            elif cmd == 'lineTo':
                x, y = args[0]
                x = (x + x_offset) * scale
                y = (y + y_offset) * scale
                current_contour.append((x, y))

            elif cmd in ('curveTo', 'qCurveTo'):
                for point in args:
                    x, y = point
                    x = (x + x_offset) * scale
                    y = (y + y_offset) * scale
                    current_contour.append((x, y))

            elif cmd == 'closePath':
                if current_contour:
                    contours.append(current_contour)
                    current_contour = []

        if current_contour:
            contours.append(current_contour)

        if not contours:
            return None

        wires = []
        for contour in contours:
            if len(contour) < 3:
                continue
            try:
                wire = Polyline(*[Vector(x, y, 0) for x, y in contour], close=True)
                wires.append(wire)
            except:
                continue

        if not wires:
            return None

        try:
            return make_face(wires)
        except:
            return None
