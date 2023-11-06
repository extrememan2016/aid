import threading
import pymysql
import os,subprocess,threading
import pprint

from concurrent.futures import Executor
from concurrent.futures import ThreadPoolExecutor
from time import sleep


def initdb():
    global cnx
    # Connect to MySQL database
    cnx = pymysql.connect(user='root', password='raspberry',
                              host='localhost', database='pythonprogramming')
    # Create cursor object
    
    

initdb()


# Select records from your table
query = "SELECT did,IP_cam,pingok FROM camera"

def pingit(did,ip_address,pingok):
    
    response = os.system("ping -c 1 " + ip_address)
    if response == 0:
        pingokvar = 1
    else:
        pingokvar = 0
        print("fault")
    if pingok != pingokvar:
        try:
            insert_query = f"UPDATE camera SET pingok = '{pingokvar}' WHERE did = '{did}'"
            cursor1 = cnx.cursor()
            cursor1.execute(insert_query)
            cnx.commit()
            cursor1.close()
        except Exception as e:
            print("inserting raised"+ str(e))


while True:
    threads = []
    print("############# loop start and cursur refresh #############")
    initdb()
    cursor = cnx.cursor()
    cursor.execute(query)
    alldata=cursor.fetchall()
    pingokvar = 0

           
    for (did,ip_address,pingok) in alldata:
        print("############# start unic ip ping #############" + ip_address)
        th1=threading.Thread(target=pingit,args=(did,ip_address,pingok))
        threads.append(th1)
        th1.start()
        sleep(0.1)
            

    for t in threads:
        t.join()

    sleep(3)
    cnx.close()
    cursor.close()

try:   
    cursor.close()
    cnx.close()
except:
    print("connection already closed")



