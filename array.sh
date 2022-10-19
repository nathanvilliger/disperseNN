#!/bin/bash
#SBATCH --partition=short
#SBATCH --job-name=sims
#SBATCH --output=%x.txt
#SBATCH --error=%x.txt
#SBATCH --open-mode=append
#SBATCH --time=0-05:00:00
#SBATCH --mem=2G
#SBATCH --array=0-1000
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --account=<account>
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=<email address>

module load python3
EXPONENT=$(python3 -c 'import numpy; print(numpy.random.uniform(1, 4))')
OUTDIR=simdata
mkdir -p ${OUTDIR}
./slim_3.7 -l 0 \
           -d SEED=${SLURM_ARRAY_TASK_ID} \
           -d sigma=0.2 \
           -d kernel_exponent=${EXPONENT} \
           -d K=10 \
           -d mu=0 \
           -d r=1e-8 \
           -d W=50 \
           -d G=1e8 \
           -d maxgens=1e5 \
           -d OUTDIR="'${OUTDIR}'" \
           -d OUTNAME="'output'" \
           SLiM_recipes/bat20.slim
