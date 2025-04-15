#!/bin/bash

 
# create and empty mdp file 
touch mdrun_ions.mdp
gmx grompp -f mdrun_ions.mdp -c ribosome_cg_box_solv.pdb -p system_solv.top -o ions.tpr 

gmx genion -s ions.tpr -p system_solv.top -pname "NA" -nname "CL" -pq 1 -nq -1 -neutral -conc 0.01  -o ribosome_cg_box_solv_ions.pdb

