# ForceBalance phosphate valence fit (QM-minimum)

This step builds the ForceBalance inputs for the phosphate valence fit using
QM-minimum torsion-profile targets. This workflow does **not** use an MSM force
field or require a `03_generate-msm` step.

Run from this directory on Blanca:

```bash
sbatch create-fb-inputs.sh
```

The setup script uses:

- `../01_generate-forcefield/output/initial-force-field.offxml`
- `../02_curate-data/output/optimization-training-set.json`
- `../02_curate-data/output/torsion-training-set.json`
- `../02_curate-data/counts/valence-counts.json`
- `../02_curate-data/counts/torsion-counts.json`

It writes `fb-fit.json` and populates `fb-fit/` with `optimize.in`, targets, and
the force field for ForceBalance. The torsion targets use
`energy_mode = qm_minimum`. After generating those inputs,
`create-fb-inputs.sh` copies the Blanca master and worker submission scripts
from `templates/fb-fit/` into `fb-fit/`.

After `create-fb-inputs.sh` finishes, run the fit from inside `fb-fit/`:

```bash
sbatch hpc3_master.sh
sbatch submit_hpc3_worker_local.sh
```

The default environments are `ash-sage-lily2` for input generation and `ash-sage-jul` for ForceBalance. They can be overridden at submit time with `CREATE_FB_CONDA_ENV`, `FB_CONDA_ENV`, and `FB_PORT`.
