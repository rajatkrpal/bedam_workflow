# bedam python class
__doc__="""
$Revision: 0.1 $

A class to prepare Temperature AsyncRE jobs

"""
# Contributors: Emilio Gallicchio, Junchao Xia

import os, sys, time, re, glob
from schrodinger.utils import cmdline
import schrodinger.utils.log
import shutil
import signal
import glob
import time

import sqlite3 as lite

from math import *

from bedam_prep_ac import bedam_prep_ac

class tempt_job_asyncre(bedam_prep_ac):
    """
    Class to set up BEDAM calculations
    """
    def __init__(self, command_file, options):
        bedam_prep_ac.__init__(self, command_file, options)

#
# Impact input file templates for academic
#
    def setupTemplatesASyncRE(self):
        """ Setup templates for input files for academic impact"""
        self.input_cms =  """
task {
  task = "desmond:auto"
}

build_geometry {
  box = {
     shape = "orthorhombic"
     size = [10.0 10.0 10.0 ]
     size_type = "absolute"
  }
  neutralize_system = false
  rezero_system = false
  solvate_system = false
}

assign_forcefield {
}

"""  

        self.input_idx =  """
write file -
"{out_file}" -
      title -
"{title}" *

CREATE
  build primary name species1 type auto read sqldb file -
"{dms_in}"
QUIT

SETMODEL
  setpotential
    mmechanics consolv agbnp2
  quit
  read parm file -
"paramstd.dat" -
  noprint
  energy parm dielectric 1 nodist -
   listupdate 10 -
    cutoff 12 hmass 5
  energy rescutoff byatom all
  zonecons auto
  energy constraints bonds hydrogens
QUIT

MINIMIZE
  input cntl mxcyc 0  rmscut 0.05 deltae 1.0e-05
  conjugate dx0 0.05 dxm 1.0
  run
  write sql name species1 file "{dms_out}"
QUIT

END
"""
        self.input_mintherm = """
write file -
"{out_file}" -
      title -
"{title}" *

CREATE
  build primary name species1 type auto read sqldb file -
"{dms_in}"
QUIT

SETMODEL
  setpotential
    mmechanics consolv agbnp2
    weight constraints buffer {rest_kf} halfwidth {halfwidth}
  quit
  read parm file -
"paramstd.dat" -
  noprint
  energy parm dielectric 1 nodist -
   listupdate 10 -
    cutoff 12 hmass 5
  energy rescutoff byatom all
  zonecons auto
  energy constraints bonds hydrogens
QUIT

MINIMIZE
  conjugate dx0 5.000000e-02 dxm 1.000000e+00
  input cntl mxcyc 200 rmscut 1.000000e-02 deltae 1.000000e-07
  run
QUIT

put 100 into 'temp0'
put {temperature} into 'tempt'
put 10 into 'n'
put 'tempt'- 'temp0' into 'dtemp'
put 'dtemp' / 'n' into 'dt'

put 0 into 'i'
while 'i' lt 'n'

DYNAMICS
  input cntl nstep 1000 delt 0.0005
  input cntl constant totalenergy
  input cntl initialize temperature at 'temp0'
  input cntl nprnt 100
  input cntl tol 1.00000e-07
  input cntl stop rotations
  input cntl statistics off
  run rrespa fast 8
QUIT

put 'temp0' + 'dt' into 'temp0'
put 'i' + 1 into 'i'

endwhile

DYNAMICS
  write restart coordinates formatted file "{job_name}_0.rst"  
  write sql name species1 file "{job_name}_0.dms"
QUIT

END
"""
        self.input_remd = """
write file -
"{job_name}_@n@.out" -
      title -
"{job_name}" *

CREATE
  build primary name species1 type auto read sqldb file -
"{job_name}_@nm1@.dms"
QUIT

SETMODEL
  setpotential
    mmechanics consolv agbnp2
    weight constraints buffer {rest_kf} halfwidth {halfwidth}
  quit
  read parm file -
"paramstd.dat" -
  noprint
  energy parm dielectric 1 nodist -
   listupdate 10 -
    cutoff 12 hmass 5
  energy rescutoff byatom all
  zonecons auto
  energy constraints bonds hydrogens
QUIT

if @n@ eq 1
DYNAMICS
  input target temperature @temperature@
  input cntl initialize temperature at @temperature@
QUIT
endif

DYNAMICS
  input cntl nstep {nmd} delt 0.001
  input cntl constant temperature langevin relax 1.0
  input target temperature @temperature@
  input cntl nprnt {nprnt}
  input cntl tol 1.00000e-07
  input cntl stop rotations
  input cntl statistics off
  run rrespa fast 4
  write restart coordinates and velocities formatted file "{job_name}_@n@.rst"
  write sql file "{job_name}_@n@.dms" name species1
QUIT


END
"""

        self.input_slurm = """
#!/bin/bash
#SBATCH -p normal-mic       # Queue name
#SBATCH -N 6                # This is nodes, not cores (16 cores/node)
#SBATCH -n 6                # one process per node so we get one entry per node
#SBATCH -t 47:00:00         # Max time allotted for job
#SBATCH -A TG-MCB100145

echo "Number of nodes: $SLURM_NNODES"
echo "Nodelist: $SLURM_NODELIST"
echo "Number of tasks: $SLURM_NTASKS"
echo "Tasks per node: $SLURM_TASKS_PER_NODE"

scontrol show hostname $SLURM_NODELIST > .slurm_nodes
awk '{{ for(i=0;i<4;i++)print $1 ","i",4,Linux-x86_64,{user},/tmp"}}; {{ for(i=0;i<10;i++
)print $1"-mic0,"i",24,Linux-mic,{user},/tmp"}}; ' < .slurm_nodes > nodefile

python ~/src/async_re-0.3.2-alpha-multiarch/tempt_async_re.py {job_name}_asyncre.cntl > LOG 2>&1
"""


        self.input_qsub = """
#!/bin/bash
#PBS -q production
#PBS -l select=64:ncpus=1
#PBS -N {job_name}
#PBS -l place=free
#PBS -l walltime=48:10:00
#PBS -V

cd $PBS_O_WORKDIR
sdir=/scratch/e.gallicchio

source ${{sdir}}/env/bin/activate

cp $PBS_NODEFILE .qsub_nodes
#1 core per replica
awk '{{ for(i=0;i<1;i++)print $1 ","i",1,Linux-x86_64,{user},/tmp"}}' < .qsub_nodes > nodefile

python ~/src/async_re-0.3.2-alpha-multiarch/tempt_async_re.py {job_name}_asyncre.cntl > LOG 2>&1
"""

        self.input_runimpact_standard = """#!/bin/bash
export IMPACTHOME={acd_impact_home}
export IMP_ROOT=$IMPACTHOME
export IMPACT_EXEC=$IMP_ROOT/bin/Linux-x86_64
export LD_LIBRARY_PATH=$IMP_ROOT/lib/Linux-x86_64:$LD_LIBRARY_PATH
export OMP_NUM_THREADS={subjob_cores}
nice $IMPACT_EXEC/main1m $1
"""

        self.input_runimpact_multiarch = """#!/bin/bash
export LD_LIBRARY_PATH=.:$LD_LIBRARY_PATH
nice ./main1m $1
"""

        self.input_runimpact_interactive = """#!/bin/bash
export IMP_ROOT=$IMPACTHOME
export IMPACT_EXEC=$IMP_ROOT/bin/Linux-x86_64
export LD_LIBRARY_PATH=$IMP_ROOT/lib/Linux-x86_64:$LD_LIBRARY_PATH
$IMPACT_EXEC/main1m $1
"""


