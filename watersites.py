#!/usr/bin/python
import sys, os, math
import sqlite3 as lite
import argparse



def read_watersite_param(con, filename):
	watersite = []
	with open (filename) as file:
		for line in file:
			if line.startswith('#'):continue
			line = line.strip("\n")
			if not line : continue
			watersite.append(line.split(";"))
		column = zip(*watersite)
		sql = column[0]
		hbtype = column[1]
		hbw = column[2]
		#params_dict = dict(zip(hbtype, hbw))
		#watersite_type.append((sql, params_dict))
		
		for i in range(0,len(sql)):
			index = sql[i]
			t = int(hbtype[i])
			hw = float(hbw[i])
			sql_select = "SELECT particle.id, agbnp2.hbtype FROM particle, agbnp2 WHERE " + "(" + index + ")" + " AND particle.id == agbnp2.id"

			with con:
	                	cur = con.cursor()
        	                cur.execute(sql_select)
                        	rows = cur.fetchall()
                        	for row in rows:
                                	id = row[0]
					htype=row[1]
					if t == htype:
	                                	sql_update = "UPDATE agbnp2 SET hbw = (hbw + %f) WHERE id = %s" % (hw,id)
						cur.execute(sql_update)
					elif htype == 0:
						sql_update = "UPDATE agbnp2 SET hbtype = %d , hbw = (hbw + %f) WHERE id = %s" % (t,hw,id)
                                                cur.execute(sql_update)
					else:
						msg ='hbtype %d of parameter file do not match hbtype %d of dms file' %(t,htype)
						sys.exit(msg)
"""def update_agbnp2(con, param_file, sql, hbtype, hbw):
	with con:
		cur = con.cursor()
		for i in range(0,len(sql)):
			index = sql[i]
			t = hbtype[i]
			w = hbw[i]
			sql_select = "SELECT particle.id FROM particle, agbnp2 WHERE " + "(" + index + ")" + " AND particle.id == agbnp2.id"
			cur.execute(sql_select)
			cur.fetchall()
			for row in rows:
				id = row[0]
				sql_update = "UPDATE agbnp2 SET hbtype = %d, hbw = %f WHERE id = %s" % (t,w,id)"""

def add_watersite_to_dms_file(dms_file, param_file):
	if not os.path.isfile(dms_file):
		raise IOError("file does not exist: %s " % dms_file)
	con = lite.connect(dms_file)
	read_watersite_param(con, param_file)
	con.close()

def parse_args():
	parser = argparse.ArgumentParser(usage="python watersites.py [options] <dms_file>", description='Requires dms file and watersite parameters; add the custom water sites to the dms file')
	parser.add_argument("dms_file")
	parser.add_argument("-param_file", help="path to parameter file(default: 'watersite.param')", default="watersite.param")
	return parser.parse_args()

def main():
	args = parse_args()
	try:
		add_watersite_to_dms_file(args.dms_file, args.param_file)
	except (IOError) as e:
		print >> sys.stderr, "Error: %s" % e
		sys.exit(1)

if __name__ == '__main__':
	main()
		

"""con = lite.connect('oahg3_rcpt.dms')
sql_select = "(SELECT id FROM particle WHERE resname = 'WS2' AND particle.id == agbnp2.id)"
sql_update = "UPDATE agbnp2 set hbtype = 1001, hbw = 2.0 WHERE id=" + sql_select

sql_show = "SELECT * from agbnp2 WHERE id=" + sql_select
with con:
	cur = con.cursor()
	cur.execute('SELECT * from agbnp2 WHERE id=(SELECT id FROM particle WHERE resname = \'WS1\' AND particle.id == agbnp2.id)')
	cur.execute(sql_update)

	cur.execute(sql_show)
	rows = cur.fetchall()
	for row in rows:
		print row


con = lite.connect('oahg3_rcpt.dms')
sql_select = "(SELECT id FROM particle WHERE resname = 'WS2' AND particle.id == agbnp2.id)"
sql_update = "UPDATE agbnp2 set hbtype = 1001, hbw = 2.0 WHERE id=" + sql_select

sql_show = "SELECT * from agbnp2 WHERE id=" + sql_select
with con:
	cur = con.cursor()
	cur.execute('SELECT * from agbnp2 WHERE id=(SELECT id FROM particle WHERE resname = \'WS1\' AND particle.id == agbnp2.id)')
	cur.execute(sql_update)

	cur.execute(sql_show)
	rows = cur.fetchall()
	for row in rows:
		print row

watersite_info = 'name GLOB 'CA' AND ((resid=189 OR resid=191 OR resid=192 OR resid=195 OR resid=214 OR resid=215 OR resid=217 OR resid=227) AND chain='A')'
recpt_cmd = "SELECT id,x,y,z,i_i_internal_atom_index FROM particle WHERE " + watersite_info
params_list = \'1.550 0.117 0.700 0.000 0.01200 0.00000 0.00000 1001 1.22'.split()
con = sqlite3.connect(dms_file)"""
