from database import *

def init_database(dbName='USERDATA.db'):
    db = database(dbName)
    db.dropUSER()
    db.dropDEVICE()
    db.createUSER()
    db.createDEVICE()
    db.insertUSER(2013210131,'210131',2,department='Technical',position='CEO',name='Reimu')
    db.insertUSER(2013210132,'210132',2,department='Sales',position='COO',name='Yuyuko')
    db.insertUSER(2013210133,'210133',3,department='Accounting',position='CIO',name='Cirno')
    db.insertUSER(2013210134,'210134',2,department='Operations',position='CTO',name='Flandre')

if __name__ == '__main__':
    init_database()