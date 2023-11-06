import pymysql as MySQLdb #ch_v0r90 (added by m.taheri)
def connection():
    conn = MySQLdb.connect(host="localhost",
                           user = "root",
                           passwd = "raspberry",
                           db = "pythonprogramming")
    c = conn.cursor()
    return c, conn
