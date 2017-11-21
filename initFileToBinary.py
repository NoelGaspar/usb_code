

with open('init_file.init') as f:
	lines = f.readlines()

res = []
for line in lines:
	x = line.split()
	l = []
	for v in x[1:]:
		b = bin( int(v,16) )[2:]
		b = '0'*(32-len(b)) + b
		l.append(b)
	
	res.append(' '.join(l))

s = '\n'.join(res)

with open('init_file_bin.txt','w') as f:
	f. write(s)