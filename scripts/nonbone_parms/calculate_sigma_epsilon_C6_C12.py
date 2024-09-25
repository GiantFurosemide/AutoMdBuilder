
# cal to J : 1 Kcal =  4.184 KJ
def cal2j(cal):
	return cal * 4.184

def j2cal(j):
	return j / 4.184

def convert2C6(sigma,epsilon): #  nm,kJ/mol
	return 4*epsilon*(sigma**6)

def convert2C12(sigma,epsilon): #  nm,kJ/mol
	return 4*epsilon*(sigma**12)

def print_C12_C6(sigma,epsilon):
	#print(f"C12: {convert2C12(sigma,epsilon)} ; C6: {convert2C6(sigma,epsilon)}")
	#print(f"C12: {convert2C12(sigma,epsilon):1.6e} ; C6: {convert2C6(sigma,epsilon):1.6e}")
	print(f"C6: {convert2C6(sigma,epsilon):1.6e}; C12: {convert2C12(sigma,epsilon):1.6e} ")

def mid_point(vec1:tuple,vec2:tuple)->tuple:
	x1,y1,z1 = vec1
	x2,y2,z2 = vec2
	return ((x1+x2)/2,(y1+y2)/2,(z1+z2)/2)