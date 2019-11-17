# Booking prices analysis

<br>

## Basic info:   
   * **author**: Slawomir Drzymala   
   * **code**: <a href="https://github.com/seequality" target="_blank">github/seequality</a>
   * **last update date**: 2019-10-27

## Goal
Check the average prices in the given city and given area and check if the proposed limit is accurate.

## Description:
To achieve the given goal the following steps has been made:
   1. Get hotel/apartments/etc (property) details and prices for given city for the same length of stay for different days 
   1. Specify the office location and calculate the distance between the office and each property
   1. Analye the data and check the distribution of price per person per night
      * in total
      * excluding outliers (most luxurious properties)
      * for hotels only
      * for trusted properties only (with review score > 5)
      * for properties that are within the walking distance to the office
      * all together

## Sample output
You can check the sample output visiting the following websites:
* http://sdrzymala.pythonanywhere.com/share/Warsaw.html
* http://sdrzymala.pythonanywhere.com/share/Katowice.html

## Code
* Please remember to to update the sample_config.json file and to rename the file to config.json or any other name (just please verify if the config file name corresponds the config file name specifed in given docker-compose)
* Make sure that the subnet is set up correctly for your machine. In case you are using docker-toolbox please verify with (docker-machine ip) or if running or any other linux please check with ifconfig
* This code was tested on Windows 10 with docker-toolbox, Ubuntu linux VM and linux on QNAP and seems to be working fine on all similar environments

## Final note
If you will find any issue or will have any question please create an issue or please send me an email ( slawomirdrzymala@outlook.com )   
I am not a professional Python developer so I will be grateful for any comments :)