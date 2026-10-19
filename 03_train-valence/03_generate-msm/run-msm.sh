#!/bin/bash
#SBATCH -J msm_filtered
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --partition=blanca-shirts
#SBATCH --qos=blanca-shirts
#SBATCH --account=blanca-shirts
#SBATCH -t 10:00:00
#SBATCH --export ALL
#SBATCH -o msm.out
#SBATCH -e msm.err

set -e

date
hostname

source ~/.bashrc
ml anaconda
conda activate sage-2.3.0-qubekit

FF="../01_generate-forcefield/output/initial-force-field.offxml"
OPT_DATASET="../02_curate-data/output/optimization-training-set.json"
HESSIAN_DATASET="qm-data/hessian-data/hessian_results.json"

mkdir -p logs
mkdir -p output
mkdir -p qm-data/hessian-data
mkdir -p msm-data
mkdir -p msm-ff

python make-hessian-dataset.py                         \
    --optimization-dataset "${OPT_DATASET}"             \
    --output "${HESSIAN_DATASET}"                       \
    > logs/make-hessian-dataset.log 2>&1

python calculate-msm.py                                 \
    --input-dataset "${HESSIAN_DATASET}"                \
    --output-directory msm-data                         \
    > logs/calculate-msm.log 2>&1

python generate-msm-forcefield.py                       \
    --msm-data-directory msm-data                       \
    --output-msm msm-ff/initial-force-field-msm.json    \
    --input-forcefield "${FF}"                          \
    --aggregator mean                                   \
    --output-forcefield output/initial-force-field-msm.offxml \
    > logs/generate-msm-forcefield.log 2>&1

date
