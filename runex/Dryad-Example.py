#!/usr/bin/env python
"""
# Created: Mon, 18 Mar 2013 11:57:13 +1000

Quick example test of Dryad script. Just run 'python Dryad-Example.py -v'.\
        Requires reference genes and remote file list. (Default: all_mlst.fna \
        and GB-loc in runex dir)

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

### CHANGE LOG ### 
2013-03-18 Nabil-Fareed Alikhan <n.alikhan@uq.edu.au>
    * v0.3: Formatted stand-alone version
"""
import sys, os, traceback, argparse
import time, gzip, subprocess
import urllib2

__author__ = "Nabil-Fareed Alikhan"
__licence__ = "GPLv3"
__version__ = "0.3"
__email__ = "n.alikhan@uq.edu.au"
epi = "Licence: "+ __licence__ +  " by " + __author__ + " <" + __email__ + ">"

def main ():
    global args

    # CHECK DEPENDENCIES. Dryad requires Biopython, BLAST & MUSCLE to run.
    sys.stdout.write('Testing Biopython is installed...')
    try:
        from Bio.Seq import Seq
        from Bio.Alphabet.IUPAC import unambiguous_dna
        new_seq = Seq('GATCAGAAG', unambiguous_dna)
        new_seq.translate()
    except:
        print '\nERROR: Biopython not installed, see <http://biopython.org/>'
        exit(1)
    print 'OK!'
    sys.stdout.write('Testing if BLAST+ is installed (and on PATH)...')
    try:
        subprocess.check_output(['blastn','-help'])
    except:
        print '\nERROR: BLAST+ is not installed (Or it is not on your PATH)'
        exit(1)
    print 'OK!'
    sys.stdout.write('Testing if MUSCLE is installed (and on PATH)...')
    try:
        subprocess.check_output(['muscle', '-version'])
    except:
        print '\nERROR: MUSCLE is not installed, see <http://www.drive5.com/muscle/>'
        exit(1)
    print 'OK!'

    # CREATE DIR & DOWNLOAD GENOMES
    if args.verbose: 'Options: %s' %(args)
    print 'Fetching genomes from %s' %(args.genomelist)
    if not os.path.exists('gen/'):
        os.mkdir('gen')
        if args.verbose:  'Creating dir: gen/'
    filelist = open('Example-list', 'w')
    if args.verbose:  'Writing genomes to: gen/'
    with open(args.genomelist, 'r') as gen:
        for gen in gen.readlines():
            genpath = os.path.join('gen/', gen.split('/')[-1].strip() )
            if not os.path.exists(genpath):
                fetchFile(gen,'gen')
            if genpath.endswith('.gz'):
                if args.verbose: print 'Unzipped %s' %(genpath)
                gencom = gzip.open(genpath, 'rb')
                outgbk = genpath[:-3]
                gengbk = open(outgbk, 'wb')
                gengbk.write(gencom.read())
                gencom.close()
                gengbk.close()
                filelist.write('%s\n' %(outgbk))
            else:
                filelist.write('%s\n' %(genpath))
    filelist.close()

    # LAUNCH DRYAD SCRIPT
    Dryadopts = ['python', '../Dryad.py','-gmc', args.reffile, 'Example-list',\
            '-o', 'EXAMPLE', '-p', '70']
    proc = subprocess.Popen(Dryadopts)
    print '\nRunning Dryad script as:\n\n%s %s %s %s %s %s %s %s %s\n' \
        %('python', '../Dryad.py','-gmc', args.reffile, 'Example-list', '-o',\
        'EXAMPLE', '-p', '70')
    print '===NOW LAUNCHING DRYAD SCRIPT==='
    print proc.communicate()
    print '===DRYAD COMPLETE==='

    print 'Renaming Taxa'
    try:
        from Bio import AlignIO
        alignment = AlignIO.read(open('EXAMPLEall.phy'), "phylip")
        for record in alignment:
            record.id = ExampleTable(record.id)
            outpu = open('EXAMPLEall.phy', 'w')
        AlignIO.write(alignment,outpu, "phylip-relaxed")
    except:
        print 'ERROR: Can not reformat output'
        exit(1)

def ExampleTable(acc):
    table = {} 
    table['CU928145'] = 'E.coli_55989' 
    table['AE014075'] = 'E.coli_CFT073'
    table['CP000800'] = 'E.coli_E24377A'
    table['CP000802'] = 'E.coli_HS'
    table['U00096'] = 'E.coli_K12'
    table['AP010953'] = 'E.coli_O26H11'
    table['CP001846'] = 'E.coli_O55H7'
    table['BA000007'] = 'E.coli_O157H7-Sakai'
    table['CU928158'] = 'E.fergusonii'
    table['CP000243'] = 'E.coli_UTI89'
    table['AE005174'] = 'E.coli_O157H7-EDL933'
    return table[acc]


def fetchFile(url, outdir):

    file_name = url.split('/')[-1]
    u = urllib2.urlopen(url)
    f = open(os.path.join(outdir, file_name.strip()), 'wb')
    meta = u.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    if args.verbose: print "Downloading: %s Bytes: %s" % (file_name, file_size)

    file_size_dl = 0
    block_sz = 8192
    while True:
        buffer = u.read(block_sz)
        if not buffer:
            break

        file_size_dl += len(buffer)
        f.write(buffer)
        status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
        status = status + chr(8)*(len(status)+1)
        if args.verbose: print status,

    f.close()

if __name__ == '__main__':
    try:
        start_time = time.time()
        desc = __doc__.split('\n\n')[1].strip()
        parser = argparse.ArgumentParser(description=desc,epilog=epi)
        parser.add_argument ('-v', '--verbose', action='store_true', default=False, help='verbose output')
        parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
        parser.add_argument ('-r', '--reffile', default='all_mlst.fna', action='store', help='Reference genes (Multi-FASTA). [Default: all_mlst.fna]')
        parser.add_argument ('-f','--genomelist', default='GB-loc', action='store', help='List of remote locations of genomes [Default: GB-loc]')
        args = parser.parse_args()
        if args.verbose: print "Executing @ " + time.asctime()
        main()
        if args.verbose: print "Ended @ " + time.asctime()
        if args.verbose: print 'total time in minutes:',
        if args.verbose: print (time.time() - start_time) / 60.0
        sys.exit(0)
    except KeyboardInterrupt, e: # Ctrl-C
        raise e
    except SystemExit, e: # sys.exit()
        raise e
    except Exception, e:
        print 'ERROR, UNEXPECTED EXCEPTION'
        print str(e)
        traceback.print_exc()
        os._exit(1)

