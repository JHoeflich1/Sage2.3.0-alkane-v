"""Draw unique molecules in the combined optimization training set."""

from __future__ import annotations

import io
import json
from collections import OrderedDict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from rdkit import Chem
from rdkit.Chem import rdDepictor, rdMolDescriptors
from rdkit.Chem.Draw import rdMolDraw2D


ROOT = Path(__file__).resolve().parent
TRAINING_SET = ROOT / "output" / "phosphates_alkane_ene.json"
PHOSPHATE_SET = ROOT / "output" / "phosphates.json"
OUTPUT_PDF = ROOT / "output" / "optimization-training-set.pdf"

PAGE_WIDTH = 2400
PAGE_HEIGHT = 2250
N_COLUMNS = 3
N_ROWS = 3
PER_PAGE = N_COLUMNS * N_ROWS


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{name}", size)


def unmapped_molecule(mapped_smiles: str) -> Chem.Mol:
    parser = Chem.SmilesParserParams()
    parser.removeHs = False
    molecule = Chem.MolFromSmiles(mapped_smiles, parser)
    if molecule is None:
        raise ValueError(f"Could not parse mapped SMILES: {mapped_smiles}")
    for atom in molecule.GetAtoms():
        atom.SetAtomMapNum(0)
    return Chem.RemoveHs(molecule)


def identity(molecule: Chem.Mol) -> str:
    return Chem.MolToSmiles(molecule, isomericSmiles=True)


def depict(molecule: Chem.Mol, width: int, height: int) -> Image.Image:
    molecule = Chem.Mol(molecule)
    rdDepictor.Compute2DCoords(molecule)
    drawer = rdMolDraw2D.MolDraw2DCairo(width, height)
    options = drawer.drawOptions()
    options.useBWAtomPalette()
    options.padding = 0.10
    options.bondLineWidth = 3
    drawer.DrawMolecule(molecule)
    drawer.FinishDrawing()
    return Image.open(io.BytesIO(drawer.GetDrawingText())).convert("RGB")


def make_page(groups: list[dict], page_number: int, n_pages: int) -> Image.Image:
    page = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), "white")
    draw = ImageDraw.Draw(page)
    draw.text((55, 35), "Optimization-geometry training molecules", fill="black", font=font(42, bold=True))
    draw.text(
        (55, 92),
        f"Page {page_number} / {n_pages} — repeated optimization records grouped by molecule",
        fill="#444444",
        font=font(25),
    )

    tile_width = PAGE_WIDTH // N_COLUMNS
    tile_height = (PAGE_HEIGHT - 140) // N_ROWS
    for slot, group in enumerate(groups):
        row, column = divmod(slot, N_COLUMNS)
        x = column * tile_width
        y = 140 + row * tile_height
        image = depict(group["molecule"], tile_width - 45, tile_height - 190)
        page.paste(image, (x + 20, y + 5))

        label_y = y + tile_height - 175
        draw.text(
            (x + 28, label_y),
            f"{group['formula']}    {len(group['record_ids'])} optimization record(s)",
            fill="black",
            font=font(23, bold=True),
        )
        draw.text(
            (x + 28, label_y + 34),
            "Source: " + " + ".join(sorted(group["sources"])),
            fill="#333333",
            font=font(18),
        )
        draw.text(
            (x + 28, label_y + 64),
            f"Example QCArchive record: {group['record_ids'][0]}",
            fill="#333333",
            font=font(17),
        )
        draw.text(
            (x + 28, label_y + 94),
            f"Heavy atoms: {group['n_heavy_atoms']}    InChIKey: {group['inchi_key']}",
            fill="#333333",
            font=font(17),
        )

    return page


def main() -> None:
    training_data = json.loads(TRAINING_SET.read_text())
    training_entries = [entry for entries in training_data["entries"].values() for entry in entries]
    phosphate_data = json.loads(PHOSPHATE_SET.read_text())
    phosphate_ids = {
        int(entry["record_id"])
        for entries in phosphate_data["entries"].values()
        for entry in entries
    }

    groups: OrderedDict[str, dict] = OrderedDict()
    for entry in training_entries:
        molecule = unmapped_molecule(entry["cmiles"])
        key = identity(molecule)
        if key not in groups:
            groups[key] = {
                "molecule": molecule,
                "formula": rdMolDescriptors.CalcMolFormula(molecule),
                "n_heavy_atoms": sum(atom.GetAtomicNum() != 1 for atom in molecule.GetAtoms()),
                "inchi_key": entry["inchi_key"],
                "record_ids": [],
                "sources": set(),
            }
        record_id = int(entry["record_id"])
        groups[key]["record_ids"].append(record_id)
        groups[key]["sources"].add("phosphate" if record_id in phosphate_ids else "alkane/alkene")

    ordered_groups = sorted(
        groups.values(),
        key=lambda group: ("phosphate" not in group["sources"], group["n_heavy_atoms"], group["formula"]),
    )
    n_pages = (len(ordered_groups) + PER_PAGE - 1) // PER_PAGE
    pages = [
        make_page(
            ordered_groups[index * PER_PAGE : (index + 1) * PER_PAGE],
            index + 1,
            n_pages,
        )
        for index in range(n_pages)
    ]
    pages[0].save(
        OUTPUT_PDF,
        save_all=True,
        append_images=pages[1:],
        resolution=150,
    )
    print(f"Optimization records: {len(training_entries)}")
    print(f"Unique molecules: {len(ordered_groups)}")
    print(f"Pages: {n_pages}")
    print(OUTPUT_PDF)


if __name__ == "__main__":
    main()
