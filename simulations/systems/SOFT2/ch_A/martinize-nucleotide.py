#!/usr/bin/env python

# EDITABLE SECTIONS ARE MARKED WITH #@# 

version="2.2"
authors=["Djurre de Jong", "Jaakko J. Uusitalo", "Tsjerk A. Wassenaar"]

# Parameters are defined for the following (protein) forcefields:
forcefields = ['martini22nucleic','elnedyn22nucleic']

# 
# This program has grown to be pretty complete and complex. 
# The routines have been organized in sections, which are 
# tagged to make jumping to a particular section easy.
# For working versions, the sections are in different modules
#
# Index of this file:
#
#   1. Options and documentation                             @DOC
#   2. Description, options and command line parsing         @CMD
#   3. Helper functions and macros                           @FUNC
#   4. Finegrained to coarsegrained mapping                  @MAP
#   5. Secondary structure determination and interpretation  @SS
#   6. Force field parameters (MARTINI/ELNEDYN)              @FF
#   7. Elastic network                                       @ELN
#   8. Structure I/O                                         @IO
#   9. Topology generation                                   @TOP
#  10. Main                                                  @MAIN
#  11. Web-interface                                         @WEB
#  

def cat(file_out):
    '''Function to 'compile' the martinize script into one file.'''
    import re
    files_in = 'martinize.py DOC.py CMD.py FUNC.py MAP.py SS.py '+'.py '.join(forcefields)+'.py ELN.py IO.py TOP.py MAIN.py '
    pattern1 = re.compile(files_in.replace('.py ','|')[:-1])
    pattern2 = re.compile(files_in.replace('.py ','\.|')[:-1])
    file_out = open(file_out,'w')
    tail = ''; head = True
    for f in files_in.split():
        for line in open(f).readlines():
            # Split the string to avoid the function finding itself
            if '__na'+'me__' in line:
                head = False
            if head:
                file_out.write(line)
            elif (f == 'martinize.py' and not head) and not ('import' in line and pattern1.search(line)):
                tail += pattern2.sub('',line)
            elif line[0] == '#':
                file_out.write(line)
            elif not ('import' in line and pattern1.search(line)):
                file_out.write(pattern2.sub('',line))
    file_out.write(tail)

###################################
## 1 # OPTIONS AND DOCUMENTATION ##  -> @DOC <-
###################################

    
# This is a simple and versatily option class that allows easy
# definition and parsing of options. 
class Option:
    def __init__(self,func=str,num=1,default=None,description=""):
        self.func        = func
        self.num         = num
        self.value       = default
        self.description = description
    def __nonzero__(self): 
        if self.func == bool:
            return self.value != False
        return bool(self.value)
    def __str__(self):
        return self.value and str(self.value) or ""
    def setvalue(self,v):
        if len(v) == 1:
            self.value = self.func(v[0])
        else:
            self.value = [ self.func(i) for i in v ]
    

# Lists for gathering arguments to options that can be specified 
# multiple times on the command line.
lists = {
    'cystines': [],
    'merges'  : [],
    'links'   : [],
    'multi'   : [],
    }

# List of Help text and options. 
# This way we can simply print this list if the user wants help. 
options = [
#   NOTE: Options marked with (+) can be given multiple times on the command line
#   option              type number default description
    """
MARTINIZE.py is a script to create Coarse Grain Martini input files of
proteins, ready for use in the molecular dynamics simulations package 
Gromacs. For more information on the Martini forcefield, see:
www.cgmartini.nl
and read our papers:
Monticelli et al., J. Chem. Theory Comput., 2008, 4(5), 819-834
de Jong et al., J. Chem. Theory Comput., 2013, DOI:10.1021/ct300646g

Primary input/output
--------------------
The input file (-f) should be a coordinate file in PDB or GROMOS
format. The format is inferred from the structure of the file. The 
input can also be provided through stdin, allowing piping of 
structures. The input structure can have multiple frames/models. If an output
structure file (-x) is given, each frame will be coarse grained,
resulting in a multimodel output structure. Having multiple frames may
also affect the topology. If secondary structure is determined
internally, the structure will be averaged over the frames. Likewise,
interatomic distances, as used for backbone bond lengths in Elnedyn
and in elastic networks, are also averaged over the frames available.

If an output file (-o) is indicated for the topology, that file will
be used for the master topology, using #include statements to link the
moleculetype definitions, which are written to separate files. If no
output filename is given, the topology and the moleculetype
definitions are written to stdout.

Secondary structure
-------------------
The secondary structure plays a central role in the assignment of atom
types and bonded interactions in MARTINI. Martinize allows
specification of the secondary structure as a string (-ss), or as a
file containing a specification in GROMACS' ssdump format
(-ss). Alternatively, DSSP can be used for an on-the-fly assignment of
the secondary structure. For this, the option -dssp has to be used
giving the location of the executable as the argument. 
The option -collagen will set the whole structure to collagen. If this
is not what you want (eg only part of the structure is collagen, you
can give a secondary structure file/string (-ss) and specifiy collagen
as "F". Parameters for collagen are taken from: Gautieri et al., 
J. Chem. Theory Comput., 2010, 6, 1210-1218. 
With multimodel input files, the secondary structure as determined with
DSSP will be averaged over the frames. In this case, a cutoff
can be specified (-ssc) indicating the fraction of frames to match a
certain secondary structure type for designation.

Topology
--------
Several options are available to tune the resulting topology. By
default, termini are charged, and chain breaks are kept neutral. This
behaviour can be changed using -nt and -cb, respectively.

Disulphide bridges can be specified using -cys. This option can be
given multiple times on the command line. The argument is a pair of
cysteine residues, using the format
chain/resn/resi,chain/resn/resi. For disulphide bridges, the residue
name is not required, and the chain identifier is optional. If no
chain identifier is given, all matching residue pairs will be checked,
and pairs within the cutoff distance (0.22 nm) will be linked. It is
also possible to let martinize detect cysteine pairs based on this
cut-off distance, by giving the keyword 'auto' as argument to -cys.
Alternatively, a different cut-off distance can be specified, which
will also trigger a search of pairs satisfying the distance
criterion.

In addition to cystine bridges, links between other atoms can be
specified using -link. This requires specification of the atoms, using
the format
chain/resi/resn/atom,chain/resi/resn/atom,bondlength,forceconstant.
If only two atoms are given, a constraint will be added with length
equal to the (average) distance in the coordinate file. If a bond
length is added, but no force constant, then the bondlength will be
used to set a constraint.

Linking atoms requires that the atoms are part of the same
moleculetype. Therefore any link between chains will cause the chains
to be merged. Merges can also be specified explicitly, using the
option -merge with a comma-separated list of chain identifiers to be
joined into one moleculetype. The option -merge can be used several
times. Note that specifying a chain in several merge groups will cause
all chains involved to be merged into a single moleculetype.

The moleculetype definitions are written to topology include (.itp)
files, using a name consisting of the molecule class (e.g. Protein)
and the chain identifier. With -name a name can be specified instead.
By default, martinize only writes a moleculetype for each unique
molecule, inferred from the sequence and the secondary structure
definition. It is possible to force writing a moleculetype definition
for every single molecule, using -sep.

The option -p can be used to write position restraints, using the 
force constant specified with -pf, which is set to 1000 kJ/mol 
by default.

For stability, elastic bonds are used to retain the structure of 
extended strands. The option -ed causes dihedrals to be used 
instead.

Different forcefields can be specified with -ff. All the parameters and
options belonging to that forcefield  will be set (eg. bonded interactions,
BB-bead positions, Elastic Network, etc.). By default martini 2.1 is
used.

Elastic network
---------------
Martinize can write an elastic network for atom pairs within a cutoff
distance. The force constant (-ef) and the upper distance bound (-eu) 
can be speficied. If a force field with an intrinsic Elastic
network is specified (eg. Elnedyn) with -ff, -elastic in implied and
the default values for the force constant and upper cutoff are used.
However, these can be overwritten.

Multiscaling
------------
Martinize can process a structure to yield a multiscale system,
consisting of a coordinate file with atomistic parts and
corresponding, overlaid coarsegrained parts. For chains that are
multiscaled, rather than writing a full moleculetype definition, 
additional [atoms] and [virtual_sitesn] sections are written, to 
be appended to the atomistic moleculetype definitions. 
The option -multi can be specified multiple times, and takes a chain
identifier as argument. Alternatively, the keyword 'all' can be given
as argument, causing all chains to be multiscaled.
========================================================================\n
""",
    ("-f",        Option(str,                      1,     None, "Input file (PDB|GRO)")),
    ("-o",        Option(str,                      1,     None, "Output topology (TOP)")),
    ("-x",        Option(str,                      1,     None, "Output coarse grained structure (PDB)")),
    ("-n",        Option(str,                      1,     None, "Output index file with CG (and multiscale) beads.")),
    ("-nmap",     Option(str,                      1,     None, "Output index file containing per bead mapping.")),
    ("-seq",      Option(str,                      1,     None, "Output list of bead numbers.")),
    ("-bmap",     Option(str,                      1,     None, "Output index file containing bonded terms.")),
    ("-v",        Option(bool,                     0,    False, "Verbose. Be load and noisy.")), 
    ("-h",        Option(bool,                     0,    False, "Display this help.")),
    ("-ss",       Option(str,                      1,     None, "Secondary structure (File or string)")),
    ("-ssc",      Option(float,                    1,      0.5, "Cutoff fraction for ss in case of ambiguity (default: 0.5).")),
    ("-dssp",     Option(str,                      1,     None, "DSSP executable for determining structure")),
#    ("-pymol",    Option(str,                      1,     None, "PyMOL executable for determining structure")),
    ("-collagen", Option(bool,                     0,    False, "Use collagen parameters")),
    ("-his",      Option(bool,                     0,    False, "Interactively set the charge of each His-residue.")),
    ("-nt",       Option(bool,                     0,    False, "Set neutral termini (charged is default)")), 
    ("-cb",       Option(bool,                     0,    False, "Set charges at chain breaks (neutral is default)")), 
    ("-cys",      Option(lists['cystines'].append, 1,     None, "Disulphide bond (+)")),
    ("-link",     Option(lists['links'].append,    1,     None, "Link (+)")),
    ("-merge",    Option(lists['merges'].append,   1,     None, "Merge chains: e.g. -merge A,B,C (+)")),
#    ("-mixed",    Option(bool,                     0,    False, "Allow chains of mixed type (default: False)")),
    ("-name",     Option(str,                      1,     None, "Moleculetype name")),
    ("-p",        Option(str,                      1,   'None', "Output position restraints (None/All/Backbone) (default: None)")),
    ("-pf",       Option(float,                    1,     1000, "Position restraints force constant (default: 1000 kJ/mol/nm^2)")),
    ("-ed",       Option(bool,                     0,    False, "Use dihedrals for extended regions rather than elastic bonds)")),
    ("-sep",      Option(bool,                     0,    False, "Write separate topologies for identical chains.")),
    ("-ff",       Option(str,                      1,'martini21', "Which forcefield to use: "+' ,'.join(n for n in forcefields[:-1]))),
# Fij = Fc exp( -a (rij - lo)**p )
    ("-elastic",  Option(bool,                     0,    False, "Write elastic bonds")),
    ("-ef",       Option(float,                    1,      500, "Elastic bond force constant Fc")),
    ("-el",       Option(float,                    1,        0, "Elastic bond lower cutoff: F = Fc if rij < lo")),
    ("-eu",       Option(float,                    1,     0.90, "Elastic bond upper cutoff: F = 0  if rij > up")),
    ("-ea",       Option(float,                    1,        0, "Elastic bond decay factor a")),
    ("-ep",       Option(float,                    1,        1, "Elastic bond decay power p")),
    ("-em",       Option(float,                    1,        0, "Remove elastic bonds with force constant lower than this")),
    ("-eb",       Option(str,                      1,     'BB', "Comma separated list of bead names for elastic bonds")),
    ("-type",     Option(str,                      1,     'ss', "Type of DNA/RNA topology (ss/ds-stiff/ds-soft) to create. (default: ss)")),
#    ("-hetatm",   Option(bool,                     0,    False, "Include HETATM records from PDB file (Use with care!)")),
    ("-multi",    Option(lists['multi'].append,    1,     None, "Chain to be set up for multiscaling (+)")),
    ]

## Martini Quotes
martiniq = [
    ("Robert Benchley",
     "Why don't you get out of that wet coat and into a dry martini?"),
    ("James Thurber",
     "One martini is all right, two is two many, three is not enough"),
    ("Philip Larkin",
     "The chromatic scale is what you use to give the effect of drinking a quinine martini and having an enema simultaneously."),
    ("William Emerson, Jr.",
     "And when that first martini hits the liver like a silver bullet, there is a sigh of contentment that can be heard in Dubuque."),
    ("Alec Waugh",
     "I am prepared to believe that a dry martini slightly impairs the palate, but think what it does for the soul."),
    ("Gerald R. Ford",
     "The three-martini lunch is the epitome of American efficiency. Where else can you get an earful, a bellyful and a snootful at the same time?"),
    ("P. G. Wodehouse",
     "He was white and shaken, like a dry martini."),
    ]

## DNA elastic network list 
enStrandLengths = [] 

desc = ""
    
def help():
    """Print help text and list of options and end the program."""
    import sys
    for item in options:
        if type(item) == str:
            print (item)
    for item in options:
        if type(item) != str:
            print ("%10s  %s"%(item[0],item[1].description))
    print
    sys.exit()
##############################
## 2 # COMMAND LINE PARSING ##  -> @CMD <-
##############################
import sys,logging

# Helper function to parse atom strings given on the command line:
#   resid
#   resname/resid
#   chain/resname/resid
#   resname/resid/atom
#   chain/resname/resid/atom
#   chain//resid
#   chain/resname/atom
def str2atom(a):
    a = a.split("/")   
    if len(a) == 1: # Only a residue number:
        return (None,None,int(a[0]),None)
    if len(a) == 2: # Residue name and number (CYS/123):
        return (None,a[0],int(a[1]),None)
    if len(a) == 3:
        if a[2].isdigit(): # Chain, residue name, residue number
            return (None,a[1],int(a[2]),a[0])
        else: # Residue name, residue number, atom name
            return (a[2],a[0],int(a[1]),None)
    return (a[3],a[1],int(a[2]),a[0])

def option_parser(args,options,lists,version=0):

    # Check whether there is a request for help
    if '-h' in args or '--help' in args:
        help()

    # Convert the option list to a dictionary, discarding all comments
    options = dict([i for i in options if not type(i) == str])

    # This information we would like to print to some files, so let's put it in our information class
    options['Version']             = version
    options['Arguments']           = args[:]
   
    while args:
        ar = args.pop(0)
        options[ar].setvalue([args.pop(0) for i in range(options[ar].num)])

    ## LOGGING ##
    # Set the log level and communicate which options are set and what is happening
    # If 'Verbose' is set, change the logger level
    logLevel = options["-v"] and logging.DEBUG or logging.INFO
    logging.basicConfig(format='%(levelname)-7s    %(message)s',level=logLevel)

    logging.info('MARTINIZE, script version %s'%version)
    logging.info('If you use this script please cite:')
    logging.info('de Jong et al., J. Chem. Theory Comput., 2013, DOI:10.1021/ct300646g')

    # Write options based on selected topology type.
    options['type'] = options['-type'].value
    if options['type'] == 'ss':
        options['-ff'].setvalue(['martini22nucleic'])
    elif options['type'] == 'ds-stiff':
        options['-ff'].setvalue(['elnedyn22nucleic'])
        lists['merges'].append('A,B')
        options['-eu'].setvalue(['1.0'])
        options['-ef'].setvalue(['500'])
        options['-eb'].setvalue(['BB1,BB2,BB3,SC1,SC2,SC3,SC4'])
    elif options['type'] == 'ds-soft': 
        options['-ff'].setvalue(['elnedyn22nucleic'])
        lists['merges'].append('A,B')
        options['-eu'].setvalue(['1.2'])
        options['-ef'].setvalue(['13'])
        options['-eb'].setvalue(['BB1,BB2,BB3,SC1'])
    elif options['type'] == 'ss-stiff':
        options['-ff'].setvalue(['elnedyn22nucleic'])
        options['-eu'].setvalue(['1.0'])
        options['-ef'].setvalue(['500'])
        options['-eb'].setvalue(['BB1,BB2,BB3,SC1,SC2,SC3,SC4'])
    elif options['type'] == 'ss-soft': 
        options['-ff'].setvalue(['elnedyn22nucleic'])
        options['-eu'].setvalue(['1.2'])
        options['-ef'].setvalue(['13'])
        options['-eb'].setvalue(['BB1,BB2,BB3,SC1'])
    elif options['type'] == 'ss-soft-two': 
        options['-ff'].setvalue(['elnedyn22nucleic'])
        options['-eu'].setvalue(['1.0'])
        options['-ef'].setvalue(['13'])
        options['-eb'].setvalue(['BB1,BB2,BB3,SC1,SC2,SC3,SC4'])

    elif options['type'] == 'ignore':
        pass
    else: 
        logging.error('Undefined topology type. Giving up...')
        sys.exit()
     
    # The make the program flexible, the forcefield parameters are defined
    # for multiple forcefield. Check if a existing one is defined:
    ###_tmp  = __import__(options['-ff'].value.lower())
    ###options['ForceField']  = getattr(_tmp,options['-ff'].value.lower())()
    try:
        try:
            # Try to load the forcefield class from a different file
            _tmp  = __import__(options['-ff'].value.lower())
            options['ForceField']  = getattr(_tmp,options['-ff'].value.lower())()
        except:
            # Try to load the forcefield class from the current file
            options['ForceField']  = globals()[options['-ff'].value.lower()]()
    except:
        logging.error("Forcefield '%s' can not be found."%(options['-ff']))
        sys.exit()

    # Process the raw options from the command line
    # Boolean options are set to more intuitive variables
    options['Collagen']            = options['-collagen']
    options['chHIS']               = options['-his']
    options['ChargesAtBreaks']     = options['-cb']
    options['NeutralTermini']      = options['-nt']
    options['ExtendedDihedrals']   = options['-ed']
    options['RetainHETATM']        = False # options['-hetatm']
    options['SeparateTop']         = options['-sep']
    options['MixedChains']         = False # options['-mixed']
    options['ElasticNetwork']      = options['-elastic']
 
    # Parsing of some other options into variables
    options['ElasticMaximumForce'] = options['-ef'].value 
    options['ElasticMinimumForce'] = options['-em'].value
    options['ElasticLowerBound']   = options['-el'].value
    options['ElasticUpperBound']   = options['-eu'].value
    options['ElasticDecayFactor']  = options['-ea'].value
    options['ElasticDecayPower']   = options['-ep'].value
    options['ElasticBeads']        = options['-eb'].value.split(',')
    options['PosResForce']         = options['-pf'].value

    options['PosRes']              = [i.lower() for i in options['-p'].value.split(",")]
    if "none"     in options['PosRes']: options['PosRes'] = []
    if "backbone" in options['PosRes']: options['PosRes'].append("BB")
    
    if options['ForceField'].ElasticNetwork:
        # Some forcefields, like elnedyn, always use an elatic network. This is set in the 
        # forcefield file, with the parameter ElasticNetwork.
        options['ElasticNetwork']  = True
    
    # Merges, links and cystines
    options['mergeList'] = "all" in lists['merges'] and ["all"] or [i.split(",") for i in lists['merges']]


    # Process links
    linkList   = []
    linkListCG = []
    for i in lists['links']:
        ln     = i.split(",")
        a, b   = str2atom(ln[0]), str2atom(ln[1])
        if len(ln) > 3: # Bond with given length and force constant
            bl, fc = (ln[2] and float(ln[2]) or None, float(ln[3]))
        elif len(a) == 3: # Constraint at given distance
            bl, fc = float(a[2]), None
        else: # Constraint at distance in structure
            bl, fc = None, None
        # Store the link, but do not list the atom name in the
        # atomistic link list. Otherwise it will not get noticed 
        # as a valid link when checking for merging chains
        linkList.append(((None,a[1],a[2],a[3]),(None,b[1],b[2],b[3])))
        linkListCG.append((a,b,bl,fc))
    
    
    # Cystines -- This should be done for all special bonds listed in the _special_ dictionary
    CystineCheckBonds = False   # By default, do not detect cystine bridges
    CystineMaxDist2   = (10*0.22)**2 # Maximum distance (A) for detection of SS bonds
    for i in lists['cystines']:
        if i.lower() == "auto":
            CystineCheckBonds = True
        elif i.replace(".","").isdigit():
            CystineCheckBonds = True
            CystineMaxDist2   = (10*float(i))**2
        else:
            # This item should be a pair of cysteines
            cysA, cysB = [str2atom(j) for j in i.split(",")]
            # Internally we handle the residue number shifted by ord(' ')<<20. We have to add this to the
            # cys-residue numbers given here as well.
            constant = 32<<20
            linkList.append((("SG","CYS",cysA[2]+constant,cysA[3]),("SG","CYS",cysB[2]+constant,cysB[3])))
            linkListCG.append((("SC1","CYS",cysA[2]+constant,cysA[3]),("SC1","CYS",cysB[2]+constant,cysB[3]),-1,-1))

    # Now we have done everything to it, we can add Link/cystine related stuff to options
    # 'multi' is not stored anywhere else, so that we also add
    options['linkList']          = linkList
    options['linkListCG']        = linkListCG
    options['CystineCheckBonds'] = CystineCheckBonds
    options['CystineMaxDist2']   = CystineMaxDist2
    options['multi']             = lists['multi']

    logging.info("Chain termini will%s be charged"%(options['NeutralTermini'] and " not" or ""))
    
    logging.info("Residues at chain brakes will%s be charged"%((not options['ChargesAtBreaks']) and " not" or ""))

    if options.has_key('ForceField'):
        logging.info("The %s forcefield will be used."%(options['ForceField'].name))
    else:
        logging.error("Forcefield '%s' has not been implemented."%(options['-ff']))
        sys.exit()
    
    if options['ExtendedDihedrals']:  
        logging.info('Dihedrals will be used for extended regions. (Elastic bonds may be more stable)')
    else:                  
        logging.info('Local elastic bonds will be used for extended regions.')
    
    
    if options['PosRes']:
        logging.info("Position restraints will be generated.")
        logging.warning("Position restraints are only enabled if -DPOSRES is set in the MDP file")
    
    
    if options['MixedChains']:
        logging.warning("So far no parameters for mixed chains are available. This might crash the program!")
    
    
    if options['RetainHETATM']:
        logging.warning("I don't know how to handle HETATMs. This will probably crash the program.")

    return options 
#################################################
## 3 # HELPER FUNCTIONS, CLASSES AND SHORTCUTS ##  -> @FUNC <-
#################################################

import math

#----+------------------+
## A | STRING FUNCTIONS |
#----+------------------+

# Split a string                                                              
def spl(x):                                                                   
    return x.split()                                                          


# Split each argument in a list                                               
def nsplit(*x):                                                               
    return [i.split() for i in x]                                             


# Make a dictionary from two lists                                            
def hash(x,y):                                                                
    return dict(zip(x,y))                                                     


# Function to reformat pattern strings                                        
def pat(x,c="."):                                                             
    return x.replace(c,"\x00").split()                                        


# Function to generate formatted strings according to the argument type       
def formatString(i):                                                          
    if type(i) == str:                                                        
        return i                                                              
    if type(i) == int:                                                        
        return "%5d"%i                                                        
    if type(i) == float and 0<abs(i)<1e-5:                                                      
        return "%2.1e"%i                                                      
    elif type(i) == float:                                                      
        return "%8.5f"%i                                                      
    else:                                                                     
        return str(i)                                                         


#----+----------------+
## B | MATH FUNCTIONS |
#----+----------------+


def cos_angle(a,b):
    p = sum([i*j for i,j in zip(a,b)])
    q = math.sqrt(sum([i*i for i in a])*sum([j*j for j in b]))
    return min(max(-1,p/q),1)


def norm2(a):
    return sum([i*i for i in a])


def norm(a):
    return math.sqrt(norm2(a))


def distance2(a,b):
    return (a[0]-b[0])**2+(a[1]-b[1])**2+(a[2]-b[2])**2



##########################
## 4 # FG -> CG MAPPING ##  -> @MAP <-
##########################


dnares3 = ["DA","DC","DG","DT"] 
dnares1 = ["dA","dC","dG","dT"]
rnares3 = [ "A", "C", "G", "U"]
rnares1 = [ "A", "C", "G", "U"] # 

# Amino acid nucleic acid codes:                                                                                 
# The naming (AA and '3') is not strictly correct when adding DNA/RNA, but we keep it like this for consistincy.
AA3     = dnares3+rnares3 #@#
AA1     = dnares1+rnares1 #@#


# Dictionaries for conversion from one letter code to three letter code v.v.                         
AA123, AA321 = hash(AA1,AA3),hash(AA3,AA1)                                                           


# Residue classes:
nucleic = spl("DAD DCY DGU DTH ADE CYT GUA THY URA DA DC DG DT A C G U")


residueTypes = dict([(i,"Nucleic") for i in nucleic ])

class CoarseGrained:
    # Class for mapping an atomistic residue list to a coarsegrained one
    # Should get an __init__ function taking a residuelist, atomlist, Pymol selection or ChemPy model
    # The result should be stored in a list-type attribute
    # The class should have pdbstr and grostr methods

    # Standard mapping groups
    dna_bb = nsplit("P OP1 OP2 O5' O3'","C5' O4' C4'","C3' C2' C1'")
    rna_bb = nsplit("P OP1 OP2 O5' O3'","C5' O4' C4'","C3' C2' O2' C1'")

    # This is the mapping dictionary
    # For each residue it returns a list, each element of which
    # lists the atom names to be mapped to the corresponding bead.
    # The order should be the standard order of the coarse grained
    # beads for the residue. Only atom names matching with those 
    # present in the list of atoms for the residue will be used
    # to determine the bead position. This adds flexibility to the
    # approach, as a single definition can be used for different 
    # states of a residue (e.g., GLU/GLUH).
    # For convenience, the list can be specified as a set of strings,
    # converted into a list of lists by 'nsplit' defined above.
    mapping = {
        "DA": nsplit("P OP1 OP2 O5' H5T O3' H3T O1P O2P",
                          "C5' O4' C4'",
                          "C3' C2' C1'",
                          "N9 C4",
                          "C2 N3",
                          "C6 N6 N1",
                          "C8 N7 C5"),
        "DG": nsplit("P OP1 OP2 O5' H5T O3' H3T O1P O2P",
                          "C5' O4' C4'",
                          "C3' C2' C1'",
                          "N9 C4",
                          "C2 N2 N3",
                          "C6 O6 N1",
                          "C8 N7 C5"),
        "DC": nsplit("P OP1 OP2 O5' H5T O3' H3T O1P O2P",
                          "C5' O4' C4'",
                          "C3' C2' C1'",
                          "N1 C6",
                          "N3 C2 O2",
                          "C5 C4 N4"),
        "DT": nsplit("P OP1 OP2 O5' H5T O3' H3T O1P O2P",
                          "C5' O4' C4'",
                          "C3' C2' C1'",
                          "N1 C6",
                          "N3 C2 O2",
                          "C5 C4 O4 C7 C5M"),
        "A":  nsplit("P OP1 OP2 O5' H5T O3' H3T O1P O2P",
                          "C5' O4' C4'",
                          "C3' C2' O2' C1'",
                          "N9 C4",
                          "C2 N3",
                          "C6 N6 N1",
                          "C8 N7 C5"),
        "G":  nsplit("P OP1 OP2 O5' H5T O3' H3T O1P O2P",
                          "C5' O4' C4'",
                          "C3' C2' O2' C1'",
                          "N9 C4",
                          "C2 N2 N3",
                          "C6 O6 N1",
                          "C8 N7 C5"),
        "C":  nsplit("P OP1 OP2 O5' H5T O3' H3T O1P O2P",
                          "C5' O4' C4'",
                          "C3' C2' O2' C1'",
                          "N1 C6",
                          "N3 C2 O2",
                          "C5 C4 N4"),
        "U":  nsplit("P OP1 OP2 O5' H5T O3' H3T O1P O2P",
                          "C5' O4' C4'",
                          "C3' C2' O2' C1'",
                          "N1 C6",
                          "N3 C2 O2",
                          "C5 C4 O4 C7 C5M"),
        }

    # Generic names for DNA beads
    residue_bead_names_dna = spl("BB1 BB2 BB3 SC1 SC2 SC3 SC4")
    # Generic names for RNA beads
    residue_bead_names_rna = spl("BB1 BB2 BB3 SC1 SC2 SC3 SC4")

    # This dictionary contains the bead names for all residues,
    # following the order in 'mapping'
    names  = {}
    # Add the default bead names for all DNA/RNA nucleic acids
    names.update([(i,("BB1","BB2","BB3","SC1","SC2","SC3","SC4")) for i in nucleic])

    # This dictionary allows determining four letter residue names
    # for ones specified with three letters, e.g., resulting from
    # truncation to adhere to the PDB format.
    # Each entry returns a prototypical test, given as a string,
    # and the residue name to be applied if eval(test) is True.
    # This is particularly handy to determine lipid types.
    # The test assumes there is a local or global array 'atoms'
    # containing the atom names of the residue in correct order.
    restest = {
        "POP": [('atoms[0] == "CA"', "POPG"),
                ('atoms[0] == "N"',  "POPE")]
        }

    # Crude mass for weighted average. No consideration of united atoms.
    # This will probably give only minor deviations, while also giving less headache
    mass = {'H': 1,'C': 12,'N': 14,'O': 16,'S': 32,'P': 31,'M': 0}

