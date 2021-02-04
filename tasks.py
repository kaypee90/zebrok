from zebrok import app
import time


@app.Task
def greet(firstname, lastname):
    time.sleep(10)
    print(f"Hello, {firstname} {lastname}")
    time.sleep(10)
    print("DONE!!!")
