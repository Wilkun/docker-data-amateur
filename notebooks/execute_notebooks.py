import subprocess
import pyodbc
import pandas as pd
import time
import json 




print ("Read config file and set up parameters")



# read config from file
config_file_name = '/home/jovyan/work/current_config.json'
#config_file_name = 'config_debug_local.json'
sql_query_search = "select * from dbo.search"

try:
    with open(config_file_name) as json_file:
        config = json.load(json_file)
except:
    raise ValueError("The config file was not found or file is corrupted")

db_connection_string = config["tech"]["db_connectionstring"]
no_searches = config["search"]
no_destinations = config["calculate_distance"]["destinations"]

sql_query_search_count = """
                select 
                    cnt = count(*) 
                from dbo.search (nolock) 
                where search_endtime is not null
                """

sql_query_destination_count = """
                select
                    cnt = count(*)
                from dbo.calculate_distance (nolock)
                where calculate_distance_endtime is not null
                """



print ("Try to connect to database and wait till it succeed")
print (db_connection_string)
is_connected = False
max_retries = 12 # wait one minute
i = 1
while i <= max_retries and is_connected == False:
    try:
        pyodbc.connect(db_connection_string)
        cnxn = pyodbc.connect(db_connection_string)
        is_connected = True
        print ("Connected to database")
    except pyodbc.Error as e:
        sqlstate = e.args[0]
        if sqlstate == '08001':
            print ("The database is still starting, attempt {0}/{1}".format(i, max_retries))
            i = i + 1
            time.sleep(5)
            continue
        else:
            raise ValueError("There was unexpected error while trying to connect to the database. Error: {0}".format(sqlstate))

if is_connected == False:
    raise ValueError("There was unexpected error while trying to connect to the database.")




print ("Wait till all searches are done")
no_searches_in_config_file = len(no_searches)
no_destinations_in_config_file = len(no_destinations)

is_searching_finished = False
max_retries = 12*60*12*5 # limit 12 hours => 12 hours * 60 minutes * (12 * 5) while 5 seconds is the time sleep
i = 1
while i <= max_retries and is_searching_finished == False:
    try:
        
        df_search_count = int(pd.read_sql(sql_query_search_count,cnxn)["cnt"][0])
        df_destination_count = int(pd.read_sql(sql_query_destination_count,cnxn)["cnt"][0])

        if df_search_count == no_searches_in_config_file and df_destination_count == no_destinations_in_config_file:
            is_searching_finished = True
            print ("Searching done")
        else:
            i = i + 1
            time.sleep(10)
            print ("Still searching...")
            continue
    except pyodbc.Error as e:
        raise ValueError("There was unexpected error while trying to connect to the database. Error: {0}".format(sqlstate))

if is_searching_finished == False:
    raise ValueError("There was unexpected error while waiting for script to finish searching. Timeout")




print ("Execute first notebook")
process1 = subprocess.Popen(
            ["jupyter nbconvert --to notebook --inplace --execute '/home/jovyan/work/1-booking.ipynb' --ExecutePreprocessor.timeout=600"],
            shell=True,
            )
process1.wait()
print ("Execution of first notebook is finished, exit code: {0}".format(process1.returncode))

print ("Execute second notebook")
process2 = subprocess.Popen(
            ["jupyter nbconvert --to notebook --inplace --execute '/home/jovyan/work/2-booking.ipynb' --ExecutePreprocessor.timeout=600"],
            shell=True,
            )
process2.wait()
print ("Execution of second notebook is finished, exit code: {0}".format(process2.returncode))