# Determine average position for a set of weights and coordinates
# This is a rather specific function that requires a list of items
# [(m,(x,y,z),id),..] and returns the weighted average of the 
# coordinates and the list of ids mapped to this bead
def aver(b):
    mwx,ids = zip(*[((m*x,m*y,m*z),i) for m,(x,y,z),i in b])              # Weighted coordinates     
    tm  = sum(zip(*b)[0])                                                 # Sum of weights           
    return [sum(i)/tm for i in zip(*mwx)],ids                             # Centre of mass           

# Return the CG beads for an atomistic residue, using the mapping specified above
# The residue 'r' is simply a list of atoms, and each atom is a list:
# [ name, resname, resid, chain, x, y, z ]
def map(r):
    p = CoarseGrained.mapping[r[0][1]]                                             # Mapping for this residue 
    # Get the name, mass and coordinates for all atoms in the residue
    a = [(i[0],CoarseGrained.mass.get(i[0][0],0),i[4:]) for i in r]                    
    # Store weight, coordinate and index for atoms that match a bead
    q = [[(m,coord,a.index((atom,m,coord))) for atom,m,coord in a if atom in i] for i in p]

    # Bead positions      
    return zip(*[aver(i) for i in q])

# Mapping for index file
def mapIndex(r):
    #print r[0][1]
    p = CoarseGrained.mapping[r[0][1]]                                             # Mapping for this residue 
    # Get the name, mass and coordinates for all atoms in the residue
    a = [(i[0],CoarseGrained.mass.get(i[0][0],0),i[4:]) for i in r]                    
    # Store weight, coordinate and index for atoms that match a bead
    return [[(m,coord,a.index((atom,m,coord))) for atom,m,coord in a if atom in i] for i in p]
#############################
## 5 # SECONDARY STRUCTURE ##  -> @SS <-
#############################
import logging,os,sys
import subprocess as subp

#----+--------------------------------------+
## A | SECONDARY STRUCTURE TYPE DEFINITIONS |
#----+--------------------------------------+

# This table lists all coarse grained secondary structure types
# The following are matched lists. Make sure they stay matched.
# The lists do not need to be of the same length. The longer list
# will be truncated when combined with a shorter list, e.g. with
# dihedral definitions, which are not present for coil and termini
#
ss_names = {
 "F": "Collagenous Fiber",                                                                  #@#
 "E": "Extended structure (beta sheet)",                                                    #@#
 "H": "Helix structure",                                                                    #@#
 "1": "Helix start (H-bond donor)",                                                         #@#
 "2": "Helix end (H-bond acceptor)",                                                        #@#
 "3": "Ambivalent helix type (short helices)",                                              #@#
 "T": "Turn",                                                                               #@#
 "S": "Bend",                                                                               #@#
 "C": "Coil",                                                                               #@#
}

bbss     =    spl("  F     E     H     1     2     3     T     S     C")  # SS one letter 


# The following dictionary contains secondary structure types as assigned by
# different programs. The corresponding Martini secondary structure types are               
# listed in cgss                                                                            
#                                                                                           
# NOTE:                                                                                     
#  Each list of letters in the dictionary ss should exactly match the list                  
#  in cgss.                                                                                 
#                                                                                           
ssdefs = {
    "dssp":  list(".HGIBETSC~"),             # DSSP one letter secondary structure code     #@#
    "pymol": list(".H...S...L"),             # Pymol one letter secondary structure code    #@# 
    "gmx":   list(".H...ETS.C"),             # Gromacs secondary structure dump code        #@#    
    "self":  list("FHHHEETSCC")              # Internal CG secondary structure codes        #@#
}
cgss     =   list("FHHHEETSCC")              # Corresponding CG secondary structure types   #@#


#----+-------------------------------------------+
## B | SECONDARY STRUCTURE PATTERN SUBSTITUTIONS |
#----+-------------------------------------------+


# For all structure types specific dihedrals may be used if four or
# more consecutive residues are assigned that type.                

# Helix start and end regions are special and require assignment of
# specific types. The following pattern substitutions are applied 
# (in the given order). A dot matches any other type.             
# Patterns can be added to the dictionaries. This only makes sense
# if for each key in patterns there is a matching key in pattypes.
patterns = {
    "H": pat(".H. .HH. .HHH. .HHHH. .HHHHH. .HHHHHH. .HHHHHHH. .HHHH HHHH.")                #@#
}
pattypes = {
    "H": pat(".3. .33. .333. .3333. .13332. .113322. .1113222. .1111 2222.")                #@#
}

    
#----+----------+
## C | INTERNAL |
#----+----------+


# Pymol Colors
#           F   E   H   1   2   3   T   S   C
ssnum  = ( 13,  4,  2,  2,  2,  2,  6, 22,  0 )                                             #@#

# Dictionary returning a number for a given type of secondary structure
# This can be used for setting the b-factor field for coloring         
ss2num = hash(bbss,ssnum)                                                                   


# List of programs for which secondary structure definitions can be processed
programs = ssdefs.keys()                                                                    


# Dictionaries mapping ss types to the CG ss types                                          
ssd = dict([ (i, hash(ssdefs[i],cgss)) for i in programs ])                                 


# From the secondary structure dictionaries we create translation tables
# with which all secondary structure types can be processed. Anything
# not listed above will be mapped to C (coil).
# Note, a translation table is a list of 256 characters to map standard  
# ascii characters to.
def tt(program):                                                                            
    return  "".join([ssd[program].get(chr(i),"C") for i in range(256)])                     


# The translation table depends on the program used to obtain the 
# secondary structure definitions
sstt = dict([(i,tt(i)) for i in programs])                                                  


# The following translation tables are used to identify stretches of 
# a certain type of secondary structure. These translation tables have
# every character, except for the indicated secondary structure, set to
# \x00. This allows summing the sequences after processing to obtain
# a single sequence summarizing all the features.
null = "\x00"                                                                               
sstd = dict([ (i,ord(i)*null+i+(255-ord(i))*null) for i in cgss ])                          


# Pattern substitutions
def typesub(seq,patterns,types):                                                            
    seq = null+seq+null
    for i,j in zip(patterns,types):                                                         
        seq = seq.replace(i,j)                                                              
    return seq[1:-1]                                                                              


# The following function translates a string encoding the secondary structure
# to a string of corresponding Martini types, taking the origin of the 
# secondary structure into account, and replacing termini if requested.
def ssClassification(ss,program="dssp"):                                                    
    # Translate dssp/pymol/gmx ss to Martini ss                                             
    ss  = ss.translate(sstt[program])                                                       
    # Separate the different secondary structure types                                      
    sep = dict([(i,ss.translate(sstd[i])) for i in sstd.keys()])                            
    # Do type substitutions based on patterns                                               
    # If the ss type is not in the patterns lists, do not substitute                        
    # (use empty lists for substitutions)                                                   
    typ = [ typesub(sep[i],patterns.get(i,[]),pattypes.get(i,[]))                           
            for i in sstd.keys()]                                                           
    # Translate all types to numerical values                                               
    typ = [ [ord(j) for j in list(i)] for i in typ ]                                        
    # Sum characters back to get a full typed sequence                                      
    typ = "".join([chr(sum(i)) for i in zip(*typ)])                                         
    # Return both the actual as well as the fully typed sequence                             
    return ss, typ                                                                          


# The following functions are for determination of secondary structure, 
# given a list of atoms. The atom format is generic and can be written out
# as PDB or GRO. The coordinates are in Angstrom.
# NOTE: There is the *OLD* DSSP and the *NEW* DSSP, which require 
# different calls. The old version uses '--' to indicate reading from stdin
# whereas the new version uses '-i /dev/stdin'
def call_dssp(chain,atomlist,executable='dsspcmbi'):
    '''Get the secondary structure, by calling to dssp'''
    ssdfile = 'chain_%s.ssd'%chain.id 

    try:
        if os.system(executable+" -V >/dev/null"):
            logging.debug("New version of DSSP; Executing '%s -i /dev/stdin -o %s'"%(executable,ssdfile))
            p = subp.Popen([executable,"-i","/dev/stdin","-o",ssdfile],stderr=subp.PIPE,stdout=subp.PIPE,stdin=subp.PIPE)
        else:
            logging.debug("Old version of DSSP; Executing '%s -- %s'"%(executable,ssdfile))
            p = subp.Popen([executable,"--",ssdfile],stderr=subp.PIPE,stdout=subp.PIPE,stdin=subp.PIPE)
    except OSError:
        logging.error("A problem occured calling %s."%executable)
        sys.exit(1)

    for atom in atomlist: 
        if atom[0][:2] == 'O1': atom=('O',)+atom[1:]
        if atom[0][0]!='H' and atom[0][:2]!='O2': p.stdin.write(pdbOut(atom))
    p.stdin.write('TER\n')
    data = p.communicate()
    p.wait()
    main,ss = 0,''
    for line in open(ssdfile).readlines(): 
      if main and not line[13] == "!": ss+=line[16]
      if line[:15] == '  #  RESIDUE AA': main=1
    return ss
     
ssDetermination = {
    "dssp": call_dssp
    }

class martini22nucleic:
    def __init__(self):

        # parameters are defined here for the following forcefield:
        self.name = 'martini22nucleic'
        
        # Charged types:
        self.charges = {"Qd":1, "Qa":-1, "SQd":1, "SQa":-1, "RQd":1, "AQa":-1}                                                           #@#
        self.bbcharges = {"BB1":-1}                                                                                                      #@#
        
        ##################
        # DNA PARAMETERS #
        ##################

        # DNA BACKBONE PARAMETERS
        self.dna_bb = {
            'atom'  : spl("Q0 SN0 SC2"),
            'bond'  : [(1,  0.360, 20000),          
                       (1,  0.198, 80000),          
                       (1,  0.353, 10000)],         
            'angle' : [(2,  110.0, 200),            
                       (2,  102.0, 150),           
                       (2,  106.0,  75)],           
            'dih'   : [(2,   95.0,  25),
                       (1,  180.0,   2, 3),
                       (9,   85.0,   2, 2,  9,  160.0,  2, 3)],
            'excl'  : [(), (), ()],
            'pair'  : [],
        }
        # DNA BACKBONE CONNECTIVITY
        self.dna_con  = {
            'bond'  : [(0, 1),
                       (1, 2),
                       (2, 0)],
            'angle' : [(0, 1, 2),
                       (1, 2, 0),
                       (2, 0, 1)],
            'dih'   : [(0, 1, 2, 0),
                       (1, 2, 0, 1),
                       (2, 0, 1, 2)],
            'excl'  : [(0, 2), (1, 0),(2, 1)],
            'pair'  : [],
        }

        # For bonds, angles, and dihedrals the first parameter should always 
        # be the type. It is pretty annoying to check the connectivity from 
        # elsewhere so we update these one base at a time.

        # ADENINE
        self.bases = {
            "DA": [spl("TN0 TA2 TA3 TNa"),                                      
            #     TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS
                   [(1,  0.300, 30000), (1,  0.229,  None), (1,  0.266,  None),             # BONDS
                    (1,  0.326, 20000), (1,  0.288,  None), (1,  0.162,  None),],     
                   [(2,   94.0,   250), (2,  160.0,   200), (2,  140.0,   200),             # ANGLES
                    (1,   85.0,   200), (2,  158.0,   200), (1,  125.0,   200),
                    (1,   74.0,   200), (1,   98.0,   200)],                           
                   [(2,  -90.0,    20), (2, -116.0,   0.5), (2,   98.0,    15)],            # DIHEDRALS
                   [],                                                                      # IMPROPERS 
                   [],                                                                      # VSITES
                   [(), (), (), (), (), (), (), (), (), (), (), (), (), ()],                # EXCLUSIONS
                   []],                                                                     # PAIRS
            }
        self.base_connectivity = {
            "DA": [[(2, 3),             (3, 4),             (4, 5),                         # BONDS
                    (4, 6),             (5, 6),             (6, 3)],   
                   [(1, 2, 3),          (2, 3, 4),          (2, 3, 6),                      # ANGLES
                    (3, 4, 5),          (3, 2, 7),          (4, 3, 6),
                    (4, 5, 6),          (5, 6, 3)], 
                   [(0, 1, 2, 3),       (1, 2, 3, 4),       (1, 2, 3, 6),],                # DIHEDRALS        
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(0, 3),             (0, 4),             (0, 5),                         # EXCLUSIONS
                    (0, 6),             (1, 3),             (1, 4),
                    (1, 5),             (1, 6),             (2, 3),
                    (2, 4),             (2, 5),             (2, 6),
                    (3, 5),             (4, 6)],
                   []],                                                                     # PAIRS                     
            }

        # CYTOSINE
        self.bases.update({
            "DC": [spl("TN0 TY2 TY3"),                                                     
            #     TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS
                   [(1,  0.270, 30000), (1,  0.220,  None), (1,  0.285,  None),             # BONDS
                    (1,  0.268,  None),],
                   [(2,   95.0,   210), (2,   95.0,   300), (1,  150.0,   500),             # ANGLES
                    (1,  180.0,    30), (1,   61.0,   200), (1,   71.0,   200), 
                    (1,   47.0,   200)],
                   [(2,  -78.0,    25), (2,  -90.0,    20), (2, -142.0,    50)],            # DIHEDRALS
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(), (), (), (), (), (), (), (), ()],                                    # EXCLUSIONS
                   []],                                                                     # PAIRS                     
        })
        self.base_connectivity.update({
            "DC": [[(2, 3),           (3, 4),             (4, 5),                         # BONDS
                    (5, 3)],
                   [(1, 2, 3),        (2, 3, 4),          (1, 3, 5),                      # ANGLES
                    (3, 2, 6),        (3, 4, 5),          (4, 3, 5),
                    (4, 5, 3)],
                   [(0, 1, 2, 3),     (1, 2, 3, 4),       (2, 1, 3, 5)],                  # DIHEDRALS
                   [],                                                                    # IMPROPERS
                   [],                                                                    # VSITES
                   [(0, 3),             (0, 4),             (0, 5),                         # EXCLUSIONS
                    (1, 3),             (1, 4),             (1, 5),             
                    (2, 3),             (2, 4),             (2, 5)],                                           
                   []],                                                                     # PAIRS                     
        })

        # GUANINE
        self.bases.update({
            "DG": [spl("TN0 TG2 TG3 TNa"),
            #     TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS
                   [(1,  0.300, 30000), (1,  0.295,  None), (1,  0.295,  None),             # BONDS
                    (1,  0.389, 20000), (1,  0.285,  None), (1,  0.161,  None),],     
                   [(2,   94.5,   250), (2,  137.0,   300), (2,  130.0,   250),             # ANGLES
                    (1,   69.5,   200), (2,  157.0,   150), (1,  125.0,   200),
                    (1,   84.0,   200), (1,   94.0,   200)],                           
                   [(2,  -90.0,    20), (2, -117.0,     1), (2,   92.0,    15)],            # DIHEDRALS  
                   [],                                                                      # IMPROPERS 
                   [],                                                                      # VSITES
                   [(), (), (), (), (), (), (), (), (), (), (), (), (), ()],                # EXCLUSIONS
                   []],                                                                     # PAIRS                     
        })
        self.base_connectivity.update({
            "DG": [[(2, 3),             (3, 4),             (4, 5),                         # BONDS
                    (4, 6),             (5, 6),             (6, 3)],
                   [(1, 2, 3),          (2, 3, 4),          (2, 3, 6),                      # ANGLES
                    (3, 4, 5),          (3, 2, 7),          (4, 3, 6), 
                    (4, 5, 6),          (5, 6, 3)],
                   [(0, 1, 2, 3),       (1, 2, 3, 4),       (1, 2, 3, 6),],                 # DIHEDRALS        
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(0, 3),             (0, 4),             (0, 5),                         # EXCLUSIONS
                    (0, 6),             (1, 3),             (1, 4),
                    (1, 5),             (1, 6),             (2, 3),
                    (2, 4),             (2, 5),             (2, 6),
                    (3, 5),             (4, 6)],                                           
                   []],                                                                     # PAIRS                     
        })

        # THYMINE
        self.bases.update({
            "DT": [spl("TN0 TT2 TT3"),
            #     TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS
                   [(1,  0.270, 30000), (1,  0.217,  None), (1,  0.322,  None),             # BONDS
                    (1,  0.265,  None),],
                   [(2,   92.0,   220), (2,  107.0,   300), (1,  145.0,   400),             # ANGLES
                    (1,  180.0,    30), (1,   55.0,   100), (1,   83.0,   100),
                    (1,   42.0,   100)],
                   [(2,  -75.0,    40), (2, -110.0,    15), (2, -145.0,    65)],            # DIHEDRALS
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(), (), (), (), (), (), (), (), ()],                                    # EXCLUSIONS
                   []],                                                                     # PAIRS                     
        })
        self.base_connectivity.update({
            "DT": [[(2, 3),           (3, 4),             (4, 5),                         # BONDS
                    (5, 3)],
                   [(1, 2, 3),        (2, 3, 4),          (1, 3, 5),                      # ANGLES
                    (3, 2, 6),        (3, 4, 5),          (4, 3, 5), 
                    (4, 5, 3)],
                   [(0, 1, 2, 3),     (1, 2, 3, 4),       (2, 1, 3, 5)],                  # DIHEDRALS
                   [],                                                                    # IMPROPERS
                   [],                                                                    # VSITES
                   [(0, 3),             (0, 4),             (0, 5),                         # EXCLUSIONS
                    (1, 3),             (1, 4),             (1, 5),             
                    (2, 3),             (2, 4),             (2, 5)],                                           
                   []],                                                                     # PAIRS                     
        })

        ##################
        # RNA PARAMETERS #
        ##################

        # RNA BACKBONE PARAMETERS
        self.rna_bb = {
            'atom'  : spl("Q0 SN0 SNda"),     # Have a look at BB3 bead type
            'bond'  : [(1,  0.363, 20000),          
                       (1,  0.202, 40000),    #8  , 0.202 50000    
                       (1,  0.354, 10000)],         
            'angle' : [(2,  117.0, 175),      #2, 117.0, 140       
                       (2,   95.0, 105),           
                       (1,   93.0,  75)],           
            'dih'   : [(2,    0.0, 3.5),
                       (1,    0.0,   1, 4),
                       (9,  -10.0, 1.5, 2,  9,  10.0, 1.5, 2)],
            'excl'  : [(), (), ()],
            'pair'  : [],
        }
        # RNA BACKBONE CONNECTIVITY
        self.rna_con  = {
            'bond'  : [(0, 1),
                       (1, 2),
                       (2, 0)],
            'angle' : [(0, 1, 2),
                       (1, 2, 0),
                       (2, 0, 1)],
            'dih'   : [(0, 1, 2, 0),
                       (1, 2, 0, 1),
                       (2, 0, 1, 2)],
            'excl'  : [(0, 2), (1, 0),(2, 1)],
            'pair'  : [],
        }

        # For bonds, angles, and dihedrals the first parameter should always 
        # be the type. It is pretty annoying to check the connectivity from 
        # elsewhere so we update these one base at a time.

        # ADENINE
        self.bases.update({
            "A":  [spl("TN0 TA2 TA3 TNa"),                                      
            #     TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS
                   [(1,  0.293, 28000), (1,  0.234,  None), (1,  0.263,  None),             # BONDS 
                    (1,  0.335, 40000), (1,  0.299,  None), (1,  0.162,  None),],     
                   [(2,  101.0,   260), (2,  153.0,    90), (2,  135.0,   185),             # ANGLES
                    (1,   87.0,   200), (2,  160.0,    15), (1,  115.0,   200),
                    (1,   74.0,   200), (1,   92.0,   200)],                           
                   [(2,  180.0,   1.5), (1,  -40.0,  4, 2), (1,  -10.0,  5, 2),             # DIHEDRALS
                    (2,  180.0,     0), (2,  180.0,     2), (2,   80.0,   0.5),
                    (2,    0.0,    10)],                                                    # DIHEDRALS
                   [],                                                                      # IMPROPERS 
                   [],                                                                      # VSITES
                   [(), (), (), (), (), (), (), (), (), (), (), (), (), ()],                # EXCLUSIONS
                   []],                                                                     # PAIRS
            })
        self.base_connectivity.update({
            "A":  [[(2, 3),             (3, 4),             (4, 5),                         # BONDS
                    (4, 6),             (5, 6),             (6, 3),],   
                   [(1, 2, 3),          (2, 3, 4),          (2, 3, 6),                      # ANGLES
                    (3, 4, 5),          (3, 2, 7),          (4, 3, 6),
                    (4, 5, 6),          (5, 6, 3)], 
                   [(0, 1, 2, 3),       (1, 2, 3, 4),       (1, 2, 3, 6),                   # DIHEDRALS        
                    (0, 1, 2, 3),       (1, 2, 3, 4),       (1, 2, 3, 6),
                    (3, 4, 5, 6)],                                                          
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(0, 3),             (0, 4),             (0, 5),                         # EXCLUSIONS
                    (0, 6),             (1, 3),             (1, 4),
                    (1, 5),             (1, 6),             (2, 3),
                    (2, 4),             (2, 5),             (2, 6),
                    (3, 5),             (4, 6)],
                   []],                                                                     # PAIRS                     
            })

        # CYTOSINE
        self.bases.update({
            "C":  [spl("TN0 TY2 TY3"),                                                     
            #     TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS
                   [(1,  0.280, 11000), (1,  0.224,  None), (1,  0.281,  None),             # BONDS
                    (1,  0.267,  None),],
                   [(2,   94.0,   230), (2,  103.0,   170), (1,  155.0,   100),             # ANGLES
                    (1,  130.0,   0.5), (1,   61.0,   200), (1,   71.0,   200), 
                    (1,   47.0,   200)],
                   [(1,   55.0,  3,  2), (2,  180.0,     3), (2, -130.0,      1),           # DIHEDRALS
                    (1,    0.0,  2,  6)],                                                   
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(), (), (), (), (), (), (), (), ()],                                    # EXCLUSIONS
                   []],                                                                     # PAIRS                     
        })
        self.base_connectivity.update({
            "C":  [[(2, 3),           (3, 4),             (4, 5),                           # BONDS
                    (5, 3)],
                   [(1, 2, 3),        (2, 3, 4),          (2, 3, 5),                        # ANGLES
                    (3, 2, 6),        (3, 4, 5),          (4, 3, 5),
                    (4, 5, 3)],
                   [(0, 1, 2, 3),     (1, 2, 3, 4),       (0, 1, 2, 3),                     # DIHEDRALS
                    (1, 2, 3, 4)],                                                          
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(0, 3),             (0, 4),             (0, 5),                         # EXCLUSIONS
                    (1, 3),             (1, 4),             (1, 5),             
                    (2, 3),             (2, 4),             (2, 5)],                                           
                   []],                                                                     # PAIRS                     
        })

        # GUANINE
        self.bases.update({
            "G":  [spl("TN0 TG2 TG3 TNa"),
            #     TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS
                   [(1,  0.292, 20000), (1,  0.296,  None), (1,  0.291,  None),             # BONDS
                    (1,  0.385, 40000), (1,  0.296,  None), (1,  0.162,  None),],     
                   [(2,  103.0,   260), (2,  129.0,    80), (2,  137.0,   120),             # ANGLES
                    (1,   72.0,   200), (2,  170.0,    20), (1,  117.0,   200),
                    (1,   84.0,   200), (1,   96.5,   200)],                           
                   [(1,  -20.0,  1, 2), (2,  180.0,   3.5), (1,    0.0,     5, 2),
                    (2,    0.0,    10)],                                                    # DIHEDRALS  
                   [],                                                                      # IMPROPERS 
                   [],                                                                      # VSITES
                   [(), (), (), (), (), (), (), (), (), (), (), (), (), ()],                # EXCLUSIONS
                   []],                                                                     # PAIRS                     
        })
        self.base_connectivity.update({
            "G":  [[(2, 3),             (3, 4),             (4, 5),                         # BONDS
                    (4, 6),             (5, 6),             (6, 3),],
                   [(1, 2, 3),          (2, 3, 4),          (2, 3, 6),                      # ANGLES
                    (3, 4, 5),          (3, 2, 7),          (4, 3, 6), 
                    (4, 5, 6),          (5, 6, 3)],
                   [(0, 1, 2, 3),       (1, 2, 3, 4),       (1, 2, 3, 6),
                    (3, 4, 5, 6)],                                                          # DIHEDRALS        
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(0, 3),             (0, 4),             (0, 5),                         # EXCLUSIONS
                    (0, 6),             (1, 3),             (1, 4),
                    (1, 5),             (1, 6),             (2, 3),
                    (2, 4),             (2, 5),             (2, 6),
                    (3, 5),             (4, 6)],                                           
                   []],                                                                     # PAIRS                     
        })

        # URACIL
        self.bases.update({
            "U":  [spl("TN0 TT2 TT3"),
            #     TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS
                   [(1,  0.286, 18000), (1,  0.224,  None), (1,  0.289,  None),             # BONDS
                    (1,  0.276,  None),],
                   [(2,   95.0,   225), (2,   99.0,   200), (1,  155.0,   100),             # ANGLES
                    (1,  180.0,     5), (1,   55.0,   100), (1,   83.0,   100),
                    (1,   42.0,   100)],
                   [(1,    0.0,  2, 2), (2,  180.0,     4), (1,    0.0,  2, 6)],            # DIHEDRALS
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(), (), (), (), (), (), (), (), ()],                                    # EXCLUSIONS
                   []],                                                                     # PAIRS                     
        })
        self.base_connectivity.update({
            "U":  [[(2, 3),           (3, 4),             (4, 5),                           # BONDS
                    (5, 3)],
                   [(1, 2, 3),        (2, 3, 4),          (2, 3, 5),                        # ANGLES
                    (3, 2, 6),        (3, 4, 5),          (4, 3, 5), 
                    (4, 5, 3)],
                   [(0, 1, 2, 3),     (1, 2, 3, 4),       (1, 2, 3, 4)],                    # DIHEDRALS
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(0, 3),             (0, 4),             (0, 5),                         # EXCLUSIONS
                    (1, 3),             (1, 4),             (1, 5),             
                    (2, 3),             (2, 4),             (2, 5)],                                           
                   []],                                                                     # PAIRS                     
        })

        #----+----------------+
        ## D | SPECIAL BONDS  |
        #----+----------------+
        
        self.special = {
            # Used for sulfur bridges
            # ATOM 1         ATOM 2          BOND LENGTH   FORCE CONSTANT
            (("SC1","CYS"), ("SC1","CYS")):     (0.39,         5000),
            }
        
        # By default use an elastic network
        self.ElasticNetwork = False 

        # Elastic networks bond shouldn't lead to exclusions (type 6) 
        # But Elnedyn has been parametrized with type 1.
        self.EBondType = 6
        
        #----+----------------+
        ## D | INTERNAL STUFF |
        #----+----------------+

        ## DNA DICTIONARIES ##
        # Dictionary for the connectivities and parameters of bonds between DNA backbone beads
        self.dnaBbBondDictC = dict(zip(self.dna_con['bond'],self.dna_bb['bond']))
        # Dictionary for the connectivities and parameters of angles between DNA backbone beads
        self.dnaBbAngleDictC = dict(zip(self.dna_con['angle'],self.dna_bb['angle']))
        # Dictionary for the connectivities and parameters of dihedrals between DNA backbone beads
        self.dnaBbDihDictC = dict(zip(self.dna_con['dih'],self.dna_bb['dih']))
        # Dictionary for exclusions for DNA backbone beads
        self.dnaBbExclDictC = dict(zip(self.dna_con['excl'],self.dna_bb['excl']))
        # Dictionary for pairs for DNA backbone beads
        self.dnaBbPairDictC = dict(zip(self.dna_con['pair'],self.dna_bb['pair']))

        ## RNA DICTIONARIES ##
        # Dictionary for the connectivities and parameters of bonds between rna backbone beads
        self.rnaBbBondDictC = dict(zip(self.rna_con['bond'],self.rna_bb['bond']))
        # Dictionary for the connectivities and parameters of angles between rna backbone beads
        self.rnaBbAngleDictC = dict(zip(self.rna_con['angle'],self.rna_bb['angle']))
        # Dictionary for the connectivities and parameters of dihedrals between rna backbone beads
        self.rnaBbDihDictC = dict(zip(self.rna_con['dih'],self.rna_bb['dih']))
        # Dictionary for exclusions for rna backbone beads
        self.rnaBbExclDictC = dict(zip(self.rna_con['excl'],self.rna_bb['excl']))
        # Dictionary for pairs for rna backbone beads
        self.rnaBbPairDictC = dict(zip(self.rna_con['pair'],self.rna_bb['pair']))
        
        
    # The following function returns the backbone bead for a given residue and                   
    # secondary structure type.                                                                 
    # 1. Check if the residue is DNA/RNA and return the whole backbone for those
    # 2. Look up the proper dictionary for the residue                                          
    # 3. Get the proper type from it for the secondary structure                                
    # If the residue is not in the dictionary of specials, use the default                      
    # If the secondary structure is not listed (in the residue specific                         
    # dictionary) revert to the default.                                                        
    def bbGetBead(self,r1,ss="C"):                                                               
        if r1 in dnares3:
            return self.dna_bb['atom']
        elif r1 in rnares3:
            return self.rna_bb['atom']
        else:
            sys.exit("This script supports only DNA or RNA.")
    
    def bbGetBond(self,r,ca,ss):
        # Retrieve parameters for each residue from tables defined above
        if r[0] in dnares3:
            return ca in self.dnaBbBondDictC.keys() and self.dnaBbBondDictC[ca] or None
        elif r[0] in rnares3:
            return ca in self.rnaBbBondDictC.keys() and self.rnaBbBondDictC[ca] or None
        else:
            sys.exit("This script supports only DNA or RNA.")
    
    def bbGetAngle(self,r,ca,ss):
        if r[0] in dnares3:
            return ca in self.dnaBbAngleDictC.keys() and self.dnaBbAngleDictC[ca] or None
        elif r[0] in rnares3:
            return ca in self.rnaBbAngleDictC.keys() and self.rnaBbAngleDictC[ca] or None
        else:
            sys.exit("This script supports only DNA or RNA.")

    def bbGetExclusion(self,r,ca,ss):
        if r[0] in dnares3:
            return ca in self.dnaBbExclDictC.keys() and ' ' or None
        elif r[0] in rnares3:
            return ca in self.rnaBbExclDictC.keys() and ' ' or None
        else:
            sys.exit("This script supports only DNA or RNA.")

    def bbGetPair(self,r,ca,ss):
        if r[0] in dnares3:
            return ca in self.dnaBbPairDictC.keys() and ' ' or None
        elif r[0] in rnares3:
            return ca in self.rnaBbPairDictC.keys() and ' ' or None
        else:
            sys.exit("This script supports only DNA or RNA.")

    def bbGetDihedral(self,r,ca,ss):
        # Retrieve parameters for each residue from table defined above
        if r[0] in dnares3:
            return ca in self.dnaBbDihDictC.keys() and self.dnaBbDihDictC[ca] or None
        elif r[0] in rnares3:
            return ca in self.rnaBbDihDictC.keys() and self.rnaBbDihDictC[ca] or None
        else:
            sys.exit("This script supports only DNA or RNA.")

    def getCharge(self,atype,aname):
        return self.charges.get(atype,self.bbcharges.get(aname,0))
        
    def messages(self):
        '''Prints any force-field specific logging messages.'''
        import logging
        logging.warning('################################################################################')
        logging.warning('This is a beta of Martini-nucleotide and should NOT be used for production runs.')
        logging.warning('################################################################################')
        pass


