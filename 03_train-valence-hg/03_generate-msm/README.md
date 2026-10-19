# 03_generate-msm

This folder uses the Sage 2.3.0-rc2 style Modified Seminario Method workflow.

The upstream scripts are from:

https://github.com/openforcefield/ash-sage-rc2/tree/main/03_fit-valence/03_generate-msm

Local adaptation:

- `make-hessian-dataset.py` builds a Hessian `BasicResultCollection` from
  `../02_curate-data/output/phosphates_alkane_ene.json`.
- `calculate-msm.py` calculates per-molecule MSM bond and angle values into
  `msm-data/`.
- `generate-msm-forcefield.py` averages those MSM values by force-field
  parameter and writes `output/initial-force-field-msm.offxml`.

Create the MSM environment on Blanca first:

```bash
conda env create -f msm-env.yaml
```

`msm-env.yaml` uses the upstream `sage-2.3.0-qubekit` MSM dependency
versions, with macOS-only packages and platform-specific build pins omitted
for Linux. Both `run-msm.sh` and the older
`../03_generate-initial-ff/create-msm-ff.sh` activate this environment.

Run on Blanca with:

```bash
sbatch run-msm.sh
```

The input force field is:

```text
../01_generate-forcefield/output/initial-force-field.offxml
```

The filtered optimization dataset is:

```text
../02_curate-data/output/phosphates_alkane_ene.json
```
