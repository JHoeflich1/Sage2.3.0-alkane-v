#!/bin/bash
#SBATCH -J download_intial_ff
#SBATCH -p blanca-shirts
#SBATCH --qos=blanca-shirts
#SBATCH -t 00:30:00
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --account=blanca-shirts
#SBATCH --export ALL
#SBATCH -o download_ff.out
#SBATCH -e download_ff.err

date
hostname

source ~/.bashrc
ml anaconda
conda activate ash-sage-lily 


python generate-forcefield.py                                           \
    --force-field-name          "openff_unconstrained-2.3.0_cim.offxml"     \
    --output                    "output/initial-force-field.offxml"
