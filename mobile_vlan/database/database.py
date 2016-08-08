#coding=utf-8
import sqlite3
import logging
import time
import string
# ***************************************************
# *
# * Description: Python操作SQLite3数据库辅助类(查询构造器)
# * Author: wangye
# *
# ***************************************************

def _wrap_value(value):
    return repr(value)

def _wrap_values(values):
    return list(map(_wrap_value, values))

def _wrap_fields(fields):
    for key,value in fields.items():
        fields[key] = _wrap_value(value)
    return fields

def _concat_keys(keys):
    return ",".join(keys)

def _concat_values(values):
    return ",".join(values)

def _concat_fields(fields, operator = (None, ",")):
    if operator:
        unit_operator, group_operator = operator
    # fields = _wrap_fields(fields)
    compiled = []
    for key,value in fields.items():
        compiled.append("[" + key + "]")
        if unit_operator:
            compiled.append(unit_operator)
            compiled.append(value)
        compiled.append(group_operator)
    compiled.pop() # pop last group_operator
    return " ".join(compiled)

class DataCondition(object):
    """
        本类用于操作SQL构造器辅助类的条件语句部分

        例如:
        DataCondition(("=", "AND"), id = 26)
        DataCondition(("=", "AND"), True, id = 26)
    """

    def __init__(self, operator = ("=", "AND"), ingroup = True, **kwargs):
        """
            构造方法
            参数:
                operator 操作符，分为(表达式操作符, 条件运算符)
                ingroup  是否分组，如果分组，将以括号包含
                kwargs   键值元组，包含数据库表的列名以及值
                         注意这里的等于号不等于实际生成SQL语句符号
                         实际符号是由operator[0]控制的
            例如:
            DataCondition(("=", "AND"), id = 26)
            (id=26)
            DataCondition((">", "OR"), id = 26, age = 35)
            (id>26 OR age>35)
            DataCondition(("LIKE", "OR"), False, name = "John", company = "Google")
            name LIKE 'John' OR company LIKE "Google"
        """
        self.ingroup = ingroup
        self.fields = kwargs
        self.operator = operator

    def __unicode__(self):
        self.fields = _wrap_fields(self.fields)
        result = _concat_fields(self.fields, self.operator)
        if self.ingroup:
            return "(" + result + ")"
        return result

    def __str__(self):
        return self.__unicode__()

    def toString(self):
        return self.__unicode__()

