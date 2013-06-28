Dryad-SA
========

Dryad is designed as an easy to use approach to find putative homologs from a
list of whole genome sequences and format them for use in tree building programs
like phyml, fasttree, phylip etc. 

Dependencies include: 
* BLAST+
* MUSCLE
* Biopython
* PhyML (Optional)
Be sure these are installed and on your path. 

Dryad requires two inputs:
    A Multi-FASTA file of reference gene sequences (amino acid or nucleotide)
    A text file listing locations of genomes you want to include in your tree
See USAGE for optional parameters.

Dryad is typically used like this:

    python Dryad.py -gmc Reference_genes.fna filelist.txt 

Where filelist.txt is a plain text file with a list of locations of GenBank 
files, e.g:

    gen/CU928158.gbk
    gen/CP000243.gbk
    gen/AE005174.gbk

The '-g' flag is used because these files are GenBank format, rather than 
FASTA.

Reference_gene.fna is a multi-FASTA file with gene sequences.
e.g:
    
    >arcA
    ATG.....
    >aroE
    ATG....
        etc.

Dryad will automatically detect if this file has amino acids and nucleotide
sequences. DO NOT mix aa and nucl sequences in the same reference file.

The script runs BLAST to find putative homologs of each reference gene in the
specified genomes. All the homologs for a particular reference gene are 
formatted into a multi-FASTA file, which can be aligned and used for invidual
gene trees. 

If the user has specified the '-mc' flags, Dryad will align each gene family
using MUSCLE and concatenate them into a single alignment. 
This can be used as to generate a concatenated gene tree. 

If the user has used the snps option ('-n') Dryad will further process the 
alignment produce an multiple sequence alignment that only includes SNPs. 
Regions with gaps or have no informative sites are stripped out. This improves
runtime for trees based on a large number of genes.

Run the worked example 'Dryad-Example.py' to see the script's output.


WORKED EXAMPLE
==============
The runex directory has a test case to check if Dryad is running correctly.

Dryad-Example.py is a quick example test of the Dryad script.
Just run 'python Dryad-Example.py -v'. 

It requires reference genes and remote file list. (Default: all_mlst.fna
and GB-loc in runex dir).

Dependencies include: 
* BLAST+
* MUSCLE
* Biopython
Be sure these are installed and on your path. 

This script runs an example case for the Dryad script, based off 12 EcMLST 
genes (all_mlst.fna) and 11 E. coli genomes (& E. fergusonii as an outgroup) 
downloaded from a remote server (listed in GB-loc).

This script should be run from the runex folder in the parent Dryad-SA dir.
This script will check Dependencies, format input files, and run Dryad.

Dryad output will include:
* EXAMPLEpresence.csv (a presence/absence table of reference genes)
* EXAMPLEtable.csv (a summary of all BLAST results)
* EXAMPLEall.phy (gene families concatenated together, ready for your 
    favourite tree builder.)

To produce a tree from this output, you can use phyml and figtree.
i.e RUN:
    phyml -i EXAMPLEall.phy
    figtree EXAMPLEall.phy_phyml_tree.txt

Your tree should look something like FinalTree.pdf in the runex folder.

Total Runtime: ~20 minutes. 


LICENCE
=======
Nabil-Fareed Alikhan <n.alikhan@uq.edu.au>. (C) 2012-2013.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
