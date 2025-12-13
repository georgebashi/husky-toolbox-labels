"""
STEP Export

This module handles exporting the label assembly as a STEP file
with multiple bodies for multi-color 3D printing.
"""

from pathlib import Path
from build123d import Compound, export_step, Color, Part


class LabelExporter:
    """Exports label assembly as STEP file."""

    def __init__(self, label_body: Part, text_insert: Part):
        """
        Initialize LabelExporter.

        Args:
            label_body: The main label body with recessed text
            text_insert: The text insert bodies to fill recesses
        """
        self.label_body = label_body
        self.text_insert = text_insert

    def export(self, output_path: Path) -> None:
        """
        Export multi-body STEP file.

        Args:
            output_path: Path to output STEP file
        """
        self.label_body.label = "label_body"
        self.text_insert.label = "text_insert"

        self.label_body.color = Color("gray")
        self.text_insert.color = Color("white")

        assembly = Compound(
            label="toolbox_label",
            children=[self.label_body, self.text_insert]
        )

        export_step(assembly, str(output_path))