class DataHelper(object):

    """
        SQLite3 数据查询辅助类
    """

    def __init__(self, filename):
        """
            构造方法
            参数: filename 为SQLite3 数据库文件名
        """
        self.file_name = filename

    def open(self):
        """
            打开数据库并设置游标
        """
        self.connection = sqlite3.connect(self.file_name)
        self.cursor = self.connection.cursor()
        return self

    def close(self):
        """
            关闭数据库，注意若不显式调用此方法，
            在类被回收时也会尝试调用
        """
        if hasattr(self, "connection") and self.connection:
            self.connection.close()

    def __del__(self):
        """
            析构方法，做一些清理工作
        """
        self.close()

    def commit(self):
        """
            提交事务
            SELECT语句不需要此操作，默认的execute方法的
            commit_at_once设为True会隐式调用此方法，
            否则就需要显示调用本方法。
        """
        self.connection.commit()

    def execute(self, sql = None, commit_at_once = True):
        """
            执行SQL语句
            参数:
                sql  要执行的SQL语句，若为None，则调用构造器生成的SQL语句。
                commit_at_once 是否立即提交事务，如果不立即提交，
                对于非查询操作，则需要调用commit显式提交。
        """
        if not sql:
            sql = self.sql
        self.cursor.execute(sql)
        if commit_at_once:
            self.commit()

    def fetchone(self, sql = None):
        """
            取一条记录
        """
        self.execute(sql, False)
        return self.cursor.fetchone()

    def fetchall(self, sql = None):
        """
            取所有记录
        """
        self.execute(sql, False)
        return self.cursor.fetchall()

    def __concat_keys(self, keys):
        return _concat_keys(keys)

    def __concat_values(self, values):
        return _concat_values(values)

    def table(self, *args):
        """
            设置查询的表，多个表名用逗号分隔
        """
        self.tables = args
        self.tables_snippet = self.__concat_keys(self.tables)
        return self

    def __wrap_value(self, value):
        return _wrap_value(value)

    def __wrap_values(self, values):
        return _wrap_values(values)

    def __wrap_fields(self, fields):
        return _wrap_fields(fields)

    def __where(self):
        # self.condition_snippet
        if hasattr(self, "condition_snippet"):
            self.where_snippet = " WHERE " + self.condition_snippet

    def __select(self):
        template = "SELECT %(keys)s FROM %(tables)s"
        body_snippet_fields = {
            "tables" : self.tables_snippet,
            "keys" : self.__concat_keys(self.body_keys),
        }
        self.sql = template % body_snippet_fields

    def __insert(self):
        template = "INSERT INTO %(tables)s (%(keys)s) VALUES (%(values)s)"
        body_snippet_fields = {
            "tables" : self.tables_snippet,
            "keys" : self.__concat_keys(list(self.body_fields.keys())),
            "values" : self.__concat_values(list(self.body_fields.values()))
        }
        self.sql = template % body_snippet_fields

    def __update(self):
        template = "UPDATE %(tables)s SET %(fields)s"
        body_snippet_fields = {
            "tables" : self.tables_snippet,
            "fields" : _concat_fields(self.body_fields, ("=",","))
        }
        self.sql = template % body_snippet_fields

    def __delete(self):
        template = "DELETE FROM %(tables)s"
        body_snippet_fields = {
            "tables" : self.tables_snippet
        }
        self.sql = template % body_snippet_fields

    def __drop(self):
        template = "drop table if exists %(tables)s"
        body_snippet_fields = {
            "tables": self.tables_snippet
        }
        self.sql = template % body_snippet_fields

    def __build(self):
        {
            "SELECT": self.__select,
            "INSERT": self.__insert,
            "UPDATE": self.__update,
            "DELETE": self.__delete,
            "DROP": self.__drop
        }[self.current_token]()

    def __unicode__(self):
        return self.sql

    def __str__(self):
        return self.__unicode__()

    def select(self, *args):
        self.current_token = "SELECT"
        self.body_keys = args
        self.__build()
        return self

    def insert(self, **kwargs):
        self.current_token = "INSERT"
        self.body_fields = self.__wrap_fields(kwargs)
        self.__build()
        return self

    def update(self, **kwargs):
        self.current_token = "UPDATE"
        self.body_fields = self.__wrap_fields(kwargs)
        self.__build()
        return self

    def delete(self, *conditions):
        self.current_token = "DELETE"
        self.__build()
        #if *conditions:
        self.where(*conditions)
        return self

    def where(self, *conditions):
        conditions = list(map(str, conditions))
        self.condition_snippet = " AND ".join(conditions)
        self.__where()
        if hasattr(self, "where_snippet"):
            self.sql += self.where_snippet
        return self

    def drop(self):
        self.current_token = "DROP"
        self.__build()
        return self