#
# Convert .mae files into .dms files with AGBNP2 parameters and internal atom indexes
#
    def getDesmondDMSFiles(self):
 
        mol_file =  self.keywords.get('MOL_FILE')
        if not mol_file:
            msg = "tempt_asyncre: No MOL_FILE file specified in the input file"
            self.exit(msg)
        if not os.path.exists(mol_file):
            msg = 'tempt_asyncre: File does not exist: %s' % mol_file
            self.exit(msg)

#        com_shrod_source =  self.keywords.get('COMMERCIAL_SCHRODINGER_EVN')
#        if not com_shrod_source:
#            msg = "tempt_asyncre: No commerical shrodinger source file specified in the input file"
#            self.exit(msg)

        print "Convert maegz file to cms file "
        desmond_builder_file = 'des_builder.msj'
        cms_file = self.jobname + '.cms'
        f = open(desmond_builder_file, 'w')
        input =  self.input_cms
        f.write(input)
        f.close()
        cmd = '$SCHRODINGER/utilities/multisim' + ' -JOBNAME ' + self.jobname + ' -m ' + desmond_builder_file + ' ' + mol_file + ' -o ' + cms_file + ' -HOST localhost -maxjob 1 -WAIT'
        os.system(cmd)

        print "Convert cms files to dms files"
        dms_file = self.jobname + '.dms'
	cmd = '$SCHRODINGER/run -FROM desmond mae2dms ' + cms_file + ' ' + dms_file
        os.system(cmd)

        print "add agbnp parameters into dms files"
        agbnp_cmd =  "$SCHRODINGER/run add_agbnp2.py " + dms_file
        os.system(agbnp_cmd)

	#add agbnp2 custom watersites to dms file if available(Added by Rajat K Pal)
	if os.path.exists('watersite.param'):
	    print "add custom watersites into receptor dms file"
	    watersites_cmd = "python watersites.py " + dms_file
	    os.system(watersites_cmd)

        print "add internal atom indexes into dms files"
