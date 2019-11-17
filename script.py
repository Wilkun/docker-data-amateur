#region import
from bookingtoolkit.toolkit import Toolkit
import argparse
import time
import json
#endregion


#region prepare and get arguments

# get and handle arguments
parser = argparse.ArgumentParser(description='Scrapping booking')
parser.add_argument('--run_type', 
                    type=str, 
                    help='type of run, [sb] - standby, [all] - all, [bl] - booking list, [bd] - booking details, [gm] -- google maps', 
                    default='sb'
                    )
args = parser.parse_args()
run_type = args.run_type

# read config from file
config_file_name = 'current_config.json'
#config_file_name = './config/config_debug_local.json'

try:
    with open(config_file_name) as json_file:
        config = json.load(json_file)
except:
    raise ValueError("The config file was not found or file is corrupted")

log_file_path = config["tech"]["log_path"]
selenium_driver_path = config["tech"]["selenium_driver_path"]
db_connectionstring = config["tech"]["db_connectionstring"]
    
currency = config["general"]["currency"]
language = config["general"]["language"]

calculate_distance = config["calculate_distance"]["calculate_distance"]
api_key = config["tech"]["google_api_key"]
    
search_list = config["search"]
calculate_distance_destinations = config["calculate_distance"]["destinations"]

#endregion


#region initialize toolkit
if run_type == 'sb':
    toolkit = Toolkit(log_file_path, db_connectionstring, selenium_driver_path)
    print ("stand by")
    while True:
        time.sleep(5)
elif run_type == 'all':
    toolkit = Toolkit(log_file_path, db_connectionstring, selenium_driver_path)
    toolkit.get_and_save_properties_from_booking(currency, language, search_list)
    toolkit.calculate_and_save_distance_results(calculate_distance, api_key, calculate_distance_destinations)
    print ("done")
elif run_type == 'bl':
    toolkit = Toolkit(log_file_path, db_connectionstring, selenium_driver_path)
    toolkit.get_and_save_properties_from_booking(currency, language, search_list)
    print ("done")
elif run_type == 'gm':
    toolkit = Toolkit(log_file_path, db_connectionstring, selenium_driver_path)
    toolkit.calculate_and_save_distance_results(calculate_distance, api_key, calculate_distance_destinations)
    print ("done")
else:
    raise ValueError('Unknown argument value')    
#endregion