class database():

    def __init__(self,dbName='CONTROLLER_DATA.db'):
        self.opendatabase(dbName)

    def __del__(self):
        self.closeDB()

    # open database
    def opendatabase(self, database_name):
        self.db = DataHelper(database_name)
        self.db.open()
        return

    # drop table: DEVICE
    def dropDEVICE(self):
        self.db.table("DEVICE").drop().execute()
        return

    # create table: DEVICE
    def createDEVICE(self):
        crt_device_sql = '''CREATE TABLE DEVICE
                 (MAC_ADDR    VARCHAR(100)   PRIMARY KEY NOT NULL,
                  VLAN_ID       INT          NOT NULL);'''
        self.db.execute(crt_device_sql)
        return

    # drop table: GATEWAY
    def dropGATEWAY(self):
        self.db.table("GATEWAY").drop().execute()
        return

    # create table: GATEWAY
    def createGATEWAY(self):
        crt_device_sql = '''CREATE TABLE GATEWAY
                 (MAC_ADDR    VARCHAR(100)   PRIMARY KEY NOT NULL,
                  IP_ADDR     VARCHAR(100)   NOT NULL);'''
        self.db.execute(crt_device_sql)
        return

    # drop table: DPID
    def dropDPID(self,dpid):
        table_name = 'DPID{dpid}'.format(dpid=dpid)
        self.db.table(table_name).drop().execute()
        return

    def dropMulDPID(self,dpid_list):
        for dpid in dpid_list:
            self.dropDPID(dpid)
        return

    # create table: DPID
    def createDPID(self,dpid):
        crt_device_sql = '''CREATE TABLE DPID{dpid}
                 (MAC_ADDR    VARCHAR(100)   PRIMARY KEY NOT NULL,
                  PORT_ID       INT          NOT NULL,
                  IP_ADDR     VARCHAR(100)   NOT NULL,
                  SLAVE         INT          NOT NULL);'''.format(dpid=dpid)
        self.db.execute(crt_device_sql)

    def createMulDPID(self,dpid_list):
        for dpid in dpid_list:
            self.createDPID(dpid)
        return

    # insert into DEVICE
    def insertDEVICE(self, mac_addr, vlan_id):
        self.db.table("DEVICE").insert(MAC_ADDR=mac_addr,VLAN_ID=vlan_id).execute()
        return

    # select from DEVICE
    def selectDEVICE(self):
        data_set = self.db.table("DEVICE").select("MAC_ADDR,VLAN_ID").fetchall()
        return data_set

    # insert into GATEWAY
    def insertGATEWAY(self, mac_addr, ip_addr):
        self.db.table("GATEWAY").insert(MAC_ADDR=mac_addr,IP_ADDR=ip_addr).execute()
        return

    # select from GATEWAY
    def selectGATEWAY(self):
        data_set = self.db.table("GATEWAY").select("MAC_ADDR,IP_ADDR").fetchall()
        return data_set

    # insert into DPID
    def insertDPID(self, dpid, mac_addr, port_id, ip_addr, slave):
        table_name = 'DPID{dpid}'.format(dpid=dpid)
        self.db.table(table_name).insert(MAC_ADDR=mac_addr,PORT_ID=port_id,IP_ADDR=ip_addr,SLAVE=slave).execute()
        return

    # select from DPID
    def selectDPID(self,dpid):
        table_name = 'DPID{dpid}'.format(dpid=dpid)
        data_set = self.db.table(table_name).select("MAC_ADDR,PORT_ID,IP_ADDR,SLAVE").fetchall()
        return data_set

    # select from mutiple DPIDs 
    def selectMulDPID(self,dpid_list):
        data = {}
        for dpid in dpid_list:
            dpid_name = 'dpid{dpid}'.format(dpid=dpid)
            data[dpid_name] = self.selectDPID(dpid)
        return data

	# find DEVICE by VLAN_ID/MAC_ADDR
    def findDEVICEByX(self, x, value):
        data_set = []
        if 'VLAN_ID' == x:
            data_set = self.db.table("DEVICE").select("MAC_ADDR").where(DataCondition(VLAN_ID=value)).fetchall()
        elif 'MAC_ADDR' == x:
            data_set = self.db.table("DEVICE").select("VLAN_ID").where(DataCondition(MAC_ADDR=value)).fetchall()
        else:
            print 'Please input the right option!'
        return data_set

    # find GATEWAY by MAC_ADDR/IP_ADDR
    def findGATEWAYByX(self, x, value):
        data_set = []
        if 'IP_ADDR' == x:
            data_set = self.db.table("GATEWAY").select("MAC_ADDR").where(DataCondition(IP_ADDR=value)).fetchall()
        elif 'MAC_ADDR' == x:
            data_set = self.db.table("GATEWAY").select("IP_ADDR").where(DataCondition(MAC_ADDR=value)).fetchall()
        else:
            print 'Please input the right option!'
        return data_set

    # find DPID by X
    def findDPIDByX(self, dpid, x, value):
        table_name = 'DPID{dpid}'.format(dpid=dpid)
        if 'MAC_ADDR' == x:
            data_set = self.db.table(table_name).select("PORT_ID,IP_ADDR,SLAVE").where(DataCondition(MAC_ADDR=value)).fetchall()
        elif 'PORT_ID' == x:
            data_set = self.db.table(table_name).select("MAC_ADDR,IP_ADDR,SLAVE").where(DataCondition(PORT_ID=value)).fetchall()
        elif 'IP_ADDR' == x:
            data_set = self.db.table(table_name).select("MAC_ADDR,PORT_ID,SLAVE").where(DataCondition(IP_ADDR=value)).fetchall()
        elif 'SLAVE' == x:
            data_set = self.db.table(table_name).select("MAC_ADDR,PORT_ID,IP_ADDR").where(DataCondition(SLAVE=value)).fetchall()
        else:
            print 'Please input the right option!'
        return data_set

    def findMulDPIDByX(self, dpid_list, x, value):
        data = {}
        for dpid in dpid_list:
            dpid_name = 'dpid{dpid}'.format(dpid=dpid)
            data[dpid_name] = self.findDPIDByX(dpid,x, value)
        return data

    def isMulEmpty(self,data):
        for dsName in data:
            if 0 != len(data[dsName]):
                return 0
        return 1

    def numMul(self,data):
        num = 0
        for dsName in data:
            num = num + len(data[dsName])
        return num

    # update the DEVICE
    def updateDEVICE(self, mac_addr, vlan_id):
        self.db.table("DEVICE").update(VLAN_ID=vlan_id).where(DataCondition(MAC_ADDR=mac_addr)).execute()
        return

    # update the GATEWAY
    def updateGATEWAY(self, mac_addr, ip_addr):
        self.db.table("GATEWAY").update(IP_ADDR=ip_addr).where(DataCondition(MAC_ADDR=mac_addr)).execute()
        return

    # update the DPID
    def updateDPID(self, dpid, mac_addr, port_id, ip_addr, slave):
        table_name = 'DPID{dpid}'.format(dpid=dpid)
        self.db.table(table_name).update(PORT_ID=port_id,IP_ADDR=ip_addr,SLAVE=slave).where(DataCondition(MAC_ADDR=mac_addr)).execute()    
        return

    # delete DEVICE by x
    def deleteDEVICEByX(self, x, value):
        if 'MAC_ADDR' == x:
            self.db.table("DEVICE").delete(DataCondition(MAC_ADDR=value)).execute()
        elif 'VLAN_ID' == x:
            self.db.table("DEVICE").delete(DataCondition(VLAN_ID=value)).execute()
        else:
            print 'Please input the right option!'
        return

    # delete GATEWAY by x
    def deleteGATEWAYByX(self, x, value):
        if 'MAC_ADDR' == x:
            self.db.table("GATEWAY").delete(DataCondition(MAC_ADDR=value)).execute()
        elif 'IP_ADDR' == x:
            self.db.table("GATEWAY").delete(DataCondition(IP_ADDR=value)).execute()
        else:
            print 'Please input the right option!'
        return

    # delete DPID by X
    def deleteDPIDByX(self, dpid, x, value):
        table_name = 'DPID{dpid}'.format(dpid=dpid)
        if 'MAC_ADDR' == x:
            self.db.table(table_name).delete(DataCondition(MAC_ADDR=value)).execute()
        elif 'PORT_ID' == x:
            self.db.table(table_name).delete(DataCondition(PORT_ID=value)).execute()
        elif 'IP_ADDR' == x:
            self.db.table(table_name).delete(DataCondition(IP_ADDR=value)).execute()
        elif 'SLAVE' == x:
            self.db.table(table_name).delete(DataCondition(SLAVE=value)).execute()
        else:
            print 'Please input the right option!'
        return

    def deleteMulDPIDByX(self, dpid_list, x, value):
        for dpid in dpid_list:
            self.deleteDPIDByX(dpid, x, value)
        return

    # close
    def closeDB(self):
        self.db.close()

#debug function
def printDataSet(data_set):
    if len(data_set):
        for row in data_set:
            print(row)
    else:
        print 'Empty!'