#        acd_impact_source =  self.keywords.get('ACADEMIC_IMPACT_EVN')
#        if not acd_impact_source:
#            msg = "tempt_asyncre: No academic IMPACT source file specified in the input file"
#            self.exit(msg)
        impact_input_file =   self.jobname + '_idx' + '.inp'
        impact_output_file =  self.jobname + '_idx' + '.out'
        impact_jobtitle =     self.jobname + '_idx'
        out_file =   self.jobname + '_idx' + '.dms'
        f = open(impact_input_file, 'w')
        input =  self.input_idx.format(out_file=impact_output_file, title=impact_jobtitle, dms_in=dms_file, dms_out=out_file )
        f.write(input)
        f.close()
        idx_log_file =  self.jobname + '_idx' + '.log'
        
        impact_home = os.environ['IMPACTHOME']
        os.environ['IMP_ROOT'] = impact_home
        os.environ['IMPACT_EXEC'] = impact_home + "/bin/Linux-x86_64"
        os.environ['LD_LIBRARY_PATH'] = "$LD_LIBRARY_PATH:" + impact_home + "/lib/Linux-x86_64"
        idx_cmd =  "$IMPACT_EXEC/main1m " + impact_input_file + " > " + idx_log_file + " 2>&1 "
        os.system(idx_cmd)
        if not os.path.exists(out_file):
            msg = "Impact job to generate dms files with idx failed"
            self.exit(msg)
        os.rename(out_file, dms_file)
        self.idxfile = dms_file 

    def writeCntlFile(self):
        input = ""

        job_transport = self.keywords.get('JOB_TRANSPORT')
        if job_transport is None:
            msg = "writeCntlFile: JOB_TRANSPORT is not specified"
            self.exit(msg)
        if not (job_transport == "SSH" or job_transport == "BOINC"):
            msg = "writeCntlFile: invalid JOB_TRANSPORT: %s Choose one of 'SSH', 'BOINC'." % job_transport
            self.exit(msg)
        input += "JOB_TRANSPORT = '%s'\n" % job_transport
            
        re_type = self.keywords.get('RE_TYPE')
        if re_type is None:
            msg = "writeCntlFile: RE_TYPE is not specified"
            self.exit(msg)
        if not (re_type == 'TEMPT'):
            msg = "writeCntlFile: invalid RE_TYPE. Specify 'TEMPT'."
            self.exit(msg)
        input += "RE_TYPE = '%s'\n" % re_type

        engine = self.keywords.get('ENGINE')
        if engine is None:
            engine = "IMPACT"
        input += "ENGINE = '%s'\n" % engine

        input += "ENGINE_INPUT_BASENAME = '%s'\n" % self.jobname

        if job_transport == 'SSH':
            exec_directory =  self.keywords.get('EXEC_DIRECTORY')
            if exec_directory is None:
                msg = "writeCntlFile: SSH transport requires EXEC_DIRECTORY"
                self.exit(msg)
            input += "EXEC_DIRECTORY = '%s'\n" % exec_directory

        input += "RE_SETUP = 'YES'\n"

        extfiles = self.keywords.get('ENGINE_INPUT_EXTFILES')
        required_files = "runimpact"
        if extfiles is None:
            extfiles = required_files
        else:
            extfiles += ",%s" % required_files
        rst_file = "%s_0.rst" % self.jobname
        dms_file = "%s_0.dms" % self.jobname
        input_file = "%s.inp" % self.jobname
        extfiles = extfiles + ",%s,%s,%s" % (rst_file,dms_file,input_file)
        extfiles += ",%s" % (self.idxfile)
        input += "ENGINE_INPUT_EXTFILES = '%s'\n" % extfiles
        
        temperatures = self.keywords.get('TEMPERATURES')
        if temperatures is not None:
            input += "TEMPERATURES = '%s'\n" % temperatures

        wall_time = self.keywords.get('WALL_TIME')
        if wall_time is not None:
            input += "WALL_TIME = %d\n" % int(wall_time)

        replica_run_time = self.keywords.get('REPLICA_RUN_TIME')
        if replica_run_time is not None:
            input += "REPLICA_RUN_TIME = %d\n" % int(replica_run_time)

        cycle_time = self.keywords.get('CYCLE_TIME')
        if cycle_time is not None:
            input += "CYCLE_TIME = %d\n" % int(cycle_time)
            
        if job_transport == 'SSH':
            input += "NODEFILE = 'nodefile'\n"
            total_cores = self.keywords.get('TOTAL_CORES')
            if total_cores is None:
                msg = "writeCntlFile: TOTAL_CORES is required"
                self.exit(msg)
            input += "TOTAL_CORES = %d\n" % int(total_cores) 
            subjob_cores = self.keywords.get('SUBJOB_CORES')
            if subjob_cores is not None:
                input += "SUBJOB_CORES = %d\n" % int(subjob_cores)            

        if job_transport == 'BOINC':
            total_cores = self.keywords.get('TOTAL_CORES')
            if total_cores is None:
                msg = "writeCntlFile: TOTAL_CORES is required"
                self.exit(msg)
            input += "TOTAL_CORES = %d\n" % int(total_cores) 
            subjob_cores = self.keywords.get('SUBJOB_CORES')
            if subjob_cores is not None:
                input += "SUBJOB_CORES = %d\n" % int(subjob_cores)

        if job_transport == 'BOINC':
            boinc_projectdir = self.keywords.get('BOINC_PROJECTDIR')
            if boinc_projectdir is None:
                msg = "writeCntlFile: BOINC_PROJECTDIR is required"
                self.exit(msg)
            boinc_database = self.keywords.get('BOINC_DATABASE')
            if boinc_database is None:
                msg = "writeCntlFile: BOINC_DATABASE is required"
                self.exit(msg)
            boinc_database_user = self.keywords.get('BOINC_DATABASE_USER')
            if boinc_database_user is None:
                msg = "writeCntlFile: BOINC_DATABASE_USER is required"
                self.exit(msg)
            boinc_database_password = self.keywords.get('BOINC_DATABASE_PASSWORD')
            if boinc_database_password is None:
                msg = "writeCntlFile: BOINC_DATABASE_PASSWORD is required"
                self.exit(msg)
            input += "BOINC_PROJECTDIR = '%s'\n" % boinc_projectdir
            input += "BOINC_DATABASE = '%s'\n" % boinc_database
            input += "BOINC_DATABASE_USER = '%s'\n" % boinc_database_user
            input += "BOINC_DATABASE_PASSWORD = '%s'\n" % boinc_database_password

        subjobs_buffer_size = self.keywords.get('SUBJOBS_BUFFER_SIZE')
        if subjobs_buffer_size is not None:
            input += "SUBJOBS_BUFFER_SIZE = '%f'\n" % float(subjobs_buffer_size)

        verbose = self.keywords.get('VERBOSE')
        if verbose is not None:
            input += "VERBOSE = '%s'\n" % verbose
        
        cntlfile = "%s_asyncre.cntl" % self.jobname
        f = open(cntlfile, "w")
        f.write(input)
        f.close