class elnedyn22nucleic:
    def __init__(self):

        # parameters are defined here for the following (protein) forcefields:
        self.name = 'elnedyn22nucleic'
        
        # Charged types:
        self.charges = {"Qd":1, "Qa":-1, "SQd":1, "SQa":-1, "RQd":1, "AQa":-1}                                                           #@#
        self.bbcharges = {"BB1":-1}                                                                                                      #@#
        
        # Not all (eg Elnedyn) forcefields use backbone-backbone-sidechain angles and BBBB-dihedrals.
        self.UseBBSAngles          = False 
        self.UseBBBBDihedrals      = False
        
        ##################
        # DNA PARAMETERS #
        ##################

        # DNA BACKBONE PARAMETERS
        self.dna_bb = {
            'atom'  : spl("Q0 SN0 SC2"),
            'bond'  : [(1,  0.360, 20000),          
                       (1,  0.198, 80000),          
                       (1,  0.353, 10000)],         
            'angle' : [(2,  110.0, 200),            
                       (2,  102.0, 150),           
                       (2,  106.0,  75)],           
            'dih'   : [(2,   95.0,  25),
                       (1,  180.0,   2, 3),
                       (9,   85.0,   2, 2,  9,  160.0,  2, 3)],
            'excl'  : [(), (), ()],
            'pair'  : [],
        }
        # DNA BACKBONE CONNECTIVITY
        self.dna_con  = {
            'bond'  : [(0, 1),
                       (1, 2),
                       (2, 0)],
            'angle' : [(0, 1, 2),
                       (1, 2, 0),
                       (2, 0, 1)],
            'dih'   : [(0, 1, 2, 0),
                       (1, 2, 0, 1),
                       (2, 0, 1, 2)],
            'excl'  : [(0, 2), (1, 0),(2, 1)],
            'pair'  : [],
        }

        # For bonds, angles, and dihedrals the first parameter should always 
        # be the type. It is pretty annoying to check the connectivity from 
        # elsewhere so we update these one base at a time.

        # ADENINE
        self.bases = {
            "DA": [spl("TN0 TA2 TA3 TNa"),                                      
            #     TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS
                   [(1,  0.300, 30000), (1,  0.229,  None), (1,  0.266,  None),             # BONDS
                    (1,  0.326, 20000), (1,  0.288,  None), (1,  0.162,  None),],     
                   [(2,   94.0,   250), (2,  160.0,   200), (2,  140.0,   200),             # ANGLES
                    (1,   85.0,   200), (2,  158.0,   200), (1,  125.0,   200),
                    (1,   74.0,   200), (1,   98.0,   200)],                           
                   [(2,  -90.0,    20), (2, -116.0,   0.5), (2,   98.0,    15)],            # DIHEDRALS
                   [],                                                                      # IMPROPERS 
                   [],                                                                      # VSITES
                   [(), (), (), (), (), (), (), (), (), (), (), (), (), ()],                # EXCLUSIONS
                   []],                                                                     # PAIRS
            }
        self.base_connectivity = {
            "DA": [[(2, 3),             (3, 4),             (4, 5),                         # BONDS
                    (4, 6),             (5, 6),             (6, 3)],   
                   [(1, 2, 3),          (2, 3, 4),          (2, 3, 6),                      # ANGLES
                    (3, 4, 5),          (3, 2, 7),          (4, 3, 6),
                    (4, 5, 6),          (5, 6, 3)], 
                   [(0, 1, 2, 3),       (1, 2, 3, 4),       (1, 2, 3, 6),],                # DIHEDRALS        
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(0, 3),             (0, 4),             (0, 5),                         # EXCLUSIONS
                    (0, 6),             (1, 3),             (1, 4),
                    (1, 5),             (1, 6),             (2, 3),
                    (2, 4),             (2, 5),             (2, 6),
                    (3, 5),             (4, 6)],
                   []],                                                                     # PAIRS                     
            }

        # CYTOSINE
        self.bases.update({
            "DC": [spl("TN0 TY2 TY3"),                                                     
            #     TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS
                   [(1,  0.270, 30000), (1,  0.220,  None), (1,  0.285,  None),             # BONDS
                    (1,  0.268,  None),],
                   [(2,   95.0,   210), (2,   95.0,   300), (1,  150.0,   500),             # ANGLES
                    (1,  180.0,    30), (1,   61.0,   200), (1,   71.0,   200), 
                    (1,   47.0,   200)],
                   [(2,  -78.0,    25), (2,  -90.0,    20), (2, -142.0,    50)],            # DIHEDRALS
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(), (), (), (), (), (), (), (), ()],                                    # EXCLUSIONS
                   []],                                                                     # PAIRS                     
        })
        self.base_connectivity.update({
            "DC": [[(2, 3),           (3, 4),             (4, 5),                         # BONDS
                    (5, 3)],
                   [(1, 2, 3),        (2, 3, 4),          (1, 3, 5),                      # ANGLES
                    (3, 2, 6),        (3, 4, 5),          (4, 3, 5),
                    (4, 5, 3)],
                   [(0, 1, 2, 3),     (1, 2, 3, 4),       (2, 1, 3, 5)],                  # DIHEDRALS
                   [],                                                                    # IMPROPERS
                   [],                                                                    # VSITES
                   [(0, 3),             (0, 4),             (0, 5),                         # EXCLUSIONS
                    (1, 3),             (1, 4),             (1, 5),             
                    (2, 3),             (2, 4),             (2, 5)],                                           
                   []],                                                                     # PAIRS                     
        })

        # GUANINE
        self.bases.update({
            "DG": [spl("TN0 TG2 TG3 TNa"),
            #     TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS
                   [(1,  0.300, 30000), (1,  0.295,  None), (1,  0.295,  None),             # BONDS
                    (1,  0.389, 20000), (1,  0.285,  None), (1,  0.161,  None),],     
                   [(2,   94.5,   250), (2,  137.0,   300), (2,  130.0,   250),             # ANGLES
                    (1,   69.5,   200), (2,  157.0,   150), (1,  125.0,   200),
                    (1,   84.0,   200), (1,   94.0,   200)],                           
                   [(2,  -90.0,    20), (2, -117.0,     1), (2,   92.0,    15)],            # DIHEDRALS  
                   [],                                                                      # IMPROPERS 
                   [],                                                                      # VSITES
                   [(), (), (), (), (), (), (), (), (), (), (), (), (), ()],                # EXCLUSIONS
                   []],                                                                     # PAIRS                     
        })
        self.base_connectivity.update({
            "DG": [[(2, 3),             (3, 4),             (4, 5),                         # BONDS
                    (4, 6),             (5, 6),             (6, 3)],
                   [(1, 2, 3),          (2, 3, 4),          (2, 3, 6),                      # ANGLES
                    (3, 4, 5),          (3, 2, 7),          (4, 3, 6), 
                    (4, 5, 6),          (5, 6, 3)],
                   [(0, 1, 2, 3),       (1, 2, 3, 4),       (1, 2, 3, 6),],                 # DIHEDRALS        
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(0, 3),             (0, 4),             (0, 5),                         # EXCLUSIONS
                    (0, 6),             (1, 3),             (1, 4),
                    (1, 5),             (1, 6),             (2, 3),
                    (2, 4),             (2, 5),             (2, 6),
                    (3, 5),             (4, 6)],                                           
                   []],                                                                     # PAIRS                     
        })

        # THYMINE
        self.bases.update({
            "DT": [spl("TN0 TT2 TT3"),
            #     TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS
                   [(1,  0.270, 30000), (1,  0.217,  None), (1,  0.322,  None),             # BONDS
                    (1,  0.265,  None),],
                   [(2,   92.0,   220), (2,  107.0,   300), (1,  145.0,   400),             # ANGLES
                    (1,  180.0,    30), (1,   55.0,   100), (1,   83.0,   100),
                    (1,   42.0,   100)],
                   [(2,  -75.0,    40), (2, -110.0,    15), (2, -145.0,    65)],            # DIHEDRALS
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(), (), (), (), (), (), (), (), ()],                                    # EXCLUSIONS
                   []],                                                                     # PAIRS                     
        })
        self.base_connectivity.update({
            "DT": [[(2, 3),           (3, 4),             (4, 5),                         # BONDS
                    (5, 3)],
                   [(1, 2, 3),        (2, 3, 4),          (1, 3, 5),                      # ANGLES
                    (3, 2, 6),        (3, 4, 5),          (4, 3, 5), 
                    (4, 5, 3)],
                   [(0, 1, 2, 3),     (1, 2, 3, 4),       (2, 1, 3, 5)],                  # DIHEDRALS
                   [],                                                                    # IMPROPERS
                   [],                                                                    # VSITES
                   [(0, 3),             (0, 4),             (0, 5),                         # EXCLUSIONS
                    (1, 3),             (1, 4),             (1, 5),             
                    (2, 3),             (2, 4),             (2, 5)],                                           
                   []],                                                                     # PAIRS                     
        })

        ##################
        # RNA PARAMETERS #
        ##################

        # RNA BACKBONE PARAMETERS
        self.rna_bb = {
            'atom'  : spl("Q0 SN0 SNda"),     # Have a look at BB3 bead type
            'bond'  : [(1,  0.363, 20000),          
                       (1,  0.202, 40000),    #8  , 0.202 50000    
                       (1,  0.354, 10000)],         
            'angle' : [(2,  117.0, 175),      #2, 117.0, 140       
                       (2,   95.0, 105),           
                       (1,   93.0,  75)],           
            'dih'   : [(2,    0.0, 3.5),
                       (1,    0.0,   1, 4),
                       (9,  -10.0, 1.5, 2,  9,  10.0, 1.5, 2)],
            'excl'  : [(), (), ()],
            'pair'  : [],
        }
        # RNA BACKBONE CONNECTIVITY
        self.rna_con  = {
            'bond'  : [(0, 1),
                       (1, 2),
                       (2, 0)],
            'angle' : [(0, 1, 2),
                       (1, 2, 0),
                       (2, 0, 1)],
            'dih'   : [(0, 1, 2, 0),
                       (1, 2, 0, 1),
                       (2, 0, 1, 2)],
            'excl'  : [(0, 2), (1, 0),(2, 1)],
            'pair'  : [],
        }

        # For bonds, angles, and dihedrals the first parameter should always 
        # be the type. It is pretty annoying to check the connectivity from 
        # elsewhere so we update these one base at a time.

        # ADENINE
        self.bases.update({
            "A":  [spl("TN0 TA2 TA3 TNa"),                                      
            #     TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS
                   [(1,  0.293, 28000), (1,  0.234,  None), (1,  0.263,  None),             # BONDS 
                    (1,  0.335, 40000), (1,  0.299,  None), (1,  0.162,  None),],     
                   [(2,  101.0,   260), (2,  153.0,    90), (2,  135.0,   185),             # ANGLES
                    (1,   87.0,   200), (2,  160.0,    15), (1,  115.0,   200),
                    (1,   74.0,   200), (1,   92.0,   200)],                           
                   [(2,  180.0,   1.5), (1,  -40.0,  4, 2), (1,  -10.0,  5, 2),             # DIHEDRALS
                    (2,  180.0,     0), (2,  180.0,     2), (2,   80.0,   0.5),
                    (2,    0.0,    10)],                                                    # DIHEDRALS
                   [],                                                                      # IMPROPERS 
                   [],                                                                      # VSITES
                   [(), (), (), (), (), (), (), (), (), (), (), (), (), ()],                # EXCLUSIONS
                   []],                                                                     # PAIRS
            })
        self.base_connectivity.update({
            "A":  [[(2, 3),             (3, 4),             (4, 5),                         # BONDS
                    (4, 6),             (5, 6),             (6, 3),],   
                   [(1, 2, 3),          (2, 3, 4),          (2, 3, 6),                      # ANGLES
                    (3, 4, 5),          (3, 2, 7),          (4, 3, 6),
                    (4, 5, 6),          (5, 6, 3)], 
                   [(0, 1, 2, 3),       (1, 2, 3, 4),       (1, 2, 3, 6),                   # DIHEDRALS        
                    (0, 1, 2, 3),       (1, 2, 3, 4),       (1, 2, 3, 6),
                    (3, 4, 5, 6)],                                                          
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(0, 3),             (0, 4),             (0, 5),                         # EXCLUSIONS
                    (0, 6),             (1, 3),             (1, 4),
                    (1, 5),             (1, 6),             (2, 3),
                    (2, 4),             (2, 5),             (2, 6),
                    (3, 5),             (4, 6)],
                   []],                                                                     # PAIRS                     
            })

        # CYTOSINE
        self.bases.update({
            "C":  [spl("TN0 TY2 TY3"),                                                     
            #     TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS
                   [(1,  0.280, 11000), (1,  0.224,  None), (1,  0.281,  None),             # BONDS
                    (1,  0.267,  None),],
                   [(2,   94.0,   230), (2,  103.0,   170), (1,  155.0,   100),             # ANGLES
                    (1,  130.0,   0.5), (1,   61.0,   200), (1,   71.0,   200), 
                    (1,   47.0,   200)],
                   [(1,   55.0,  3,  2), (2,  180.0,     3), (2, -130.0,      1),           # DIHEDRALS
                    (1,    0.0,  2,  6)],                                                   
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(), (), (), (), (), (), (), (), ()],                                    # EXCLUSIONS
                   []],                                                                     # PAIRS                     
        })
        self.base_connectivity.update({
            "C":  [[(2, 3),           (3, 4),             (4, 5),                           # BONDS
                    (5, 3)],
                   [(1, 2, 3),        (2, 3, 4),          (2, 3, 5),                        # ANGLES
                    (3, 2, 6),        (3, 4, 5),          (4, 3, 5),
                    (4, 5, 3)],
                   [(0, 1, 2, 3),     (1, 2, 3, 4),       (0, 1, 2, 3),                     # DIHEDRALS
                    (1, 2, 3, 4)],                                                          
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(0, 3),             (0, 4),             (0, 5),                         # EXCLUSIONS
                    (1, 3),             (1, 4),             (1, 5),             
                    (2, 3),             (2, 4),             (2, 5)],                                           
                   []],                                                                     # PAIRS                     
        })

        # GUANINE
        self.bases.update({
            "G":  [spl("TN0 TG2 TG3 TNa"),
            #     TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS
                   [(1,  0.292, 20000), (1,  0.296,  None), (1,  0.291,  None),             # BONDS
                    (1,  0.385, 40000), (1,  0.296,  None), (1,  0.162,  None),],     
                   [(2,  103.0,   260), (2,  129.0,    80), (2,  137.0,   120),             # ANGLES
                    (1,   72.0,   200), (2,  170.0,    20), (1,  117.0,   200),
                    (1,   84.0,   200), (1,   96.5,   200)],                           
                   [(1,  -20.0,  1, 2), (2,  180.0,   3.5), (1,    0.0,     5, 2),
                    (2,    0.0,    10)],                                                    # DIHEDRALS  
                   [],                                                                      # IMPROPERS 
                   [],                                                                      # VSITES
                   [(), (), (), (), (), (), (), (), (), (), (), (), (), ()],                # EXCLUSIONS
                   []],                                                                     # PAIRS                     
        })
        self.base_connectivity.update({
            "G":  [[(2, 3),             (3, 4),             (4, 5),                         # BONDS
                    (4, 6),             (5, 6),             (6, 3),],
                   [(1, 2, 3),          (2, 3, 4),          (2, 3, 6),                      # ANGLES
                    (3, 4, 5),          (3, 2, 7),          (4, 3, 6), 
                    (4, 5, 6),          (5, 6, 3)],
                   [(0, 1, 2, 3),       (1, 2, 3, 4),       (1, 2, 3, 6),
                    (3, 4, 5, 6)],                                                          # DIHEDRALS        
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(0, 3),             (0, 4),             (0, 5),                         # EXCLUSIONS
                    (0, 6),             (1, 3),             (1, 4),
                    (1, 5),             (1, 6),             (2, 3),
                    (2, 4),             (2, 5),             (2, 6),
                    (3, 5),             (4, 6)],                                           
                   []],                                                                     # PAIRS                     
        })

        # URACIL
        self.bases.update({
            "U":  [spl("TN0 TT2 TT3"),
            #     TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS
                   [(1,  0.286, 18000), (1,  0.224,  None), (1,  0.289,  None),             # BONDS
                    (1,  0.276,  None),],
                   [(2,   95.0,   225), (2,   99.0,   200), (1,  155.0,   100),             # ANGLES
                    (1,  180.0,     5), (1,   55.0,   100), (1,   83.0,   100),
                    (1,   42.0,   100)],
                   [(1,    0.0,  2, 2), (2,  180.0,     4), (1,    0.0,  2, 6)],            # DIHEDRALS
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(), (), (), (), (), (), (), (), ()],                                    # EXCLUSIONS
                   []],                                                                     # PAIRS                     
        })
        self.base_connectivity.update({
            "U":  [[(2, 3),           (3, 4),             (4, 5),                           # BONDS
                    (5, 3)],
                   [(1, 2, 3),        (2, 3, 4),          (2, 3, 5),                        # ANGLES
                    (3, 2, 6),        (3, 4, 5),          (4, 3, 5), 
                    (4, 5, 3)],
                   [(0, 1, 2, 3),     (1, 2, 3, 4),       (1, 2, 3, 4)],                    # DIHEDRALS
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(0, 3),             (0, 4),             (0, 5),                         # EXCLUSIONS
                    (1, 3),             (1, 4),             (1, 5),             
                    (2, 3),             (2, 4),             (2, 5)],                                           
                   []],                                                                     # PAIRS                     
        })
        
        # By default use an elastic network
        self.ElasticNetwork = True  

        # Elastic networks bond shouldn't lead to exclusions (type 6) 
        # But Elnedyn has been parametrized with type 1.
        self.EBondType = 6
        
        #----+----------------+
        ## D | INTERNAL STUFF |
        #----+----------------+

        ## DNA DICTIONARIES ##
        # Dictionary for the connectivities and parameters of bonds between DNA backbone beads
        self.dnaBbBondDictC = dict(zip(self.dna_con['bond'],self.dna_bb['bond']))
        # Dictionary for the connectivities and parameters of angles between DNA backbone beads
        self.dnaBbAngleDictC = dict(zip(self.dna_con['angle'],self.dna_bb['angle']))
        # Dictionary for the connectivities and parameters of dihedrals between DNA backbone beads
        self.dnaBbDihDictC = dict(zip(self.dna_con['dih'],self.dna_bb['dih']))
        # Dictionary for exclusions for DNA backbone beads
        self.dnaBbExclDictC = dict(zip(self.dna_con['excl'],self.dna_bb['excl']))
        # Dictionary for pairs for DNA backbone beads
        self.dnaBbPairDictC = dict(zip(self.dna_con['pair'],self.dna_bb['pair']))

        ## RNA DICTIONARIES ##
        # Dictionary for the connectivities and parameters of bonds between rna backbone beads
        self.rnaBbBondDictC = dict(zip(self.rna_con['bond'],self.rna_bb['bond']))
        # Dictionary for the connectivities and parameters of angles between rna backbone beads
        self.rnaBbAngleDictC = dict(zip(self.rna_con['angle'],self.rna_bb['angle']))
        # Dictionary for the connectivities and parameters of dihedrals between rna backbone beads
        self.rnaBbDihDictC = dict(zip(self.rna_con['dih'],self.rna_bb['dih']))
        # Dictionary for exclusions for rna backbone beads
        self.rnaBbExclDictC = dict(zip(self.rna_con['excl'],self.rna_bb['excl']))
        # Dictionary for pairs for rna backbone beads
        self.rnaBbPairDictC = dict(zip(self.rna_con['pair'],self.rna_bb['pair']))
        
        
    # The following function returns the backbone bead for a given residue and                   
    # secondary structure type.                                                                 
    # 1. Check if the residue is DNA/RNA and return the whole backbone for those
    # 2. Look up the proper dictionary for the residue                                          
    # 3. Get the proper type from it for the secondary structure                                
    # If the residue is not in the dictionary of specials, use the default                      
    # If the secondary structure is not listed (in the residue specific                         
    # dictionary) revert to the default.                                                        
    def bbGetBead(self,r1,ss="C"):                                                               
        if r1 in dnares3:
            return self.dna_bb['atom']
        elif r1 in rnares3:
            return self.rna_bb['atom']
        else:
            sys.exit("This script supports only DNA or RNA.")
    
    def bbGetBond(self,r,ca,ss):
        # Retrieve parameters for each residue from tables defined above
        if r[0] in dnares3:
            return ca in self.dnaBbBondDictC.keys() and self.dnaBbBondDictC[ca] or None
        elif r[0] in rnares3:
            return ca in self.rnaBbBondDictC.keys() and self.rnaBbBondDictC[ca] or None
        else:
            sys.exit("This script supports only DNA or RNA.")
    
    def bbGetAngle(self,r,ca,ss):
        if r[0] in dnares3:
            return ca in self.dnaBbAngleDictC.keys() and self.dnaBbAngleDictC[ca] or None
        elif r[0] in rnares3:
            return ca in self.rnaBbAngleDictC.keys() and self.rnaBbAngleDictC[ca] or None
        else:
            sys.exit("This script supports only DNA or RNA.")

    def bbGetExclusion(self,r,ca,ss):
        if r[0] in dnares3:
            return ca in self.dnaBbExclDictC.keys() and ' ' or None
        elif r[0] in rnares3:
            return ca in self.rnaBbExclDictC.keys() and ' ' or None
        else:
            sys.exit("This script supports only DNA or RNA.")

    def bbGetPair(self,r,ca,ss):
        if r[0] in dnares3:
            return ca in self.dnaBbPairDictC.keys() and ' ' or None
        elif r[0] in rnares3:
            return ca in self.rnaBbPairDictC.keys() and ' ' or None
        else:
            sys.exit("This script supports only DNA or RNA.")

    def bbGetDihedral(self,r,ca,ss):
        # Retrieve parameters for each residue from table defined above
        if r[0] in dnares3:
            return ca in self.dnaBbDihDictC.keys() and self.dnaBbDihDictC[ca] or None
        elif r[0] in rnares3:
            return ca in self.rnaBbDihDictC.keys() and self.rnaBbDihDictC[ca] or None
        else:
            sys.exit("This script supports only DNA or RNA.")

    def getCharge(self,atype,aname):
        return self.charges.get(atype,self.bbcharges.get(aname,0))
        
    def messages(self):
        '''Prints any force-field specific logging messages.'''
        import logging
        logging.warning('################################################################################')
        logging.warning('This is a beta of Martini-nucleotide and should NOT be used for production runs.')
        logging.warning('################################################################################')
        pass


