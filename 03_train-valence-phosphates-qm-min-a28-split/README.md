# Phosphate QM-minimum fit with an a28 split

This is a controlled sibling of `03_train-valence-phosphates-qm-min`. It uses
the same 600 accepted optimization records and 52 accepted torsion drives, but
splits generic angle `a28` into:

| ID | SMIRKS | chemical context |
|---|---|---|
| `a28` | `[*:1]-[#8:2]-[*:3]` | generic fallback |
| `a28b` | `[#6X3:1](=[#8X1])-[#8X2:2]-[#6:3]` | ester C(=O)-O-C |
| `a28c` | `[#6:1]-[#8X2:2]-[#15:3]` | C-O-P |
| `a28d` | `[#15:1]-[#8X2:2]-[#15:3]` | P-O-P |

The children start with exactly the same angle and force constant as `a28`, so
the starting energy surface is unchanged. SMIRNOFF last-match precedence makes
the three specific children override the generic parent. `a28a` (H-O-X) stays
after them.

## Run order on Blanca

Run each command from the directory containing the named script. Wait for each
setup job to finish successfully before submitting the next one.

```bash
cd 01_generate-forcefield-split-params
sbatch generate_ff.sh

cd ../02_curate-data
sbatch download-and-curate-opt.sh

cd ../04_fit-forcefield
sbatch create-fb-inputs.sh
```

Step 02 does not contact QCArchive. It uses the already copied accepted
optimization dataset and recomputes valence assignments/counts using the split
force field. The existing torsion dataset and torsion counts are reused because
the proper-torsion SMIRKS did not change, so `download-and-curate-td.sh` does
not need to be rerun.

Inspect `02_curate-data/download_and_filter_opt.out` before continuing. With
the current data, `a28b` and `a28c` should exceed the fit cutoff of 3 records;
`a28d` is expected to have only one record and remain fixed. Do not lower the
global cutoff just to train `a28d`.

After step 04 succeeds:

```bash
cd fb-fit
sbatch hpc3_master.sh
```

Wait until `host` exists and the master log indicates that ForceBalance has
started listening, then submit workers:

```bash
sbatch submit_hpc3_worker_local.sh
```

The default ForceBalance port is `59980`. It can be overridden when creating
the inputs:

```bash
FB_PORT=59982 sbatch --export=ALL,FB_PORT create-fb-inputs.sh
```

All torsion-profile targets are generated with `energy_mode = qm_minimum`.
