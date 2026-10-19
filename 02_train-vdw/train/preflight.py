"""Validate the inputs and exercise ASHGC assignment without running MD."""

import argparse
import importlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
MODEL = "openff-gnn-am1bcc-1.0.0.pt"
# LJ types exercised by the current 12-molecule hydrocarbon training set.
TRAINABLE = {"n2", "n7", "n14", "n16"}


def check_environment():
    """Check runtime imports before allocating MD work or loading the model."""
    modules = {
        "requests": "requests", "python-dateutil": "dateutil.parser",
        "pyyaml": "yaml", "pydantic": "pydantic", "networkx": "networkx",
        "scipy": "scipy", "rdkit": "rdkit", "mdtraj": "mdtraj",
        "netcdf4": "netCDF4", "pandas": "pandas", "uncertainties": "uncertainties",
        "dask": "dask", "distributed": "distributed", "dask-jobqueue": "dask_jobqueue",
        "pymbar": "pymbar", "openmmtools": "openmmtools",
    }
    failures = []
    for package, module in modules.items():
        try:
            importlib.import_module(module)
        except Exception as exc:
            failures.append(f"{package}: {type(exc).__name__}: {exc}")
    if shutil.which("packmol") is None:
        failures.append("packmol: executable is missing from PATH")
    if failures:
        raise RuntimeError(
            "Fitting environment has missing or broken runtime dependencies:\n  "
            + "\n  ".join(failures)
            + "\nUpdate the activated environment from environment.yaml before submitting."
        )
    from openff.units import unit
    if not isinstance(unit.Measurement, type):
        raise RuntimeError("unit.Measurement is not a class; check the Pint/uncertainties pins.")
    from forcebalance.evaluator_io import Evaluator_SMIRNOFF  # noqa: F401
    from openff.evaluator.backends.dask import DaskLocalCluster  # noqa: F401
    from openff.evaluator.server import EvaluatorServer  # noqa: F401
    return {"runtime_imports": "passed", "packmol": shutil.which("packmol")}


def check_inputs(root=ROOT):
    root = Path(root)
    ff = ET.parse(root / "forcefield/force_field_tagged.offxml").getroot()
    if ff.find("ToolkitAM1BCC") is not None:
        raise ValueError("AM1-BCC handler found: this run must use ASHGC.")
    handler = ff.find("ChargeIncrementModel")
    if handler is None or handler.get("partial_charge_method") != MODEL:
        raise ValueError(f"Expected ChargeIncrementModel with {MODEL}.")
    if len(handler) or ff.find("NAGLCharges") is not None:
        raise ValueError("Unexpected charge increments or competing NAGL handler.")
    tagged = {p.get("id"): p.get("parameterize") for p in ff.iter()
              if p.get("parameterize")}
    if set(tagged) != TRAINABLE or any(
        set(value.replace(" ", "").split(",")) != {"epsilon", "rmin_half"}
        for value in tagged.values()
    ):
        raise ValueError(
            f"Expected epsilon and rmin_half for LJ types {sorted(TRAINABLE)}; "
            f"found tags {tagged}."
        )
    data = json.loads((root / "targets/pure_data/training_set.json").read_text())
    smiles = sorted({c["smiles"] for p in data["properties"]
                     for c in p["substance"]["components"]})
    if not smiles:
        raise ValueError("Empty training set.")
    return smiles


def check_charges(root=ROOT, **kwargs):
    # kwargs accepts Evaluator's available_resources when submitted as a task.
    import numpy as np
    from openff.toolkit import ForceField, Molecule
    from openff.toolkit.utils import GLOBAL_TOOLKIT_REGISTRY
    from openff.toolkit.utils.nagl_wrapper import NAGLToolkitWrapper
    from openff.units import unit
    from openmm import NonbondedForce, unit as omm_unit

    smiles = check_inputs(root)
    if not any(isinstance(t, NAGLToolkitWrapper)
               for t in GLOBAL_TOOLKIT_REGISTRY.registered_toolkits):
        raise RuntimeError(
            "NAGL is absent from the global toolkit registry. Activate the supplied "
            "environment with the pinned Toolkit patch; do not switch to AM1-BCC."
        )
    ff = ForceField(str(Path(root) / "forcefield/force_field_tagged.offxml"),
                    allow_cosmetic_attributes=True)
    summaries = []
    for smi in smiles:
        mol = Molecule.from_smiles(smi)
        reference = Molecule(mol)
        reference.assign_partial_charges(MODEL, toolkit_registry=NAGLToolkitWrapper())
        # No charge_from_molecules override: test the actual force-field handler.
        system = ff.create_openmm_system(mol.to_topology())
        forces = [f for f in system.getForces() if isinstance(f, NonbondedForce)]
        if len(forces) != 1 or forces[0].getNumParticles() != mol.n_atoms:
            raise RuntimeError(f"Unexpected nonbonded system for {smi}.")
        assigned = np.array([forces[0].getParticleParameters(i)[0].value_in_unit(
            omm_unit.elementary_charge) for i in range(mol.n_atoms)])
        expected = reference.partial_charges.m_as(unit.elementary_charge)
        np.testing.assert_allclose(assigned, expected, atol=1e-7, rtol=0,
                                   err_msg=f"ASHGC charge mismatch for {smi}")
        if not np.isfinite(assigned).all():
            raise RuntimeError(f"Nonfinite charges for {smi}.")
        summaries.append({"smiles": smi, "atoms": mol.n_atoms,
                          "max_charge_error_e": float(np.max(np.abs(assigned - expected)))})
    return {"model": MODEL, "molecules": summaries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--xml-only", action="store_true",
                      help="Check input structure with standard-library Python only.")
    mode.add_argument("--environment-only", action="store_true",
                      help="Check runtime imports and Packmol without loading NAGL or running MD.")
    args = parser.parse_args()
    if args.xml_only:
        print(json.dumps({"smiles": check_inputs(), "model": MODEL}, indent=2))
    elif args.environment_only:
        print(json.dumps(check_environment(), indent=2))
    else:
        check_environment()
        print(json.dumps(check_charges(), indent=2))


if __name__ == "__main__":
    main()