class dna22plot:
    def __init__(self):

        # parameters are defined here for the following (protein) forcefields:
        self.name = 'rna22plot'
        
        # Charged types:
        self.charges = {"Qd":1, "Qa":-1, "SQd":1, "SQa":-1, "RQd":1, "AQa":-1}                                                           #@#
        self.bbcharges = {"BB1":-1}                                                                                                      #@#

        # DNA BACKBONE PARAMETERS
        self.dna_bb = {
            'atom'  : FUNC.spl("Q0 SN0 SC2"),
            'bond'  : [(1,  0.360, 30000),          
                       (1,  0.400, 10000),          
                       (1,  0.200, 50000),          
                       (1,  0.355, 10000)],         
            'angle' : [(2,  115.0,  85),           
                       (2,  102.0, 105),           
                       (2,  110.0,  60)],           
            'dih'   : [(2,  100.0,  1),           
                       (2, -120.0,  5),           
                       (2,  140.0,  5)],          
            'excl'  : [(), (), ()],
        }
        # DNA BACKBONE CONNECTIVITY
        self.dna_con  = {
            'bond'  : [(0, 1),
                       (0, 2),
                       (1, 2),
                       (2, 0)],
            'angle' : [(0, 1, 2),
                       (1, 2, 0),
                       (2, 0, 1)],
            'dih'   : [(0, 1, 2, 0),
                       (1, 2, 0, 1),
                       (2, 0, 1, 2)],
            'excl'  : [(0, 2), (1, 0), (2, 1)],
        }
        # ADENINE
        self.bases = {
            "DA": [FUNC.spl("TNa TNa TP1 TNa"),                                      
            #     TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS
                   [(1,  0.330, 30000), (1,  0.229, 30000), (1,  0.266, 30000),             # BONDS BB3-SC1 bond lengthened by 0.030 nm.
                    (1,  0.325, 30000), (1,  0.288, 30000), (1,  0.162, 30000),],     
                   [(2,   93.0,   250), (2,  160.0,   200), (2,  140.0,   200),             # ANGLES
                    (2,   85.0,   200), (2,  148.0,   350), (2,  125.0,   200),
                    (2,   74.0,   200), (2,   98.0,   200)],                           
                   [(2,    0.0,     1), (2,    0.0,     1), (2,    0.0,     1),
                    (2,    0.0,     1), (2,    0.0,     1), (2,    0.0,     1),
                    (2,    0.0,     1), (2,    0.0,     1), (2,    0.0,     1),
                    (2,    0.0,     1), (2,    0.0,     1), (2,    0.0,     1),
                    (2,    0.0,     1), (2,    0.0,     1)],
                   [(2,    0.0,   500)],                                                    # IMPROPERS 
                   [],                                                                      # VSITES
                   [(), (), (), (), (), (), (), (), (), (), (), (), (), ()]],               # EXCLUSIONS
            }
        self.base_connectivity = {
            "DA": [[(2, 3),             (3, 4),             (4, 5),                         # BONDS
                    (4, 6),             (5, 6),             (6, 3)],   
                   [(1, 2, 3),          (2, 3, 4),          (2, 3, 6),                      # ANGLES
                    (3, 4, 5),          (3, 2, 7),          (4, 3, 6),
                    (4, 5, 6),          (5, 6, 3)], 
                   [(0, 1, 2, 3),       (0, 2, 3, 4),       (0, 2, 3, 6),                  # DIHEDRALS        
                    (1, 2, 3, 4),       (1, 2, 3, 6),       (2, 8, 9,10),
                    (3, 2, 7, 8),       (3, 2, 7, 9),       (3, 2, 7,10),
                    (3, 7, 8,10),       (3, 8, 9,10),       (4, 2, 7, 8),
                    (7, 2, 3, 4),       (7, 2, 3, 6)],
                   [(3, 4, 5, 6)],                                                          # IMPROPERS
                   [],                                                                      # VSITES
                   [(0, 3),             (0, 4),             (0, 5),                         # EXCLUSIONS
                    (0, 6),             (1, 3),             (1, 4),
                    (1, 5),             (1, 6),             (2, 3),
                    (2, 4),             (2, 5),             (2, 6),
                    (3, 5),             (4, 6)]],                                           
            }

        # CYTOSINE
        self.bases.update({
            "DC": [FUNC.spl("TNa TPa TPd"),                                                     
            #     TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS
                   [(1,  0.290, 30000), (1,  0.220, 30000), (1,  0.285, 30000),             # BONDS BB3-SC1 bond lenghtened by 0.020 nm.
                    (1,  0.268, 30000),],
                   [(2,   93.0,   200), (2,  108.0,   250), (2,  170.0,   350),             # ANGLES
                    (2,  180.0,     1), (2,   62.0,   200), (2,   71.0,   200), 
                    (2,   47.0,   200), (2,  100.0,     1), (2,    0.0,     1),
                    (2,    0.0,     1), (2,    0.0,     1), (2,    0.0,     1)],
                   [(2,    0.0,     1), (2,    0.0,     1), (2,    0.0,     1),
                    (2,    0.0,     1), (2,    0.0,     1), (2,    0.0,     1),
                    (2,    0.0,     1), (2,    0.0,     1), (2,    0.0,     1),
                    (2,    0.0,     1), (2,    0.0,     1), (2,    0.0,     1),
                    (2,    0.0,     1), (2,    0.0,     1), (2,    0.0,     1),
                    (2,    0.0,     1)],
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(), (), (), (), (), (), (), (), ()]],                                   # EXCLUSIONS
        })
        self.base_connectivity.update({
            "DC": [[(2, 3),           (3, 4),             (4, 5),                         # BONDS
                    (5, 3)],
                   [(1, 2, 3),        (2, 3, 4),          (2, 3, 5),                      # ANGLES
                    (3, 2, 6),        (3, 4, 5),          (4, 3, 5),
                    (4, 5, 3),        (1, 3, 5),          (1, 5, 3),
                    (2, 3, 6),        (2, 1, 3),          (2, 1, 5)],
                   [(0, 1, 2, 3),       (0, 2, 3, 4),       (0, 2, 3, 5),                  # DIHEDRALS        
                    (1, 2, 3, 4),       (1, 2, 3, 5),       (2, 7, 8, 9),
                    (3, 2, 6, 7),       (3, 2, 6, 8),       (3, 2, 6, 9),
                    (3, 6, 7, 9),       (3, 7, 8, 9),       (4, 2, 6, 7),
                    (6, 2, 3, 4),       (6, 2, 3, 5),       (2, 1, 3, 5),
                    (2, 1, 5, 3)],
                   [],                                                                    # IMPROPERS
                   [],                                                                    # VSITES
                   [(0, 3),             (0, 4),             (0, 5),                         # EXCLUSIONS
                    (1, 3),             (1, 4),             (1, 5),             
                    (2, 3),             (2, 4),             (2, 5)]],                                           
        })

        # GUANINE
        self.bases.update({
            "DG": [FUNC.spl("TNa TPd TP1 TNa"),
            #     TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS
                   [(1,  0.300, 30000), (1,  0.295, 30000), (1,  0.295, 30000),             # BONDS BB3-SC1 bond stays the same.
                    (1,  0.390, 30000), (1,  0.285, 30000), (1,  0.161, 30000),],     
                   [(2,   95.0,   250), (2,  137.0,   300), (2,  128.0,   250),             # ANGLES
                    (2,   69.0,   200), (2,  145.0,   350), (2,  125.0,   200),
                    (2,   84.0,   200), (2,   94.0,   200)],                           
                   [(2,    0.0,     1), (2,    0.0,     1), (2,    0.0,     1),
                    (2,    0.0,     1), (2,    0.0,     1), (2,    0.0,     1),
                    (2,    0.0,     1), (2,    0.0,     1), (2,    0.0,     1),
                    (2,    0.0,     1), (2,    0.0,     1), (2,    0.0,     1),
                    (2,    0.0,     1), (2,    0.0,     1)],
                   [(2,    0.0,   150)],                                                    # IMPROPERS 
                   [],                                                                      # VSITES
                   [(), (), (), (), (), (), (), (), (), (), (), (), (), ()]],               # EXCLUSIONS
        })
        self.base_connectivity.update({
            "DG": [[(2, 3),             (3, 4),             (4, 5),                         # BONDS
                    (4, 6),             (5, 6),             (6, 3)],
                   [(1, 2, 3),          (2, 3, 4),          (2, 3, 6),                      # ANGLES
                    (3, 4, 5),          (3, 2, 7),          (4, 3, 6), 
                    (4, 5, 6),          (5, 6, 3)],
                   [(0, 1, 2, 3),       (0, 2, 3, 4),       (0, 2, 3, 6),                  # DIHEDRALS        
                    (1, 2, 3, 4),       (1, 2, 3, 6),       (2, 8, 9,10),
                    (3, 2, 7, 8),       (3, 2, 7, 9),       (3, 2, 7,10),
                    (3, 7, 8,10),       (3, 8, 9,10),       (4, 2, 7, 8),
                    (7, 2, 3, 4),       (7, 2, 3, 6)],
                   [(3, 4, 5, 6)],                                                          # IMPROPERS
                   [],                                                                      # VSITES
                   [(0, 3),             (0, 4),             (0, 5),                         # EXCLUSIONS
                    (0, 6),             (1, 3),             (1, 4),
                    (1, 5),             (1, 6),             (2, 3),
                    (2, 4),             (2, 5),             (2, 6),
                    (3, 5),             (4, 6)]],                                           
        })

        # THYMINE
        self.bases.update({
            "DT": [FUNC.spl("TNa TP1 TPa"),
            #     TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS
                   [(1,  0.310, 30000), (1,  0.217, 30000), (1,  0.322, 30000),             # BONDS BB3-SC1 bond lengthened by 0.040 nm.
                    (1,  0.265, 30000),],
                   [(2,   93.0,   250), (2,  108.0,   350), (2,  165.0,   550),             # ANGLES
                    (2,  165.0,   400), (2,   55.0,   200), (2,   83.0,   200),
                    (2,   42.0,   200), (2,    0.0,     1), (2,    0.0,     1),
                    (2,    0.0,     1), (2,    0.0,     1)],
                   [(2,    0.0,     1), (2,    0.0,     1), (2,    0.0,     1),
                    (2,    0.0,     1), (2,    0.0,     1), (2,    0.0,     1),
                    (2,    0.0,     1), (2,    0.0,     1), (2,    0.0,     1),
                    (2,    0.0,     1), (2,    0.0,     1), (2,    0.0,     1),
                    (2,    0.0,     1), (2,    0.0,     1), (2,    0.0,     1)],
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(), (), (), (), (), (), (), (), ()]],                                   # EXCLUSIONS
        })
        self.base_connectivity.update({
            "DT": [[(2, 3),           (3, 4),             (4, 5),                         # BONDS
                    (5, 3)],
                   [(1, 2, 3),        (2, 3, 4),          (2, 3, 5),                      # ANGLES
                    (3, 2, 6),        (3, 4, 5),          (4, 3, 5), 
                    (4, 5, 3),        (2, 3, 6),          (1, 3, 5),
                    (2, 1, 3),        (2, 1, 5)],
                   [(0, 1, 2, 3),       (0, 2, 3, 4),       (0, 2, 3, 5),                  # DIHEDRALS        
                    (1, 2, 3, 4),       (1, 2, 3, 5),       (2, 7, 8, 9),
                    (3, 2, 6, 7),       (3, 2, 6, 8),       (3, 2, 6, 9),
                    (3, 6, 7, 9),       (3, 7, 8, 9),       (4, 2, 6, 7),
                    (6, 2, 3, 4),       (6, 2, 3, 5),       (2, 1, 3, 5)],
                   [],                                                                    # IMPROPERS
                   [],                                                                    # VSITES
                   [(0, 3),             (0, 4),             (0, 5),                         # EXCLUSIONS
                    (1, 3),             (1, 4),             (1, 5),             
                    (2, 3),             (2, 4),             (2, 5)]],                                           
        })

        # By default use an elastic network
        self.ElasticNetwork = False 

        # Elastic networks bond shouldn't lead to exclusions (type 6) 
        # But Elnedyn has been parametrized with type 1.
        self.EBondType = 6
        
        #----+----------------+
        ## D | INTERNAL STUFF |
        #----+----------------+

        ## RNA DICTIONARIES ##
        # Dictionary for the connectivities and parameters of bonds between rna backbone beads
        self.rnaBbBondDictC = dict(zip(self.rna_con['bond'],self.rna_bb['bond']))
        # Dictionary for the connectivities and parameters of angles between rna backbone beads
        self.rnaBbAngleDictC = dict(zip(self.rna_con['angle'],self.rna_bb['angle']))
        # Dictionary for the connectivities and parameters of dihedrals between rna backbone beads
        self.rnaBbDihDictC = dict(zip(self.rna_con['dih'],self.rna_bb['dih']))
        # Dictionary for exclusions for rna backbone beads
        self.rnaBbExclDictC = dict(zip(self.rna_con['excl'],self.rna_bb['excl']))
        # Dictionary for pairs for rna backbone beads
        self.rnaBbPairDictC = dict(zip(self.rna_con['pair'],self.rna_bb['pair']))
        

    # The following function returns the backbone bead for a given residue and                   
    # secondary structure type.                                                                 
    # 1. Check if the residue is DNA/RNA and return the whole backbone for those
    # 2. Look up the proper dictionary for the residue                                          
    # 3. Get the proper type from it for the secondary structure                                
    # If the residue is not in the dictionary of specials, use the default                      
    # If the secondary structure is not listed (in the residue specific                         
    # dictionary) revert to the default.                                                        
    def bbGetBead(self,r1,ss="C"):                                                               
        if r1 in dnares3:
            return self.dna_bb['atom']
        elif r1 in rnares3:
            return self.rna_bb['atom']
        else:
            sys.exit("This script supports only DNA or RNA.")
    
    def bbGetBond(self,r,ca,ss):
        # Retrieve parameters for each residue from tables defined above
        if r[0] in dnares3:
            return ca in self.dnaBbBondDictC.keys() and self.dnaBbBondDictC[ca] or None
        elif r[0] in rnares3:
            return ca in self.rnaBbBondDictC.keys() and self.rnaBbBondDictC[ca] or None
        else:
            sys.exit("This script supports only DNA or RNA.")
    
    def bbGetAngle(self,r,ca,ss):
        if r[0] in dnares3:
            return ca in self.dnaBbAngleDictC.keys() and self.dnaBbAngleDictC[ca] or None
        elif r[0] in rnares3:
            return ca in self.rnaBbAngleDictC.keys() and self.rnaBbAngleDictC[ca] or None
        else:
            sys.exit("This script supports only DNA or RNA.")

    def bbGetExclusion(self,r,ca,ss):
        if r[0] in dnares3:
            return ca in self.dnaBbExclDictC.keys() and ' ' or None
        elif r[0] in rnares3:
            return ca in self.rnaBbExclDictC.keys() and ' ' or None
        else:
            sys.exit("This script supports only DNA or RNA.")

    def bbGetPair(self,r,ca,ss):
        if r[0] in dnares3:
            return ca in self.dnaBbPairDictC.keys() and ' ' or None
        elif r[0] in rnares3:
            return ca in self.rnaBbPairDictC.keys() and ' ' or None
        else:
            sys.exit("This script supports only DNA or RNA.")

    def bbGetDihedral(self,r,ca,ss):
        # Retrieve parameters for each residue from table defined above
        if r[0] in dnares3:
            return ca in self.dnaBbDihDictC.keys() and self.dnaBbDihDictC[ca] or None
        elif r[0] in rnares3:
            return ca in self.rnaBbDihDictC.keys() and self.rnaBbDihDictC[ca] or None
        else:
            sys.exit("This script supports only DNA or RNA.")

    def getCharge(self,atype,aname):
        return self.charges.get(atype,self.bbcharges.get(aname,0))
        
    def messages(self):
        '''Prints any force-field specific logging messages.'''
        import logging
        logging.warning('################################################################################')
        logging.warning('This is a beta of Martini-nucleotide and should NOT be used for production runs.')
        logging.warning('################################################################################')
        pass


class rna22plot:
    def __init__(self):

        # parameters are defined here for the following (protein) forcefields:
        self.name = 'rna22plot'
        
        # Charged types:
        self.charges = {"Qd":1, "Qa":-1, "SQd":1, "SQa":-1, "RQd":1, "AQa":-1}                                                           #@#
        self.bbcharges = {"BB1":-1}                                                                                                      #@#

        # RNA BACKBONE PARAMETERS
        self.rna_bb = {
            'atom'  : spl("Q0 SN0 SNda"),
            'bond'  : [(1,  0.360, 20000),          
                       (1,  0.198, 80000),          
                       (1,  0.198, 80000),          
                       (1,  0.353, 10000)],         
            'angle' : [(2,  110.0, 200),            
                       (2,  102.0, 150),           
                       (2,  106.0,  75)],           
            'dih'   : [(2,   95.0,  25),
                       (1,  180.0,   2, 3),
                       (9,   85.0,   2, 2,  9,  160.0,  2, 3)],
            'excl'  : [(), (), ()],
            'pair'  : [],
        }
        # RNA BACKBONE CONNECTIVITY
        self.rna_con  = {
            'bond'  : [(0, 1),
                       (0, 2),
                       (1, 2),
                       (2, 0)],
            'angle' : [(0, 1, 2),
                       (1, 2, 0),
                       (2, 0, 1)],
            'dih'   : [(0, 1, 2, 0),
                       (1, 2, 0, 1),
                       (2, 0, 1, 2)],
            'excl'  : [(0, 2), (1, 0),(2, 1)],
            'pair'  : [],
        }

        # For bonds, angles, and dihedrals the first parameter should always 
        # be the type. It is pretty annoying to check the connectivity from 
        # elsewhere so we update these one base at a time.

        # ADENINE
        self.bases = {
            "RA": [spl("TN0 TA2 TA3 TNa"),                                      
            #     TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS
                   [(1,  0.300, 30000), (1,  0.229,  None), (1,  0.266,  None),             # BONDS BB3-SC1 bond lengthened by 0.048 nm.
                    (1,  0.326, 20000), (1,  0.288,  None), (1,  0.162,  None),],     
                   [(2,   94.0,   250), (2,  160.0,   200), (2,  140.0,   200),             # ANGLES
                    (1,   85.0,   200), (2,  158.0,   200), (1,  125.0,   200),
                    (1,   74.0,   200), (1,   98.0,   200)],                           
                   [(2,  -90.0,    20), (2, -116.0,   0.5), (2,   98.0,    15),
                    (2,    0.0,    10)],                                                    # DIHEDRALS
                   [],                                                                      # IMPROPERS 
                   [],                                                                      # VSITES
                   [(), (), (), (), (), (), (), (), (), (), (), (), (), ()],                # EXCLUSIONS
                   []],                                                                     # PAIRS
            }
        self.base_connectivity = {
            "RA": [[(2, 3),             (3, 4),             (4, 5),                         # BONDS
                    (4, 6),             (5, 6),             (6, 3)],   
                   [(1, 2, 3),          (2, 3, 4),          (2, 3, 6),                      # ANGLES
                    (3, 4, 5),          (3, 2, 7),          (4, 3, 6),
                    (4, 5, 6),          (5, 6, 3)], 
                   [(0, 1, 2, 3),       (1, 2, 3, 4),       (1, 2, 3, 6),
                    (3, 4, 5, 6)],                                                          # DIHEDRALS        
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(0, 3),             (0, 4),             (0, 5),                         # EXCLUSIONS
                    (0, 6),             (1, 3),             (1, 4),
                    (1, 5),             (1, 6),             (2, 3),
                    (2, 4),             (2, 5),             (2, 6),
                    (3, 5),             (4, 6)],
                   []],                                                                     # PAIRS                     
            }

        # CYTOSINE
        self.bases.update({
            "RC": [spl("TN0 TY2 TY3"),                                                     
            #     TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS
                   [(1,  0.270, 30000), (1,  0.220,  None), (1,  0.285,  None),             # BONDS BB3-SC1 bond lenghtened by 0.033 nm.
                    (1,  0.268,  None),],
                   [(2,   95.0,   210), (2,   95.0,   300), (1,  150.0,   500),             # ANGLES
                    (1,  180.0,    30), (1,   61.0,   200), (1,   71.0,   200), 
                    (1,   47.0,   200)],
                   [(2,  -78.0,    25), (2,  -90.0,    20), (2, -142.0,    50),
                    (2,    0.0,    10)],                                                    # DIHEDRALS
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(), (), (), (), (), (), (), (), ()],                                    # EXCLUSIONS
                   []],                                                                     # PAIRS                     
        })
        self.base_connectivity.update({
            "RC": [[(2, 3),           (3, 4),             (4, 5),                           # BONDS
                    (5, 3)],
                   [(1, 2, 3),        (2, 3, 4),          (1, 3, 5),                        # ANGLES
                    (3, 2, 6),        (3, 4, 5),          (4, 3, 5),
                    (4, 5, 3)],
                   [(0, 1, 2, 3),     (1, 2, 3, 4),       (2, 1, 3, 5),
                    (1, 2, 3, 5)],                                                          # DIHEDRALS
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(0, 3),             (0, 4),             (0, 5),                         # EXCLUSIONS
                    (1, 3),             (1, 4),             (1, 5),             
                    (2, 3),             (2, 4),             (2, 5)],                                           
                   []],                                                                     # PAIRS                     
        })

        # GUANINE
        self.bases.update({
            "RG": [spl("TN0 TG2 TG3 TNa"),
            #     TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS
                   [(1,  0.300, 30000), (1,  0.295,  None), (1,  0.295,  None),             # BONDS BB3-SC1 bond lengthened by 0.053 nm.
                    (1,  0.389, 20000), (1,  0.285,  None), (1,  0.161,  None),],     
                   [(2,   94.5,   250), (2,  137.0,   300), (2,  130.0,   250),             # ANGLES
                    (1,   69.5,   200), (2,  157.0,   150), (1,  125.0,   200),
                    (1,   84.0,   200), (1,   94.0,   200)],                           
                   [(2,  -90.0,    20), (2, -117.0,     1), (2,   92.0,    15),
                    (2,    0.0,    10)],                                                    # DIHEDRALS  
                   [],                                                                      # IMPROPERS 
                   [],                                                                      # VSITES
                   [(), (), (), (), (), (), (), (), (), (), (), (), (), ()],                # EXCLUSIONS
                   []],                                                                     # PAIRS                     
        })
        self.base_connectivity.update({
            "RG": [[(2, 3),             (3, 4),             (4, 5),                         # BONDS
                    (4, 6),             (5, 6),             (6, 3)],
                   [(1, 2, 3),          (2, 3, 4),          (2, 3, 6),                      # ANGLES
                    (3, 4, 5),          (3, 2, 7),          (4, 3, 6), 
                    (4, 5, 6),          (5, 6, 3)],
                   [(0, 1, 2, 3),       (1, 2, 3, 4),       (1, 2, 3, 6),
                    (3, 4, 5, 6)],                                                          # DIHEDRALS        
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(0, 3),             (0, 4),             (0, 5),                         # EXCLUSIONS
                    (0, 6),             (1, 3),             (1, 4),
                    (1, 5),             (1, 6),             (2, 3),
                    (2, 4),             (2, 5),             (2, 6),
                    (3, 5),             (4, 6)],                                           
                   []],                                                                     # PAIRS                     
        })

        # URACIL
        self.bases.update({
            "RU": [spl("TN0 TT2 TT3"),
            #     TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS TYPE   EQUIL   OPTS
                   [(1,  0.270, 30000), (1,  0.217,  None), (1,  0.322,  None),             # BONDS BB3-SC1 bond lengthened by 0.056 nm.
                    (1,  0.265,  None),],
                   [(2,   92.0,   220), (2,  107.0,   300), (1,  145.0,   400),             # ANGLES
                    (1,  180.0,    30), (1,   55.0,   100), (1,   83.0,   100),
                    (1,   42.0,   100)],
                   [(2,  -75.0,    40), (2, -110.0,    15), (2, -145.0,    65),
                    (2,    0.0,    10)],                                                    # DIHEDRALS
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(), (), (), (), (), (), (), (), ()],                                    # EXCLUSIONS
                   []],                                                                     # PAIRS                     
        })
        self.base_connectivity.update({
            "RU": [[(2, 3),           (3, 4),             (4, 5),                           # BONDS
                    (5, 3)],
                   [(1, 2, 3),        (2, 3, 4),          (1, 3, 5),                        # ANGLES
                    (3, 2, 6),        (3, 4, 5),          (4, 3, 5), 
                    (4, 5, 3)],
                   [(0, 1, 2, 3),     (1, 2, 3, 4),       (2, 1, 3, 5),
                    (1, 2, 3, 5)],                                                          # DIHEDRALS
                   [],                                                                      # IMPROPERS
                   [],                                                                      # VSITES
                   [(0, 3),             (0, 4),             (0, 5),                         # EXCLUSIONS
                    (1, 3),             (1, 4),             (1, 5),             
                    (2, 3),             (2, 4),             (2, 5)],                                           
                   []],                                                                     # PAIRS                     
        })

        # By default use an elastic network
        self.ElasticNetwork = False 

        # Elastic networks bond shouldn't lead to exclusions (type 6) 
        # But Elnedyn has been parametrized with type 1.
        self.EBondType = 6
        
        #----+----------------+
        ## D | INTERNAL STUFF |
        #----+----------------+

        ## RNA DICTIONARIES ##
        # Dictionary for the connectivities and parameters of bonds between rna backbone beads
        self.rnaBbBondDictC = dict(zip(self.rna_con['bond'],self.rna_bb['bond']))
        # Dictionary for the connectivities and parameters of angles between rna backbone beads
        self.rnaBbAngleDictC = dict(zip(self.rna_con['angle'],self.rna_bb['angle']))
        # Dictionary for the connectivities and parameters of dihedrals between rna backbone beads
        self.rnaBbDihDictC = dict(zip(self.rna_con['dih'],self.rna_bb['dih']))
        # Dictionary for exclusions for rna backbone beads
        self.rnaBbExclDictC = dict(zip(self.rna_con['excl'],self.rna_bb['excl']))
        # Dictionary for pairs for rna backbone beads
        self.rnaBbPairDictC = dict(zip(self.rna_con['pair'],self.rna_bb['pair']))
        

    # The following function returns the backbone bead for a given residue and                   
    # secondary structure type.                                                                 
    # 1. Check if the residue is DNA/RNA and return the whole backbone for those
    # 2. Look up the proper dictionary for the residue                                          
    # 3. Get the proper type from it for the secondary structure                                
    # If the residue is not in the dictionary of specials, use the default                      
    # If the secondary structure is not listed (in the residue specific                         
    # dictionary) revert to the default.                                                        
    def bbGetBead(self,r1,ss="C"):                                                               
        if r1 in dnares3:
            return self.dna_bb['atom']
        elif r1 in rnares3:
            return self.rna_bb['atom']
        else:
            sys.exit("This script supports only DNA or RNA.")
    
    def bbGetBond(self,r,ca,ss):
        # Retrieve parameters for each residue from tables defined above
        if r[0] in dnares3:
            return ca in self.dnaBbBondDictC.keys() and self.dnaBbBondDictC[ca] or None
        elif r[0] in rnares3:
            return ca in self.rnaBbBondDictC.keys() and self.rnaBbBondDictC[ca] or None
        else:
            sys.exit("This script supports only DNA or RNA.")
    
    def bbGetAngle(self,r,ca,ss):
        if r[0] in dnares3:
            return ca in self.dnaBbAngleDictC.keys() and self.dnaBbAngleDictC[ca] or None
        elif r[0] in rnares3:
            return ca in self.rnaBbAngleDictC.keys() and self.rnaBbAngleDictC[ca] or None
        else:
            sys.exit("This script supports only DNA or RNA.")

    def bbGetExclusion(self,r,ca,ss):
        if r[0] in dnares3:
            return ca in self.dnaBbExclDictC.keys() and ' ' or None
        elif r[0] in rnares3:
            return ca in self.rnaBbExclDictC.keys() and ' ' or None
        else:
            sys.exit("This script supports only DNA or RNA.")

    def bbGetPair(self,r,ca,ss):
        if r[0] in dnares3:
            return ca in self.dnaBbPairDictC.keys() and ' ' or None
        elif r[0] in rnares3:
            return ca in self.rnaBbPairDictC.keys() and ' ' or None
        else:
            sys.exit("This script supports only DNA or RNA.")

    def bbGetDihedral(self,r,ca,ss):
        # Retrieve parameters for each residue from table defined above
        if r[0] in dnares3:
            return ca in self.dnaBbDihDictC.keys() and self.dnaBbDihDictC[ca] or None
        elif r[0] in rnares3:
            return ca in self.rnaBbDihDictC.keys() and self.rnaBbDihDictC[ca] or None
        else:
            sys.exit("This script supports only DNA or RNA.")

    def getCharge(self,atype,aname):
        return self.charges.get(atype,self.bbcharges.get(aname,0))
        
    def messages(self):
        '''Prints any force-field specific logging messages.'''
        import logging
        logging.warning('################################################################################')
        logging.warning('This is a beta of Martini-nucleotide and should NOT be used for production runs.')
        logging.warning('################################################################################')
        pass