#
# writes receptor dms file with restraints
#
    def writeStructureDMSFile(self):
        if self.idxfile is None :
            msg = "writeStructureDMSFile: Internal error: Structure file not found"
            self.exit(msg)            
        if not os.path.exists(self.idxfile):
            msg = 'File does not exist: %s' % self.idxfile
            self.exit(msg)

        rest_sql =  self.keywords.get('REST_SQL')
        rest_kf = self.keywords.get('REST_KF')
        if not rest_kf:
            rest_kf = float('0.6')
        else:
            rest_kf = float(self.keywords.get('REST_KF'))
        if rest_sql is not None: 
            con = lite.connect(self.idxfile)
            with con:
                cur = con.cursor()  
                cur.execute("CREATE TABLE IF NOT EXISTS posre_harm_term (p0 INTEGER PRIMARY KEY, x0 REAL, y0 REAL, z0 REAL, param INTEGER )")
                cur.execute("CREATE TABLE IF NOT EXISTS posre_harm_param (id INTEGER PRIMARY KEY, fcx REAL, fcy REAL, fcz REAL)")
                # Impact supports only one value of force constant
                cur.execute("INSERT INTO posre_harm_param (fcx, fcy, fcz, id) VALUES (%f, %f, %f, 0)" % (rest_kf, rest_kf, rest_kf)) 
                cur.execute("SELECT id, x, y, z FROM particle WHERE " + rest_sql)
                rows = cur.fetchall()
                for row in rows:
                    atom = row[0]
                    x0 = row[1]
                    y0 = row[2]
                    z0 = row[3]
                    cur.execute("INSERT INTO posre_harm_term (p0, x0, y0, z0, param) VALUES (%d, %f, %f, %f, 0)" % (atom, x0, y0, z0))
 
        froz_sql =  self.keywords.get('FROZ_RECEPTOR_SQL')
        if froz_sql is not None: 
            con = lite.connect(self.idxfile)
            sql_cmd = "PRAGMA table_info(particle)";
            columnExists = False; 
            with con:
                cur = con.cursor()  
                cur.execute(sql_cmd)
                rows = cur.fetchall()
                for row in rows:
                    if row[1] == "grp_frozen" : 
                        columnExists = True
                if not columnExists : 
                    cur.execute("ALTER TABLE particle ADD COLUMN grp_frozen int DEFAULT(0);")
                cmd = "SELECT id FROM particle WHERE " + froz_sql
                cur.execute(cmd)
                atoms = cur.fetchall()      
                for iat in atoms:
                    cur.execute("UPDATE particle SET grp_frozen=? WHERE Id=?", (1, iat[0]))

