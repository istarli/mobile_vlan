from database import *

def init_db():
    db = database()
    db.dropDEVICE()
    db.dropGATEWAY()
    db.createGATEWAY()
    db.insertGATEWAY('00:00:00:00:00:ff','10.0.0.200')

if __name__ == '__main__':
    init_db()