#########################
## 7 # ELASTIC NETWORK ##  -> @ELN <-
#########################
import math

## ELASTIC NETWORK ##

# Only the decay function is defined here, the network 
# itself is set up through the Topology class

# The function to determine the decay scaling factor for the elastic network 
# force constant, based on the distance and the parameters provided.
# This function is very versatile and can be fitted to most commonly used 
# profiles, including a straight line (rate=0)
def decayFunction(distance,shift,rate,power):
    return math.exp(-rate*math.pow(distance-shift,power))

def rubberBands(atomList,lowerBound,upperBound,decayFactor,decayPower,forceConstant,minimumForce):
    out = []
    u2  = upperBound**2
    while len(atomList) > 3:
        bi,xi = atomList.pop(0)
        # This is a bit weird (=wrong I think) way of doing the cutoff...
        #for bj,xj in atomList[2:]:
        for bj,xj in atomList:
            # Mind the nm/A conversion -- This has to be standardized! Global use of nm?
            d2 = distance2(xi,xj)/100
            if bi==73 and bj==79:
                print (xi, xj, d2)
            
            if d2 < u2:
                dij  = math.sqrt(d2)
                fscl = decayFunction(dij,lowerBound,decayFactor,decayPower)
                if fscl*forceConstant > minimumForce:
                    out.append({"atoms":(bi,bj),"parameters": (dij,"RUBBER_FC*%f"%fscl)})
    return out



#######################
## 8 # STRUCTURE I/O ##  -> @IO <-
#######################
import logging,math,random,sys

#----+---------+
## A | PDB I/O |
#----+---------+

d2r = 3.14159265358979323846264338327950288/180

# Reformatting of lines in structure file                                     
pdbAtomLine = "ATOM  %5d %4s%4s %1s%4d%1s   %8.3f%8.3f%8.3f%6.2f%6.2f\n"        
pdbBoxLine  = "CRYST1%9.3f%9.3f%9.3f%7.2f%7.2f%7.2f P 1           1\n"        


def pdbBoxString(box):
    # Box vectors
    u, v, w  = box[0:3], box[3:6], box[6:9]

    # Box vector lengths
    nu,nv,nw = [math.sqrt(norm2(i)) for i in (u,v,w)]

    # Box vector angles
    alpha = nv*nw == 0 and 90 or math.acos(cos_angle(v,w))/d2r
    beta  = nu*nw == 0 and 90 or math.acos(cos_angle(u,w))/d2r
    gamma = nu*nv == 0 and 90 or math.acos(cos_angle(u,v))/d2r

    return pdbBoxLine % (10*norm(u),10*norm(v),10*norm(w),alpha,beta,gamma)


def pdbAtom(a):
    ##01234567890123456789012345678901234567890123456789012345678901234567890123456789
    ##ATOM   2155 HH11 ARG C 203     116.140  48.800   6.280  1.00  0.00
    if a.startswith("TER"):
        return 0
    # NOTE: The 27th field of an ATOM line in the PDB definition can contain an
    #       insertion code. We shift that 20 bits and add it to the residue number
    #       to ensure that residue numbers will be unique.
    ## ===> atom name,       res name,        res id,                        chain,
    return (a[12:16].strip(),a[17:20].strip(),int(a[22:26])+(ord(a[26])<<20),a[21],
    ##            x,              y,              z       
            float(a[30:38]),float(a[38:46]),float(a[46:54]))


def pdbOut(atom,i=1):
    insc = atom[2]>>20
    resi = atom[2]-(insc<<20)
    pdbline = "ATOM  %5i  %-3s %3s%2s%4i%1s   %8.3f%8.3f%8.3f%6.2f%6.2f           %1s  \n"
    return pdbline%((i,atom[0][:3],atom[1],atom[3],resi,chr(insc)) + atom[4:] + (1,40,atom[0][0])) 


def isPdbAtom(a):    
    return a.startswith("ATOM") or (options["-hetatm"] and a.startswith("HETATM")) or a.startswith("TER")


def pdbBoxRead(a):
    fa, fb, fc, aa, ab, ac = [float(i) for i in a.split()[1:7]]
    ca, cb, cg, sg         = math.cos(d2r*aa), math.cos(d2r*ab), math.cos(d2r*ac) , math.sin(d2r*ac)
    wx, wy                 = 0.1*fc*cb, 0.1*fc*(ca-cb*cg)/sg
    wz                     = math.sqrt(0.01*fc*fc - wx*wx - wy*wy)
    return [0.1*fa, 0, 0, 0.1*fb*cg, 0.1*fb*sg, 0, wx, wy, wz]


# Function for splitting a PDB file in chains, based
# on chain identifiers and TER statements
def pdbChains(pdbAtomList):
    chain = []
    for atom in pdbAtomList:
        if not atom: # Was a "TER" statement
            if chain:
                yield chain
            else:
                logging.info("Skipping empty chain definition")
            chain = [] 
            continue
        if not chain or chain[-1][3] == atom[3]:
            chain.append(atom)
        else:
            yield chain
            chain = [atom]
    if chain:
        yield chain


# Simple PDB iterator
def pdbFrameIterator(streamIterator):  
    title, atoms, box = [], [], []
    for i in streamIterator:
        if i.startswith("ENDMDL"):
            yield "".join(title), atoms, box
            title, atoms, box = [], [], []            
        elif i.startswith("TITLE"):
            title.append(i)
        elif i.startswith("CRYST1"):
            box = pdbBoxRead(i)
        elif i.startswith("ATOM") or i.startswith("HETATM"):
            atoms.append(pdbAtom(i))
    if atoms:
        yield "".join(title), atoms, box


#----+---------+
## B | GRO I/O |
#----+---------+

groline = "%5d%-5s%5s%5d%8.3f%8.3f%8.3f\n"                                    

def groBoxRead(a):    
    b = [float(i) for i in a.split()] + 6*[0]             # Padding for rectangular boxes
    return b[0],b[3],b[4],b[5],b[1],b[6],b[7],b[8],b[2]   # Return full definition xx,xy,xz,yx,yy,yz,zx,zy,zz

def groAtom(a):
    # In PDB files, there might by an insertion code. To handle this, we internally add
    # constant to all resids. To be consistent, we have to do the same for gro files.
    # 32 equal ord(' '), eg an empty insertion code
    constant = 32<<20
    #012345678901234567890123456789012345678901234567890
    #    1PRN      N    1   4.168  11.132   5.291
    ## ===> atom name,        res name,          res id,    chain,
    return (a[10:15].strip(), a[5:10].strip(),   int(a[:5])+constant, " ", 
    ##               x,                 y,                 z       
            10*float(a[20:28]),10*float(a[28:36]),10*float(a[36:44]))

# Simple GRO iterator
def groFrameIterator(streamIterator):
    while True:
        try:
            title = streamIterator.next()
        except StopIteration:
            break
        natoms = streamIterator.next().strip()
        if not natoms:
            break
        natoms = int(natoms)
        atoms  = [groAtom(streamIterator.next())  for i in range(natoms)] 
        box    = groBoxRead(streamIterator.next())
        yield title, atoms, box


#----+-------------+
## C | GENERAL I/O |
#----+-------------+

# It is not entirely clear where this fits in best.
# Called from main. 
def getChargeType(resname,resid,choices):
    '''Get user input for the charge of residues, based on list with choises.'''
    print ('Which %s type do you want for residue %s:'%(resname,resid+1))
    for i,choice in choices.iteritems():
        print ('%s. %s'%(i,choice))
    choice = None
    while choice not in choices.keys():
        choice = input('Type a number:')
    return choices[choice]

# *NOTE*: This should probably be a CheckableStream class that
# reads in lines until either of a set of specified conditions
# is met, then setting the type and from thereon functioning as
# a normal stream.
def streamTag(stream):
    # Tag the stream with the type of structure file
    # If necessary, open the stream, taking care of 
    # opening using gzip for gzipped files

    # First check whether we have have an open stream or a file
    # If it's a file, check whether it's zipped and open it
    if type(stream) == str:
        if stream.endswith("gz"):
            logging.info('Read input structure from zipped file.')
            s = gzip.open(stream)
        else:
            logging.info('Read input structure from file.')
            s = open(stream)
    else:
        logging.info('Read input structure from command-line')
        s = stream

    # Read a few lines, but save them
    x = [s.readline(), s.readline()]
    if x[-1].strip().isdigit():
        # Must be a GRO file
        logging.info("Input structure is a GRO file. Chains will be labeled consecutively.")
        yield "GRO"
    else:
        # Must be a PDB file then
        # Could wind further to see if we encounter an "ATOM" record
        logging.info("Input structure is a PDB file.")
        yield "PDB"
    
    # Hand over the lines that were stored
    for i in x:
        yield i

    # Now give the rest of the lines from the stream
    for i in s:
        yield i


#----+-----------------+
## D | STRUCTURE STUFF |
#----+-----------------+


# This list allows to retrieve atoms based on the name or the index
# If standard, dictionary type indexing is used, only exact matches are
# returned. Alternatively, partial matching can be achieved by setting
# a second 'True' argument. 
class Residue(list):
    def __getitem__(self,tag): 
        if type(tag) == int:
            # Call the parent class __getitem__
            return list.__getitem__(self,tag)
        if type(tag) == str:
            for i in self:
                if i[0] == tag:
                    return i
            else:
                return 
        if tag[1]:
            return [i for i in self if tag[0] in i[0]] # Return partial matches
        else:
            return [i for i in self if i[0] == tag[0]] # Return exact matches only


def residues(atomList):
    residue = [atomList[0]]
    for atom in atomList[1:]:
        if (atom[1] == residue[-1][1] and # Residue name check
            atom[2] == residue[-1][2] and # Residue id check
            atom[3] == residue[-1][3]):   # Chain id check
            residue.append(atom)
        else:
            yield Residue(residue)
            residue = [atom]
    yield Residue(residue)


def residueDistance2(r1,r2):
    return min([distance2(i,j) for i in r1 for j in r2])


# Increased the cut-off from 2.5 to 3.0 for DNA. Should check that no problems arise for proteins.
def breaks(residuelist,selection=("N","CA","C","P","C2'","C3'","O3'","C4'","C5'","O5'"),cutoff=3.0):
    # Extract backbone atoms coordinates
    bb = [[atom[4:] for atom in residue if atom[0] in selection] for residue in residuelist]
    # Needed to remove waters residues from mixed residues.
    bb = [res for res in bb if res != []]

    # We cannot rely on some standard order for the backbone atoms.
    # Therefore breaks are inferred from the minimal distance between
    # backbone atoms from adjacent residues.
    return [ i+1 for i in range(len(bb)-1) if residueDistance2(bb[i],bb[i+1]) > cutoff]


def contacts(atoms,cutoff=5):
    rla = range(len(atoms))
    crd = [atom[4:] for atom in atoms]
    return [(i,j) for i in rla[:-1] for j in rla[i+1:] 
            if distance2(crd[i],crd[j]) < cutoff]

def add_dummy(beads,dist=0.11,n=2):
    # Generate a random vector in a sphere of -1 to +1, to add to the bead position
    v    = [random.random()*2.-1,random.random()*2.-1,random.random()*2.-1]
    # Calculated the length of the vector and divide by the final distance of the dummy bead
    norm_v = norm(v)/dist
    # Resize the vector
    vn   = [i/norm_v for i in v]
    # m sets the direction of the added vector, currently only works when adding one or two beads.
    m = 1
    for j in range(n):
        newName = 'SCD' 
        newBead = (newName,tuple([i+(m*j) for i,j in zip(beads[-1][1],vn)]), beads[-1][2])
        beads.append(newBead)
        m *= -2
    return beads

def check_merge(chains, m_list=[], l_list=[], ss_cutoff=0):
    chainIndex = range(len(chains))

    if 'all' in m_list:
        logging.info("All chains will be merged in a single moleculetype.")
        return chainIndex, [chainIndex]

    chainID = [chain.id for chain in chains]

    # Mark the combinations of chains that need to be merged
    merges = []
    if m_list:
        # Build a dictionary of chain IDs versus index
        # To give higher priority to top chains the lists are reversed 
        # before building the dictionary
        chainIndex.reverse()
        chainID.reverse()
        dct = dict(zip(chainID,chainIndex))
        chainIndex.reverse()
        # Convert chains in the merge_list to numeric, if necessary
        # NOTE The internal numbering is zero-based, while the 
        # command line chain indexing is one-based. We have to add
        # one to the number in the dictionary to bring it on par with
        # the numbering from the command line, but then from the 
        # result we need to subtract one again to make indexing 
        # zero-based
        merges = [[(i.isdigit() and int(i) or dct[i]+1)-1 for i in j] for j in m_list]
        for i in merges:
            i.sort()

    # Rearrange merge list to a list of pairs
    pairs = [(i[j],i[k]) for i in merges for j in range(len(i)-1) for k in range(j+1,len(i))]

    # Check each combination of chains for connections based on
    # ss-bridges, links and distance restraints
    for i in chainIndex[:-1]:
        for j in chainIndex[i+1:]:           
            if (i,j) in pairs:
                continue
            # Check whether any link links these two groups
            for a,b in l_list:                
                if ((a in chains[i] and b in chains[j]) or 
                    (a in chains[j] and b in chains[i])):
                    logging.info("Merging chains %d and %d to allow link %s"%(i+1,j+1,str((a,b))))
                    pairs.append( i<j and (i,j) or (j,i) )
                    break
            if (i,j) in pairs:
                continue
            # Check whether any cystine bond given links these two groups
            #for a,b in s_list:
            #    if ((a in chains[i] and b in chains[j]) or 
            #        (a in chains[j] and b in chains[i])):
            #        logging.info("Merging chains %d and %d to allow cystine bridge"%(i+1,j+1))
            #        pairs.append( i<j and (i,j) or (j,i) )
            #        break
            #if (i,j) in pairs:
            #    continue
            # Check for cystine bridges based on distance
            if not ss_cutoff:
                continue
            # Get SG atoms from cysteines from either chain
            # Check this pair of chains
            for cysA in chains[i]["CYS"]:
                for cysB in chains[j]["CYS"]:
                    d2 = distance2(cysA["SG"][4:7],cysB["SG"][4:7]) 
                    if d2 <= ss_cutoff:
                        logging.info("Found SS contact linking chains %d and %d (%f nm)"%(i+1,j+1,math.sqrt(d2)/10))
                        pairs.append((i,j))
                    break
                if (i,j) in pairs:
                    break

    # Sort the combinations
    pairs.sort(reverse=True)

    merges = []
    while pairs:
        merges.append(set([pairs[-1][0]]))
        for i in range(len(pairs)-1,-1,-1):
            if pairs[i][0] in merges[-1]:
                merges[-1].add(pairs.pop(i)[1])
            elif pairs[i][1] in merges[-1]:
                merges[-1].add(pairs.pop(i)[0])
    merges = [list(i) for i in merges]
    for i in merges:
        i.sort()

    order = [j for i in merges for j in i]

    if merges:
        logging.warning("Merging chains.")
        logging.warning("This may change the order of atoms and will change the number of topology files.")
        logging.info("Merges: " + ", ".join([str([j+1 for j in i]) for i in merges]))

    if len(merges) == 1 and len(merges[0]) > 1 and set(merges[0]) == set(chainIndex):
        logging.info("All chains will be merged in a single moleculetype")

    # Determine the order for writing; merged chains go first
    merges.extend([[j] for j in chainIndex if not j in order])
    order.extend([j for j in chainIndex if not j in order])

    return order, merges


## !! NOTE !! ##
## XXX The chain class needs to be simplified by extracting things to separate functions/classes
class Chain:
    # Attributes defining a chain
    # When copying a chain, or slicing, the attributes in this list have to
    # be handled accordingly.
    _attributes = ("residues","sequence","seq","ss","ssclass","sstypes")

    def __init__(self,options,residuelist=[],name=None,multiscale=False):
        self.residues   = residuelist
        self._atoms     = [atom[:3] for residue in residuelist for atom in residue]
        self.sequence   = [residue[0][1] for residue in residuelist]
        # *NOTE*: Check for unknown residues and remove them if requested
        #         before proceeding.
        self.seq        = "".join([AA321.get(i,"X") for i in self.sequence])
        self.ss         = ""
        self.ssclass    = ""
        self.sstypes    = ""
        self.mapping    = []
        self.multiscale = multiscale
        self.options    = options

        # Unknown residues
        self.unknowns   = "X" in self.seq

        # Determine the type of chain
        self._type      = ""
        self.type()

        # Determine number of atoms
        self.natoms     = len(self._atoms) 

        # BREAKS: List of indices of residues where a new fragment starts
        # Only when polymeric (protein, DNA, RNA, ...)
        # For now, let's remove it for the Nucleic acids...
        self.breaks     = self.type() in ("Protein","Mixed") and breaks(self.residues) or []

        # LINKS:  List of pairs of pairs of indices of linked residues/atoms
        # This list is used for cysteine bridges and peptide bonds involving side chains
        # The list has items like ((#resi1, #atid1), (#resi2, #atid2))
        # When merging chains, the residue number needs ot be update, but the atom id
        # remains unchanged.
        # For the coarse grained system, it needs to be checked which beads the respective
        # atoms fall in, and bonded terms need to be added there.
        self.links      = []                   

        # Chain identifier; try to read from residue definition if no name is given
        self.id         = name or residuelist and residuelist[0][0][3] or ""

        # Container for coarse grained beads
        self._cg        = None
        
    def __len__(self):
        # Return the number of residues
        # DNA/RNA contain non-CAP d/r to indicate type. We remove those first.
        return len(''.join(i for i in self.seq if i.isupper()))

    def __add__(self,other):
        newchain = Chain(name=self.id+"+"+other.id)
        # Combine the chain items that can be simply added
        for attr in self._attributes:
            setattr(newchain, attr, getattr(self,attr) + getattr(other,attr))
        # Set chain items, shifting the residue numbers
        shift  = len(self)
        newchain.breaks     = self.breaks + [shift] + [i+shift for i in other.breaks]
        newchain.links      = self.links + [((i[0]+shift,i[1]),(j[0]+shift,j[1])) for i,j in other.links]
        newchain.natoms     = len(newchain.atoms())
        newchain.multiscale = self.multiscale or other.multiscale
        # Return the merged chain
        return newchain

    def __eq__(self,other):
        return (self.seq        == other.seq    and 
                self.ss         == other.ss     and
                self.breaks     == other.breaks and
                self.links      == other.links  and
                self.multiscale == other.multiscale)

    # Extract a residue by number or the list of residues of a given type
    # This facilitates selecting residues for links, like chain["CYS"]
    def __getitem__(self,other):
        if type(other) == str:
            if not other in self.sequence:
                return []
            return [i for i in self.residues if i[0][1] == other]
        elif type(other) == tuple:
            # This functionality is set up for links
            # between coarse grained beads. So these are
            # checked first,
            for i in self.cg():
                if other == i[:4]:
                    return i
            else:
                for i in self.atoms():
                    if other[:3] == i[:3]:
                        return i
                else:
                    return []
        return self.sequence[other]

    # Extract a piece of a chain as a new chain
    def __getslice__(self,i,j):
        newchain = Chain(self.options,name=self.id)        
        # Extract the slices from all lists
        for attr in self._attributes:           
            setattr(newchain, attr, getattr(self,attr)[i:j])
        # Breaks that fall within the start and end of this chain need to be passed on.
        # Residue numbering is increased by 20 bits!!
        # XXX I don't know if this works.
        ch_sta,ch_end = newchain.residues[0][0][2],newchain.residues[-1][0][2]
        newchain.breaks     = [crack for crack in self.breaks if ch_sta < (crack<<20) < ch_end]
        newchain.links     = [link for link in self.links if ch_sta < (link<<20) < ch_end]
        newchain.multiscale = self.multiscale
        newchain.natoms     = len(newchain.atoms())
        newchain.type()
        # Return the chain slice
        return newchain

    def _contains(self,atomlist,atom):
        atnm,resn,resi,chn = atom
        
        # If the chain does not match, bail out
        if chn != self.id:
            return False

        # Check if the whole tuple is in
        if atnm and resn and resi:
            return (atnm,resn,resi) in self.atoms()

        # Fetch atoms with matching residue id
        match = (not resi) and atomlist or [j for j in atomlist if j[2] == resi]
        if not match:
            return False

        # Select atoms with matching residue name
        match = (not resn) and match or [j for j in match if j[1] == resn]
        if not match:
            return False

        # Check whether the atom is given and listed
        if not atnm or [j for j in match if j[0] == atnm]:
            return True

        # It just is not in the list!
        return False

    def __contains__(self,other):
        return self._contains(self.atoms(),other) or self._contains(self.cg(),other)

    def __hash__(self):
        return id(self)

    def atoms(self):
        if not self._atoms:
            self._atoms = [atom[:3] for residue in self.residues for atom in residue]
        return self._atoms

    # Split a chain based on residue types; each subchain can have only one type
    def split(self):
        chains = []
        chainStart = 0
        for i in range(len(self.sequence)-1):
            if residueTypes.get(self.sequence[i],"Unknown") != residueTypes.get(self.sequence[i+1],"Unknown"):
                # Use the __getslice__ method to take a part of the chain.
                chains.append(self[chainStart:i+1])
                chainStart = i+1
        if chains:
            logging.debug('Splitting chain %s in %s chains'%(self.id,len(chains)+1))
        return chains + [self[chainStart:]]

    def getname(self,basename=None):
        name = []
        if basename:                      name.append(basename)
        if self.type() and not basename:  name.append(self.type())
        if type(self.id) == int:
            name.append(chr(64+self.id))
        elif self.id.strip():               
            name.append(str(self.id))
        return "_".join(name)

    def set_ss(self,ss,source="self"):
        if len(ss) == 1:
            self.ss = len(self)*ss
        else:
            self.ss = ss
        # Infer the Martini backbone secondary structure types
        self.ssclass, self.sstypes = ssClassification(self.ss,source)

    def dss(self,method=None,executable=None):
        # The method should take a list of atoms and return a 
        # string of secondary structure classifications       
        if self.type() == "Protein":
            if method:
                atomlist = [atom for residue in self.residues for atom in residue]
                self.set_ss(ssDetermination[method](self,atomlist,executable),source=method)
            else:
                self.set_ss(len(self)*"C")
        else:
            self.set_ss(len(self.sequence)*"-")
        return self.ss

    def type(self,other=None):
        if other:
            self._type = other
        elif not self._type and len(self):
            # Determine the type of chain
            self._type     = set([residueTypes.get(i,"Unknown") for i in set(self.sequence)])
            self._type     = len(self._type) > 1 and "Mixed" or list(self._type)[0]
        return self._type


    # XXX The following (at least the greater part of it) should be made a separate function, put under "MAPPING"
    def cg(self,force=False,com=False,dna=False):
        # Generate the coarse grained structure
        # Set the b-factor field to something that reflects the secondary structure
        
        # If the coarse grained structure is set already, just return, 
        # unless regeneration is forced.
        if self._cg and not force:
            return self._cg
        self._cg = []
        atid     = 1
        bb       = [1]
        fail     = False
        previous = ''
        for residue,rss,resname in zip(self.residues,self.sstypes,self.sequence):
            # For DNA we need to get the O3' to the following residue when calculating COM
            # The force and com options ensure that this part does not affect itp generation or anything else
            if com:
                # Just an initialization, this should complain if it isn't updated in the loop
                store = 0
                for ind, i in enumerate(residue):
                    if i[0] == "O3'":
                        if previous != '':
                            residue[ind] = previous
                            previous = i
                        else:
                            store = ind
                            previous = i
                # We couldn't remove the O3' from the 5' end residue during the loop so we do it now
                if store > 0:
                    del residue[store]

            # Check if residues names has changed, for example because user has set residues interactively.
            residue = [(atom[0],resname)+atom[2:] for atom in residue]
            if residue[0][1] in ("SOL","HOH","TIP"):
                continue
            if not residue[0][1] in CoarseGrained.mapping.keys():
                logging.warning("Skipped unknown residue %s\n"%residue[0][1])
                continue
            # Get the mapping for this residue
            # CG.map returns bead coordinates and mapped atoms
            # This will fail if there are (too many) atoms missing, which is
            # only problematic if a mapped structure is written; the topology
            # is inferred from the sequence. So this is the best place to raise 
            # an error
            try:
                # The last residue, in the case of a polBB has only a CA-positioned bead.
                beads, ids = map(residue)
                beads      = zip(CoarseGrained.names[residue[0][1]],beads,ids)
            except ValueError:
                logging.error("Too many atoms missing from residue %s %d(ch:%s):",residue[0][1],residue[0][2]>>20,residue[0][3])
                logging.error(repr([ i[0] for i in residue ]))
                fail = True

            for name,(x,y,z),ids in beads:                    
                # Add the bead with coordinates and secondary structure id to the list
                self._cg.append((name,residue[0][1][:3],residue[0][2],residue[0][3],x,y,z,ss2num[rss]))
                # Add the ids to the list, after converting them to indices to the list of atoms
                self.mapping.append([atid+i for i in ids])

            # Increment the atom id; This pertains to the atoms that are included in the output.
            atid += len(residue)

            # Keep track of the numbers for CONECTing
            bb.append(bb[-1]+len(beads))

        if fail:
            logging.error("Unable to generate coarse grained structure due to missing atoms.")
            sys.exit(1)

        return self._cg

    def conect(self):
        # Return pairs of numbers that should be CONECTed
        # First extract the backbone IDs
        cg = self.cg()
        bb = [i+1 for i,j in zip(range(len(cg)),cg) if j[0] == "BB"]
        bb = zip(bb,bb[1:]+[len(bb)])
        # Set the backbone CONECTs (check whether the distance is consistent with binding)        
        conect = [(i,j) for i,j in bb[:-1] if distance2(cg[i-1][4:7],cg[j-1][4:7]) < 14]
        # Now add CONECTs for sidechains
        for i,j in bb:
            nsc = j-i-1
