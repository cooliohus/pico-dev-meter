def f1():
    print("f1")
          
def f2(s):
    print("f2",s)


opcodes = {">f1":f1,">f2":f2}
cmd = "hello"

opcodes[">f2"](cmd)

#print(opcodes)