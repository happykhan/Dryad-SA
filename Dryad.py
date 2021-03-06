#!/usr/bin/env python
"""
# Created: Tue, 10 Jan 2012 11:57:35 +1000

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

### CHANGE LOG ### 
2013-03-18 Nabil-Fareed Alikhan <n.alikhan@uq.edu.au>
    * v0.3: Formatted stand-alone version
"""
import sys
import os
import traceback
import optparse
import time
import re
from Bio.Blast.Applications import NcbiblastxCommandline
from Bio.Blast.Applications import NcbiblastnCommandline
from Bio.Blast.Applications import NcbiblastpCommandline
from Bio.Blast import NCBIXML
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio import SeqIO
from Bio.Alphabet import generic_protein, generic_dna
from Bio import Phylo
from Bio.Phylo.Applications import PhymlCommandline
from Bio import AlignIO
from Bio.Align.Applications import MuscleCommandline
from Bio.Align import MultipleSeqAlignment
import subprocess

#from pexpect import run, spawn
__author__ = "Nabil-Fareed Alikhan"
__licence__ = "GPLv3"
__version__ = "0.3"
__email__ = "n.alikhan@uq.edu.au"
epi = "Licence: " + __licence__ + " by " + __author__ + " <" + __email__ + ">"
USAGE = "%prog [options] <Reference genes (faa)> <filelist>"

