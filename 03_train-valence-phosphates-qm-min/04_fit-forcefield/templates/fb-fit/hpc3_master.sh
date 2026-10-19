#!/bin/bash
#SBATCH -J fit-alkane-valence-filtered
#SBATCH -p blanca-shirts
#SBATCH -t 7-00:00:00
#SBATCH --qos=blanca-shirts
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --ntasks=1
#SBATCH --mem=10000mb
#SBATCH --account blanca-shirts
#SBATCH --export ALL
#SBATCH -o master-%A.out
#SBATCH -e master-%A.err

# Execute a force field optimization job using SLRUM for job scheduling and FB for computational tasks. Manages workflow by setting up a temp directory, activating a conda environemnt, and handling data transfers. 
ml anaconda
conda_env="${FB_CONDA_ENV:-ash-sage-jul}"

# Creates a temporary directory to isolate job files and prevent conflicts with other jobs
TMPDIR=/scratch/alpine/juho8819/tmp/$SLURM_JOB_ID
# /scratch/alpine/juho8819/LipidsFFF/sage-2.2.1-sdata-core/tmp

rm -rf $TMPDIR
mkdir -p $TMPDIR || { echo "Failed to create TMPDIR"; exit 1; }
cd $TMPDIR

pwd

source $HOME/.bashrc
conda activate $conda_env

echo $CONDA_PREFIX > $SLURM_SUBMIT_DIR/env.path

# Copies files from the submission directory to the temp directory 
rsync -av  $SLURM_SUBMIT_DIR/{optimize.in,targets.tar.gz,forcefield}     $TMPDIR

tar -xzf targets.tar.gz

datadir=$(pwd)
echo $(hostname) > $SLURM_SUBMIT_DIR/host

export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1


mkdir -p result/optimize
#creates an empty file named force-field.offxml to act as a placeholder for later operations
touch result/optimize/force-field.offxml

if ForceBalance.py optimize.in ; then  #runs the force balance script using the input file optimize.in
   echo "-- Force field done --"
   # cat result/optimize/force-field.offxml > "${SLURM_SUBMIT_DIR}/result/optimize/force-field.offxml"
   echo "-- -- -- -- -- -- -- --"
   tar -czf optimize.tmp.tar.gz optimize.tmp #compress the directory optimize.tmp into a tarball optimize.tmp.tar.gz
   rsync  -azIi -rv --exclude="optimize.tmp" --exclude="optimize.bak" \
	  --exclude="fb*"\
	  --exclude="targets*" $TMPDIR/* $SLURM_SUBMIT_DIR > copy.log
   rm -rf $TMPDIR #rsync command synchronizes files from $TMPDIR to $SLURM_SUBMIT_DIR (job submission directory) 
fi

echo "All done"
