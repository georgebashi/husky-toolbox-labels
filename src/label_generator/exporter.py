"""
Multi-Format Export

This module handles exporting the label assembly in various formats
(STEP, STL) with multiple bodies for multi-color 3D printing.
"""

from pathlib import Path
from build123d import Compound, export_step, export_stl, Color, Part
from typing import Literal


class LabelExporter:
    """Exports label assembly in multiple formats."""

    def __init__(self, label_body: Part, text_insert: Part):
        """
        Initialize LabelExporter.

        Args:
            label_body: The main label body with recessed text
            text_insert: The text insert bodies to fill recesses
        """
        self.label_body = label_body
        self.text_insert = text_insert

        self.label_body.label = "label_body"
        self.text_insert.label = "text_insert"

        self.label_body.color = Color(0.2, 0.2, 0.2)
        self.text_insert.color = Color(1.0, 1.0, 1.0)

    def export(self, output_path: Path, format: Literal["step", "stl"] = "step") -> None:
        """
        Export label assembly in specified format.

        Args:
            output_path: Path to output file
            format: Export format - "step" or "stl"
        """
        if format == "step":
            self._export_step(output_path)
        elif format == "stl":
            self._export_stl(output_path)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_step(self, output_path: Path) -> None:
        """Export as single STEP file with multiple bodies."""
        assembly = Compound(
            label="toolbox_label",
            children=[self.label_body, self.text_insert]
        )
        export_step(assembly, str(output_path))

    def _export_stl(self, output_path: Path) -> None:
        """Export as multiple STL files (one per body)."""
        base_path = output_path.with_suffix('')

        body_path = base_path.with_name(f"{base_path.name}_body.stl")
        text_path = base_path.with_name(f"{base_path.name}_text.stl")

        export_stl(self.label_body, str(body_path))
        export_stl(self.text_insert, str(text_path))

        print(f"  Exported body: {body_path}")
        print(f"  Exported text: {text_path}")
