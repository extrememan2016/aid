import pymysql
import os
import pprint
# Connect to MySQL database
cnx = pymysql.connect(user='root', password='raspberry',
                              host='localhost', database='pythonprogramming')
# Create cursor object
cursor = cnx.cursor()
cursor1 = cnx.cursor()
# Select records from your table
query = "SELECT did,IP_cam,pingok FROM camera"
while True:
    cursor.execute(query)
    alldata=cursor.fetchall()
    pingokvar = 0

    # Iterate over the records and ping each IP address 3 times
    for (did,ip_address,pingok) in alldata:
        for i in range(3):
            response = os.system("ping -c 1 " + ip_address)
            if response == 0:
                pingokvar = 1
                break
            else:
                pingokvar = 0

        # Insert the result into your table

        if pingok != pingokvar:
            try:
                insert_query = f"UPDATE camera SET pingok = '{pingokvar}' WHERE did = '{did}'"
                cursor1.execute(insert_query)
                cnx.commit()
            except Exception as e:
                print("inserting raised"+ str(e))

    # Close the cursor and connection
    
    #cursor.close()
    #cnx.close()