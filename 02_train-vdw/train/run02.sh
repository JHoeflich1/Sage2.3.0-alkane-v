#!/bin/bash
#SBATCH -J vdW-ASHGC
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --partition=blanca-shirts
#SBATCH --qos=blanca-shirts
#SBATCH --account=blanca-shirts
#SBATCH --gres=gpu:1
#SBATCH -t 6-00:00:00
#SBATCH --mem=16000mb
#SBATCH --export=ALL
#SBATCH -o vdW-%j.out
#SBATCH -e vdW-%j.err

set -eo pipefail
module load anaconda
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "${ASHGC_ENV:-sage-lipid-ashgc-vdw}"
set -u
cd "${SLURM_SUBMIT_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)}"
export OE_LICENSE="${OE_LICENSE:-/projects/juho8819/oe_license.txt}"
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
# Respect Slurm's GPU assignment; do not replace it with CUDA_VISIBLE_DEVICES=0.
nvidia-smi
conda env export > "environment-resolved-${SLURM_JOB_ID:-local}.yaml"
python -m pip freeze > "pip-freeze-${SLURM_JOB_ID:-local}.txt"
python -u run_evaluator.py "$@"
