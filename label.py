#!/usr/bin/env python3
"""
Generate 3D printable toolbox labels.

Usage:
    python label.py "Label Text" -o output.step
"""

import argparse
import sys
from pathlib import Path


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate 3D printable toolbox labels",
        epilog="Example: python label.py \"Socket Wrenches\" -o socket_wrenches.step"
    )
    parser.add_argument(
        "text",
        type=str,
        help="Text to display on the label"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("label.step"),
        help="Output STEP file path (default: label.step)"
    )
    parser.add_argument(
        "--profile",
        type=Path,
        default=Path("cross-section.svg"),
        help="SVG file with clip cross-section (default: cross-section.svg)"
    )
    parser.add_argument(
        "--font",
        type=Path,
        default=Path("InterVariable.ttf"),
        help="TTF font file for text (default: InterVariable.ttf)"
    )
    parser.add_argument(
        "-f", "--format",
        type=str,
        choices=["step", "stl"],
        default="step",
        help="Output format: step (single file) or stl (multi-file) (default: step)"
    )

    args = parser.parse_args()

    if not args.profile.exists():
        print(f"Error: Profile file not found: {args.profile}", file=sys.stderr)
        return 1

    if not args.font.exists():
        print(f"Error: Font file not found: {args.font}", file=sys.stderr)
        return 1

    try:
        from src.label_generator.svg_profile import ClipProfile
        from src.label_generator.text_geometry import LabelText
        from src.label_generator.label_builder import LabelBuilder
        from src.label_generator.exporter import LabelExporter

        print(f"Generating label: \"{args.text}\"")

        profile = ClipProfile(args.profile)
        profile.load().scale_to_dimensions()
        print("  ✓ Profile loaded and scaled")

        text = LabelText(args.text, args.font)
        text.create_text()
        print(f"  ✓ Text created (width: {text.text_width:.1f}mm, label: {text.get_label_width():.1f}mm)")

        builder = LabelBuilder(
            profile.scaled_face,
            text.text_geometry,
            text.get_label_width()
        )
        builder.build_body().add_text_recess().create_text_insert()
        print(f"  ✓ Label assembled (volume: {builder.label_body.volume:.0f}mm³)")

        exporter = LabelExporter(builder.label_body, builder.text_insert)
        exporter.export(args.output, format=args.format)

        if args.format == "step":
            print(f"  ✓ Exported to: {args.output}")
            file_size = args.output.stat().st_size / 1024
            print(f"\n✓ Label generated successfully ({file_size:.1f} KB)")
        else:
            print(f"\n✓ Label generated successfully ({args.format.upper()} format)")

        return 0

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
