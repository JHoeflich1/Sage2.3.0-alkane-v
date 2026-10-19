# from openff.evaluator.utils import get_data_filename
import os
from openff.evaluator.datasets import PhysicalPropertyDataSet
from openff.evaluator.attributes import UNDEFINED
from openff.evaluator.datasets.curation.components.filtering import (FilterBySmiles,FilterBySmilesSchema)
from openff.toolkit.typing.engines.smirnoff import ForceField
from openff.toolkit.topology import Molecule, Topology
from forcebalance.evaluator_io import Evaluator_SMIRNOFF
from openff.units import unit
from openff.evaluator.client import RequestOptions
from openff.evaluator.properties import Density, EnthalpyOfVaporization

def check_dataset(dataset):
    """
    Check the dataset to zero out undefined uncertainties.
    This is a temporary fix for a bug in ForceBalance.
    """
    current_directory = os.getcwd() #Ideally you run this script in the same directory as the dataset
    os.makedirs("./targets/pure_data", exist_ok=True)
    data_set_path = os.path.join(current_directory, dataset)
    data_set = PhysicalPropertyDataSet.from_json(data_set_path)
    for physical_property in data_set:
        if physical_property.uncertainty != UNDEFINED:
            continue
        physical_property.uncertainty = 0.0 * physical_property.default_unit()
    
    # If you wnat to filter your dataset, you can do it here, but I will not apply any filteres as there is only 14 datapoints
    # data_set = FilterBySmiles.apply(
    #     data_set,
    #     FilterBySmilesSchema(smiles_to_include=["CCO"]),
    # )
    # save cleaned and filtered datasetr in the pure data folder
    data_set.json("./targets/pure_data/training_set.json")
    return data_set

def load_and_tag_forcefield(data_set, forcefield):
    """
    Load the force field and tag.
    """
    current_directory = os.getcwd()
    os.makedirs("./forcefield", exist_ok=True)
    forcefield_path = os.path.join(current_directory, forcefield)
    force_field = ForceField(forcefield_path, allow_cosmetic_attributes=True)

    # Tag the force field with the dataset
    all_smiles = {
        component.smiles
        for substance in data_set.substances
        for component in substance.components
    }
    #added new section to avoid undefined stereochemistry 
    from openff.toolkit.utils.exceptions import UndefinedStereochemistryError
    for smiles in all_smiles:
        # Find those VdW parameters which would be applied to those components.
        try:
            molecule = Molecule.from_smiles(smiles)
        except UndefinedStereochemistryError:
            print(f"Skipping {smiles} due to undefined stereochemistry")
            continue
        topology = Topology.from_molecules([molecule])

        labels = force_field.label_molecules(topology)[0]

        # Tag the exercised parameters as to be optimized.
        for parameter in labels["vdW"].values():
            parameter.add_cosmetic_attribute("parameterize", "epsilon, rmin_half")
    
    # Save the annotated force field file.
    force_field.to_file(f"./forcefield/force_field_tagged.offxml")

def create_FB_estimator_options(dataset):
    """
    Create the estimator options for ForceBalance.
    """
    # Create the ForceBalance options object
    target_options = Evaluator_SMIRNOFF.OptionsFile()
    # Set the path to the data set #set the path, not enumerate ab object 
    target_options.data_set_path = "training_set.json"


    # Both properties will contribute equally to the objective function.
    target_options.weights = {"Density": 1.0, "EnthalpyOfVaporization": 1.0}
    target_options.denominators = {
        "Density": 30.0 * unit.kilogram / unit.meter**3,
        "EnthalpyOfVaporization": 3.0 * unit.kilojoule / unit.mole,
    }


    # Create the options which evaluator should use.
    evaluator_options = RequestOptions()
    # Choose which calculation layers to make available.
    evaluator_options.calculation_layers = ["SimulationLayer"]

    #I could select the number of moelcules I want to use, but not doing that here

    target_options.estimation_options = evaluator_options
    with open("./targets/pure_data/options.json", "w") as file:
        file.write(target_options.to_json())

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Check the dataset.")
    parser.add_argument(
        "--data_set_name",
        '-d',
        type=str,
        default="filtered_data_set_alkanes.json",
        help="Name of data set file.",
    )
    parser.add_argument(
        "--forcefield",
        '-f',
        type=str,
        default="sage2.2.1-alkanes-filtered-no-cosmetic-att.offxml",
        help="Name of force field file.",
    )
    args = parser.parse_args()
    data_set_name = args.data_set_name
    force_field = args.forcefield

    ds = check_dataset(data_set_name)
    print("Dataset checked and saved in targets/pure_data folder.\n\n")
    print("Loading force field.\n\n")
    load_and_tag_forcefield(ds, force_field)
    print("Force field loaded and tagged and saved in forcefield folder.\n\n")
    print("Reminder to create the ForceBalance input file optimize.in\n\n")
    create_FB_estimator_options(ds)
    print("Estimator options created and saved in targets/pure_data/options.json\n\n")
    print("All done. You can now run the ForceBalance optimization.\n\n")
