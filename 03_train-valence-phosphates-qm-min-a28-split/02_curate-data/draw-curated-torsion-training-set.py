"""Draw the curated torsion training set with driven torsions in red."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from openff.toolkit import ForceField
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[4]
TRAINING_SET = ROOT / "output" / "torsion-training-set.json"
OUTPUT_PDF = ROOT / "output" / "torsion-training-set.pdf"
FORCE_FIELD = ROOT.parent / "01_generate-forcefield" / "output" / "initial-force-field.offxml"
SOURCES = {
    "OpenFF Alkane Torsion Drives v1.0": REPO_ROOT / "ff-training" / "OpenFFAlkaneTorsionDrivesv1.0.json",
    "OpenFF Phosphate Torsion Drives v1.0": REPO_ROOT / "ff-training" / "OpenFFPhosphateTorsionDrivesv1.0.json",
    "OpenFF Lipid Torsion Drives v4.0": REPO_ROOT / "ff-training" / "OpenFFLipidTorsionDrivesv4.0.json",
    "OpenFF Lipid Torsion Drives v4.1": REPO_ROOT / "ff-training" / "OpenFFLipidTorsionDrivesv4.1.json",
}


def load_catalog_module():
    path = ROOT / "prepare-td-candidates.py"
    spec = importlib.util.spec_from_file_location("td_candidate_catalog", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> None:
    catalog = load_catalog_module()
    force_field = ForceField(str(FORCE_FIELD), allow_cosmetic_attributes=True)

    source_by_id = {}
    for source_name, source_path in SOURCES.items():
        for entry in json.loads(source_path.read_text())["qm_torsions"]:
            record_id = int(entry["qcarchive_id"])
            if record_id in source_by_id:
                raise ValueError(f"Duplicate source record ID: {record_id}")
            source_by_id[record_id] = (source_name, entry)

    training_data = json.loads(TRAINING_SET.read_text())
    training_entries = [entry for entries in training_data["entries"].values() for entry in entries]
    records = []
    missing = []

    for training_entry in training_entries:
        record_id = int(training_entry["record_id"])
        if record_id not in source_by_id:
            missing.append(record_id)
            continue

        source_name, source_entry = source_by_id[record_id]
        parameter_id, parameter_smirks = catalog.assigned_parameter(force_field, source_entry)
        molecule = catalog.mapped_rdkit_molecule(source_entry["mapped_smiles"])
        atom_by_map = {atom.GetAtomMapNum(): atom for atom in molecule.GetAtoms()}
        driven_maps = [index + 1 for index in source_entry["dihedral_indices"]]
        records.append(
            {
                "record_id": record_id,
                "source_dataset": source_name,
                "parameter_id": parameter_id,
                "parameter_smirks": parameter_smirks,
                "dihedral_indices": "-".join(str(index) for index in source_entry["dihedral_indices"]),
                "driven_elements": "-".join(atom_by_map[index].GetSymbol() for index in driven_maps),
                "formula": rdMolDescriptors.CalcMolFormula(molecule),
                "n_heavy_atoms": sum(atom.GetAtomicNum() != 1 for atom in molecule.GetAtoms()),
                "n_scan_points": len(source_entry["energies"]),
                "_entry": source_entry,
            }
        )

    if missing:
        raise ValueError(f"Training records missing from local source datasets: {missing}")

    records.sort(key=lambda row: (row["source_dataset"], row["parameter_id"], row["record_id"]))
    n_pages = (len(records) + catalog.PER_PAGE - 1) // catalog.PER_PAGE
    pages = [
        catalog.make_page(
            records[index * catalog.PER_PAGE : (index + 1) * catalog.PER_PAGE],
            index + 1,
            n_pages,
            "Curated torsion-drive training molecules",
        )
        for index in range(n_pages)
    ]
    pages[0].save(
        OUTPUT_PDF,
        save_all=True,
        append_images=pages[1:],
        resolution=150,
    )
    print(f"Records: {len(records)}")
    print(f"Pages: {n_pages}")
    print(OUTPUT_PDF)


if __name__ == "__main__":
    main()
