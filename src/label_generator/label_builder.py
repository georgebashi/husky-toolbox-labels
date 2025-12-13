"""
Label Body Assembly

This module handles the 3D assembly of the label:
- Extruding the profile to create the label body
- Finding the front face for text placement
- Creating recessed text cutouts
- Generating text insert bodies
"""

from build123d import (
    BuildPart, BuildSketch, Plane, Axis, SortBy, Location,
    extrude, Mode, Compound, Face, Solid, add
)


class LabelBuilder:
    """Assembles the complete 3D label geometry."""

    FRONT_FACE_LENGTH = 27.5
    TOLERANCE = 1.0

    def __init__(self, profile: Face, text_geometry: Compound, label_width: float, text_depth: float = 0.8):
        """
        Initialize LabelBuilder.

        Args:
            profile: Scaled Face in Y-Z plane
            text_geometry: Text Compound from LabelText
            label_width: Total width for extrusion
            text_depth: Depth to recess text (default 0.8mm)
        """
        self.profile = profile
        self.text_geometry = text_geometry
        self.label_width = label_width
        self.text_depth = text_depth
        self.label_body = None
        self.text_insert = None

    def build_body(self) -> 'LabelBuilder':
        """
        Extrude profile to create label body.

        Returns:
            Self for method chaining
        """
        with BuildPart() as part:
            with BuildSketch(Plane.YZ):
                add(self.profile)
            extrude(amount=self.label_width, dir=(1, 0, 0))

        self.label_body = part.part
        return self

    def find_front_face(self) -> Face:
        """
        Identify the front face for text placement.

        The front face is identified as:
        - A planar face
        - Contains an edge approximately 27.5mm long
        - Largest area among candidates

        Returns:
            The front face as a Face object
        """
        faces = self.label_body.faces()

        candidate_faces = []
        for face in faces:
            if not face.is_planar:
                continue

            edges = face.edges()
            for edge in edges:
                if abs(edge.length - self.FRONT_FACE_LENGTH) < self.TOLERANCE:
                    candidate_faces.append(face)
                    break

        if not candidate_faces:
            raise ValueError(
                f"Could not find planar front face with edge length ~{self.FRONT_FACE_LENGTH}mm"
            )

        front_face = sorted(candidate_faces, key=lambda f: f.area, reverse=True)[0]
        return front_face

    def add_text_recess(self) -> 'LabelBuilder':
        """
        Cut recessed text into front face.

        Returns:
            Self for method chaining
        """
        front_face = self.find_front_face()

        sketch_plane = Plane(
            origin=front_face.center(),
            z_dir=front_face.normal_at()
        )

        rotated_text = self.text_geometry.rotate(Axis.Z, 90)

        cleaned_text = rotated_text.clean().fix()

        text_faces = cleaned_text.faces()

        extrude_depth = -(self.text_depth + 0.1)

        with BuildPart() as part:
            add(self.label_body)
            with BuildSketch(sketch_plane):
                for face in text_faces:
                    add(face.fix())
            extrude(amount=extrude_depth, mode=Mode.SUBTRACT)

        self.label_body = part.part
        return self

    def create_text_insert(self) -> 'LabelBuilder':
        """
        Create separate bodies to fill text recesses.

        Returns:
            Self for method chaining
        """
        front_face = self.find_front_face()

        sketch_plane = Plane(
            origin=front_face.center(),
            z_dir=front_face.normal_at()
        )

        rotated_text = self.text_geometry.rotate(Axis.Z, 90)

        cleaned_text = rotated_text.clean().fix()

        text_faces = cleaned_text.faces()

        with BuildPart() as insert:
            with BuildSketch(sketch_plane):
                for face in text_faces:
                    add(face.fix())
            extrude(amount=-self.text_depth)

        self.text_insert = insert.part
        return self