def main():
    global options, args
    identCutoff = 80
    lenCutoff = 80
    Uevalue = '0.00005'
    outFile = 'out.'

    # Parse and validate input
    if len(args) < 1 or not os.path.isfile(args[0]):
        sys.stderr.write('Multi-FASTA is not specified or is not a regular file\n')
        sys.exit(1)
    if len(args) < 2 or not os.path.isfile(args[1]):
        sys.stderr.write('Filelist is not specified or is not a regular file\n')
        sys.exit(1)
    if options.eval != None:
        Uevalue = options.eval
    if options.len != None:
        lenCutoff = options.len
    if options.id != None:
        identCutoff = options.id
    if options.out != None:
        outFile = options.out
    NUMSNPS = None 
    if options.numsnps != None: 
        NUMSNPS = options.numsnps
    list = open( args[1], 'r' )
    genomeList = list.readlines()
    refPro = args[0]

    # Determine if protein or nucleotide reference
    dbtype = 'nucl'
    RefPro = False
    GBK = options.gbk
    if (isPro(refPro) > 0 ): 
        RefPro = True
        dbtype = 'prot'
    if (GBK or RefPro) and options.len == None:
        lenCutoff = 70
    if (GBK or RefPro) and options.id == None:
        identCutoff = 70

    # output to stdout a table detailing best alignment results, columns:
    # <ref_gene> <len> <genome_file_name> <fasta_entry> <len> <id_vs_threshold> <length_vs_threshold> ...
    # <e-value> <ref_start> <ref_stop> <genome_start> <genome_stop> <best?>
    # output to a file multi-FASTA nuc/pro of aligned regions from best hits
    # index lengths of database genes
    if not os.path.exists('temp'):
        os.mkdir('temp')
    f = open(outFile + 'table.csv', 'w')
    header = 'ref_gene\tdesc\tlen\tgenome_file_name\tfasta_entry\tlen\tidentity\tperOflength\te-value\tref_start\tref_stop\tgenome_start\tgenome_stop\tscore\tadded\tsequence'
    if GBK:
        header = header + '\t'+  header 
    f.write(header + '\n')
    masterOut = []
    masterSeq = {}

    # Format BLAST db accordingly
    proc = subprocess.Popen([ "makeblastdb", "-in" , str(refPro), "-dbtype" ,dbtype ], stdout=subprocess.PIPE)
    print(  proc.stdout.read())

    pre = open(outFile + 'presence.csv','w')
    # Run BLASTx if protein ref, BLASTn if nucl ref
    for genome  in genomeList:
        print 'reading ' + genome 
        genome = genome.strip()
        blastRes = 'temp/' + os.path.basename(refPro) + os.path.basename(genome) + dbtype  + '.xml'
        #repoBlast = 'temp/' + os.path.basename(genome) + os.path.basename(refPro) + dbtype  + '.xml'
        # if GBK convert to faa, run RBH:
        if GBK:
            input_handle  = open(genome, "r")
            INEXT = '.gbk'
            INTYPE = 'genbank'
            if genome.endswith('.embl'):
                INEXT = '.embl'
                INTYPE = 'embl'
            if RefPro:
                genome = 'temp/' + os.path.basename(genome).replace(INEXT,'.faa')
            else:
                genome = 'temp/' + os.path.basename(genome).replace(INEXT,'.fna')
            print 'checking ' + genome 
            if not os.path.exists(genome) or os.path.getsize(genome) == 0:
                output_handle = open(genome, "w")
                print 'Creating fas: ' + genome 
                for seq_record in SeqIO.parse(input_handle, INTYPE):
                    print "Dealing with GenBank record %s" % seq_record.id
                    for seq_feature in seq_record.features:
                        if seq_feature.type== "CDS" :
                            na = ''
                            labled = True 
                            if seq_feature.qualifiers.has_key('locus_tag'):
                                na = seq_feature.qualifiers['locus_tag'][0]  
                            elif seq_feature.qualifiers.has_key('gene'):
                                na = seq_feature.qualifiers['gene'][0]
                            else:
                                labled = False
                            if RefPro and labled:
                                try:
                                    if seq_feature.qualifiers.has_key('pseudo') == False:
                                        if not seq_feature.qualifiers.has_key('translation'):
                                            pr = seq_feature.extract(seq_record.seq)
                                            seq_feature.qualifiers['translation'] = [pr.translate()]
                                        output_handle.write(">%s|%s [%s]\n%s\n" % (
                                            na,
                                            seq_record.name, seq_feature.qualifiers['product'][0],
                                            seq_feature.qualifiers['translation'][0]))
                                except Exception as e:
                                    print 'ERROR:' +  str(e)
                                    print seq_feature
                            elif labled:
                                try:
                                    descs = 'pseudogene'
                                    if  seq_feature.qualifiers.has_key('product'): 
                                        descs =  seq_feature.qualifiers['product']
                                    output_handle.write(">%s|%s [%s]\n%s\n" % (
                                            na,
                                            seq_record.name, descs,
                                            seq_feature.extract(seq_record).seq))
                                except Exception as e:
                                    print 'ERROR ' + str(e)
                                    print seq_feature
                output_handle.close()
                input_handle.close()
            #if not os.path.exists(str(genome) + '.phr') and RefPro:
            #    proc = subprocess.Popen([ "makeblastdb", "-in" , str(genome), "-dbtype", "prot"  ], stdout=subprocess.PIPE)
            #    print(  proc.stdout.read())
            if RefPro and (not os.path.exists(blastRes) or os.path.getsize(blastRes) == 0):
                cline = NcbiblastpCommandline(query=genome, seg='no',db=refPro,evalue=Uevalue,outfmt=5,out=blastRes,num_threads='8')
                print(str(cline) + '\n')
                cline()
            elif not os.path.exists(blastRes) or os.path.getsize(blastRes) == 0:
                cline = NcbiblastnCommandline(task='blastn',query=genome, dust='no',db=refPro,evalue=Uevalue,outfmt=5,out=blastRes)
                print(str(cline) + '\n')
                cline()
            #if not os.path.exists(repoBlast) or os.path.getsize(repoBlast) == 0:
            #    cline = NcbiblastpCommandline(query=refPro, seg='no',db=genome,evalue=Uevalue,outfmt=5,out=repoBlast)
            #    print(str(cline) + '\n')
            #    cline()
        else:
        # else run regular BLAST search
            if not os.path.exists(blastRes) or os.path.getsize(blastRes) == 0: 
                cline = '' 
                if RefPro:
                    cline = NcbiblastxCommandline(query=genome, seg='no',  db=refPro, evalue=Uevalue, outfmt=5, out=blastRes)
                else: 
                    cline = NcbiblastnCommandline(query=genome, dust='no', task='blastn', db=refPro, evalue=Uevalue, outfmt=5, out=blastRes)
                print(str(cline) + '\n')
                cline()
        print 'reading BLAST ' + blastRes
        result_handle = open(blastRes)
        blast_records = NCBIXML.parse(result_handle)
        int_handle  = open(genome, "r")
        fast = SeqIO.to_dict(SeqIO.parse(int_handle, "fasta"))
        print 'indexed fasta' 
        for blast_record in blast_records:
            for alignment in blast_record.alignments:
                hits = 0
                for hsp in alignment.hsps:
                    outLine  = []
                    refHead =  alignment.hit_def.split('|')
		    if refHead[0] == 'gi': refHead = refHead[3:] 
		    tempdoop = None
                    if GBK and RefPro:
                        tempse = fast[blast_record.query.split()[0].strip()]
			tempdoop = SeqRecord(Seq(str(tempse.seq),generic_protein),id=os.path.basename(genome).split('.')[0],description=refHead[0],name=refHead[1])
                        if tempdoop == None:
                            print   'Error:\t' + blast_record.query.split('|')[0]
                    elif GBK and not RefPro: 
                        tempse = fast[blast_record.query.split()[0].strip()] 
                        seqseq = Seq(str(tempse.seq), generic_dna)
                        if hsp.frame[1] == -1:
                            seqseq = seqseq.reverse_complement()
                        tempdoop = SeqRecord(seqseq,id=os.path.basename(genome).split('.')[0],description=refHead[0])
                        if tempdoop == None:
                            print  'Error:\t' + blast_record.query.split('|')[0]
                    elif not GBK and  RefPro:
                        tempdoop = SeqRecord(Seq(hsp.query, generic_protein), id=os.path.basename(genome).split('.')[0],description=refHead[0] )
                    else:
                        seqseq = Seq(hsp.query,generic_dna) 
                        if hsp.frame[1] == -1:
                            seqseq = seqseq.reverse_complement()
                        tempdoop = SeqRecord(seqseq, id=os.path.basename(genome).split('.')[0],description=refHead[-1])
                    outLine.append(refHead[0])
                    outLine.append(refHead[-1])
                    outLine.append(alignment.length)
                    outLine.append(os.path.basename(genome))
                    outLine.append(blast_record.query)
                    outLine.append(blast_record.query_letters)
                    outLine.append(int(float(hsp.identities) / float(hsp.align_length) * float(100)))
                    outLine.append(int(float(hsp.align_length) / float(alignment.length) * float(100)))
                    outLine.append(hsp.expect)
                    outLine.append(hsp.sbjct_start)
                    outLine.append(hsp.sbjct_end)
                    outLine.append(hsp.query_start)
                    outLine.append(hsp.query_end)
                    outLine.append(hsp.score)
                    # IF GENBANK: Append details of reciprocal hit
                    REPOCHECK = True
                    #if GBK:
                    #    print 'check if reprocal hit passes cutoff'
                    # Grab only first hit, i.e best hit. 
                    # Create dict (key: ref gene) and add sequences for that gene to an array
                    if ( REPOCHECK and hits == 0 and float(hsp.identities) / float(hsp.align_length) * float(100)  ) > float(identCutoff) \
                            and ( float(hsp.align_length) / float(alignment.length) * float(100) > lenCutoff):
                        hits += 1
                        outLine.append('1')
                        if not masterSeq.has_key(outLine[0]):
                            masterSeq[outLine[0]] = [ tempdoop ]
                        else:
                            arry = masterSeq[outLine[0]]
                            dupe = 0
                            for rec in arry:
                                if rec.id == tempdoop.id:
                                    dupe += 1
                            if dupe == 0:
                                arry.append(tempdoop)
                                masterSeq[ outLine[0] ] = arry
                    else:
                        outLine.append('0')
                    if tempdoop != None: 
                        outLine.append( tempdoop.seq )
                    masterOut.append(outLine)
                    deg = ''
                    for el in outLine:
                        deg += str(el) + '\t'
                    f.write(deg + '\n')
    f.close()
    genlist = []
    for genome in genomeList:
        genome = genome.strip()
        tempgen = os.path.basename(genome).split('.')[0]
        genlist.append(tempgen)
    genlist.sort()
    head = ''
    for ge in genlist:
        head += ge  +'\t'
    pre.write('\t'+head +'\n')
    for do in masterSeq.keys():
        o =  masterSeq[do][0].description
        sert = []
        lin = ''
        for gen in masterSeq[do]:
            sert.append(gen.id)
        for genome in genlist:
            hasgene = 0
            for hgene in sert:
                if hgene == genome:
                    hasgene += 1 
            if hasgene > 0:
                lin += '1\t'
            else:
                lin += '0\t' 
        pre.write(o +'\t' + lin+'\n')
    pre.close()
    if not os.path.exists('fas'):
        os.mkdir('fas')
    # Output FASTA files
    xmfaOut = open(outFile + 'all.xmfa','w')
    for name in masterSeq.keys():
        outFas = outFile + name + '.fas'
        SeqIO.write(masterSeq[name], 'fas/' + outFas, 'fasta')
        if options.muscle or options.tree or options.xfma:
            if not os.path.exists('aln'):
                os.mkdir('aln')
            if not os.path.exists('phy'):
                os.mkdir('phy')
            # Create MUSCLE alignment
            align(outFas, options.write)
            if options.xfma:
                # xfmaOut is a standard filestream handler.
                # alignment is the alignmentIO record from the input file
                alignment = AlignIO.read(open('aln/' +outFas + ".aln"), 'clustal') 
                # Input alignment is a clustal alignment produced by muscle
                # Writes the genename as a comment i.e. dnaG.aln -> #dnaG in the file
                xmfaOut.write('#%s\n' %outFas ) 
                # For each alignment record in a gene family, just dump as a 
                # FASTA record. >%head\n%sequence 
                for record in alignment:
                    xmfaOut.write('>%s\n%s\n' %(record.id, record.seq))
                # alignments in xfma have a '=' at the end. 
                xmfaOut.write('=\n')
            if options.tree and not options.concat:
                tree('phy/' + outFas + ".phy", RefPro, options.write)
    if options.concat:
        # Open muscle alignments
        print 'Concating sequences ' 
        doop = {} 
        for name in masterSeq.keys():
            outAln = outFile + name + '.fas'
            outAln = 'aln/' + outAln +".aln"
            try:
                alignment = AlignIO.read(open(outAln), "clustal")
                if len(alignment) == len(genomeList):
                    for record in alignment:
                        if doop.has_key(record.id):
                            doop[record.id] += record
                        else:
                            doop[record.id] = record
            except Exception as e:
                print 'BAD SEQUENCE'
                print e
        outgen = []
        for k in doop:
            outgen.append(doop[k])
        outFas = outFile + 'all'
        outgen = [MultipleSeqAlignment(outgen)]
        AlignIO.write(outgen, outFas + ".phy", "phylip")
        AlignIO.write(outgen, outFas + ".aln", "clustal")
        if options.tree:
            tree(outFas + ".phy", RefPro)
        if NUMSNPS != None and NUMSNPS > 0 :
            print 'Creating snp file'
            alignment = AlignIO.read(open(outFas + ".aln"), "clustal")
            doop = [] 
            print 'reading records'
            for record in alignment:
                doop.append(record)
            index = 0 
            keepdex = [] 
            print 'loading snp positions'
            for byte in doop[0]:
                snps = 0 
                gaps = 0
                if index % 1000 == 0:
                    print 'read ' + str(index)
                for al in doop:
                    if al[index] != byte:
                        snps += 1 
                    if al[index] == '-':
                        gaps += 1 
                if snps > NUMSNPS and gaps == 0:
                    keepdex.append(index)
                index += 1
            print 'snps ' + str(len(keepdex))
            print 'rebuilding alignments' 
            if len(keepdex) != 0:
                for al in doop:
                    seqseq = '' 
                    for pos in keepdex:
                        seqseq+= al.seq[pos]
                    al.seq = (Seq(seqseq, al.seq.alphabet))
                doop = [MultipleSeqAlignment(doop)]
                AlignIO.write(doop, outFas + "snp.phy", 'phylip')
                AlignIO.write(doop, outFas + "snp.aln", 'clustal')
                if options.tree:
                    tree(outFas + "snp.phy", RefPro, options.write)
            else: 
                print 'WARNING: NO SNPS'

        
