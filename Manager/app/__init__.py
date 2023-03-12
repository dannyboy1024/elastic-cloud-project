import os
from flask import Flask
from flask_cors import CORS
import boto3
import mysql.connector
from mysql.connector import (connection, errorcode)
from botocore.exceptions import ClientError

class FILEINFO:
    def __init__(self, key, location, size):
        self.key = key
        self.location = location
        self.size = size

class RDBMS:

    # Create a db and a table
    #    File Info
    def __init__(self):

        connection, cursor = self.connect()
        
        ####### Create a database #######################
        try:
            cursor.execute("CREATE DATABASE A2_RDBMS")
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_DB_CREATE_EXISTS:
                print("Database A2_RDBMS already exists.")
            else:
                raise err
        cursor.execute("Use A2_RDBMS")

        ####### Create a File Info table #########################
        cursor.execute("DROP TABLE fileInfo")
        sql = """
        CREATE TABLE fileInfo (
        fileKey VARCHAR(150) NOT NULL,
        location VARCHAR(150) NOT NULL,
        size VARCHAR(150) NOT NULL,
        PRIMARY KEY (fileKey)
        );
        """
        try:
            cursor.execute(sql)
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                print("Table fileInfo already exists.")
            else:
                print(err.msg)

        ###### Commit the changes on the 3 tables and disconnct ######
        connection.commit()
        cursor.close()
        connection.close()

    def connect(self, db=None):
        connection = mysql.connector.connect(host='database-a2w23.c352jaremkjb.us-east-1.rds.amazonaws.com', user='admin', passwd='ece1779a2', port=3309, database=db)
        cursor = connection.cursor()
        return connection, cursor

    #######################################
    ###########    Create    ##############
    ####################################### 
    def insertFileInfo(self, fileInfo):
        
        connection, cursor = self.connect(db='A2_RDBMS')
        
        # Current table is cacheConfigs
        tableName = "fileInfo"
        sql = """
        INSERT INTO {} (fileKey, location, size)
        VALUES (%s, %s, %s)
        """.format(tableName)
        vals = (fileInfo.key, fileInfo.location, fileInfo.size)
        cursor.execute(sql, vals)

        # Commit the changes and disconnect
        connection.commit()
        cursor.close()
        connection.close()


    #######################################
    ###########     Read     ##############
    #######################################
    def readFileInfo(self, fileKey):

        connection, cursor = self.connect(db='A2_RDBMS')

        # query
        tableName = "fileInfo"
        sql = """
        SELECT * 
        FROM {}
        WHERE fileKey = %s
        """.format(tableName)
        val = (fileKey,)
        cursor.execute(sql, val)
        record = cursor.fetchone()

        # disconnect
        cursor.close()
        connection.close()

        # get and return file info
        return None if record==None else FILEINFO(*record)

    def readAllFileKeys(self):

        connection, cursor = self.connect(db='A2_RDBMS')

        # query
        tableName = "fileInfo"
        sql = """
        SELECT filekey
        FROM {}
        """.format(tableName)
        cursor.execute(sql)
        records = cursor.fetchall()

        # disconnect
        cursor.close()
        connection.close()

        # get and return all the keys from db 
        return [record[0] for record in records]
    
    def readAllFilePaths(self):

        connection, cursor = self.connect(db='A2_RDBMS')

        # query
        tableName = "fileInfo"
        sql = """
        SELECT location
        FROM {}
        """.format(tableName)
        cursor.execute(sql)
        records = cursor.fetchall()

        # disconnect
        cursor.close()
        connection.close()

        # get and return all the file paths from db 
        return [record[0] for record in records]

    #######################################
    ###########     Update    #############
    ####################################### 
    def updFileInfo(self, fileInfo):

        connection, cursor = self.connect(db='A2_RDBMS')
        
        # Current table is cacheConfigs
        tableName = "fileInfo"
        sql = """
        UPDATE {}
        SET location = %s, size = %s
        WHERE fileKey = %s
        """.format(tableName)
        val = (fileInfo.location, fileInfo.size, fileInfo.key)
        cursor.execute(sql, val)

        # Commit the changes and disconnect
        connection.commit()
        cursor.close()
        connection.close()


    #######################################
    ###########     Delete    #############
    #######################################
    def delFileInfo(self, fileKey):
        
        connection, cursor = self.connect(db='A2_RDBMS')
        
        # table fileInfo
        tableName = "fileInfo"
        sql = """
        DELETE FROM {} 
        WHERE fileKey = %s
        """.format(tableName)
        val = (fileKey,)
        cursor.execute(sql, val)

        # Commit the changes and disconnect
        connection.commit()
        cursor.close()
        connection.close()

    def delAllFileInfo(self):

        connection, cursor = self.connect(db='A2_RDBMS')

        # table fileInfo
        tableName = "fileInfo"
        sql = """
        TRUNCATE TABLE {}
        """.format(tableName)
        cursor.execute(sql)

        # disconnect
        connection.commit()
        cursor.close()
        connection.close()


manager = Flask(__name__)
db = RDBMS()
CORS(manager)
from app import main