##################
## 7 # TOPOLOGY ##  -> @TOP <-
##################
import logging,math

# This is a generic class for Topology Bonded Type definitions
class Bonded:
    # The init method is generic to the bonded types,
    # but may call the set method if atoms are given
    # as (ID, ResidueName, SecondaryStructure) tuples
    # The set method is specific to the different types.
    def __init__(self,other=None,options=None,**kwargs):
        self.atoms = []
        self.type = -1
        self.parameters = []
        self.comments = []
        self.category = None 

        if options and type(options) == dict:
            self.options = options
        if other:
            # If other is given, then copy the attributes
            # if it is of the same class or set the 
            # attributes according to the key names if
            # it is a dictionary
            if other.__class__ == self.__class__:
                for attr in dir(other):
                    if not attr[0] == "_":
                        setattr(self,attr,getattr(other,attr))
            elif type(other) == dict:
                for attr in other.keys():
                    setattr(self,attr,other[attr])
            elif type(other) in (list,tuple):
                self.atoms = other

        # For every item in the kwargs keys, set the attribute
        # with the same name. This can be used to specify the 
        # attributes directly or to override attributes 
        # copied from the 'other' argument.
        for key in kwargs:
            setattr(self,key,kwargs[key])
        
        # If atoms are given as tuples of
        # (ID, ResidueName[, SecondaryStructure])
        # then determine the corresponding parameters 
        # from the lists above
        if self.atoms and type(self.atoms[0]) == tuple:
            self.set(self.atoms,**kwargs)          

    def __nonzero__(self):
        return bool(self.atoms) and bool(self.parameters) 

    def __str__(self):
        if not self.atoms or not self.parameters:
            return ""
        s = ["%5d" % i for i in self.atoms]
        # For exclusions, no type is defined, which equals -1
        if self.type != -1: s.append(" %5d " % self.type)
        # Print integers and floats in proper format and neglect None terms
        s.extend([formatString(i) for i in self.parameters if i != None])
        if self.comments:
            s.append(';')
            if type(self.comments) == str:
                s.append(self.comments)
            else:
                s.extend([str(i) for i in self.comments])
        return " ".join(s)

    def __iadd__(self,num):
        self.atoms = tuple([i+int(num) for i in self.atoms])
        return self

    def __add__(self,num):
        out  = self.__class__(self)
        out += num
        return out

    def __eq__(self,other):
        if type(other) in (list,tuple):
            return self.atoms == other
        else:
            return self.atoms == other.atoms and self.type == other.type and self.parameters == other.parameters

    # This function needs to be overridden for descendents
    def set(self,atoms,**kwargs):
        pass


# The set method of this class will look up parameters for backbone beads
# Side chain bonds ought to be set directly, using the constructor
# providing atom numbers, bond type, and parameters
# Constraints are bonds with kb = None, which can be extracted 
# using the category
class Bond(Bonded):
    def set(self,atoms,**kwargs):
        ids,r,ss,ca     = zip(*atoms)     
        self.atoms      = ids
        self.type       = 1
        self.positionCa = ca
        self.comments   = "%s(%s)-%s(%s)" % (r[0],ss[0],r[1],ss[1])
        # The category can be used to keep bonds sorted
        self.category   = kwargs.get("category")
       
        if not self.parameters:
            self.parameters = self.options['ForceField'].bbGetBond(r,ca,ss)
        # If there are more than two parameters given, user HAS TO define the bond type as the first one.
        # This is to allow use of any gromacs bond type.
        if self.parameters and len(self.parameters) > 2:
            self.type, self.parameters = self.parameters[0], self.parameters[1:]
        # Backbone bonds also can be constraints. We could change the type further on, but this is more general.
        # Even better would be to add a new type: BB-Constraint
        if self.parameters and self.parameters[1] == None:
            self.category = 'Constraint'

    # Overriding __str__ method to suppress printing of bonds with Fc of 0
    def __str__(self):
        if len(self.parameters) > 1 and self.parameters[1] == 0:
            return ""
        return Bonded.__str__(self)


# Similar to the preceding class
class Angle(Bonded):
    def set(self,atoms,**kwargs):
        ids,r,ss,ca     = zip(*atoms)
        self.atoms      = ids
        self.type       = 2
        self.positionCa = ca
        self.comments   = "%s(%s)-%s(%s)-%s(%s)" % (r[0],ss[0],r[1],ss[1],r[2],ss[2])
        self.category   = kwargs.get("category")
        
        self.parameters = self.options['ForceField'].bbGetAngle(r,ca,ss)
        # If there are more than two parameters given, user HAS TO define the angle type as the first one.
        # This is to allow use of any gromacs angle type.
        if self.parameters and len(self.parameters) > 2:
            self.type, self.parameters = self.parameters[0], self.parameters[1:]

# Similar to the preceding class
class Vsite(Bonded):
    def set(self,atoms,**kwargs):
        ids,r,ss,ca     = zip(*atoms)
        self.atoms      = ids
        self.type       = 1
        self.positionCa = ca
        self.comments   = "%s"% (r[0])
        self.category   = kwargs.get("category")
        self.parameters = kwargs.get("parameters") 
        if not self.parameters:
            self.parameters = self.options['ForceField'].bbGetVsite(r,ca,ss)
            # This assumes type one virtual sites, COM of two beads
            if self.parameters and len(self.parameters)>1:
                self.atoms += self.parameters[:-1]
                self.parameters = self.parameters[-1:]

# Similar to the preceding class
class Exclusion(Bonded):
    def set(self,atoms,**kwargs):
        ids,r,ss,ca     = zip(*atoms)
        self.atoms      = ids
        self.positionCa = ca
        self.comments   = "%s"% (r[0])
        self.category   = kwargs.get("category")
        self.parameters = kwargs.get("parameters") 
        if not self.parameters:
            self.parameters = self.options['ForceField'].bbGetExclusion(r,ca,ss)

# Similar to the preceding class
class Pair(Bonded):
    def set(self,atoms,**kwargs):
        ids,r,ss,ca     = zip(*atoms)
        self.atoms      = ids
        self.positionCa = ca
        self.comments   = "%s(%s)-%s(%s)"% (r[0],ss[0],r[1],ss[1])
        self.category   = kwargs.get("category")
        self.type       = kwargs.get("type") or 1 
        if not self.parameters:
            self.parameters = self.options['ForceField'].bbGetPair(r,ca,ss)

# Similar to the preceding class
class Dihedral(Bonded):
    def set(self,atoms,**kwargs):
        ids,r,ss,ca     = zip(*atoms)
        self.atoms      = ids
        self.type       = 1
        self.positionCa = ca
        self.comments   = "%s(%s)-%s(%s)-%s(%s)-%s(%s)" % (r[0],ss[0],r[1],ss[1],r[2],ss[2],r[3],ss[3])
        self.category   = kwargs.get("category")
        if not self.parameters:
            self.parameters = self.options['ForceField'].bbGetDihedral(r,ca,ss)
        # If there are more than two parameters given, user HAS TO define the diheral type as the first one.
        # This is to allow use of any gromacs dihedral type.
        if self.parameters and len(self.parameters)>2:
            self.type,self.parameters = self.parameters[0],self.parameters[1:]

        # XXX Move this to force field files to accommodate polbb and dna dihedrals in a uniform way
        # if ''.join(i for i in ss) == 'FFFF':
        #    # Collagen
        #    self.parameters = self.options['ForceField'].bbDihedDictD['F']
        #elif ''.join(i for i in ss) == 'EEEE' and self.options['ExtendedDihedrals']:
        #    # Use dihedrals
        #    self.parameters = self.options['ForceField'].bbDihedDictD['E']
        #elif set(ss).issubset("H123"):
        #    # Helix
        #    self.parameters = self.options['ForceField'].bbDihedDictD['H']
        #else:
        #    self.parameters = None


# This list allows to retrieve Bonded class items based on the category
# If standard, dictionary type indexing is used, only exact matches are
# returned. Alternatively, partial matching can be achieved by setting
# a second 'True' argument. 
class CategorizedList(list):
    def __getitem__(self,tag): 
        if type(tag) == int:
            # Call the parent class __getitem__
            return list.__getitem__(self,tag)

        if type(tag) == str:
            return [i for i in self if i.category == tag]

        if tag[1]:
            return [i for i in self if tag[0] in i.category]
        else:
            return [i for i in self if i.category == tag[0]]


