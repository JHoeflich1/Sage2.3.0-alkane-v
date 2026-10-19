#!/usr/bin/env python
import logging
import pathlib
import sys

import click


logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@click.command()
@click.option(
    "--optimization-dataset",
    "-i",
    required=True,
    type=click.Path(exists=True, dir_okay=False, file_okay=True),
    help="Filtered OptimizationResultCollection JSON from 02_curate-data.",
)
@click.option(
    "--output",
    "-o",
    required=True,
    type=click.Path(exists=False, dir_okay=False, file_okay=True),
    help="Output BasicResultCollection JSON containing Hessian records.",
)
def main(optimization_dataset: str, output: str):
    from openff.qcsubmit.results import OptimizationResultCollection
    from openff.qcsubmit.results.filters import LowestEnergyFilter

    dataset = OptimizationResultCollection.parse_file(optimization_dataset)
    logger.info("Loaded %d optimization records", dataset.n_results)

    filtered = dataset.filter(LowestEnergyFilter())
    logger.info("Kept %d lowest-energy optimization records", filtered.n_results)

    hessian_set = filtered.to_basic_result_collection(driver="hessian")
    logger.info("Found %d Hessian records", hessian_set.n_results)
    logger.info("Found %d Hessian molecules", hessian_set.n_molecules)

    output_path = pathlib.Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(hessian_set.json(indent=2))
    logger.info("Wrote Hessian dataset to %s", output_path)


if __name__ == "__main__":
    main()
