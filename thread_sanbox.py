import threading
import time

def tarefa():
    print("Thread iniciada")
    time.sleep(5)
    print("Thread terminou")

t = threading.Thread(target=tarefa, daemon=False)
t.start()

print("Programa principal terminou")