#
# writes the Impact input file for minimization/thermalization
#
    def  writeThermInputFile(self):
        if self.idxfile is None:
            msg = "writeThermInputFile: Internal error: receptor structure file not found"
            self.exit(msg)
        if not os.path.exists(self.idxfile):
            msg = 'File does not exist: %s' % self.idxfile
            self.exit(msg)

        if self.keywords.get('REST_KF') is not None:
            rest_kf = self.keywords.get('REST_KF')
        else:
            rest_kf = '0.6'

        if self.keywords.get('HALFWIDTH') is not None:
            hw= self.keywords.get('HALFWIDTH')
        else:
            hw = '0.0'

        temperature =  self.keywords.get('TEMPERATURE')
        if not temperature:
            temperature = '300.0'
        impact_input_file =   self.jobname + '_mintherm' + '.inp'
        impact_output_file =  self.jobname + '_mintherm' + '.out'
        impact_jobtitle =     self.jobname + '_mintherm'

        input = self.input_mintherm.format(
            job_name = self.jobname,
            out_file = impact_output_file, title = impact_jobtitle,
            dms_in = self.idxfile, 
            temperature = temperature, rest_kf = rest_kf, halfwidth = hw)

        f = open(impact_input_file, "w")
        f.write(input)
        f.close

#
# writes the Impact input file for AsyncRE production
#
    def  writeRemdInputFile(self):
        if self.idxfile is None:
            msg = "writeThermInputFile: Internal error: receptor structure file not found"
            self.exit(msg)
        if not os.path.exists(self.idxfile):
            msg = 'File does not exist: %s' % self.recidxfile
            self.exit(msg)

        if self.keywords.get('REST_KF') is not None:
            rest_kf = self.keywords.get('REST_KF')
        else:
            rest_kf = '0.6'

        if self.keywords.get('HALFWIDTH') is not None:
            hw= self.keywords.get('HALFWIDTH')
        else:
            hw = '0.0'

        nmd = self.keywords.get('PRODUCTION_STEPS')
        if not nmd:
            msg = "tempt_asyncre: Number of production steps not specified"
            self.exit(msg)
        nprnt = self.keywords.get('PRNT_FREQUENCY')
        if not nprnt:
            msg = "Number of printing frequency not specified"
            self.exit(msg)

        input_dms_file = self.jobname + "_@nm1@" + ".dms"

        input = self.input_remd.format(
            job_name = self.jobname,
            rest_kf = rest_kf, halfwidth = hw,
            nmd = nmd, nprnt = nprnt)

        impact_input_file = self.jobname + ".inp"

        f = open(impact_input_file, "w")
        f.write(input)
        f.close

