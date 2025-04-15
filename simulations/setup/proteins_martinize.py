#!/usr/bin/env python

import os
def process_text(filename):
    # Open the file and read the contents
    with open(filename, 'r') as f:
        lines = f.readlines()
    # Remove the first line
    lines = lines[1:]
    # Concatenate the remaining lines into a single string
    text = ''.join(lines)
    # Replace "~" with "C" in the string
    text = text.replace('~', 'C')
    # Return the resulting string
    return text


CHAINS = ['0', '1', '2', '3', '4', '5', '6', '7',  'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',  'b',
 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't',
 'u']
home_dir = os.getcwd()
for ef in CHAINS:
    if ef.islower():  
        os.chdir("./ch_%sS"%ef)
        name = "./ch_%sS"%ef
    else:  
        os.chdir("./ch_%s"%ef)
        name = "./ch_%s"%ef
    os.system("python ../martinize.py -f kan_chain_%s.pdb -o %s.top -x %s_CG.pdb  -p backbone -ef 500 -eu 0.7 -ff elnedyn22 -ss %s"%(ef,name,name, process_text("ssdump.dat")))
    
    os.chdir(home_dir)


