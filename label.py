#!/usr/bin/env python3
"""
Generate 3D printable toolbox labels.
"""

import sys
from pathlib import Path
from typing import Optional
import typer
from rich import print as rprint
import re
from build123d import Face

app = typer.Typer(add_completion=False)

def sanitize_filename(text: str) -> str:
    """Convert text to a safe filename (lowercase, snake_case)."""
    # Replace non-alphanumeric characters with underscores
    s = re.sub(r'[^a-zA-Z0-9]+', '_', text)
    # Convert to lowercase
    s = s.lower()
    # Remove leading/trailing underscores
    s = s.strip('_')
    return s if s else "label"

def generate_single_label(
    text_content: str,
    output_path: Path,
    profile_face: Face,
    output_format: str
) -> bool:
    """
    Generate a single label.
    Returns True if successful, False otherwise.
    """
    try:
        from src.label_generator.svg_profile import ClipProfile
        from src.label_generator.text_geometry import LabelText
        from src.label_generator.label_builder import LabelBuilder
        from src.label_generator.exporter import LabelExporter

        rprint(f"Generating label: [bold cyan]\"{text_content}\"[/bold cyan]")

        # Create text
        text_obj = LabelText(text_content)
        text_obj.create_text()
        
        # Build label
        builder = LabelBuilder(
            profile_face,
            text_obj.text_geometry,
            text_obj.get_label_width()
        )
        builder.build_body().add_text_recess().create_text_insert()

        # Export
        exporter = LabelExporter(builder.label_body, builder.text_insert)
        exporter.export(output_path, format=output_format)

        if output_format == "step":
            file_size = output_path.stat().st_size / 1024
            rprint(f"  [green]✓[/green] Exported to: {output_path} ({file_size:.1f} KB)")
        else:
            rprint(f"  [green]✓[/green] Exported to: {output_path}")
            
        return True

    except Exception as e:
        rprint(f"[bold red]Error generating label \"{text_content}\":[/bold red] {e}")
        # import traceback
        # traceback.print_exc()
        return False

@app.command()
def main(
    text: Optional[str] = typer.Argument(None, help="Text to display on the label (optional if using --file)"),
    file: Optional[Path] = typer.Option(None, "--file", help="Input text file for batch processing"),
    output: Path = typer.Option(Path("label.step"), "--output", "-o", help="Output file path (for single label mode)"),
    output_dir: Path = typer.Option(Path("labels_out"), "--output-dir", help="Output directory (for batch mode)"),
    profile: Path = typer.Option(Path("cross-section.svg"), help="SVG file with clip cross-section"),
    format: str = typer.Option("step", "--format", "-f", help="Output format: step or stl"),
):
    """
    Generate 3D printable toolbox labels.
    
    You can provide a single text argument to generate one label,
    or use --file to generate multiple labels from a text file.
    """
    from src.label_generator.svg_profile import ClipProfile

    if not profile.exists():
        rprint(f"[bold red]Error:[/bold red] Profile file not found: {profile}")
        raise typer.Exit(code=1)

    try:
        # Load and scale profile once
        rprint(f"Loading profile from {profile}...")
        clip_profile = ClipProfile(profile)
        clip_profile.load().scale_to_dimensions()
        profile_face = clip_profile.scaled_face
    except Exception as e:
        rprint(f"[bold red]Error loading profile:[/bold red] {e}")
        raise typer.Exit(code=1)

    
    if file:
        # Batch mode
        if not file.exists():
            rprint(f"[bold red]Error:[/bold red] Input file not found: {file}")
            raise typer.Exit(code=1)
            
        try:
            with open(file, 'r') as f:
                lines = [line.strip() for line in f if line.strip()]
        except Exception as e:
            rprint(f"[bold red]Error reading file:[/bold red] {e}")
            raise typer.Exit(code=1)
            
        if not lines:
            rprint("[yellow]Warning:[/yellow] Input file is empty.")
            return

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        rprint(f"Processing [bold]{len(lines)}[/bold] labels from {file} into {output_dir}/...")

        success_count = 0
        for line in lines:
            safe_name = sanitize_filename(line)
            # Determine extension based on format. STL export creates multiple files so we might want a subdir or just prefix?
            # Existing exporter for STL creates {name}_body.stl and {name}_text.stl. 
            # So if we pass path/to/safe_name.stl, it does the right thing.
            
            ext = "step" if format == "step" else "stl"
            label_output_path = output_dir / f"{safe_name}.{ext}"
            
            if generate_single_label(line, label_output_path, profile_face, format):
                success_count += 1
        
        rprint(f"\n[bold green]Batch processing complete![/bold green] ({success_count}/{len(lines)} successful)")
        
    elif text:
        # Single label mode
        if not generate_single_label(text, output, profile_face, format):
            raise typer.Exit(code=1)
            
    else:
        # No arguments provided
        rprint("[bold red]Error:[/bold red] Missing argument 'TEXT' or option '--file'.")
        rprint("Use --help for more information.")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
