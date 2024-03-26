import subprocess
import time
import threading
import pymysql  


def initdb():
    global cnx
    cnx = pymysql.connect(user='root', password='raspberry',
                              host='localhost', database='pythonprogramming')
   

def run_script(script_path, arguments):
    """Runs a Python script with given arguments and monitors its completion."""
    proc = subprocess.Popen(["python", script_path] + list(str(arguments)))
    
    while True:
        time.sleep(10)  # Adjust sleep time as needed
        returncode = proc.poll()
        if returncode is not None:
            # Script has finished
            if returncode == 0:
                print(f"Script {script_path} completed successfully.")
            else:
                print(f"Script {script_path} exited with code {returncode}. Restarting...")
                run_script(script_path, arguments)
            break

def main():
    
    """Fetches script and argument details from the database and starts threads."""
    initdb() 
    cur = cnx.cursor()
    
    cur.execute("SELECT t.did as arguments FROM `camera` t WHERE t.isenable = 1 and t.isvalid=1")
    camid_data = cur.fetchall()
    script_path = ".\\app.py"
    pinger_script_path = [".\\pinger2.py"]

    threads = []
    
    for arguments in camid_data:
        
        thread = threading.Thread(target=run_script, args=(script_path, arguments))
        threads.append(thread)
        thread.start()

    for scripts in pinger_script_path:
        
        thread = threading.Thread(target=run_script, args=(scripts, '0'))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    cur.close()

if __name__ == "__main__":
    main()
