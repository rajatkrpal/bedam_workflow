# bedam python class
__doc__="""
$Revision: 0.1 $

A class to prepare BEDAM AsyncRE jobs

"""
# Contributors: Emilio Gallicchio, Junchao Xia

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

    #override for supermic
    input_qsub = """    
#!/bin/bash
#PBS -q workq
#PBS -l nodes=1:ppn=20
#PBS -N {job_name}
#PBS -o {job_name}.out
#PBS -j oe
#PBS -l walltime=48:10:00
#PBS -A TG-MCB150001


cd $PBS_O_WORKDIR

head -1 $PBS_NODEFILE > .qsub_nodes

awk '{{ for(i=0;i<2;i++)print $1 ","i",4,Linux-x86_64,{user},/tmp" }}; {{ for(i=0;i<1;i++)print $1 ","i",2,Linux-x86_64,{user},/tmp" }}; {{ for(i=0;i<10;i++)print $1 "p-mic0,"i",24,Linux-mic,{user},/tmp" }}' < .qsub_nodes > nodefile

python ~/src/AsyncRE/bedamtempt_async_re.py {job_name}_asyncre.cntl >LOG &

cd ../{job_name}

head -1 $PBS_NODEFILE > .qsub_nodes

awk '{{ for(i=0;i<2;i++)print $1 ","i",4,Linux-x86_64,{user},/tmp" }}; {{ for(i=0;i<1;i++)print $1 ","i",2,Linux-x86_64,{user},/tmp" }}; {{ for(i=0;i<10;i++)print $1 "p-mic1,"i",24,Linux-mic,{user},/tmp" }}' < .qsub_nodes > nodefile

python ~/src/AsyncRE/bedamtempt_async_re.py {job_name}_asyncre.cntl >LOG &

wait

"""

    bedam.input_qsub = input_qsub
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
