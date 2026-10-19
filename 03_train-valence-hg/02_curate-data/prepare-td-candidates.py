"""Build a visual catalog for selecting phosphate torsion-drive records.

The source JSON already contains QCArchive IDs, mapped SMILES, and driven
atom indices, so this script does not contact QCArchive. Each candidate is
tagged with the ProperTorsions parameter assigned by the initial force field.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
from collections import Counter
from pathlib import Path

from openff.toolkit import ForceField, Molecule
from PIL import Image, ImageDraw, ImageFont
from rdkit import Chem
from rdkit.Chem import rdDepictor, rdMolDescriptors
from rdkit.Chem.Draw import rdMolDraw2D


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[4]
SOURCE_GROUPS = {
    "phosphate": {
        "title": "Phosphate torsion-drive candidates",
        "directory": "phosphate-torsion-drives",
        "sources": {
            "OpenFF Phosphate Torsion Drives v1.0": REPO_ROOT / "ff-training" / "OpenFFPhosphateTorsionDrivesv1.0.json",
        },
    },
    "lipid": {
        "title": "Lipid torsion-drive candidates",
        "directory": "lipid-torsion-drives",
        "sources": {
            "OpenFF Lipid Torsion Drives v4.0": REPO_ROOT / "ff-training" / "OpenFFLipidTorsionDrivesv4.0.json",
            "OpenFF Lipid Torsion Drives v4.1": REPO_ROOT / "ff-training" / "OpenFFLipidTorsionDrivesv4.1.json",
        },
    },
}
FORCE_FIELD = ROOT.parent / "01_generate-forcefield" / "output" / "initial-force-field.offxml"

PAGE_WIDTH = 2400
PAGE_HEIGHT = 2250
N_COLUMNS = 3
N_ROWS = 3
PER_PAGE = N_COLUMNS * N_ROWS


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{name}", size)


def assigned_parameter(force_field: ForceField, entry: dict) -> tuple[str, str]:
    molecule = Molecule.from_mapped_smiles(
        entry["mapped_smiles"],
        allow_undefined_stereo=True,
    )
    labels = force_field.label_molecules(molecule.to_topology())[0]["ProperTorsions"]
    indices = tuple(entry["dihedral_indices"])
    parameter = labels.get(indices) or labels.get(indices[::-1])
    if parameter is None:
        raise KeyError(f"No ProperTorsions assignment for record {entry['qcarchive_id']}: {indices}")
    return parameter.id, parameter.smirks


def mapped_rdkit_molecule(mapped_smiles: str) -> Chem.Mol:
    """Parse mapped SMILES without discarding explicit mapped hydrogens."""
    parser = Chem.SmilesParserParams()
    parser.removeHs = False
    molecule = Chem.MolFromSmiles(mapped_smiles, parser)
    if molecule is None:
        raise ValueError("Could not parse mapped SMILES")
    return molecule


def depict(entry: dict, width: int = 720, height: int = 520) -> Image.Image:
    molecule = mapped_rdkit_molecule(entry["mapped_smiles"])

    selected_maps = {index + 1 for index in entry["dihedral_indices"]}
    for atom in molecule.GetAtoms():
        atom.SetIntProp("original_map", atom.GetAtomMapNum())
        if atom.GetAtomicNum() == 1 and atom.GetAtomMapNum() in selected_maps:
            atom.SetIsotope(2)

    molecule = Chem.RemoveHs(molecule)
    map_to_index = {
        atom.GetIntProp("original_map"): atom.GetIdx()
        for atom in molecule.GetAtoms()
    }
    selected_atoms = [map_to_index[index] for index in selected_maps]
    selected_bonds = []
    driven_maps = [index + 1 for index in entry["dihedral_indices"]]
    for first, second in zip(driven_maps, driven_maps[1:]):
        bond = molecule.GetBondBetweenAtoms(map_to_index[first], map_to_index[second])
        if bond is None:
            raise ValueError(f"Missing driven bond in record {entry['qcarchive_id']}: {first}-{second}")
        selected_bonds.append(bond.GetIdx())

    for atom in molecule.GetAtoms():
        atom.SetAtomMapNum(0)
        if atom.GetAtomicNum() == 1:
            atom.SetIsotope(0)

    rdDepictor.Compute2DCoords(molecule)
    drawer = rdMolDraw2D.MolDraw2DCairo(width, height)
    options = drawer.drawOptions()
    options.useBWAtomPalette()
    options.padding = 0.08
    options.bondLineWidth = 3
    red = (1.0, 0.12, 0.12)
    drawer.DrawMolecule(
        molecule,
        highlightAtoms=selected_atoms,
        highlightBonds=selected_bonds,
        highlightAtomColors={index: red for index in selected_atoms},
        highlightBondColors={index: red for index in selected_bonds},
    )
    drawer.FinishDrawing()
    return Image.open(io.BytesIO(drawer.GetDrawingText())).convert("RGB")


def make_page(records: list[dict], page_number: int, n_pages: int, title: str) -> Image.Image:
    page = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), "white")
    draw = ImageDraw.Draw(page)
    draw.text((55, 35), title, fill="black", font=font(42, bold=True))
    draw.text(
        (55, 92),
        f"Page {page_number} / {n_pages} — red atoms and bonds define the driven torsion",
        fill="#444444",
        font=font(25),
    )

    tile_width = PAGE_WIDTH // N_COLUMNS
    tile_height = (PAGE_HEIGHT - 140) // N_ROWS
    for slot, record in enumerate(records):
        row, column = divmod(slot, N_COLUMNS)
        x = column * tile_width
        y = 140 + row * tile_height
        image = depict(record["_entry"], width=tile_width - 45, height=tile_height - 200)
        page.paste(image, (x + 20, y + 5))

        label_y = y + tile_height - 185
        draw.text(
            (x + 28, label_y),
            f"QCArchive {record['record_id']}    {record['parameter_id']}",
            fill="black",
            font=font(23, bold=True),
        )
        draw.text(
            (x + 28, label_y + 34),
            record["source_dataset"],
            fill="#333333",
            font=font(18),
        )
        draw.text(
            (x + 28, label_y + 62),
            f"Driven indices (0-based): {record['dihedral_indices']}",
            fill="#333333",
            font=font(19),
        )
        draw.text(
            (x + 28, label_y + 90),
            f"Atoms: {record['driven_elements']}    Formula: {record['formula']}",
            fill="#333333",
            font=font(19),
        )
        draw.text(
            (x + 28, label_y + 118),
            f"Heavy atoms: {record['n_heavy_atoms']}    Scan points: {record['n_scan_points']}",
            fill="#333333",
            font=font(19),
        )

    return page


def main(group_name: str) -> None:
    group = SOURCE_GROUPS[group_name]
    sources = group["sources"]
    output = ROOT / "candidates" / group["directory"]
    png_dir = output / "pages"
    output.mkdir(parents=True, exist_ok=True)
    png_dir.mkdir(parents=True, exist_ok=True)

    force_field = ForceField(str(FORCE_FIELD), allow_cosmetic_attributes=True)
    records = []

    for source_dataset, source_path in sources.items():
        source_data = json.loads(source_path.read_text())["qm_torsions"]
        for entry in source_data:
            parameter_id, parameter_smirks = assigned_parameter(force_field, entry)
            rdkit_molecule = mapped_rdkit_molecule(entry["mapped_smiles"])
            atom_by_map = {atom.GetAtomMapNum(): atom for atom in rdkit_molecule.GetAtoms()}
            driven_maps = [index + 1 for index in entry["dihedral_indices"]]
            driven_elements = "-".join(atom_by_map[index].GetSymbol() for index in driven_maps)
            canonical = Chem.MolToSmiles(Chem.RemoveHs(rdkit_molecule), isomericSmiles=True)
            records.append(
                {
                    "record_id": int(entry["qcarchive_id"]),
                    "source_dataset": source_dataset,
                    "source_file": source_path.name,
                    "parameter_id": parameter_id,
                    "parameter_smirks": parameter_smirks,
                    "dihedral_indices": "-".join(str(index) for index in entry["dihedral_indices"]),
                    "driven_elements": driven_elements,
                    "formula": rdMolDescriptors.CalcMolFormula(rdkit_molecule),
                    "n_heavy_atoms": sum(atom.GetAtomicNum() != 1 for atom in rdkit_molecule.GetAtoms()),
                    "n_scan_points": len(entry["energies"]),
                    "canonical_smiles": canonical,
                    "mapped_smiles": entry["mapped_smiles"],
                    "_entry": entry,
                }
            )

    record_ids = [record["record_id"] for record in records]
    if len(record_ids) != len(set(record_ids)):
        raise ValueError("Duplicate QCArchive record IDs found across source datasets")

    records.sort(
        key=lambda row: (
            row["parameter_id"],
            row["source_dataset"],
            row["n_heavy_atoms"],
            row["record_id"],
        )
    )
    fieldnames = [key for key in records[0] if not key.startswith("_")]
    with (output / "torsion-drive-candidates.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows({key: row[key] for key in fieldnames} for row in records)

    counts = Counter(record["parameter_id"] for record in records)
    counts_by_source = {
        source_dataset: dict(
            sorted(Counter(record["parameter_id"] for record in records if record["source_dataset"] == source_dataset).items())
        )
        for source_dataset in sources
    }
    with (output / "parameter-counts.json").open("w") as file:
        json.dump({"total": dict(sorted(counts.items())), "by_source": counts_by_source}, file, indent=2)

    n_pages = (len(records) + PER_PAGE - 1) // PER_PAGE
    page_paths = []
    for page_index in range(n_pages):
        page_records = records[page_index * PER_PAGE : (page_index + 1) * PER_PAGE]
        page = make_page(page_records, page_index + 1, n_pages, group["title"])
        path = png_dir / f"torsion-drive-candidates-{page_index + 1:02d}.png"
        page.save(path, optimize=True)
        page_paths.append(path)

    page_images = [Image.open(path).convert("RGB") for path in page_paths]
    page_images[0].save(
        output / "torsion-drive-candidates.pdf",
        save_all=True,
        append_images=page_images[1:],
        resolution=150,
    )

    print(f"Source records: {len(records)}")
    print(f"Candidate pages: {n_pages}")
    print(f"Parameter counts: {dict(sorted(counts.items()))}")
    print(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", choices=sorted(SOURCE_GROUPS), required=True)
    arguments = parser.parse_args()
    main(arguments.group)
