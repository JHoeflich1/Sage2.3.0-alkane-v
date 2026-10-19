#!/bin/bash
#SBATCH -J download_and_filter_opt
#SBATCH --partition=blanca-shirts
#SBATCH --qos=blanca-shirts
#SBATCH --account=blanca-shirts
#SBATCH -t 4-00:00:00
#SBATCH --nodes=1
#SBATCH --export ALL
#SBATCH -o download_and_filter_opt.out
#SBATCH -e download_and_filter_opt.err

date
hostname

source ~/.bashrc
ml anaconda
conda activate ash-sage-lily

mkdir -p counts
mkdir -p output

# Use every record in the full alkane/alkene optimization collection.
# Write the downstream dataset and regenerate parameter coverage/counts.
python curate-dataset.py generate-smirks \
    --input 			"output/phosphates_alkane_ene.json" \
    --initial-forcefield 	"../01_generate-forcefield-split-params/output/initial-force-field.offxml" \
    --output-filtered-dataset "output/optimization-training-set.json" \
    --output-parameter-smirks	"output/training-valence-smirks.json" \
    --output-count-file   "counts/valence-counts.json" \
    --verbose
date
