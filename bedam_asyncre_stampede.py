# bedam python class
#override the input_slurm script for running in Stampede
#Rajat K Pal
__doc__="""
$Revision: 0.1 $

A class to prepare BEDAM AsyncRE jobs

"""
# Main Contributors: Emilio Gallicchio, Junchao Xia

import os, sys, time, re, glob
from schrodinger.utils import cmdline
import schrodinger.utils.log
import shutil
import signal
import glob
import time

from bedam_asyncre import bedam_job_asyncre

##################### MAIN CODE ##########################
if __name__ == '__main__':

    # Setup the logger
    logger = schrodinger.utils.log.get_output_logger("bedam_prep")

    # Parse arguments:
    usage = "%prog [options] <inputfile>"
    parser = cmdline.SingleDashOptionParser(usage)
    (options, args) = parser.parse_args(sys.argv[1:])

    if len(args) != 2:
        parser.error("usage= python bedam_asyncre_supermic.py <commandfile> <user>")

    commandFile = args[0]

    print ""
    print "===================================="
    print "       BEDAM Job Preparation for supermic        "
    print "===================================="
    print ""
    print "SCHRODINGER: " + os.environ['SCHRODINGER']
    print "Started at: " + str(time.asctime())
    print "Input file:", commandFile
    print ""
    sys.stdout.flush()

    print "Reading options"
    bedam = bedam_job_asyncre(commandFile, options)

    print "Set put templates for input files ..."
    bedam.setupTemplatesASyncRE()
    print "Analyzing structure files ..."
    bedam.getDesmondDMSFiles()
    print "Writing BEDAM restraint file ..."
    bedam.writeRestraintFile()
    print "Adding atomic restraints to receptor file ..."
    bedam.writeRecStructureFile()
    print "Writing job input files ..."
    bedam.writeCntlFile()
    bedam.writeThermInputFile()
    bedam.writeRemdInputFile()
    bedam.writeRunimpactFile()

    username = args[1]
    if not username:
        username = ""

    #override for stampede
    input_slurm = """
#!/bin/bash
#SBATCH -p normal-mic       # Queue name
#SBATCH -N 1                # This is nodes, not cores (16 cores/node)
#SBATCH -n 1                # one process per node so we get one entry per node
#SBATCH -t 47:00:00         # Max time allotted for job
#SBATCH -A TG-MCB150001

echo "Number of nodes: $SLURM_NNODES"
echo "Nodelist: $SLURM_NODELIST"
echo "Number of tasks: $SLURM_NTASKS"
echo "Tasks per node: $SLURM_TASKS_PER_NODE"

scontrol show hostname $SLURM_NODELIST > .slurm_nodes
awk '{{ for(i=0;i<4;i++)print $1 ","i",4,Linux-x86_64,{user},/tmp"}}; {{ for(i=0;i<10;i++)print $1"-mic0,"i",24,Linux-mic,{user},/tmp"}}; ' < .slurm_nodes > nodefile

python ~/src/AsyncRE/bedamtempt_async_re.py {job_name}_asyncre.cntl > LOG 2>&1
"""


    bedam.input_slurm = input_slurm
    bedam.nodefile_username = username

    bedam.writeQueueFiles()


    print
    print "Job preparation complete"
    print ""
    print "To run the minimization/thermalization calculation do:"
    exec_directory =  bedam.keywords.get('EXEC_DIRECTORY')
    if exec_directory is not None:
        print "export IMPACTHOME=" + exec_directory
    else:
        print "export IMPACTHOME=" + "<path_to_academic_impact_directory>"
    print "export OMP_NUM_THREADS=" + "<number_of_CPU_cores>"
    print "./runimpact_i %s_mintherm.inp" % bedam.jobname
    print ""
    print "When completed run the production calculation with:"
    print "<path_to_asyncre>/bedamtempt_async_re.py %s_asyncre.cntl" % bedam.jobname
    print ""