def align(fas, clean):
    if not os.path.exists( 'aln/' + fas +".aln") or clean:
        cmdline = MuscleCommandline(input='fas/' + fas, out='aln/' + fas + ".aln", clw=True)
        print(str(cmdline) + '\n')
        cmdline()
    try:
        AlignIO.convert( 'aln/' + fas +".aln", "clustal", 'phy/' + fas + ".phy", "phylip")
    except Exception as e :
        print 'WARNING: BAD ALIGNMENT'
        print e

def tree(fas, RefPro, clean):
    try:
        if not os.path.exists('phy/' + fas + ".phy_phyml_tree.txt") or clean:
            phytype = 'nt'
            if RefPro:
                phytype = 'aa'
            cmdline = PhymlCommandline(input='phy/' + fas + ".phy", datatype=phytype, alpha='e', bootstrap=10)
            print(str(cmdline) + '\n')
            cmdline()
            egfr_tree = Phylo.read('phy/' + fas + ".phy_phyml_tree.txt", "newick")
            Phylo.draw_ascii(egfr_tree)
    except Exception as e:
        print 'WARNING: BAD TREE'
        print e 

def isPro( fastaFile ):
    handle = open(fastaFile, "rU")
    proHit = 0 
    for record in SeqIO.parse(handle, "fasta") :
        if re.match('[^ATCGNatcgn]+', str(record.seq) ) != None:
            proHit += 1
    handle.close()
    return proHit

