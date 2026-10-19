#!/bin/bash
#SBATCH -J download_and_filter_td
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=8
#SBATCH --partition=blanca-shirts
#SBATCH --qos=blanca-shirts
#SBATCH --account=blanca-shirts
#SBATCH -t 03:00:00
#SBATCH --export ALL
#SBATCH -o download_and_filter_td.out
#SBATCH -e download_and_filter_td.err

date
hostname

source ~/.bashrc
ml anaconda
conda activate ash-sage-lily

mkdir -p counts
mkdir -p output

# Curated training-set run:
# - only_download_core_records.dat contains the QCArchive torsion-drive IDs
#   selected from the candidate molecule groups.
python curate-dataset.py download-td                                                \
    --core-td-dataset       "OpenFF Alkane Torsion Drives v1.0"      \
    --core-td-dataset       "OpenFF Lipid Torsion Drives v4.0"  \
    --core-td-dataset       "OpenFF Lipid Torsion Drives v4.1"  \
    --aux-td-dataset        "OpenFF Alkane Torsion Drives v1.0"                  \
    --initial-forcefield    "../01_generate-forcefield/output/initial-force-field.offxml" \
    --only-download-these-records-core "only_download_core_records.dat"             \
    --n-processes           8                                                       \
    --output                "output/torsion-training-set.json"                      \
    --output-parameter-smirks "output/training-torsion-smirks.json"                 \
    --verbose                 \
    --output-count-file "./counts/torsion-counts.json"
date
