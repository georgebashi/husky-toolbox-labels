"""
Text Geometry Creation

This module handles creating 3D text geometry from the label text string
using the specified font.
"""

from pathlib import Path
from build123d import Text, Align, Compound, FontStyle


class LabelText:
    """Creates 3D text geometry for the label."""

    FONT_SIZE = 16.0
    RECESS_DEPTH = 0.8
    PADDING = 20.0

    def __init__(self, text: str, font_path: Path):
        """
        Initialize LabelText.

        Args:
            text: The text string to render
            font_path: Path to the TTF font file
        """
        self.text = text
        self.font_path = font_path
        self.text_geometry = None
        self.text_width = None

    def create_text(self) -> Compound:
        """
        Generate 2D text geometry.

        Returns:
            Compound containing the text geometry
        """
        self.text_geometry = Text(
            self.text,
            font_size=self.FONT_SIZE,
            font_path=str(self.font_path),
            font_style=FontStyle.BOLD,
            align=(Align.CENTER, Align.CENTER)
        )

        bbox = self.text_geometry.bounding_box()
        self.text_width = bbox.size.X

        return self.text_geometry

    def get_label_width(self) -> float:
        """
        Calculate total label width including padding.

        Returns:
            Label width in mm (text width + 20mm padding)
        """
        if self.text_width is None:
            self.create_text()
        return self.text_width + self.PADDING
