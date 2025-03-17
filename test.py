import sys
import subprocess

def task1():
	print('--begin task 1')
	
def task2():
	print('--begin task 2')

if len(sys.argv) > 1 and sys.argv[1] == "task1complete":
    task2()
    print('--script finished')
else:
    print('--begin script')
    task1()
    subprocess.Popen([sys.executable] + sys.argv + ["task1complete"], close_fds=True) # relaunch the script
    sys.exit() # ensure the original script closes and locks release