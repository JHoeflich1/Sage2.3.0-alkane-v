Set up nonbonded training scripts

conda activate evaluator-050

Manually create the /forcefield and targets/pure_data folders

python 03_Prepare_inputs.py -d ../create-targets/nonbonded_training_internal_alkanes_train.json -f ../../01_train-valence/04_fit-forcefield/fb-fit/result/optimize/openff-2.3.0-lipid-valence-v1.offxml
