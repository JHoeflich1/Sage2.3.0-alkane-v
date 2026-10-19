#!/bin/bash
#SBATCH -J check_env
#SBATCH -p blanca-shirts
#SBATCH --qos=blanca-shirts
#SBATCH -t 00:30:00
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --account=blanca-shirts
#SBATCH --export ALL
#SBATCH -o check.out
#SBATCH -e check.err

date
hostname

source ~/.bashrc
ml anaconda
conda activate ash-sage-lily


python make_cim_ff.py 
