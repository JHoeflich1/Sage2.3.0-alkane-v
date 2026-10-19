# Sage 2.3.0 lipid force-field refits

This directory contains the main Sage 2.3.0 lipid-refit pipeline and several
alternative final valence fits.

```text
Sage 2.3.0 + CIM
  -> 01_train-valence -> lipid-valence-v1
  -> 02_train-vdw     -> alkane-v1
  -> one of the 03_train-valence* branches
```

## Directory guide

| Directory | Purpose and generated force field |
| --- | --- |
| `01_train-valence/` | alkane/alkene valence fitProduces `openff-2.3.0-lipid-valence-v1.offxml`. |
| `02_train-vdw/` | Fits vdW epsilon and radius parameters, starting from `lipid-valence-v1`. Produces `openff-2.3.0-alkane-v1.offxml`. |
| `03_train-valence/` | Standard second valence fit starting from `alkane-v1`; MSM values initialize bonds and angles. Average energy mode on FB. Produces `openff-2.3.0-alkane-v2.offxml`. |
| `03_train-valence-qm_min/` | Alternative second valence fit starting from `alkane-v1`, with FB QM minimum and no MSM initialization. Produces `openff-2.3.0-alkane-v3.offxml`. |
| `03_train-valence-hg/` | Extends the `alkane-v1` valence fit with lipid-headgroup/phosphate QM data. Produces `openff-2.3.0-alkane-lipid-headgroup-v1.offxml`. |
| `03_train-valence-phosphates-qm-min/` | Experimental phosphate valence fit using QM-minimum torsion targets. Not complete. |
| `03_train-valence-phosphates-qm-min-a28-split/` | Controlled version of the phosphate QM-minimum fit that splits generic angle `a28` into ester, C-O-P, and P-O-P environments. Not complete. |

The `03_train-valence*` directories are alternative branches from
`openff-2.3.0-alkane-v1.offxml`; they are not intended to be run sequentially.