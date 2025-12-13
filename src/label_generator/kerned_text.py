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
        Create build123d geometry from shaped text using shapely to union
        polygons and eliminate self-overlapping geometry.

        Returns:
            Compound containing all glyph faces, centered at (0, 0)
        """
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        from fontTools.pens.recordingPen import RecordingPen

        shaped_glyphs = self.shape_text()
        scale_factor = self.font_size / self.units_per_em

        # Collect all polygons from all glyphs
        all_polygons = []

        for glyph_name, x_pos, y_pos in shaped_glyphs:
            if glyph_name == '.notdef':
                continue

            # Get glyph outline
            pen = RecordingPen()
            self.glyph_set[glyph_name].draw(pen)

            if not pen.value:
                continue

            # Convert glyph outline to polygons
            polygons = self._recording_to_polygons(pen.value, x_pos * scale_factor, y_pos * scale_factor, scale_factor)
            all_polygons.extend(polygons)

        if not all_polygons:
            raise ValueError(f"No glyphs could be rendered for text: {self.text}")

        # Union all polygons to eliminate self-overlapping geometry
        unioned = unary_union(all_polygons)

        # Convert back to SVG and import
        svg_content = self._polygon_to_svg(unioned)

        # Save debug SVG
        svg_path = 'debug_text.svg'
        with open(svg_path, 'w') as f:
            f.write(svg_content)

        # Import the SVG
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

    def _recording_to_polygons(self, recording: list, x_offset: float, y_offset: float, scale: float):
        """
        Convert fontTools recording to shapely polygons with tessellated curves.

        Args:
            recording: RecordingPen value
            x_offset: X offset in mm
            y_offset: Y offset in mm
            scale: Scale factor

        Returns:
            List of shapely Polygon objects
        """
        from shapely.geometry import Polygon
        from shapely.affinity import scale as shapely_scale

        def tessellate_quadratic(p0, p1, p2, segments=10):
            """Tessellate quadratic Bezier curve."""
            points = []
            for i in range(segments + 1):
                t = i / segments
                x = (1-t)**2 * p0[0] + 2*(1-t)*t * p1[0] + t**2 * p2[0]
                y = (1-t)**2 * p0[1] + 2*(1-t)*t * p1[1] + t**2 * p2[1]
                points.append((x, y))
            return points

        def tessellate_cubic(p0, p1, p2, p3, segments=12):
            """Tessellate cubic Bezier curve."""
            points = []
            for i in range(segments + 1):
                t = i / segments
                x = (1-t)**3 * p0[0] + 3*(1-t)**2*t * p1[0] + 3*(1-t)*t**2 * p2[0] + t**3 * p3[0]
                y = (1-t)**3 * p0[1] + 3*(1-t)**2*t * p1[1] + 3*(1-t)*t**2 * p2[1] + t**3 * p3[1]
                points.append((x, y))
            return points

        contours = []
        current_contour = []
        current_pos = None

        for cmd, args in recording:
            if cmd == 'moveTo':
                if current_contour:
                    contours.append(current_contour)
                    current_contour = []
                x, y = args[0]
                x = (x + x_offset / scale) * scale
                y = (y + y_offset / scale) * scale
                current_pos = (x, y)
                current_contour.append(current_pos)

            elif cmd == 'lineTo':
                x, y = args[0]
                x = (x + x_offset / scale) * scale
                y = (y + y_offset / scale) * scale
                current_pos = (x, y)
                current_contour.append(current_pos)

            elif cmd == 'qCurveTo':
                if not current_pos:
                    continue
                points = list(args)
                if len(points) == 1:
                    x, y = points[0]
                    x = (x + x_offset / scale) * scale
                    y = (y + y_offset / scale) * scale
                    current_contour.append((x, y))
                    current_pos = (x, y)
                elif len(points) == 2:
                    cp_x, cp_y = points[0]
                    cp_x = (cp_x + x_offset / scale) * scale
                    cp_y = (cp_y + y_offset / scale) * scale
                    end_x, end_y = points[1]
                    end_x = (end_x + x_offset / scale) * scale
                    end_y = (end_y + y_offset / scale) * scale
                    curve_points = tessellate_quadratic(current_pos, (cp_x, cp_y), (end_x, end_y))
                    current_contour.extend(curve_points[1:])
                    current_pos = (end_x, end_y)
                else:
                    prev_point = current_pos
                    for i in range(len(points) - 1):
                        cp_x, cp_y = points[i]
                        cp_x = (cp_x + x_offset / scale) * scale
                        cp_y = (cp_y + y_offset / scale) * scale
                        if i < len(points) - 2:
                            next_cp_x, next_cp_y = points[i + 1]
                            next_cp_x = (next_cp_x + x_offset / scale) * scale
                            next_cp_y = (next_cp_y + y_offset / scale) * scale
                            on_curve = ((cp_x + next_cp_x) / 2, (cp_y + next_cp_y) / 2)
                        else:
                            end_x, end_y = points[i + 1]
                            end_x = (end_x + x_offset / scale) * scale
                            end_y = (end_y + y_offset / scale) * scale
                            on_curve = (end_x, end_y)
                        curve_points = tessellate_quadratic(prev_point, (cp_x, cp_y), on_curve)
                        current_contour.extend(curve_points[1:])
                        prev_point = on_curve
                    current_pos = prev_point

            elif cmd == 'curveTo':
                if not current_pos or len(args) < 3:
                    continue
                cp1_x, cp1_y = args[0]
                cp1_x = (cp1_x + x_offset / scale) * scale
                cp1_y = (cp1_y + y_offset / scale) * scale
                cp2_x, cp2_y = args[1]
                cp2_x = (cp2_x + x_offset / scale) * scale
                cp2_y = (cp2_y + y_offset / scale) * scale
                end_x, end_y = args[2]
                end_x = (end_x + x_offset / scale) * scale
                end_y = (end_y + y_offset / scale) * scale
                curve_points = tessellate_cubic(current_pos, (cp1_x, cp1_y), (cp2_x, cp2_y), (end_x, end_y))
                current_contour.extend(curve_points[1:])
                current_pos = (end_x, end_y)

            elif cmd == 'closePath':
                if current_contour:
                    contours.append(current_contour)
                    current_contour = []
                    current_pos = None

        if current_contour:
            contours.append(current_contour)

        # Convert contours to shapely polygons
        polygons = []
        for contour in contours:
            if len(contour) >= 3:
                try:
                    poly = Polygon(contour)
                    # Fix self-intersections and invalid geometry with buffer(0)
                    poly = poly.buffer(0)
                    if poly.is_valid and not poly.is_empty:
                        # Flip Y coordinates (fonts have Y-up, we need Y-down)
                        poly = shapely_scale(poly, xfact=1, yfact=-1, origin=(0, 0))
                        polygons.append(poly)
                except:
                    continue

        return polygons

    def _polygon_to_svg(self, geom) -> str:
        """
        Convert shapely geometry to SVG.

        Args:
            geom: Shapely Polygon or MultiPolygon

        Returns:
            SVG document string
        """
        from shapely.geometry import MultiPolygon, Polygon

        paths = []

        if isinstance(geom, Polygon):
            geoms = [geom]
        elif isinstance(geom, MultiPolygon):
            geoms = list(geom.geoms)
        else:
            geoms = []

        for poly in geoms:
            # Combine exterior and interior rings into a single path
            path_parts = []

            # Exterior ring
            coords = list(poly.exterior.coords)
            if coords:
                path_d = f"M {coords[0][0]:.3f} {coords[0][1]:.3f}"
                for x, y in coords[1:]:
                    path_d += f" L {x:.3f} {y:.3f}"
                path_d += " Z"
                path_parts.append(path_d)

            # Interior rings (holes) as subpaths
            for interior in poly.interiors:
                coords = list(interior.coords)
                if coords:
                    path_d = f"M {coords[0][0]:.3f} {coords[0][1]:.3f}"
                    for x, y in coords[1:]:
                        path_d += f" L {x:.3f} {y:.3f}"
                    path_d += " Z"
                    path_parts.append(path_d)

            # Combine all parts into a single path with evenodd fill-rule
            if path_parts:
                combined_path = " ".join(path_parts)
                paths.append(f'  <path d="{combined_path}" fill="black" fill-rule="evenodd"/>')

        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" version="1.1">
{chr(10).join(paths)}
</svg>'''

        return svg

    def _create_text_svg(self) -> str:
        """
        Create an SVG document with a <text> element.

        This will be converted to outlined paths by Inkscape.

        Returns:
            SVG document as a string
        """
        # Convert font path to absolute path for SVG
        font_path_abs = self.font_path.absolute()

        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="200mm" height="50mm" viewBox="0 0 200 50">
  <defs>
    <style type="text/css">
      @font-face {{
        font-family: 'CustomFont';
        src: url('file://{font_path_abs}');
      }}
    </style>
  </defs>
  <text x="10" y="35" font-family="CustomFont" font-size="{self.font_size}" fill="black">{self.text}</text>
</svg>'''

        return svg

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
