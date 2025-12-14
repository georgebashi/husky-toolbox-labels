"""
Text Geometry Creation

This module handles creating 3D text geometry from the label text string
using the specified font with proper kerning via HarfBuzz.
"""

from pathlib import Path
from build123d import Compound
from .kerned_text import KernedText


class LabelText:
    """Creates 3D text geometry for the label with proper kerning."""

    FONT_SIZE = 16.0
    RECESS_DEPTH = 0.8
    PADDING = 20.0

    def __init__(self, text: str):
        """
        Initialize LabelText.

        Args:
            text: The text string to render
        """
        self.text = text
        self.text_geometry = None
        self.text_width = None

    def create_text(self) -> Compound:
        """
        Generate 2D text geometry with proper kerning.

        Returns:
            Compound containing the text geometry
        """
        kerned = KernedText(self.text, self.FONT_SIZE)
        self.text_geometry = kerned.create_geometry()

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
