#!/bin/bash
#SBATCH -J fb_input
#SBATCH --partition=blanca-shirts
#SBATCH --qos=blanca-shirts
#SBATCH --account=blanca-shirts
#SBATCH -t 1-00:00:00
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --export ALL
#SBATCH -o fb_input.out-%A
#SBATCH -e fb_input.err-%A

# creates output/schemas/optimizations folder

date
hostname

source ~/.bashrc
ml anaconda

CREATE_FB_CONDA_ENV="${CREATE_FB_CONDA_ENV:-ash-sage-lily2}"
FB_PORT="${FB_PORT:-59980}"

conda activate "${CREATE_FB_CONDA_ENV}"

python create-fb-inputs-nagl.py                                                                          \
    --tag                       "fb-fit"                                                            \
    --optimization-dataset      "../02_curate-data/output/phosphates_alkane_ene.json"                \
    --torsion-dataset           "../02_curate-data/output/torsion-training-set.json"                \
    --forcefield                "../03_generate-msm/output/initial-force-field-msm.offxml"       \
    --valence-counts            "../02_curate-data/counts/valence-counts.json"         \
    --torsion-counts            "../02_curate-data/counts/torsion-counts.json"                 \
    --n-min-valence             3       \
    --n-min-torsion             1       \
    --angle-k-prior             100     \
    --bond-k-prior              100     \
    --angle-angle-prior         5       \
    --bond-length-prior         0.1     \
    --frozen-angle-file         "linear-angles.json"                                             \
    --max-iterations            100                                                                 \
    --port                      "${FB_PORT}"                                                        \
    --output-directory          "output"                                                            \
    --verbose

mkdir -p fb-fit/worker-logs
cp templates/fb-fit/hpc3_master.sh fb-fit/hpc3_master.sh
cp templates/fb-fit/submit_hpc3_worker_local.sh fb-fit/submit_hpc3_worker_local.sh
chmod +x fb-fit/hpc3_master.sh fb-fit/submit_hpc3_worker_local.sh

date
