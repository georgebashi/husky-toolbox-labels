"""
Kerned Text Rendering using Inkscape

This module uses Inkscape to render text to SVG paths, which are then
imported using build123d.
"""

import subprocess
import tempfile
from pathlib import Path
from build123d import import_svg, Compound, Face, Wire
from typing import List, Tuple


class KernedText:
    """Renders text by shelling out to Inkscape."""

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

    def create_geometry(self) -> Compound:
        """
        Create build123d geometry using Inkscape for rendering.

        Returns:
            Compound containing all glyph faces, centered at (0, 0)
        """
        # Save debug files to current directory for inspection
        source_svg = Path("debug_source.svg")
        outlined_svg = Path("debug_outlined.svg")

        # 1. Create source SVG with text
        self._create_source_svg(source_svg)

        # 2. Run Inkscape to convert text to paths
        self._run_inkscape(source_svg, outlined_svg)

        # 3. Import the result
        shapes = import_svg(str(outlined_svg))

        if len(shapes) == 0:
            raise ValueError(f"No shapes imported from Inkscape SVG for text: {self.text}")

        # 4. Convert shapes to Faces
        faces = []
        for shape in shapes:
            if isinstance(shape, Face):
                faces.append(shape)
            elif isinstance(shape, Wire):
                faces.append(Face(shape))
        
        if not faces:
            raise ValueError(f"No faces created from Inkscape SVG for text: {self.text}")

        # 5. Create Compound and center
        result = Compound(faces)
        
        # Inkscape exports in pixels (96 DPI). Convert to mm.
        # 1 inch = 25.4 mm = 96 px
        # Scale factor = 25.4 / 96
        PX_TO_MM = 25.4 / 96.0
        
        # Scale down to mm
        result = result.scale(PX_TO_MM)
        
        # Center the text at origin
        bbox = result.bounding_box()
        center_x = (bbox.min.X + bbox.max.X) / 2
        center_y = (bbox.min.Y + bbox.max.Y) / 2
        
        centered = result.translate((-center_x, -center_y, 0))

        return centered

    def _create_source_svg(self, path: Path):
        """Write the source SVG with <text> element."""
        font_path_abs = self.font_path.absolute()
        
        # Use a viewBox that comfortably fits text. 
        # Inkscape will handle the bounds during export usually, but giving it created text is fine.
        # We assume standard pixels for SVG (96 DPI).
        # We want font_size in mm. SVG 'font-size' without units is user units (pixels).
        # 1 mm = 3.7795 px.
        # However, build123d import_svg assumes 1 unit = 1 mm if strictly following some conventions?
        # Actually build123d import_svg reads units.
        # Let's be explicit with units in SVG.
        
        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="500mm" height="200mm" viewBox="0 0 500 200">
  <defs>
    <style type="text/css">
      @font-face {{
        font-family: 'Inter';
        font-weight: bold;
      }}
    </style>
  </defs>
  <text x="10" y="100" font-family="Inter" font-weight="bold" font-size="{self.font_size}mm" fill="black" style="text-rendering: optimizeLegibility; font-feature-settings: 'kern'; letter-spacing: -2px;">{self.text}</text>
</svg>'''
        
        with open(path, 'w') as f:
            f.write(svg)

    def _run_inkscape(self, input_path: Path, output_path: Path):
        """Run Inkscape CLI to convert text to paths."""
        # Inkscape 1.0+ command line options
        # --export-type=svg --export-text-to-path --export-filename=...
        
        cmd = [
            "inkscape",
            f"--export-filename={str(output_path)}",
            "--export-type=svg",
            "--export-text-to-path",
            str(input_path)
        ]
        
        try:
            result = subprocess.run(
                cmd, 
                check=True, 
                capture_output=True, 
                text=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Inkscape failed: {e.stderr}")
