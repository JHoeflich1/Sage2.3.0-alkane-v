from openff.toolkit import Molecule, ForceField

ff = ForceField("openff_unconstrained-2.3.0_cim.offxml")
mol = Molecule.from_smiles("CCO")
ff.create_openmm_system(mol.to_topology())