#
# writes the 'runimpact' script for interactive and asyncre use
#
    def  writeRunimpactFile(self):
        
        job_transport = self.keywords.get('JOB_TRANSPORT')
        if job_transport is None:
            msg = "writeRunimpactFile: JOB_TRANSPORT is not specified"
            self.exit(msg)

        if job_transport == 'SSH':
            input = self.input_runimpact_multiarch
            f = open('runimpact', "w")
            f.write(input)
            f.close
            os.chmod('runimpact',0744)

        #this is the interactive version
        input = self.input_runimpact_interactive
        f = open('runimpact_i', "w")
        f.write(input)
        f.close
        os.chmod('runimpact_i',0744)

#
# writes sample submission scripts for slurm (stampede) and PBS
#
    def writeQueueFiles(self):
        
        try:
	   username = self.nodefile_username
        except:
	   username = ""

           
        input = self.input_slurm.format(user = username, job_name = self.jobname)
        slurm_file = self.jobname + '.slurm'
        #print "%s" % input
        f = open(slurm_file, "w")
        f.write(input)
        f.close
        
        

        try:
	   username = self.nodefile_username
        except:
	   username = ""

        input = self.input_qsub.format(user = username, job_name = self.jobname)
        qsub_file = self.jobname + '.qsub'
        f = open(qsub_file, "w")
        f.write(input)
        f.close

##################### MAIN CODE ##########################
if __name__ == '__main__':

    # Setup the logger
    logger = schrodinger.utils.log.get_output_logger("bedam_prep")

    # Parse arguments:
    usage = "%prog [options] <inputfile>"
    parser = cmdline.SingleDashOptionParser(usage)
    (options, args) = parser.parse_args(sys.argv[1:])
    
    if len(args) != 1:
        parser.error("Please specify ONE input file")
    
    commandFile = args[0]

    print ""
    print "===================================="
    print "       BEDAM Job Preparation        "
    print "===================================="
    print ""
    print "SCHRODINGER: " + os.environ['SCHRODINGER']
    print "Started at: " + str(time.asctime())
    print "Input file:", commandFile
    print ""
    sys.stdout.flush()
    
    print "Reading options"
    tempt = tempt_job_asyncre(commandFile, options)

    print "Set up templates for input files ..."
    tempt.setupTemplatesASyncRE()
    print "Analyzing structure files ..."
    tempt.getDesmondDMSFiles()
    print "Adding atomic restraints to receptor file ..."
    tempt.writeStructureDMSFile()
    print "Writing job input files ..."
    tempt.writeCntlFile()
    tempt.writeThermInputFile()    
    tempt.writeRemdInputFile()
    tempt.writeRunimpactFile()
    print "Write the submission scripts for SuperMIC and Stampede"
    tempt.writeQueueFiles()

    print
    print "Job preparation complete"
    print ""
    print "To run the minimization/thermalization calculation do:"
    exec_directory =  tempt.keywords.get('EXEC_DIRECTORY')
    if exec_directory is not None:
        print "export IMPACTHOME=" + exec_directory
    else:
        print "export IMPACTHOME=" + "<path_to_academic_impact_directory>"
    print "export OMP_NUM_THREADS=" + "<number_of_CPU_cores>"
    print "./runimpact_i %s_mintherm.inp" % tempt.jobname
    print ""
    print "When completed run the production calculation with:"
    print "<path_to_asyncre>/tempt_async_re.py %s_asyncre.cntl" % tempt.jobname
    print ""