class Topology:
    def __init__(self,other=None,options=None,name=""):
        self.name        = ''
        self.nrexcl      = 1
        self.atoms       = CategorizedList()
        self.pairs       = CategorizedList()
        self.vsites      = CategorizedList() 
        self.exclusions  = CategorizedList() 
        self.bonds       = CategorizedList()
        self.angles      = CategorizedList()
        self.dihedrals   = CategorizedList()
        self.impropers   = CategorizedList()
        self.constraints = CategorizedList()
        self.posres      = CategorizedList()
        self.sequence    = []
        self.secstruc    = ""
        # Okay, this is sort of funny; we will add a 
        #   #define mapping virtual_sitesn
        # to the topology file, followed by a header
        #   [ mapping ]
        self.mapping     = []
        # For multiscaling we have to keep track of the number of 
        # real atoms that correspond to the beads in the topology
        self.natoms      = 0        
        self.multiscale  = options['multi']

        if options:
            self.options = options
        else:
            self.options = {}

        if not other:
            # Returning an empty instance
            return
        elif isinstance(other,Topology):
            for attrib in ["atoms","vsites","bonds","angles","dihedrals","impropers","constraints","posres"]:
                setattr(self,attrib,getattr(other,attrib,[]))
        elif isinstance(other,Chain):
            if other.type() == "Protein" and other.options['ForceField'].name in ['polbb']:
                self.fromAminoAcidSequencePolBB(other)
            elif other.type() == "Protein":
                self.fromAminoAcidSequence(other)
            elif other.type() == "Nucleic":
                self.fromNucleicAcidSequence(other)
            else:
                # This chain should not be polymeric, but a collection of molecules
                # For each unique residue type fetch the proper moleculetype 
                self.fromMoleculeList(other)
        if name:
            self.name = name

    def __iadd__(self,other):
        if not isinstance(other,Topology):
            other = Topology(other)
        shift     = len(self.atoms)
        last      = self.atoms[-1]
        atoms     = zip(*other.atoms)
        atoms[0]  = [i+shift for i in atoms[0]]   # Update atom numbers
        atoms[2]  = [i+last[2] for i in atoms[2]] # Update residue numbers
        atoms[5]  = [i+last[5] for i in atoms[5]] # Update charge group numbers
        atoms     = zip(*atoms)
        # The zippings above kills all atoms with specified mass (9 long lists) 
        # Let's add some band aid to fix it...
        # This of course doesn't work if there was a secondary structure to keep
        # but think it affects at this stage only the output comment.
        for i in range(len(atoms)):
            if atoms[i][-1] == 0:
                atoms[i] = atoms[i] + ('c',)
        self.atoms.extend(atoms)
        for attrib in ["bonds","vsites","angles","dihedrals","impropers","constraints","posres"]:
            getattr(self,attrib).extend([source+shift for source in getattr(other,attrib)])
        return self

    def __add__(self,other):
        out = Topology(self)
        if not isinstance(other,Topology):
            other = Topology(other)
        out += other
        return out

    def __str__(self):
        if self.multiscale:
             out  = [ '; MARTINI (%s) Multiscale virtual sites topology section for "%s"' %(self.options['ForceField'].name,self.name) ]
        else:
             string  = '; MARTINI (%s) Coarse Grained topology file for "%s"' %(self.options['ForceField'].name, self.name)
             string += '\n; Created by py version %s \n; Using the following options:  ' %(self.options['Version'])
             string += ' '.join(self.options['Arguments'])
             string += '\n; #####################################################################################################'
             string += '\n; This topology is based on development beta of Martini DNA and should NOT be used for production runs.'
             string += '\n; #####################################################################################################'
             out  = [ string ]
        if self.sequence:
            out += [
                '; Sequence:',
                '; ' + ''.join([ AA321.get(AA) for AA in self.sequence ]),
                '; Secondary Structure:',
                '; ' + self.secstruc,
                ]
        
        # Do not print a molecule name when multiscaling
        # In that case, the topology created here needs to be appended
        # at the end of an atomistic moleculetype
        if not self.multiscale:
            out += [ '\n[ moleculetype ]',
                     '; Name         Exclusions',  
                     '%-15s %3d' % (self.name,self.nrexcl)]

        out.append('\n[ atoms ]')

        # For virtual sites and dummy beads we have to be able to specify the mass.
        # Thus we need two different format strings:
        fs8 = '%5d %5s %5d %5s %5s %5d %7.4f ; %s'  
        fs9 = '%5d %5s %5d %5s %5s %5d %7.4f %7.4f ; %s'  
        out.extend([len(i)==9 and fs9%i or fs8%i for i in self.atoms])
        #for i in self.atoms:
        #    print i

        # Print the pairs.
        pairs = [str(i) for i in self.pairs]
        if pairs:
            out.append('\n[ pairs ]')
            out.extend(pairs)

        # Print out the vsites only if they excist. Right now it can only be type 1 virual sites.
        # TODO: This needs to be generalized for all virtual site types.
        vsitesBB = [str(i) for i in self.vsites["BB"]]
        vsitesSC = [str(i) for i in self.vsites["SC"]]
        if vsitesBB or vsitesSC:
            out.append('\n[ virtual_sites3 ]')
        if vsitesBB:
            out.append("; Backbone virtual sites.")
            out.extend(vsitesBB)
        if vsitesSC:
            out.append("; Backbone virtual sites.")
            out.extend(vsitesSC)

        # Bonds in order: backbone, backbone-sidechain, sidechain, short elastic, long elastic        
        out.append("\n[ bonds ]")       
        # Backbone-backbone
        bonds = [str(i) for i in self.bonds["BB"]]
        if bonds:
            out.append("; Backbone bonds")
            out.extend(bonds)
        # Rubber Bands
        bonds = [str(i) for i in self.bonds["Rubber",True]]
        #print bonds
        if bonds:
            # Add a CPP style directive to allow control over the elastic network
            out.append("#ifdef RUBBER_BANDS")
            out.append("#ifndef RUBBER_FC\n#define RUBBER_FC %f\n#endif"%self.options['ElasticMaximumForce'])
            out.extend(bonds)
            out.append("#endif")
        # Backbone-Sidechain/Sidechain-Sidechain
        bonds = [str(i) for i in self.bonds["SC"]]
        if bonds:
            out.append("; Sidechain bonds")
            out.extend(bonds)
        # Short elastic/Long elastic
        bonds = [str(i) for i in self.bonds["Elastic short"]]
        if bonds:
            out.append("; Short elastic bonds for extended regions")
            out.extend(bonds)
        bonds = [str(i) for i in self.bonds["Elastic long"]]
        if bonds:
            out.append("; Long elastic bonds for extended regions")
            out.extend(bonds)
        # Cystine bridges
        bonds = [str(i) for i in self.bonds["Cystine"]]
        if bonds:
            out.append("; Cystine bridges")
            out.extend(bonds)
        # Other links
        bonds = [str(i) for i in self.bonds["Link"]]
        if bonds:
            out.append("; Links/Cystine bridges")
            out.extend(bonds)

        # Constraints
        out.append("\n[ constraints ]")
        out.extend([str(i) for i in self.bonds["Constraint"]])

        # Print out the exclusions only if they excist.
        exclusions = [str(i) for i in self.exclusions]
        if exclusions:
            out.append('\n[ exclusions ]')
            out.extend(exclusions)

        if self.multiscale:
            out += ['\n;\n; Coarse grained to atomistic mapping\n;',
                    '#define mapping virtual_sitesn',
                    '[ mapping ]']
            for i,j in self.mapping:
                out.append( ("%5d     2 "%i)+" ".join(["%5d"%k for k in j]) )
            
            logging.info('Created virtual sites section for multiscaled topology')
            return "\n".join(out)

        # Angles
        out.append("\n[ angles ]")
        out.append("; Backbone angles")
        out.extend([str(i) for i in self.angles["BBB"]])
        out.append("; Backbone-sidechain angles")
        out.extend([str(i) for i in self.angles["BBS"]])
        out.append("; Sidechain angles")
        out.extend([str(i) for i in self.angles["SC"]])

        # Dihedrals
        out.append("\n[ dihedrals ]")
        out.append("; Backbone dihedrals")
        out.extend([str(i) for i in self.dihedrals["BBBB"] if i.parameters])
        out.append("; Sidechain dihedrals")
        out.extend([str(i) for i in self.dihedrals["BSC"] if i.parameters])
        out.append("; Sidechain improper dihedrals")
        out.extend([str(i) for i in self.dihedrals["SC"] if i.parameters])

        # Postition Restraints
        if self.posres:
            out.append("\n#ifdef POSRES")
            out.append("#ifndef POSRES_FC\n#define POSRES_FC %.2f\n#endif"%self.options['PosResForce'])
            out.append(" [ position_restraints ]")
            out.extend(['  %5d    1    POSRES_FC    POSRES_FC    POSRES_FC'%i for i in self.posres])
            out.append("#endif")

        logging.info('Created coarsegrained topology')
        return "\n".join(out)


    def ndx(self,start):
        bonds_out = []
        angles_out = []
        dihs_out = []
        # We print out an index file with similar bonds grouped together 
        # We print out an index group for each bond, angle and dihedral
        # Backbone-backbone
        bonds = [str(i) for i in self.bonds["BB"]]
        for i in bonds:
            params = i.split()
            params = [str(start + int(i)) for i in params[:2]]
            bonds_out.append('[BB-bond-%s-%s]\n' % (params[0], params[1]))
            bonds_out.append(' %s %s\n' % (params[0], params[1]))
        # Backbone-Sidechain/Sidechain-Sidechain
        bonds = [str(i) for i in self.bonds["SC"]]
        for i in bonds:
            params = i.split()
            params = [str(start + int(i)) for i in params[:2]]
            bonds_out.append('[SC-bond-%s-%s]\n' % (params[0], params[1]))
            bonds_out.append(' %s %s\n' % (params[0], params[1]))
        # Constraints
        bonds = [str(i) for i in self.bonds["Constraint"]]
        for i in bonds:
            params = i.split()
            params = [str(start + int(i)) for i in params[:2]]
            bonds_out.append('[Const-bond-%s-%s]\n' % (params[0], params[1]))
            bonds_out.append(' %s %s\n' % (params[0], params[1]))

        # Angles
        angles = [str(i) for i in self.angles["BBB"]]
        for i in angles:
            params = i.split()
            params = [str(start + int(i)) for i in params[:3]]
            angles_out.append('[BBB-angle-%s-%s-%s]\n' % (params[0], params[1], params[2]))
            angles_out.append(' %s %s %s\n' % (params[0], params[1], params[2]))
        angles = [str(i) for i in self.angles["BBS"]]
        for i in angles:
            params = i.split()
            params = [str(start + int(i)) for i in params[:3]]
            angles_out.append('[BBS-angle-%s-%s-%s]\n' % (params[0], params[1], params[2]))
            angles_out.append(' %s %s %s\n' % (params[0], params[1], params[2]))
        angles = [str(i) for i in self.angles["SC"]]
        for i in angles:
            params = i.split()
            params = [str(start + int(i)) for i in params[:3]]
            angles_out.append('[SC-angle-%s-%s-%s]\n' % (params[0], params[1], params[2]))
            angles_out.append(' %s %s %s\n' % (params[0], params[1], params[2]))

        # Dihedrals
        dihs = [str(i) for i in self.dihedrals["BBBB"] if i.parameters]
        for i in dihs:
            params = i.split()
            params = [str(start + int(i)) for i in params[:4]]
            dihs_out.append('[BB-dihedral-%s-%s-%s-%s]\n' % (params[0], params[1], params[2], params[3]))
            dihs_out.append(' %s %s %s %s\n' % (params[0], params[1], params[2], params[3]))
        dihs = [str(i) for i in self.dihedrals["BSC"] if i.parameters]
        for i in dihs:
            params = i.split()
            params = [str(start + int(i)) for i in params[:4]]
            dihs_out.append('[BSC-dihedral-%s-%s-%s-%s]\n' % (params[0], params[1], params[2], params[3]))
            dihs_out.append(' %s %s %s %s\n' % (params[0], params[1], params[2], params[3]))
        dihs = [str(i) for i in self.dihedrals["SC"] if i.parameters]
        for i in dihs:
            params = i.split()
            params = [str(start + int(i)) for i in params[:4]]
            dihs_out.append('[SC-dihedral-%s-%s-%s-%s]\n' % (params[0], params[1], params[2], params[3]))
            dihs_out.append(' %s %s %s %s\n' % (params[0], params[1], params[2], params[3]))

        logging.info('Created index files for bonded parameters.')
        return ''.join(bonds_out), ''.join(angles_out), ''.join(dihs_out)

  
    # The sequence function can be used to generate the topology for 
    # a sequence :) either given as sequence or as chain
    def fromAminoAcidSequence(self,sequence,secstruc=None,links=None,breaks=None,
                              mapping=None,rubber=False,multi=False):
        # Shift for the atom numbers of the atomistic part in a chain 
        # that is being multiscaled
        shift = 0
        # First check if we get a sequence or a Chain instance
        if isinstance(sequence, Chain):
            chain         = sequence
            links         = chain.links
            breaks        = chain.breaks
            # If the mapping is not specified, the actual mapping is taken,
            # used to construct the coarse grained system from the atomistic one.
            # The function argument "mapping" could be used to use a default 
            # mapping scheme in stead, like the mapping for the GROMOS96 force field.
            mapping = mapping           or chain.mapping
            multi   = self.options['multi']  or chain.multiscale
            self.secstruc = chain.sstypes or len(chain)*"C"
            self.sequence = chain.sequence
            # If anything hints towards multiscaling, do multiscaling
            self.multiscale = self.multiscale or chain.multiscale or multi
            if self.multiscale:
                shift        = self.natoms
                self.natoms += len(chain.atoms())
        elif not secstruc:
            # If no secondary structure is provided, set all to coil
            chain         = None
            self.secstruc = len(self.sequence)*"C"
        else:
            # If a secondary structure is provided, use that. chain is none.
            chain         = None
            self.secstruc = secstruc

        logging.debug(self.secstruc)
        logging.debug(self.sequence)

        # Fetch the sidechains
        # Pad with empty lists for atoms, bonds, angles 
        # and dihedrals, and take the first four lists out
        # This will avoid errors for residues for which 
        # these are not defined.

        sc = [(self.options['ForceField'].sidechains[res]+5*[[]])[:5] for res in self.sequence]

        # ID of the first atom/residue
        # The atom number and residue number follow from the last 
        # atom c.q. residue id in the list processed in the topology
        # thus far. In the case of multiscaling, the real atoms need 
        # also be accounted for.
        startAtom = self.natoms + 1 
        startResi = self.atoms and self.atoms[-1][2]+1 or 1

        # Backbone bead atom IDs
        bbid = [startAtom]
        for i in zip(*sc)[0]:
            bbid.append(bbid[-1]+len(i)+1)

        # Calpha positions, to get Elnedyn BBB-angles and BB-bond lengths
        # positionCa = [residue[1][4:] for residue in chain.residues]
        # The old method (line above) assumed no hydrogens: Ca would always be
        # the second atom of the residue. Now we look at the name.
        positionCa = []
        for residue in chain.residues:
            for atom in residue:
                if atom[0] == "CA":
                    positionCa.append(atom[4:])

        # Residue numbers for this moleculetype topology
        resid = range(startResi,startResi+len(self.sequence))     
        
        # This contains the information for deriving backbone bead types,
        # bb bond types, bbb/bbs angle types, and bbbb dihedral types and
        # Elnedyn BB-bondlength BBB-angles
        seqss = zip(bbid,self.sequence,self.secstruc,positionCa)

        # Fetch the proper backbone beads          
        bb = [self.options['ForceField'].bbGetBead(res,typ) for num,res,typ,Ca in seqss]

        # If termini need to be charged, change the bead types
        if not self.options['NeutralTermini']:
            bb[0]  ="Qd"
            bb[-1] = "Qa"

        # If breaks need to be charged, change the bead types 
        if self.options['ChargesAtBreaks']:
            for i in breaks:
                bb[i]   = "Qd"
                bb[i-1] = "Qa"

        # For backbone parameters, iterate over fragments, inferred from breaks
        for i,j in zip([0]+breaks,breaks+[-1]):
            # Extract the fragment
            frg = j==-1 and seqss[i:] or seqss[i:j]

            # Iterate over backbone bonds
            self.bonds.extend([Bond(pair,category="BB",options=self.options,) for pair in zip(frg,frg[1:])])

            # Iterate over backbone angles
            # Don't skip the first and last residue in the fragment
            self.angles.extend([Angle(triple,options=self.options,category="BBB") for triple in zip(frg,frg[1:],frg[2:])])

            # Get backbone quadruples
            quadruples = zip(frg,frg[1:],frg[2:],frg[3:])

            # No i-1,i,i+1,i+2 interactions defined for Elnedyn
            if self.options['ForceField'].UseBBBBDihedrals:
                # Process dihedrals
                for q in quadruples:
                    id,rn,ss,ca = zip(*q)
                    # Maybe do local elastic networks
                    if ss == ("E","E","E","E") and not self.options['ExtendedDihedrals']:
                        # This one may already be listed as the 2-4 bond of a previous one
                        if not (id[0],id[2]) in self.bonds:
                            self.bonds.append(Bond(options=self.options,atoms=(id[0],id[2]),parameters=self.options['ForceField'].ebonds['short'],type=1,
                                                   comments="%s(%s)-%s(%s) 1-3"%(rn[0],id[0],rn[2],id[2]),
                                                   category="Elastic short"))
                        self.bonds.append(Bond(options=self.options,atoms=(id[1],id[3]),parameters=self.options['ForceField'].ebonds['short'],type=1,
                                               comments="%s(%s)-%s(%s) 2-4"%(rn[1],id[1],rn[3],id[3]),
                                               category="Elastic short"))
                        self.bonds.append(Bond(options=self.options,atoms=(id[0],id[3]),parameters=self.options['ForceField'].ebonds['long'],type=1,
                                               comments="%s(%s)-%s(%s) 1-4"%(rn[0],id[0],rn[3],id[3]),
                                               category="Elastic long"))
                    else:
                        # Since dihedrals can return None, we first collect them separately and then
                        # add the non-None ones to the list
                        dihed = Dihedral(q,options=self.options,category="BBBB")
                        if dihed:
                            self.dihedrals.append(dihed)

            # Elnedyn does not use backbone-backbone-sidechain-angles
            if self.options['ForceField'].UseBBSAngles:
                # Backbone-Backbone-Sidechain angles
                # If the first residue has a sidechain, we take SBB, otherwise we skip it
                # For other sidechains, we 'just' take BBS
                if len(frg) > 1 and frg[1][0]-frg[0][0] > 1:
                    self.angles.append(Angle(options=self.options,atoms=(frg[0][0]+1,frg[0][0],frg[1][0]),parameters=self.options['ForceField'].bbsangle,type=2,
                                            comments="%s(%s)-%s(%s) SBB"%(frg[0][1],frg[0][2],frg[1][1],frg[1][2]),
                                            category="BBS"))
    
                # Start from first residue: connects sidechain of second residue
                for (ai,ni,si,ci),(aj,nj,sj,cj),s in zip(frg[0:],frg[1:],sc[1:]):
                    if s[0]:
                        self.angles.append(Angle(options=self.options,atoms=(ai,aj,aj+1),parameters=self.options['ForceField'].bbsangle,type=2,
                                                comments="%s(%s)-%s(%s) SBB"%(ni,si,nj,sj),
                                                category="BBS"))
           
        # Now do the atom list, and take the sidechains along
        #
        # AtomID AtomType ResidueID ResidueName AtomName ChargeGroup Charge ; Comments
        # 
        atid  = startAtom
        for resi,resname,bbb,sidechn,ss in zip(resid,self.sequence,bb,sc,self.secstruc):
            scatoms, bon_par, ang_par, dih_par, vsite_par = sidechn

            # Side chain bonded terms
            # Collect bond, angle and dihedral connectivity
            bon_con,ang_con,dih_con,vsite_con = (self.options['ForceField'].connectivity[resname]+4*[[]])[:4]

            # Side Chain Bonds/Constraints
            for atids,par in zip(bon_con,bon_par):
                if par[1] == None:
                    self.bonds.append(Bond(options=self.options,atoms=atids,parameters=[par[0]],type=1,
                                           comments=resname,category="Constraint"))
                else:
                    self.bonds.append(Bond(options=self.options,atoms=atids,parameters=par,type=1,
                                           comments=resname,category="SC"))
                # Shift the atom numbers
                self.bonds[-1] += atid

            # Side Chain Angles
            for atids,par in zip(ang_con,ang_par):
                self.angles.append(Angle(options=self.options,atoms=atids,parameters=par,type=2,
                                         comments=resname,category="SC"))
                # Shift the atom numbers
                self.angles[-1] += atid

            # Side Chain Dihedrals
            for atids,par in zip(dih_con,dih_par):
                self.dihedrals.append(Dihedral(options=self.options,atoms=atids,parameters=par,type=2,
                                               comments=resname,category="SC"))
                # Shift the atom numbers
                self.dihedrals[-1] += atid

            # Side Chain V-Sites
            for atids,par in zip(vsite_con,vsite_par):
                self.vsites.append(Vsite(options=self.options,atoms=atids,parameters=par,type=1,
                                               comments=resname,category="SC"))
                # Shift the atom numbers
                self.vsites[-1] += atid
            
            # Side Chain exclusions
            # The new polarizable forcefield give problems with the charges in the sidechain, if the backbone is also charged.
            # To avoid that, we add explicit exclusions
            if bbb in self.options['ForceField'].charges.keys() and resname in self.options['ForceField'].mass_charge.keys():
                for i in [i for i, d in enumerate(scatoms) if d=='D']:
                    self.exclusions.append(Exclusion(options=self.options,atoms=(atid,i+atid+1),comments='%s(%s)'%(resname,resi),parameters=(None,)))

            # All residue atoms
            counter = 0  # Counts over beads
            for atype,aname in zip([bbb]+list(scatoms),CoarseGrained.residue_bead_names):
                if self.multiscale:
                    atype,aname = "v"+atype,"v"+aname
                # If mass or charge diverse, we adopt it here. 
                # We don't want to do this for BB beads because of charged termini.
                if resname in self.options['ForceField'].mass_charge.keys() and counter != 0:
                    M,Q = self.options['ForceField'].mass_charge[resname]
                    aname = Q[counter-1]>0 and 'SCP' or Q[counter-1]<0 and 'SCN' or aname
                    self.atoms.append((atid,atype,resi,resname,aname,atid,Q[counter-1],M[counter-1],ss))
                else:
                    self.atoms.append((atid,atype,resi,resname,aname,atid,self.options['ForceField'].charges.get(atype,0),ss))
                # Doing this here save going over all the atoms onesmore.
                # Generate position restraints for all atoms or Backbone beads only.
                if 'all' in self.options['PosRes']:
                    self.posres.append((atid)) 
                elif aname in self.options['PosRes']:
                    self.posres.append((atid))
                if mapping:
                    self.mapping.append((atid,[i+shift for i in mapping[counter]]))
                atid    += 1
                counter += 1

        # The rubber bands are best applied outside of the chain class, as that gives
        # more control when chains need to be merged. The possibility to do it on the 
        # chain level is retained to allow building a complete chain topology in 
        # a straightforward manner after importing this script as module.
        if rubber and chain:
            rubberList = rubberBands(
                [(i[0],j[4:7]) for i,j in zip(self.atoms,chain.cg()) if i[4] in ElasticBeads],
                ElasticLowerBound,ElasticUpperBound,
                ElasticDecayFactor,ElasticDecayPower,
                ElasticMaximumForce,ElasticMinimumForce)
            self.bonds.extend([Bond(i,options=self.options,type=6,category="Rubber band") for i in rubberList])
        
        # Note the equivalent of atomistic atoms that have been processed 
        if chain and self.multiscale:
            self.natoms += len(chain.atoms())

    def fromNucleicAcidSequence(self,sequence,secstruc=None,links=None,breaks=None,
                              mapping=None,rubber=False,multi=False):

        # Shift for the atom numbers of the atomistic part in a chain 
        # that is being multiscaled
        shift = 0
        # Elastic network for DNA
        #self.options['ElasticBeads'] = ['BB1', 'BB2', 'BB3', 'SC1', 'SC2', 'SC3', 'SC4']
        #self.options['ElasticBeads'] = ['BB3', 'SC1', 'SC2', 'SC3', 'SC4']
        #self.options['ElasticBeads'] = ['BB1', 'BB2', 'BB3']
        #self.options['ElasticBeads'] = ['BB1', 'BB2']
        # First check if we get a sequence or a Chain instance
        if isinstance(sequence, Chain):
            chain         = sequence
            links         = chain.links
            breaks        = chain.breaks
            # If the mapping is not specified, the actual mapping is taken,
            # used to construct the coarse grained system from the atomistic one.
            # The function argument "mapping" could be used to use a default 
            # mapping scheme in stead, like the mapping for the GROMOS96 force field.
            mapping = mapping           or chain.mapping
            multi   = self.options['multi']  or chain.multiscale
            self.secstruc = chain.sstypes or len(chain)*"C"
            self.sequence = chain.sequence
            # If anything hints towards multiscaling, do multiscaling
            self.multiscale = self.multiscale or chain.multiscale or multi
            if self.multiscale:
                shift        = self.natoms
                self.natoms += len(chain.atoms())
        elif not secstruc:
            # If no secondary structure is provided, set all to coil
            chain         = None
            self.secstruc = len(self.sequence)*"C"
        else:
            # If a secondary structure is provided, use that. chain is none.
            chain         = None
            self.secstruc = secstruc

        logging.debug(self.secstruc)
        logging.debug(self.sequence)

        # Fetch the base information 
        # Pad with empty lists for atoms, bonds, angles 
        # and dihedrals, and take the first five lists out
        # This will avoid errors for residues for which 
        # these are not defined.

        sc = [(self.options['ForceField'].bases[res]+8*[[]])[:8] for res in self.sequence]

        # ID of the first atom/residue
        # The atom number and residue number follow from the last 
        # atom c.q. residue id in the list processed in the topology
        # thus far. In the case of multiscaling, the real atoms need 
        # also be accounted for.
        startAtom = self.natoms + 1 
        startResi = self.atoms and self.atoms[-1][2]+1 or 1

        # Backbone bead atom IDs
        bbid = [[startAtom,startAtom+1,startAtom+2]]
        for i in zip(*sc)[0]:
            bbid1 = bbid[-1][0]+len(i)+3
            bbid.append([bbid1,bbid1+1,bbid1+2])
            #bbid.append(bbid[-1]+len(i)+1)

        # Residue numbers for this moleculetype topology
        resid = range(startResi,startResi+len(self.sequence))     

        # This contains the information for deriving backbone bead types,
        # bb bond types, bbb/bbs angle types, and bbbb dihedral types.
        seqss = zip(bbid,self.sequence,self.secstruc)

        # Fetch the proper backbone beads          
        # Since there are three beads we need to split these to the list
        bb = [self.options['ForceField'].bbGetBead(res,typ) for num,res,typ in seqss]
        bbMulti = [i for j in bb for i in j]

        # This is going to be usefull for the type of the last backbone bead.
        # If termini need to be charged, change the bead types
        #if not self.options['NeutralTermini']:
        #    bb[0]  ="Qd"
        #    bb[-1] = "Qa"

        # If breaks need to be charged, change the bead types 
        #if self.options['ChargesAtBreaks']:
        #    for i in breaks:
        #        bb[i]   = "Qd"
        #        bb[i-1] = "Qa"

        # For backbone parameters, iterate over fragments, inferred from breaks
        for i,j in zip([0]+breaks,breaks+[-1]):
            # Extract the fragment
            frg = j==-1 and seqss[i:] or seqss[i:j]
            # Expand the 3 bb beads per residue into one long list
            # Resulting list contains three tuples per residue 
            # We use the useless ca parameter to get the correct backbone bond from bbGetBond 
            # The i is used to define ca because it conveniently here gives the right sequence 0,1,2,0,1,...
            frg = [(j[0][i],j[1],j[2],i) for j in frg for i in range(len(j[0]))]

            # Iterate over backbone bonds, two loops are needed because there are multipe cross bonds in the BB.
            # Since bonded interactions can return None, we first collect them separately and then
            # add the non-None ones to the list
            # This part assumes you have a linear backbone (checks only combinations that make sense for such) 
            for ind,k in enumerate(frg):
                    
                # Exclusions iterate over the second atom.
                # and then checked for each pair.
                for l in frg[ind:ind+3]:
                    excl = Exclusion((k,l),category="BB",options=self.options,)
                    if excl:
                        self.exclusions.append(excl) 

                # Pairs iterate over the second atom.
                # and then checked for each pair.
                for l in frg[ind:ind+3]:
                    pair = Pair((k,l),category="BB",options=self.options,)
                    if pair:
                        self.pairs.append(pair) 

                # Bonds iterate over the second atom.
                for l in frg[ind:ind+3]:
                    bond = Bond((k,l),category="BB",options=self.options,)
                    if bond:
                        self.bonds.append(bond)
                        
                    # The angles need a third loop.
                    for m in frg[ind:ind+3]:
                        angle = Angle((k,l,m,),options=self.options,category="BBB")
                        if angle:
                            self.angles.append(angle)
                            
                        # The dihedrals need a fourth loop.
                        for n in frg[ind+1:ind+4]:
                            dihed = Dihedral((k,l,m,n,),options=self.options,category="BBBB")
                            if dihed:
                                if len(dihed.parameters) > 3:
                                    dihed2 = Dihedral((k,l,m,n,),options=self.options, parameters=dihed.parameters[3:],category="BBBB")
                                    dihed.parameters = dihed.parameters[:3]
                                    self.dihedrals.append(dihed)
                                    self.dihedrals.append(dihed2)
                                else:
                                    self.dihedrals.append(dihed)

        # Now do the atom list, and take the sidechains along
        #
        atid  = startAtom
        # We need to do some trickery to get all 3 bb beads in to these lists
        # This adds each element to a list three times, feel free to shorten up
        residMulti = [i for i in resid for j in range(3)]
        sequenceMulti = [i for i in self.sequence for j in range(3)]
        scMulti = [i for i in sc for j in range(3)]
        secstrucMulti = [i for i in self.secstruc for j in range(3)]
        count = 0
        for resi,resname,bbb,sidechn,ss in zip(residMulti,sequenceMulti,bbMulti,scMulti,secstrucMulti):
            # We only want one side chain per three backbone beads so this skips the others
            if (count % 3) == 0:    
                # Note added impropers in contrast to aa
                scatoms, bon_par, ang_par, dih_par, imp_par, vsite_par, excl_par, pair_par = sidechn

                # Side chain bonded terms
                # Collect bond, angle and dihedral connectivity
                # Impropers needed to be added here for DNA
                bon_con,ang_con,dih_con,imp_con,vsite_con,excl_con, pair_con = (self.options['ForceField'].base_connectivity[resname]+7*[[]])[:7]
                # Ill try to fix the exclusions by using separate connectivity record for DNA
                #bon_con,ang_con,dih_con,imp_con,vsite_con = (self.options['ForceField'].connectivity[resname]+5*[[]])[:5]

                # Side Chain Bonds/Constraints
                for atids,par in zip(bon_con,bon_par):
                    if par[2] == None:
                        self.bonds.append(Bond(options=self.options,atoms=atids,parameters=[par[1]],type=par[0],
                                               comments=resname,category="Constraint"))
                    else:
                        self.bonds.append(Bond(options=self.options,atoms=atids,parameters=par[1:],type=par[0],
                                               comments=resname,category="SC"))
                    # Shift the atom numbers
                    self.bonds[-1] += atid

                # Side Chain Angles
                for atids,par in zip(ang_con,ang_par):
                    self.angles.append(Angle(options=self.options,atoms=atids,parameters=par[1:],type=par[0],
                                             comments=resname,category="SC"))
                    # Shift the atom numbers
                    self.angles[-1] += atid

                # Side Chain Dihedrals
                for atids,par in zip(dih_con,dih_par):
                    self.dihedrals.append(Dihedral(options=self.options,atoms=atids,parameters=par[1:],type=par[0],
                                                   comments=resname,category="BSC"))
                    # Shift the atom numbers
                    self.dihedrals[-1] += atid

                # Side Chain Impropers
                for atids,par in zip(imp_con,imp_par):
                    self.dihedrals.append(Dihedral(options=self.options,atoms=atids,parameters=par[1:],type=par[0],
                                                   comments=resname,category="SC"))
                    # Shift the atom numbers
                    self.dihedrals[-1] += atid

                # Side Chain V-Sites
                for atids,par in zip(vsite_con,vsite_par):
                    self.vsites.append(Vsite(options=self.options,atoms=atids,parameters=par,type=1,
                                                   comments=resname,category="SC"))
                    # Shift the atom numbers
                    self.vsites[-1] += atid

                # XXX Should not be hard coded here!
                # Currently DNA needs exclusions for the base
                # The loop runs over the first backbone bead so 3 needs to be added to the indices
                # for i in range(len(scatoms)):
                #    for j in range(i+1, len(scatoms)):
                #        self.exclusions.append(Exclusion(options=self.options,atoms=(i+atid+3,j+atid+3),comments='%s(%s)'%(resname,resi),parameters=(None,)))
                # The above one is ugly hack if only one connectivity record can be used
                # The one below is equally ugly but works for now
                for atids,par in zip(excl_con,excl_par):
                    self.exclusions.append(Exclusion(options=self.options,atoms=atids,parameters=' '))
                    # Shift the atom numbers
                    self.exclusions[-1] += atid

                # Pairs
                for atids,par in zip(pair_con,pair_par):
                    self.pairs.append(Pair(options=self.options,atoms=atids,parameters=' '))
                    # Shift the atom numbers
                    self.pairs[-1] += atid
                
                # All residue atoms
                counter = 0  # Counts over beads
                # Need to tweak this to get all the backbone beads to the list with the side chain
                bbbset = [bbMulti[count], bbMulti[count+1], bbMulti[count+2]]
                for atype,aname in zip(bbbset+list(scatoms),CoarseGrained.residue_bead_names_dna):
                    if self.multiscale:
                        atype,aname = "v"+atype,"v"+aname
                    #self.atoms.append((atid,atype,resi,resname,aname,atid,self.options['ForceField'].getCharge(atype,aname),ss))
                    if atid in [vSite.atoms[0] for vSite in self.vsites]:
                        #print 'in vsites', atid
                        charge = self.options['ForceField'].getCharge(atype,aname)
                        mass = 0
                        self.atoms.append((atid,atype,resi,resname,aname,atid,charge,mass,ss))
                        #print self.atoms[-1]
                    else:
                        charge = self.options['ForceField'].getCharge(atype,aname)
                        if aname == 'BB1':
                            mass = 72
                        # For virtual sites
                        #elif 'SC' in aname and (resname == 'DA' or resname == 'DG'):
                        #    mass = 60
                        else: 
                            mass = 45
                        self.atoms.append((atid,atype,resi,resname,aname,atid,charge,mass,ss))
                    # Doing this here saves going over all the atoms onesmore.
                    # Generate position restraints for all atoms or Backbone beads only.
                    if 'all' in self.options['PosRes']:
                        self.posres.append((atid)) 
                    elif aname in self.options['PosRes']:
                        self.posres.append((atid))
                    if mapping:
                        self.mapping.append((atid,[i+shift for i in mapping[counter]]))
                    atid    += 1
                    counter += 1
            count += 1

        # One more thing, we need to remove dihedrals (2) and an angle (1)  that reach beyond the 3' end
        # This is stupid to do now but the total number of atoms seems not to be available before
        # This iterate the list in reverse order so that removals don't affect later checks
        for i in range(len(self.dihedrals)-1,-1,-1):
            if (max(self.dihedrals[i].atoms) > self.atoms[-1][0]):
                del self.dihedrals[i]
        for i in range(len(self.angles)-1,-1,-1):
            if (max(self.angles[i].atoms) > self.atoms[-1][0]):
                del self.angles[i]

        # The first residue of DNA (The 5' end) has a backbone that is only two beads. This is ugly
        # but we'll save our headache of changing the whole internal logic. 
        for i in range(len(self.bonds)-1,-1,-1):
            if 1 in self.bonds[i].atoms:
                del self.bonds[i]
            else: 
                self.bonds[i].atoms = tuple([j-1 for j in self.bonds[i].atoms])
        for i in range(len(self.angles)-1,-1,-1):
            if 1 in self.angles[i].atoms:
                del self.angles[i]
            else: 
                self.angles[i].atoms = tuple([j-1 for j in self.angles[i].atoms])
        for i in range(len(self.dihedrals)-1,-1,-1):
            if 1 in self.dihedrals[i].atoms:
                del self.dihedrals[i]
            else: 
                self.dihedrals[i].atoms = tuple([j-1 for j in self.dihedrals[i].atoms])
        for i in range(len(self.vsites)-1,-1,-1):
            if 1 in self.vsites[i].atoms:
                del self.vsites[i]
            else: 
                self.vsites[i].atoms = tuple([j-1 for j in self.vsites[i].atoms])
        for i in range(len(self.exclusions)-1,-1,-1):
            if 1 in self.exclusions[i].atoms:
                del self.exclusions[i]
            else: 
                self.exclusions[i].atoms = tuple([j-1 for j in self.exclusions[i].atoms])
        for i in range(len(self.pairs)-1,-1,-1):
            if 1 in self.pairs[i].atoms:
                del self.pairs[i]
            else: 
                self.pairs[i].atoms = tuple([j-1 for j in self.pairs[i].atoms])

        # Remove the first bead and shift the numbers of all others by one.
        del self.atoms[0]
        for i in range(len(self.atoms)):
            self.atoms[i] = tuple([self.atoms[i][0]-1] + [j for j in self.atoms[i][1:]])
        enStrandLengths.append(self.atoms[-1][0])

        # Remove the last posres, faster than removing first and shifting all.
        if len(self.posres) > 0:
            del self.posres[-1]

        # The rubber bands are best applied outside of the chain class, as that gives
        # more control when chains need to be merged. The possibility to do it on the 
        # chain level is retained to allow building a complete chain topology in 
        # a straightforward manner after importing this script as module.
        if rubber and chain:
            rubberList = rubberBands(
                [(i[0],j[4:7]) for i,j in zip(self.atoms,chain.cg()) if i[4] in ElasticBeads],
                ElasticLowerBound,ElasticUpperBound,
                ElasticDecayFactor,ElasticDecayPower,
                ElasticMaximumForce,ElasticMinimumForce)
            #self.bonds.extend([Bond(i,options=self.options,type=6,category="Rubber band") for i in rubberList])


    def fromAminoAcidSequencePolBB(self,sequence,secstruc=None,links=None,breaks=None,
                              mapping=None,rubber=False,multi=False):

        # Shift for the atom numbers of the atomistic part in a chain 
        # that is being multiscaled
        shift = 0
        # First check if we get a sequence or a Chain instance
        if isinstance(sequence, Chain):
            chain         = sequence
            links         = chain.links
            breaks        = chain.breaks
            # If the mapping is not specified, the actual mapping is taken,
            # used to construct the coarse grained system from the atomistic one.
            # The function argument "mapping" could be used to use a default 
            # mapping scheme in stead, like the mapping for the GROMOS96 force field.
            mapping = mapping           or chain.mapping
            multi   = self.options['multi']  or chain.multiscale
            self.secstruc = chain.sstypes or len(chain)*"C"
            self.sequence = chain.sequence
            # If anything hints towards multiscaling, do multiscaling
            self.multiscale = self.multiscale or chain.multiscale or multi
            if self.multiscale:
                shift        = self.natoms
                self.natoms += len(chain.atoms())
        elif not secstruc:
            # If no secondary structure is provided, set all to coil
            chain         = None
            self.secstruc = len(self.sequence)*"C"
        else:
            # If a secondary structure is provided, use that. chain is none.
            chain         = None
            self.secstruc = secstruc

        logging.debug(self.secstruc)
        logging.debug(self.sequence)

        # Fetch the base information 
        # Pad with empty lists for atoms, bonds, angles 
        # and dihedrals, and take the first five lists out
        # This will avoid errors for residues for which 
        # these are not defined.

        sc = [(self.options['ForceField'].sidechains[res]+6*[[]])[:6] for res in self.sequence]

        # ID of the first atom/residue
        # The atom number and residue number follow from the last 
        # atom c.q. residue id in the list processed in the topology
        # thus far. In the case of multiscaling, the real atoms need 
        # also be accounted for.
        startAtom = self.natoms + 1 
        startResi = self.atoms and self.atoms[-1][2]+1 or 1

        # Backbone bead atom IDs
        # XXX Number of backbone beads hardcoded
        bbid = [[startAtom+i for i in range(4)]]
        for i in zip(*sc)[0]:
            bbid1 = bbid[-1][0]+len(i)+4
            bbid.append([bbid1+i for i in range(4)])
            #bbid.append(bbid[-1]+len(i)+1)

        # Residue numbers for this moleculetype topology
        resid = range(startResi,startResi+len(self.sequence))     

        # This contains the information for deriving backbone bead types,
        # bb bond types, bbb/bbs angle types, and bbbb dihedral types.
        seqss = zip(bbid,self.sequence,self.secstruc)
        # The last residue only has a Calpha in the BB and no dipole.
        seqss[-1] = (seqss[-1][0][:1],)+seqss[-1][1:]

        # Fetch the proper backbone beads          
        # Since there are  N beads we need to split these to the list
        bb = [self.options['ForceField'].bbGetBead(res,typ) for num,res,typ in seqss]
        # bbGetBead always returns all the BB-beads. For the last residue to get out
        # only the last we preprocess it together with seqss (which does have the right length).
        bbMulti = [beadname for residue,beads in zip(seqss,bb) for atomid,beadname in zip(residue[0],beads)]

        # This is going to be usefull for the type of the last backbone bead.
        # If termini need to be charged, change the bead types
        #if not self.options['NeutralTermini']:
        #    bb[0]  ="Qd"
        #    bb[-1] = "Qa"

        # If breaks need to be charged, change the bead types 
        #if self.options['ChargesAtBreaks']:
        #    for i in breaks:
        #        bb[i]   = "Qd"
        #        bb[i-1] = "Qa"

        # For backbone parameters, iterate over fragments, inferred from breaks
        for i,j in zip([0]+breaks,breaks+[-1]):
            # Extract the fragment
            frg = j==-1 and seqss[i:] or seqss[i:j]
            # Expand the N bb beads per residue into one long list
            # Resulting list contains three tuples per residue 
            # We use the useless ca parameter to get the correct backbone bond from bbGetBond 
            frg = [(j[0][i],j[1],j[2],j[0][i]-1) for j in frg for i in range(len(j[0]))]

            # Iterate over backbone bonds, two loops are needed because there are multipe cross bonds in the BB.
            # Since bonded interactions can return None, we first collect them separately and then
            # add the non-None ones to the list
            # Number of backbone beads hardcoded to 4
            for ind,k in enumerate(frg):
                # Virtual site and exclusions we check per bead
                vsite = Vsite((k,),category="BB",options=self.options,)
                if vsite:
                     self.vsites.append(vsite)
                excl = Exclusion((k,),category="BB",options=self.options,)
                if excl and max(excl.parameters) <= len(bbMulti):
                    self.exclusions.append(excl)
                
                # Bonds and pairs interate over the second atom.
                for l in frg[ind:ind+9]:
                    bond = Bond((k,l),category="BB",options=self.options,)
                    if bond:
                        self.bonds.append(bond)
                    pair = Pair((k,l),category="BB",options=self.options,type=2,)
                    if pair:
                        self.pairs.append(pair)

                    # The angles need a third loop.
                    for m in frg[ind:ind+9]:
                        angle = Angle((k,l,m,),options=self.options,category="BBB")
                        if angle:
                            self.angles.append(angle)

                        # The dihedrals need a fourth loop.
                        for n in frg[ind:ind+9]:
                            dihed = Dihedral((k,l,m,n,),options=self.options,category="BBBB")
                            if dihed:
                                self.dihedrals.append(dihed)

        # Now do the atom list, and take the sidechains along
        #
        atid  = startAtom
        # We need to do some trickery to get all N bb beads in to these lists
        # This adds each element to a list three times, feel free to shorten up
        residMulti = [res for i,res in enumerate(resid) for j in range(len(bb[i]))]
        sequenceMulti = [resname for i,resname in enumerate(self.sequence) for j in range(len(bb[i]))]
        # Would it be easier to only give a sidechain for the beads that connect to one (ie the first)?
        scMulti = [sidechain for i,sidechain in enumerate(sc) for j in range(len(bb[i]))]
        secstrucMulti = [secstruc for i,secstruc in enumerate(self.secstruc) for j in range(len(bb[i]))]
        count = 0
        for resi,resname,bbb,sidechn,ss in zip(residMulti,sequenceMulti,bbMulti,scMulti,secstrucMulti):
            # We only want one side chain per three backbone beads so this skips the others
            if (count % len(bb[0])) == 0:    
                # Note added impropers in contrast to aa
                scatoms, bon_par, ang_par, dih_par, imp_par, vsite_par = sidechn

                # Side chain bonded terms
                # Collect bond, angle and dihedral connectivity
                bon_con,ang_con,dih_con,imp_con,vsite_con = (self.options['ForceField'].connectivity[resname]+5*[[]])[:5]

                # Side Chain Bonds/Constraints
                for atids,par in zip(bon_con,bon_par):
                    if par[1] == None:
                        self.bonds.append(Bond(options=self.options,atoms=atids,parameters=[par[0]],type=1,
                                               comments=resname,category="Constraint"))
                    else:
                        self.bonds.append(Bond(options=self.options,atoms=atids,parameters=par,type=1,
                                               comments=resname,category="SC"))
                    # Shift the atom numbers
                    self.bonds[-1] += atid

                # Side Chain Angles
                for atids,par in zip(ang_con,ang_par):
                    self.angles.append(Angle(options=self.options,atoms=atids,parameters=par,type=2,
                                             comments=resname,category="SC"))
                    # Shift the atom numbers
                    self.angles[-1] += atid

                # Side Chain Dihedrals
                for atids,par in zip(dih_con,dih_par):
                    self.dihedrals.append(Dihedral(options=self.options,atoms=atids,parameters=par,type=2,
                                                   comments=resname,category="SC"))
                    # Shift the atom numbers
                    self.dihedrals[-1] += atid

                # Side Chain Impropers
                for atids,par in zip(imp_con,imp_par):
                    self.dihedrals.append(Dihedral(options=self.options,atoms=atids,parameters=par,type=2,
                                                   comments=resname,category="SC"))
                    # Shift the atom numbers
                    self.dihedrals[-1] += atid

                # Side Chain V-Sites
                for atids,par in zip(vsite_con,vsite_par):
                    self.vsites.append(Vsite(options=self.options,atoms=atids,parameters=par,type=1,
                                                   comments=resname,category="SC"))
                    # Shift the atom numbers
                    self.vsites[-1] += atid
            
                # Side Chain exclusions
                # The new polarizable forcefield give problems with the charges in the sidechain, if the backbone is also charged.
                # To avoid that, we add explicit exclusions
                if bbb in self.options['ForceField'].charges.keys() and resname in self.options['ForceField'].mass_charge.keys():
                    for i in [i for i, d in enumerate(scatoms) if d=='D']:
                        self.exclusions.append(Exclusion(options=self.options,atoms=(atid,i+atid+1),comments='%s(%s)'%(resname,resi),parameters=(None,)))

                # All residue atoms
                counter = 0  # Counts over beads
                # Count it the current backbone bead. bbb is the current backbone residue
                bbbset = [bbMulti[count+i] for i in range(len(seqss[resi-1][0]))]
                aNames = CoarseGrained.residue_bead_names_polBB[1:4]+CoarseGrained.residue_bead_names_polBB[:1]+CoarseGrained.residue_bead_names_polBB[4:]
                for atype,aname in zip(bbbset+list(scatoms),aNames):
                    if self.multiscale:
                        atype,aname = "v"+atype,"v"+aname
                    # If mass or charge diverse, we adopt it here. 
                    # We don't want to do this for BB beads because of charged termini.
                    if resname in self.options['ForceField'].mass_charge.keys() and counter != 0:
                        logging.error('Polarizable backbones and sidechains are not yet compatible.')
                        sys.exit()
                        M,Q = self.options['ForceField'].mass_charge[resname]
                        aname = Q[counter-1]>0 and 'SCP' or Q[counter-1]<0 and 'SCN' or aname
                        self.atoms.append((atid,atype,resi,resname,aname,atid,Q[counter-1],M[counter-1],ss))
                    elif atid in [vSite.atoms[0] for vSite in self.vsites]:
                        charge = self.options['ForceField'].getCharge(atype,aname)
                        mass = 0
                        self.atoms.append((atid,atype,resi,resname,aname,atid,charge,mass,ss))
                    else:
                        charge = self.options['ForceField'].getCharge(atype,aname)
                        self.atoms.append((atid,atype,resi,resname,aname,atid,charge,ss))
                    # Doing this here save going over all the atoms onesmore.
                    # Generate position restraints for all atoms or Backbone beads only.
                    if 'all' in self.options['PosRes']:
                        self.posres.append((atid)) 
                    elif aname in self.options['PosRes']:
                        self.posres.append((atid))
                    if mapping:
                        self.mapping.append((atid,[i+shift for i in mapping[counter]]))
                    atid    += 1
                    counter += 1
            count += 1

