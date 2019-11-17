import pyodbc
import json
import time


# read connection string
try:
    with open('config.json') as json_file:
        a = json_file
        config = json.load(json_file)
except:
    raise ValueError("The config file was not found or file is corrupted")
db_connectionstring = config["tech"]["db_connectionstring"]
print (db_connectionstring)


# try to connect
is_connected = False
max_retries = 30
i = 1
while i <= max_retries and is_connected == False:
    try:
        cnxn = pyodbc.connect(db_connectionstring)
        is_connected = True
    except pyodbc.Error as e:
        sqlstate = e.args[0]
        if sqlstate == '08001':
            print ("The database is still starting, attempt {0}/{1}".format(i, max_retries))
            i = i + 1
            time.sleep(5)
            continue
        else:
            raise ValueError("There was unexpected error while trying to connect to the database. Error: {0}".format(sqlstate))




# return
if is_connected:
    print ("Database is up and running")
else:
    raise ValueError("After {0} attempts the database didn't start. Stopping. Please verify".format(max_retries))