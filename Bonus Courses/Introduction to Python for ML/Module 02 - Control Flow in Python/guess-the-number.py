import random

number = random.randint(1, 1000)

while True:
    inp = int(input())
    
    if (inp >= number):
        print("Number is smaller")
    elif (inp <= number):
        print("Number is bigger")
        
    if inp == number:
        print("Found it!")
        break
        
    