#        # One more thing, we need to remove dihedrals (2) and an angle (1)  that reach beyond the 3' end
#        # This is stupid to do now but the total number of atoms seems not to be available before
#        # This iterate the list in reverse order so that removals don't affect later checks
#        for i in range(len(self.dihedrals)-1,-1,-1):
#            if (max(self.dihedrals[i].atoms) > self.atoms[-1][0]):
#                del self.dihedrals[i]
#        for i in range(len(self.angles)-1,-1,-1):
#            if (max(self.angles[i].atoms) > self.atoms[-1][0]):
#                del self.angles[i]


    def fromMoleculeList(self,other):
        pass

#############
## 8 # MAIN #  -> @MAIN <-
#############
import sys,logging,random,math,os,re

def main(options):
    # Check whether to read from a gro/pdb file or from stdin
    # We use an iterator to wrap around the stream to allow
    # inferring the file type, without consuming lines already
    inStream = streamTag(options["-f"] and options["-f"].value or sys.stdin)
    

    # The streamTag iterator first yields the file type, which 
    # is used to specify the function for reading frames
    fileType = inStream.next()
    if fileType == "GRO":
        frameIterator = groFrameIterator
    else:
        frameIterator = pdbFrameIterator
    

    ## ITERATE OVER FRAMES IN STRUCTURE FILE ##

    # Now iterate over the frames in the stream
    # This should become a StructureFile class with a nice .next method
    model     = 1
    cgOutPDB  = None
    ssTotal   = []
    cysteines = []
    for title,atoms,box in frameIterator(inStream):
    
        if fileType == "PDB":
            # The PDB file can have chains, in which case we list and process them specifically
            # TER statements are also interpreted as chain separators
            # A chain may have breaks in which case the breaking residues are flagged
            chains = [ Chain(options,[i for i in residues(chain)]) for chain in pdbChains(atoms) ]        
        else:
            # The GRO file does not define chains. Here breaks in the backbone are
            # interpreted as chain separators. 
            residuelist = [residue for residue in residues(atoms)]
            # The breaks are indices to residues
            broken = breaks(residuelist)
            # Reorder, such that each chain is specified with (i,j,k)
            # where i and j are the start and end of the chain, and 
            # k is a chain identifier
            chains = zip([0]+broken,broken+[len(residuelist)],range(len(broken)+1))
            chains = [ Chain(options,residuelist[i:j],name=chr(65+k)) for i,j,k in chains ]
    
        for chain in chains:
            chain.multiscale = "all" in options['multi'] or chain.id in options['multi']
    
        # Check the chain identifiers
        if model == 1 and len(chains) != len(set([i.id for i in chains])):
            # Ending down here means that non-consecutive blocks of atoms in the 
            # PDB file have the same chain ID. The warning pertains to PDB files only, 
            # since chains from GRO files get a unique chain identifier assigned.
            logging.warning("Several chains have identical chain identifiers in the PDB file.")
    
        # Check if chains are of mixed type. If so, split them.
        # Note that in some cases HETATM residues are part of a 
        # chain. This will get problematic. But we cannot cover
        # all, probably.
        if not options['MixedChains']:
            demixedChains = []
            for chain in chains:
                demixedChains.extend(chain.split())
            chains = demixedChains
    
        n = 1
        logging.info("Found %d chains:"%len(chains))
        for chain in chains:
            logging.info("  %2d:   %s (%s), %d atoms in %d residues."%(n,chain.id,chain._type,chain.natoms,len(chain)))
            n += 1
    
        # Check all chains
        keep = []
        for chain in chains:
            if chain.type() == "Water":
                logging.info("Removing %d water molecules (chain %s)."%(len(chain),chain.id))
            elif chain.type() in ("Protein","Nucleic"):
                keep.append(chain)
            # This is currently not active:
            elif options['RetainHETATM']:
                keep.append(chain)
            else:
                logging.info("Removing HETATM chain %s consisting of %d residues."%(chain.id,len(chain)))
        chains = keep

        # Here we interactively check the charge state of resides
        # Can be easily expanded to residues other than HIS
        for chain in chains:
            for i,resname in enumerate(chain.sequence):
                 if resname == 'HIS' and options['chHIS']:
                     choices = {0:'HIH',1:'HIS'}
                     choice = getChargeType(resname,i,choices)
                     chain.sequence[i] = choice

    

        # Check which chains need merging
        if model == 1:
            order, merge = check_merge(chains, options['mergeList'], options['linkList'], options['CystineCheckBonds'] and options['CystineMaxDist2'])
    

        # Get the total length of the sequence
        seqlength = sum([len(chain) for chain in chains])
        logging.info('Total size of the system: %s residues.'%seqlength)
    

        ## SECONDARY STRUCTURE
        ss = '' 
        if options['Collagen']:
            for chain in chains:
                chain.set_ss("F")
                ss += chain.ss
        elif options["-ss"]:
            # XXX We need error-catching here, 
            # in case the file doesn't excist, or the string contains bogus.
            # If the string given for the sequence consists strictly of upper case letters
            # and does not appear to be a file, assume it is the secondary structure
            ss = options["-ss"].value.replace('~','L').replace(' ','L')
            if ss.isalnum() and ss.isupper() and not os.path.exists(options["-ss"].value):
                ss = options["-ss"].value
                logging.info('Secondary structure read from command-line:\n'+ss)
            else:
                # There ought to be a file with the name specified
                ssfile = [ i.strip() for i in open(options["-ss"].value) ]
        
                # Try to read the file as a Gromacs Secondary Structure Dump
                # Those have an integer as first line
                if ssfile[0].isdigit():
                    logging.info('Will read secondary structure from file (assuming Gromacs ssdump).')
                    ss = "".join([ i for i in ssfile[1:] ])
                else:
                    # Get the secondary structure type from DSSP output
                    logging.info('Will read secondary structure from file (assuming DSSP output).')
                    pss = re.compile(r"^([ 0-9]{4}[0-9]){2}")
                    ss  = "".join([i[16] for i in open(options["-ss"].value) if re.match(pss,i)])        
            
            # Now set the secondary structure for each of the chains
            sstmp = ss
            for chain in chains:
                ln = min(len(sstmp),len(chain)) 
                chain.set_ss(sstmp[:ln])
                sstmp = ss[:ln]                         
        else:
            if options["-dssp"]:
                method, executable = "dssp", options["-dssp"].value
            #elif options["-pymol"]:
            #    method, executable = "pymol", options["-pymol"].value
            else:
                logging.warning("No secondary structure or determination method speficied. Protein chains will be set to 'COIL'.")
                method, executable = None, None
        
            for chain in chains:
                ss += chain.dss(method, executable)
        
            # Used to be: if method in ("dssp","pymol"): but pymol is not supported
            if method in ["dssp"]:
                logging.debug('%s determined secondary structure:\n'%method.upper()+ss)
        
        # Collect the secondary structure classifications for different frames
        ssTotal.append(ss)    
    
        # Write the coarse grained structure if requested
        if options["-x"].value:
            logging.info("Writing coarse grained structure.")
            if cgOutPDB == None:
                cgOutPDB = open(options["-x"].value,"w")
            cgOutPDB.write("MODEL %8d\n"%model)
            cgOutPDB.write(title)
            cgOutPDB.write(pdbBoxString(box))
            atid = 1
            write_start = 0
            for i in order:
                ci = chains[i]
                if ci.multiscale:
                    for r in ci.residues:
                        for name,resn,resi,chain,x,y,z in r:
                            insc  = resi>>20
                            resi -= insc<<20
                            cgOutPDB.write(pdbAtomLine%(atid,name,resn[:3],chain,resi,chr(insc),x,y,z,1,0))
                            atid += 1
                coarseGrained = ci.cg(com=True)
                if coarseGrained:
                    # For DNA we need to remove the first bead on the 5' end and shift the atids. 
                    if ci.type() == 'Nucleic':
                        write_start = 1
                    else:
                        write_start = 0
                    for name,resn,resi,chain,x,y,z,ssid in coarseGrained[write_start:]:
                        insc  = resi>>20
                        resi -= insc<<20
                        if ci.multiscale:
                            name = "v"+name
                        cgOutPDB.write(pdbAtomLine%(atid,name,resn[:3],chain,resi,chr(insc),x,y,z,1,ssid))
                        atid += 1 
                    cgOutPDB.write("TER\n")          
                else:
                    logging.warning("No mapping for coarse graining chain %s (%s); chain is skipped."%(ci.id,ci.type()))
            cgOutPDB.write("ENDMDL\n")
    
        # Gather cysteine sulphur coordinates
        cyslist = [cys["SG"] for chain in chains for cys in chain["CYS"]]
        cysteines.append([cys for cys in cyslist if cys])
    
        model += 1
    
    
    # Write the index file if requested.
    # Mainly of interest for multiscaling.
    # Could be improved by adding separte groups for BB, SC, etc.
    if options["-n"].value:
        logging.info("Writing index file.")
        # Lists for All-atom, Virtual sites and Coarse Grain.
        NAA,NVZ,NCG = [],[],[]
        atid = 1
        for i in order:
            ci = chains[i]
            coarseGrained = ci.cg(force=True)
            if ci.multiscale:
                NAA.extend([" %5d"%(a+atid) for a in range(ci.natoms)]) 
                atid += ci.natoms
            if coarseGrained:
                # For DNA there is not first bead on 5' end and thus one bead less.
                if ci.type() == 'Nucleic':
                    if ci.multiscale:
                        NVZ.extend([" %5d"%(a+atid) for a in range(len(coarseGrained)-1)])
                    else:
                        NCG.extend([" %5d"%(a+atid) for a in range(len(coarseGrained)-1)])
                    atid += len(coarseGrained)-1               
                else:
                    if ci.multiscale:
                        NVZ.extend([" %5d"%(a+atid) for a in range(len(coarseGrained))])
                    else:
                        NCG.extend([" %5d"%(a+atid) for a in range(len(coarseGrained))])
                    atid += len(coarseGrained)               
        outNDX   = open(options["-n"].value,"w")
        outNDX.write("\n[ AA ]\n"+"\n".join([" ".join(NAA[i:i+15]) for i in range(0,len(NAA),15)]))
        outNDX.write("\n[ VZ ]\n"+"\n".join([" ".join(NVZ[i:i+15]) for i in range(0,len(NVZ),15)]))
        outNDX.write("\n[ CG ]\n"+"\n".join([" ".join(NCG[i:i+15]) for i in range(0,len(NCG),15)]))
        outNDX.close()

    
    # Write the index file for mapping AA trajectory if requested
    if options["-nmap"].value:
        logging.info("Writing trajectory index file.")
        atid = 1
        outNDX = open(options["-nmap"].value,"w")
        # Write the list of bead numbers for mapping AA trajectories
        if options["-seq"].value:
            logging.info("Writing bead number list.")
            outSEQ = open(options["-seq"].value,"w")
            counter = 0
        # Get all AA atoms as lists of atoms in residues
        # First we skip hetatoms and unknowns then iterate over beads
        # DNA requires some modifications for 5' end and O3' atoms, variables for that.
        current_chain = 0
        ci = chains[current_chain]
        atom_limit = ci.natoms
        chain_residue = 0
        o3_shift = ''
        for i_count, i in enumerate(residues(atoms)):
            if i[0][1] in ("SOL","HOH","TIP"):
                continue
            if not i[0][1] in CoarseGrained.mapping.keys():
                continue
            nra = 0
            names = [j[0] for j in i]
            shift = 0
            # This gives out a list of atoms in residue, each tuple has other 
            # stuff in it that's needed elsewhere so we just take the last 
            # element which is the atom index (in that residue)
            for j_count, j in enumerate(mapIndex(i)):
                if atid == atom_limit + 1:
                    current_chain += 1
                    ci = chains[current_chain]
                    atom_limit += ci.natoms
                    chain_residue = 0
                # In DNA the first bead of 5' end is omitted, this checks for that.
                # Also, the O3' atom is mapped together with atoms from the next residue.
                # This stores it until we get to the next residue.
                if ci.type() == 'Nucleic' and chain_residue == 0:
                    if j_count == 0:
                        for k in j:
                            if names[k[2]] == "O3'":
                                o3_shift = k[2]+atid
                            if k[2] > shift:
                                shift = k[2]
                    # On the first residue of chain the bead numbers are shifted down by one.
                    else:
                        outNDX.write('[ Bead %i of residue %i ]\n'%(j_count,i_count+1))
                        line = ''
                        for k in j:
                            if names[k[2]] == "O3'":
                                line += '%s '%(str(o3_shift)) 
                                o3_shift = k[2]+atid
                            else:
                                line += '%i '%(k[2]+atid) 
                            if k[2] > shift:
                                shift = k[2]
                        line += '\n'
                        outNDX.write(line)
                        if options["-seq"].value:
                            outSEQ.write(str(counter) + '\n')
                            counter += 1
                # For all DNA residues the O3' atoms need to be put on the next residue.
                elif ci.type() == 'Nucleic':
                    outNDX.write('[ Bead %i of residue %i ]\n'%(j_count+1,i_count+1))
                    line = ''
                    for k in j:
                        if names[k[2]] == "O3'":
                            line += '%s '%(str(o3_shift)) 
                            o3_shift = k[2]+atid
                        else:
                            line += '%i '%(k[2]+atid) 
                        if k[2] > shift:
                            shift = k[2]
                    line += '\n'
                    outNDX.write(line)
                    if options["-seq"].value:
                        outSEQ.write(str(counter) + '\n')
                        counter += 1
                # Other types behave normally.
                else:
                    outNDX.write('[ Bead %i of residue %i ]\n'%(j_count+1,i_count+1))
                    line = ''
                    for k in j:
                        line += '%i '%(k[2]+atid) 
                    line += '\n'
                    outNDX.write(line)
                    if options["-seq"].value:
                        outSEQ.write(str(counter) + '\n')
                        counter += 1
            atid += shift+1
            chain_residue += 1
        outNDX.close()
        if options["-seq"].value:
            outSEQ.close()

    
    # Evertything below here we only need, if we need to write a Topology
    if options['-o']:

        # Collect the secondary structure stuff and decide what to do with it
        # First rearrange by the residue
        ssTotal = zip(*ssTotal)
        ssAver  = []
        for i in ssTotal:
            si = list(set(i))
            if len(si) == 1:
                # Only one type -- consensus
                ssAver.append(si[0])
            else:
                # Transitions between secondary structure types
                i = list(i)
                si = [(1.0*i.count(j)/len(i),j) for j in si]
                si.sort()
                if si[-1][0] > options["-ssc"].value:
                    ssAver.append(si[-1][1])
                else:
                    ssAver.append(" ")
        
        ssAver = "".join(ssAver)
        logging.info('(Average) Secondary structure has been determined (see head of .itp-file).')
        

        # Divide the secondary structure according to the division in chains
        # This will set the secondary structure types to be used for the 
        # topology.
        for chain in chains:
            chain.set_ss(ssAver[:len(chain)])
            ssAver = ssAver[len(chain):]

        
        # Now the chains are complete, each consisting of a residuelist, 
        # and a secondary structure designation if the chain is of type 'Protein'.
        # There may be mixed chains, there may be HETATM things. 
        # Water has been discarded. Maybe this has to be changed at some point.
        # The order in the coarse grained files matches the order in the set of chains.
        #
        # If there are no merges to be done, i.e. no global Elnedyn network, no 
        # disulphide bridges, no links, no distance restraints and no explicit merges,
        # then we can write out the topology, which will match the coarse grained file.
        #
        # If there are merges to be done, the order of things may be changed, in which
        # case the coarse grained structure will not match with the topology...
        
        ## CYSTINE BRIDGES ##
        # Extract the cysteine coordinates (for all frames) and the cysteine identifiers
        if options['CystineCheckBonds']:
            logging.info("Checking for cystine bridges, based on sulphur (SG) atoms lying closer than %.4f nm"%math.sqrt(options['CystineMaxDist2']/100))
        
            cyscoord  = zip(*[[j[4:7] for j in i] for i in cysteines])
            cysteines = [i[:4] for i in cysteines[0]]
        
            bl, kb    = options['ForceField'].special[(("SC1","CYS"),("SC1","CYS"))]
        
            # Check the distances and add the cysteines to the link list if the 
            # SG atoms have a distance smaller than the cutoff.
            rlc = range(len(cysteines))
            for i in rlc[:-1]:
                for j in rlc[i+1:]:
                    # Checking the minimum distance over all frames
                    # But we could also take the maximum, or the mean
                    d2 = min([distance2(a,b) for a,b in zip(cyscoord[i],cyscoord[j])])
                    if d2 <= options['CystineMaxDist2']:
                        a, b = cysteines[i], cysteines[j]
                        options['linkListCG'].append((("SC1","CYS",a[2],a[3]),("SC1","CYS",b[2]-(32<<20),b[3]),bl,kb))
                        a,b = (a[0],a[1],a[2]-(32<<20),a[3]),(b[0],b[1],b[2]-(32<<20),b[3])
                        logging.info("Detected SS bridge between %s and %s (%f nm)"%(a,b,math.sqrt(d2)/10))
        
        
        ## REAL ITP STUFF ##
        # Check whether we have identical chains, in which case we 
        # only write the ITP for one...
        # This means making a distinction between chains and 
        # moleculetypes.
        
        molecules = [tuple([chains[i] for i in j]) for j in merge]
        
        # At this point we should have a list or dictionary of chains
        # Each chain should be given a unique name, based on the value
        # of options["-o"] combined with the chain identifier and possibly
        # a number if there are chains with identical identifiers.
        # For each chain we then write an ITP file using the name for 
        # moleculetype and name + ".itp" for the topology include file.
        # In addition we write a master topology file, using the value of
        # options["-o"], with an added extension ".top" if not given.
        
        # XXX *NOTE*: This should probably be gathered in a 'Universe' class
        itp = 0
        moleculeTypes = {}
        cumulative_atoms = 0
        for mi in range(len(molecules)):
            mol = molecules[mi]
            # Check if the moleculetype is already listed
            # If not, generate the topology from the chain definition
            if not mol in moleculeTypes or options['SeparateTop']:
                # Name of the moleculetype
                # NOTE: The naming should be changed; now it becomes Protein_X+Protein_Y+...
                name = "+".join([chain.getname(options['-name'].value) for chain in mol])
                moleculeTypes[mol] = name
    
                # Write the molecule type topology
                top = Topology(mol[0],options=options,name=name)
                # This merges topologies, properties how adding happens in Topology method __iadd__
                for m in mol[1:]:
                    top += Topology(m,options=options)
    
                # Have to add the connections, like the connecting network
                # Gather coordinates
                mcg, coords = zip(*[(j[:4],j[4:7]) for m in mol for j in m.cg(force=True)])
                mcg         = list(mcg)
        
                # Run through the link list and add connections (links = cys bridges or hand specified links)
                for atomA,atomB,bondlength,forceconst in options['linkListCG']:
                    if bondlength == -1 and forceconst == -1:
                        bondlength, forceconst = options['ForceField'].special[(atomA[:2],atomB[:2])]
                    # Check whether this link applies to this group
                    atomA = atomA in mcg and mcg.index(atomA)+1
                    atomB = atomB in mcg and mcg.index(atomB)+1
                    if atomA and atomB:
                        cat = (mcg[atomA][1] == "CYS" and mcg[atomB][1] == "CYS") and "Cystine" or "Link"
                        top.bonds.append(Bond((atomA,atomB),options=options,type=1,parameters=(bondlength,forceconst),category=cat))
        
                # Elastic Network
                # The elastic network is added after the topology is constructed, since that
                # is where the correct atom list with numbering and the full set of 
                # coordinates for the merged chains are available. 
                # For Nucleic have to watch out for the missing first bead again.
                # THIS IS BANDAID FOR NOW, ONLY WORKS FOR TWO CHAINS
                if name.split('_')[0] == 'Nucleic':
                    strands = len(enStrandLengths)
                    cuts = [enStrandLengths[0]+1]
                    nucleic_coords = coords[1:cuts[0]]
                    if strands != 1:
                        for i in range(1,strands):
                            cuts.append(cuts[-1]+enStrandLengths[i]+1)
                        for i in range(1,strands):
                            nucleic_coords += coords[cuts[i-1]+1:cuts[i]]
                    if options['ElasticNetwork']:
                        #print options['ElasticBeads']
                        #print top.atoms[0]
                        rubberType = options['ForceField'].EBondType
                        rubberList = rubberBands(
                            [(i[0],j) for i,j in zip(top.atoms,nucleic_coords) if i[4] in         options['ElasticBeads']],
                            options['ElasticLowerBound'],options['ElasticUpperBound'],
                            options['ElasticDecayFactor'],options['ElasticDecayPower'],
                            options['ElasticMaximumForce'],options['ElasticMinimumForce'])
                        top.bonds.extend([Bond(i,options=options,type=rubberType,category="Rubber band") for i in rubberList])
                else:
                    if options['ElasticNetwork']:
                        print (options['ElasticBeads'])
                        print (top.atoms[0])
                        rubberType = options['ForceField'].EBondType
                        rubberList = rubberBands(
                            [(i[0],j) for i,j in zip(top.atoms,coords) if i[4] in options['ElasticBeads']],
                            options['ElasticLowerBound'],options['ElasticUpperBound'],
                            options['ElasticDecayFactor'],options['ElasticDecayPower'],
                            options['ElasticMaximumForce'],options['ElasticMinimumForce'])
                        top.bonds.extend([Bond(i,options=options,type=rubberType,category="Rubber band") for i in rubberList])
    
                # Write out the MoleculeType topology
                destination = options["-o"] and open(moleculeTypes[mol]+".itp",'w') or sys.stdout
                destination.write(str(top))        

                # If index files for parameterization are needed, print them here
                # This will write out separate index files for bonds, angles and dihedrals
                if options["-bmap"].value:
                    logging.info("Writing index file for bonded terms.")
                    b_out, a_out, d_out = top.ndx(cumulative_atoms)
                    # Make sure old files are overwritten
                    if cumulative_atoms == 0:
                        outB = open(options["-bmap"].value+'-bonds.ndx',"w")
                        outA = open(options["-bmap"].value+'-angles.ndx',"w")
                        outD = open(options["-bmap"].value+'-dihedrals.ndx',"w")
                    else:
                        outB = open(options["-bmap"].value+'-bonds.ndx',"a")
                        outA = open(options["-bmap"].value+'-angles.ndx',"a")
                        outD = open(options["-bmap"].value+'-dihedrals.ndx',"a")
                    outB.write(b_out); outA.write(a_out); outD.write(d_out)
                    outB.close(); outA.close(); outD.close()
        
                itp += 1
        
            # Check whether other chains are equal to this one 
            # Skip this step if we are to write all chains to separate moleculetypes
            if not options['SeparateTop']:
                for j in range(mi+1,len(molecules)):
                    if not molecules[j] in moleculeTypes and mol == molecules[j]:
                        # Molecule j is equal to a molecule mi
                        # Set the name of the moleculetype to the one of that molecule
                        moleculeTypes[molecules[j]] = moleculeTypes[mol]

            # For the parameterization index files we need to update the cumulative number of atoms.
            # For parameterization option SepareteTop should always be used because otherwise the numbering will fail.
            cumulative_atoms += len(top.atoms)
        
        logging.info('Written %d ITP file%s'%(itp,itp>1 and "s" or ""))
                
        # WRITING THE MASTER TOPOLOGY
        # Output stream
        top  = options["-o"] and open(options['-o'].value,'w') or sys.stdout
        
        # ITP file listing
        itps = '\n'.join(['#include "%s.itp"'%molecule for molecule in set(moleculeTypes.values())])
        
        # Molecule listing
        logging.info("Output contains %d molecules:"%len(molecules))
        n = 1
        for molecule in molecules:
            chainInfo = (n, moleculeTypes[molecule], len(molecule)>1 and "s" or " ", " ".join([i.id for i in molecule]))
            logging.info("  %2d->  %s (chain%s %s)"%chainInfo)
            n += 1
        molecules   = '\n'.join(['%s \t 1'%moleculeTypes[molecule] for molecule in molecules])
        
        # Set a define if we are to use rubber bands
        useRubber   = options['ElasticNetwork'] and "#define RUBBER_BANDS" or ""
       
        # XXX Specify a better, version specific base-itp name.
        # Do not set a define for position restrains here, as people are more used to do it in mdp file?
        top.write(
'''#include "martini.itp"
    
%s
  
%s
    
[ system ]
; name
Martini system from %s
    
[ molecules ]
; name        number
%s''' % (useRubber, itps, options["-f"] and options["-f"].value or "stdin", molecules))
    
        logging.info('Written topology files')
    
    # Maybe there are forcefield specific log messages?
    options['ForceField'].messages()

    # The following lines are always printed (if no errors occur).
    print ("\n\tThere you are. One MARTINI. Shaken, not stirred.\n")
    Q = martiniq.pop(random.randint(0,len(martiniq)-1))
    print ("\n", Q[1], "\n%80s"%("--"+Q[0]), "\n")
if __name__ == '__main__':
    import sys,logging
    args = sys.argv[1:]
    if '-cat' in args:
        cat('martinize-'+version+'.py')
        sys.exit()
    options,lists = options,lists
    options = option_parser(args,options,lists,version)

    main(options)