if __name__ == '__main__':
    try:
        start_time = time.time()
        desc = __doc__.split('\n\n')[1]
        parser = optparse.OptionParser(usage=USAGE,epilog = epi, formatter=optparse.IndentedHelpFormatter(), description=desc,  version='%prog v' + __version__)
        parser.add_option('-g','--gbk',action='store_true', default=False,help='Genbank filelist')
        parser.add_option('-v', '--verbose', action='store_true', default=False, help='verbose output')
        parser.add_option('-l', '--len', action='store', type='int', help='minimum percent match for length')
        parser.add_option('-x', '--xfma', action='store_true',help='Produce XFMA alignment for ClonalFrame')
        parser.add_option('-p', '--id', action='store', type='int', help='minutes percent identity')
        parser.add_option('-e', '--evalue', action='store', type='string', dest='eval', help='evalue cutoff for BLAST')
        parser.add_option('-t', '--tree', action='store_true', dest='tree', default=False, help='produce trees with PhyML')
        parser.add_option('-m', '--muscle', action='store_true', dest='muscle', default=False, help='produce multiple alignments with MUSCLE')
        parser.add_option('-c', '--concat', action='store_true', dest='concat', default=False, help='concatenate gene sequences')
        parser.add_option('-o', '--output', action='store', type='string',dest='out', help='output prefix')
        parser.add_option('-n', '--numsnps', action='store', type='int', help='minimum number of snps')
        parser.add_option('-w', '--write', action='store_true', default=False, help='Overwrite all files')
        (options, args) = parser.parse_args()
        if options.verbose:
            print "Executing @ " + time.asctime()
        main()
        if options.verbose:
            print "Ended @ " + time.asctime()
        if options.verbose:
            print 'total time in minutes:',
        if options.verbose:
            print (time.time() - start_time) / 60.0
        sys.exit(0)
    except KeyboardInterrupt, e:  # Ctrl-C
        raise e
    except SystemExit, e:  # sys.exit()
        raise e
    except Exception, e:
        print 'ERROR, UNEXPECTED EXCEPTION'
        print str(e)
        traceback.print_exc()
        os._exit(1)
