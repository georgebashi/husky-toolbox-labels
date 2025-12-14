# Toolbox Label Generator

A Python tool to generate custom 3D printable labels. It uses an SVG profile for the label shape and generates clean 3D text geometry.

## Features

- **Custom Profiles**: Generates label bodies from a `cross-section.svg` profile.
- **High-Quality Text**: Uses system fonts (processed via Inkscape) for precise 3D text geometry.
- **Batch Processing**: Generate multiple labels at once from a list.
- **Parametric**: Automatically handles label width and text centering.
- **Formats**: Outputs STEP (recommended for CAD/Slicers) or STL files.

## Prerequisites

- **Python 3.10+**
- **Inkscape**: Required for text-to-path conversion. The tool expects Inkscape to be installed and available.
    - On macOS, it checks `/Applications/Inkscape.app/Contents/MacOS/inkscape`.
- **Inter Font**: This project expects the [Inter](https://fonts.google.com/specimen/Inter) font family to be installed on your system.

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/georgebashi/labels.git
    cd labels
    ```

2.  Install dependencies using `uv`:
    ```bash
    uv sync
    ```

3.  Activate the environment:
    ```bash
    source .venv/bin/activate
    ```

## Usage

### Single Label

Generate a single label with custom text:

```bash
python label.py "Screwdrivers"
```

This will create `label.step` in the current directory.

**Options:**

- `--output`, `-o`: Specify output filename (e.g., `-o my_label.step`).
- `--format`, `-f`: format `step` or `stl` (default: `step`).

### Batch Processing

Generate multiple labels from a text file (one label per line):

1.  Create a text file (e.g., `tools.txt`):
    ```text
    Hammers
    Wrenches
    Pliers
    ```

2.  Run the batch generator:
    ```bash
    python label.py --file tools.txt --output-dir out/
    ```

This will generate `hammers.step`, `wrenches.step`, etc., in the `out/` directory.

## Configuration

- **Profile**: The shape of the label is defined by `cross-section.svg`. You can provide a custom profile using `--profile`.
- **Fonts**: The tool uses the standard system font for Inkscape. To change the font, you would currently need to modify the Inkscape command logic or system defaults.

## Troubleshooting

- **Inkscape not found**: Ensure Inkscape is installed. If it's in a non-standard location, you may need to add it to your PATH.
