from zebrok import app
import time


@app.Task
def greet(firstname, lastname):
    time.sleep(2)
    print(f"Hello, {firstname} {lastname}")
    time.sleep(2)
    print("DONE!!!")
