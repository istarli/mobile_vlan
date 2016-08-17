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

    def __init__(self,dbName='USERDATA.db'):
        self.opendatabase(dbName)

    def __del__(self):
        self.closeDB()

    # open database
    def opendatabase(self, database_name):
        self.db = DataHelper(database_name)
        self.db.open()
        return

    # drop table: USER
    def dropUSER(self):
        self.db.table("USER").drop().execute()
        return

    # create table: USER
    def createUSER(self):
        crt_user_sql = '''CREATE TABLE USER
            (USER_ID        INT       PRIMARY KEY NOT NULL,
             PASSWORD   VARCHAR(100)  NOT NULL,
             VLAN_ID		INT       NOT NULL,
             DEPARTMENT VARCHAR(100),
 			 POSITION   VARCHAR(100),
             NAME       VARCHAR(100));'''
        self.db.execute(crt_user_sql)
        return

    # drop table: DEVICE
    def dropDEVICE(self):
        self.db.table("DEVICE").drop().execute()
        return

    # create table: DEVICE
    def createDEVICE(self):
        crt_device_sql = '''CREATE TABLE DEVICE
                 (IP_ADDR    VARCHAR(100)   PRIMARY KEY NOT NULL,
                  USER_ID		INT          NOT NULL);'''
        self.db.execute(crt_device_sql)
        return

    # insert into USER
    def insertUSER(self, user_id, password, vlan_id, department='SDN_FiLL', position='Boss', name='Mike'):
        self.db.table("USER").insert(USER_ID=user_id, PASSWORD=password, VLAN_ID=vlan_id, DEPARTMENT=department, POSITION=position, Name=name).execute()
        return

    # insert into DEVICE
    def insertDEVICE(self, ip_addr, user_id):
        self.db.table("DEVICE").insert(IP_ADDR=ip_addr, USER_ID=user_id).execute()
        return

    # select from USER
    def selectUSER(self):
        data_set = self.db.table("USER").select("USER_ID,PASSWORD,VLAN_ID,DEPARTMENT,POSITION,NAME").fetchall()
        return data_set

    # select from DEVICE
    def selectDEVICE(self):
        data_set = self.db.table("DEVICE").select("IP_ADDR,USER_ID").fetchall()
        return data_set

    # find USER by x
    def findUSERByX(self, x, value):
        data_set = []
        if 'VLAN_ID' == x:
            data_set = self.db.table("USER").select("USER_ID,PASSWORD,DEPARTMENT,POSITION,NAME").where(DataCondition(VLAN_ID=value)).fetchall()
        elif 'USER_ID' == x:
            data_set = self.db.table("USER").select("PASSWORD,VLAN_ID,DEPARTMENT,POSITION,NAME").where(DataCondition(USER_ID=value)).fetchall()
        elif 'PASSWORD' == x:
            data_set = self.db.table("USER").select("USER_ID,VLAN_ID,DEPARTMENT,POSITION,NAME").where(DataCondition(PASSWORD=value)).fetchall()
        elif 'NAME' == x:
            data_set = self.db.table("USER").select("USER_ID,PASSWORD,VLAN_ID,DEPARTMENT,POSITION").where(DataCondition(NAME=value)).fetchall()
        else:
            print 'Please input right option!'
        return data_set

	# find DEVICE by x
    def findDEVICEByX(self, x, value):
    	data_set = []
    	if 'USER_ID' == x:
        	data_set = self.db.table("DEVICE").select("IP_ADDR").where(DataCondition(USER_ID=value)).fetchall()
        elif 'IP_ADDR' == x:
        	data_set = self.db.table("DEVICE").select("USER_ID").where(DataCondition(IP_ADDR=value)).fetchall()
        else:
        	print 'Please input right option!'
        return data_set

    # update USER
    def updateUSER(self, user_id, password, vlan_id, department='SDN_FiLL', position='Boss', name='Mike'):
        self.db.table("USER").update(PASSWORD=password,VLAN_ID=vlan_id,DEPARTMENT=department,POSITION=position, NAME=name).where( DataCondition(USER_ID=user_id)).execute()
        return

    # update the DEVICE
    def updateDEVICE(self, ip_addr, user_id):
        self.db.table("DEVICE").update(USER_ID=user_id).where(DataCondition(IP_ADDR=ip_addr)).execute()
        return

    # delete USER by X
    def deleteUSERByX(self, x, value):
        if 'USER_ID' == x:
            self.db.table("USER").delete(DataCondition(USER_ID=value)).execute()
        elif 'VLAN_ID' == x:
            self.db.table("USER").delete(DataCondition(VLAN_ID=value)).execute()
        elif 'PASSWORD' == x:
            self.db.table("USER").delete(DataCondition(PASSWORD=value)).execute()
        elif 'NAME' == x:
            self.db.table("USER").delete(DataCondition(NAME=value)).execute()
        else:
            print 'Please input right option!'
        return

    # delete DEVICE by x
    def deleteDEVICEByX(self, x, value):
    	if 'IP_ADDR' == x:
        	self.db.table("DEVICE").delete(DataCondition(IP_ADDR=value)).execute()
        elif 'VLAN_ID' == x:
        	self.db.table("DEVICE").delete(DataCondition(VLAN_ID=value)).execute()
        else:
        	print 'Please input right option!'
        return

    # close
    def closeDB(self):
        self.db.close()
        return

#debug functions
def printDataSet(data_set):
	if len(data_set):
		for row in data_set:
			print(row)
	else:
		print 'Empty!'


