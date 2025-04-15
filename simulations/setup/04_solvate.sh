#!/bin/bash



gmx solvate -cp minim.first.*.gro -cs water.gro -radius 0.21 -o ribosome_cg_box_solv.pdb  
