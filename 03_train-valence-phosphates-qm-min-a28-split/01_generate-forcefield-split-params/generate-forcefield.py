"""Create the controlled a28-split starting force field.

All child parameters inherit the original a28 equilibrium angle and force
constant.  The split therefore changes perception only; it does not change
the starting energy surface.
"""

from pathlib import Path

import click


SPLIT_PARAMETERS = (
    ("a28b", "[#6X3:1](=[#8X1])-[#8X2:2]-[#6:3]"),  # ester C(=O)-O-C
    ("a28c", "[#6:1]-[#8X2:2]-[#15:3]"),             # C-O-P
    ("a28d", "[#15:1]-[#8X2:2]-[#15:3]"),            # P-O-P
)


@click.command()
@click.option(
    "--output",
    "output_path",
    type=click.Path(exists=False, dir_okay=False),
    required=True,
    help="Path to the split output force field.",
)
@click.option(
    "--force-field-name",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to the unsplit starting force field.",
)
def generate_force_field(output_path: str, force_field_name: str) -> None:
    from openff.toolkit import ForceField

    output_path = Path(output_path)
    force_field = ForceField(force_field_name, allow_cosmetic_attributes=True)
    angle_handler = force_field.get_parameter_handler("Angles")

    a28_matches = angle_handler.get_parameter({"id": "a28"})
    a28a_matches = angle_handler.get_parameter({"id": "a28a"})
    if len(a28_matches) != 1 or len(a28a_matches) != 1:
        raise RuntimeError("Expected exactly one a28 and one a28a parameter.")

    existing_ids = {parameter.id for parameter in angle_handler.parameters}
    duplicate_ids = existing_ids.intersection(parameter_id for parameter_id, _ in SPLIT_PARAMETERS)
    if duplicate_ids:
        raise RuntimeError(f"Split parameter IDs already exist: {sorted(duplicate_ids)}")

    parent = a28_matches[0]
    before_smirks = a28a_matches[0].smirks
    for parameter_id, smirks in SPLIT_PARAMETERS:
        child = angle_handler.AngleType(
            smirks=smirks,
            angle=parent.angle,
            k=parent.k,
            id=parameter_id,
        )
        # SMIRNOFF uses last-match precedence. Put the specific children after
        # generic a28 and before the existing H-O-X child a28a.
        angle_handler.add_parameter(parameter=child, before=before_smirks)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    force_field.to_file(str(output_path))

    # Reload and assert both ordering and identical starting values.
    written = ForceField(str(output_path), allow_cosmetic_attributes=True)
    written_angles = written.get_parameter_handler("Angles")
    ids = [parameter.id for parameter in written_angles.parameters]
    expected_order = ["a28", "a28b", "a28c", "a28d", "a28a"]
    start = ids.index("a28")
    if ids[start : start + len(expected_order)] != expected_order:
        raise RuntimeError(f"Unexpected split parameter order near a28: {ids[start:start + 5]}")

    written_parent = written_angles.get_parameter({"id": "a28"})[0]
    for parameter_id, _ in SPLIT_PARAMETERS:
        parameter = written_angles.get_parameter({"id": parameter_id})[0]
        if parameter.angle != written_parent.angle or parameter.k != written_parent.k:
            raise RuntimeError(f"{parameter_id} did not inherit the original a28 values.")

    click.echo(f"Wrote {output_path}")
    click.echo("Angle order: " + " -> ".join(expected_order))
    click.echo(f"Shared initial angle: {written_parent.angle}")
    click.echo(f"Shared initial k: {written_parent.k}")


if __name__ == "__main__":
    generate_force_field()
