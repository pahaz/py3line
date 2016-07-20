"""
>>> import subprocess
>>> def run(command):
...     r = subprocess.run(command, stdout=subprocess.PIPE,
...                        stderr=subprocess.STDOUT, shell=True)
...     print(r.stdout.decode())
...     return r.returncode
>>> run('ls ./testsuit/list-directory')
file1
file2.txt
file3.py
file4.sh
<BLANKLINE>
0
>>> run('ls -lAh ./testsuit/list-directory')
total 32
-rw-r--r--  1 pahaz  staff    12B Jul 20 07:44 file1
-rw-r--r--  1 pahaz  staff   257B Jul 20 07:45 file2.txt
-rw-r--r--  1 pahaz  staff    24B Jul 20 07:43 file3.py
-rw-r--r--  1 pahaz  staff    28B Jul 20 07:43 file4.sh
<BLANKLINE>
0
>>> run('echo "Here are\\nsome\\nwords for you." | ./py3line.py "x.split()" -a "len(x)"')
2
1
3
<BLANKLINE>
0
>>> run("echo '10\\n21\\n22\\n94\\n5\\n6' | ./py3line.py 'int(x)' -a 'x % 2 == 0' -a 'x, \\"is even!\\"'")
10 is even!
22 is even!
94 is even!
6 is even!
<BLANKLINE>
0
>>> run("ls -l1 ./testsuit/list-directory/ | ./py3line.py 'sh(\\"wc\\", \\"-l\\", \\"./testsuit/list-directory/\\" + x)'")
       2 ./testsuit/list-directory/file1
       6 ./testsuit/list-directory/file2.txt
       2 ./testsuit/list-directory/file3.py
       2 ./testsuit/list-directory/file4.sh
<BLANKLINE>
0
>>> run("ls -l1 ./testsuit/list-directory/ | ./py3line.py 'sh(\\"false\\")'")
Command '('false',)' returned non-zero exit status 1
Command '('false',)' returned non-zero exit status 1
Command '('false',)' returned non-zero exit status 1
Command '('false',)' returned non-zero exit status 1
<BLANKLINE>
0
>>> run("ls -l1 ./testsuit/list-directory/ | ./py3line.py 'spawn(\\"wc\\", \\"-l\\", \\"./testsuit/list-directory/\\" + x)'")
file1
file2.txt
file3.py
file4.sh
<BLANKLINE>
0

"""
