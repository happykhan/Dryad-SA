#!/usr/bin/env python
"""
# Created: Mon, 18 Mar 2013 11:57:13 +1000

TODO: Single line description. 

TODO: Detailed description

### CHANGE LOG ### 
YYYY-MM-DD <name> <address>
    * Initial build
"""
import sys, os, traceback, argparse
import time

__author__ = "Nabil-Fareed Alikhan"
__licence__ = "GPLv3"
__version__ = "0.3"
__email__ = "n.alikhan@uq.edu.au"
epi = "Licence: "+ __licence__ +  " by " + __author__ + " <" + __email__ + ">"

def main ():

    global args
    # TODO: Do something more interesting here...
    print 'Hello world!'
    # READ AND PRINT first positional argument (if any)
    # If you want to access positional arguments with argparse:
    # Use global "args" (declared above) not argv[0]
    if args.output != None:
        print 'Output: ' + args.output
    print args

    print args.verbose
    print args.output
    print args.arg1

if __name__ == '__main__':
    try:
        start_time = time.time()
        desc = __doc__.split('\n\n')[1].strip()
        parser = argparse.ArgumentParser(description=desc,epilog=epi)
        # EXAMPLE OF BOOLEAN FLAG: verbose
        parser.add_argument ('-v', '--verbose', action='store_true', default=False, help='verbose output')
        parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
        # EXAMPLE OF command line variable: 'output'
        parser.add_argument('-o','--output',action='store',help='output prefix')
        # EXAMPLE OF POSITIONAL ARGUMENT
        parser.add_argument ('arg1', action='store', type=int, help='First positional argument (INT)')
        parser.add_argument ('arg2', action='store', help='2nd positional argument (STRING)')
        # EXAMPLE OF NESTED PARAMETERS
        
        # subparsers = parser.add_subparsers(help='commands')
        # list_parser = subparsers.add_parser('list', help='List contents')
        # list_parser.add_argument('dirname', action='store', help='Directory to list')

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

