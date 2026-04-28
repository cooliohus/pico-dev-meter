import json 

#regs = [150000,3500,1,2047,1.4,-121,6,7,8]
regs = []
print(regs)

#with open('output.json', 'w') as file:
#    json.dump(regs, file)

with open('output.json', 'r') as file:
    regs = json.load(file)

print(regs)
#with open("demofile.txt","w") as f:
#  f.write(regs)
#  f.seek(0)
#  print(f.read()) 