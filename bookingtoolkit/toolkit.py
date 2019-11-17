#region import
from sqlalchemy import Column, Integer, String
from datetime import datetime
import json
import logging
import os
import re
import sys
import time
import traceback
import urllib
import datetime
from functools import wraps
from random import randint
from dateutil import parser

# google maps
import googlemaps

# selenium and related
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# database related
from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import func
import pyodbc

#endregion


def timeit(method):

    def timed(*args, **kw):

        ts = time.time()
        result = method(*args, **kw)
        te = time.time()

        if 'log_time' in kw:
            name = kw.get('log_name', method.__name__.upper())
            kw['log_time'][name] = int((te - ts) * 1000)
        else:
            logging.info("{}({}) | [{:%Y-%m-%d %H:%M:%S} - {:%Y-%m-%d %H:%M:%S}] | {:2.2f} ms".format(
                                                    method.__name__, 
                                                    "...", #", ".join([str(x) for x in args[1:]]).strip(), 
                                                    datetime.datetime.fromtimestamp(te),
                                                    datetime.datetime.fromtimestamp(ts),
                                                    (te - ts) * 1000)
                                                )

        return result
    return timed



class Toolkit:


    @timeit
    def __init__(self, log_file_path: str, db_connectionstring: str, selenium_driver_path: str):

        #region configure logging
        logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    handlers=[
                        logging.FileHandler(log_file_path,mode="a"),
                        logging.StreamHandler()
                    ])
        #endregion


        #region adjust when running from docker
        if os.environ.get('IS_RUNNING_FROM_DOCKER') == 'Yes':
            self.__selenium_driver_path = r'/app/chromedriver'
        else:
            self.__selenium_driver_path = selenium_driver_path
        #endregion

        #region setup and prepare db

        
        # try to connect
        print (db_connectionstring)
        is_connected = False
        max_retries = 15
        i = 1
        while i <= max_retries and is_connected == False:
            try:
                pyodbc.connect(db_connectionstring)
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



        params = urllib.parse.quote_plus(db_connectionstring)
        Base = automap_base()
        engine = create_engine("mssql+pyodbc:///?odbc_connect={}".format(params))
        
        Base.prepare(engine, reflect=True)
        self.__current_search_id = -1
        self.__current_city_id = -1
        self.__current_calculate_distance_id = -1
        self.__search = Base.classes.search
        self.__search_result = Base.classes.search_result
        self.__city = Base.classes.city
        self.__destination = Base.classes.destination
        self.__distance_result = Base.classes.distance_result
        self.__calculate_distance = Base.classes.calculate_distance
        self.__session = Session(engine)
        
        #endregion


    @timeit
    def __dispose(self):
        self.__browser.quit()

    @timeit
    def __initialize_browser(self):
        #region configure selenium
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--log-level=2")
        chrome_options.add_argument("start-maximized")
        chrome_options.add_argument("disable-infobars")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36")
        #self.__browser = webdriver.Chrome(executable_path=self.__selenium_driver_path) # to run without headless mode
        self.__browser = webdriver.Chrome(executable_path=self.__selenium_driver_path, chrome_options=chrome_options)
        self.__browser.set_page_load_timeout(180)
        self.__browser.execute_script("document.body.style.zoom='100'")
        self.__browser.set_window_size(1366, 768)
        self.__browser.maximize_window()
        self.__browser_max_wait_delay = 180
        self.__browser.delete_all_cookies()
        time.sleep(5) # let him initialize...
        self.__base_url = r"https://www.booking.com"
        self.__booking_select_dates_max_no_retries = 12
        #endregion


    @timeit
    def get_and_save_properties_from_booking(self, currency, language, search_list):
        
        for search in search_list:
            
            destination_city = search["destination_city"]
            destination_country = search["destination_country"]
            check_in_date = search["check_in_date"]
            check_out_date = search["check_out_date"]
            no_adults = search["no_adults"]
            no_childrens = search["no_childrens"]
            no_rooms = search["no_rooms"]
            is_business_trip = search["is_business_trip"]
            get_only_avaliable = search["get_only_avaliable"]
            use_dynamic_dates = search["use_dynamic_dates"]
            no_pages_limit = search["no_pages_limit"]

            if use_dynamic_dates == True:
                starting_date_index = search["dynamic_dates"]["starting_date_index"]
                length_of_stay = search["dynamic_dates"]["length_of_stay"]
                todays_date = datetime.datetime.today()
                check_in_date = (todays_date + datetime.timedelta(days=starting_date_index)).strftime('%Y-%m-%d')
                check_out_date = (todays_date + datetime.timedelta(days=(starting_date_index + length_of_stay))).strftime('%Y-%m-%d')

            self.__initialize_browser()
            self.__start_log_start_search(currency, language, destination_city, destination_country, check_in_date, check_out_date, no_adults, no_childrens, no_rooms, is_business_trip, get_only_avaliable)
            self.__open_and_setup_booking_page(currency, language)
            self.__search_booking_property_list(destination_city, destination_country, check_in_date, check_out_date, no_adults, no_childrens, no_rooms, is_business_trip, get_only_avaliable)
            self.__get_property_list(no_pages_limit)
            self.__stop_log_start_search()
            self.__dispose()





    @timeit
    def __open_and_setup_booking_page(self, currency, language):
        
        
        # go to main page
        self.__browser.get(self.__base_url)

        # close login window
        try:
            #wait = WebDriverWait(self.__browser, 10)
            #login_window = wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@class='fly-dropdown fly-dropdown--onload-shower fly-dropdown_bottom fly-dropdown_arrow-right']")))
            login_window_close_button = self.__browser.find_element_by_xpath("//div[@class='fly-dropdown fly-dropdown--onload-shower fly-dropdown_bottom fly-dropdown_arrow-right']//div[@class='bicon bicon-aclose header-signin-prompt__close']")
            login_window_close_button.click()
        except Exception as e:
            #logging.exception(e, exc_info=True)
            pass #it won't be visible always


        # select currency
        try:
            curreny_selector = self.__browser.find_element_by_xpath("//div[@id='user_form']//li[@data-id='currency_selector']")
            curreny_selector.click()

            wait = WebDriverWait(self.__browser, 30) 
            currency_list = wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@id='current_currency_foldout']")))
            selected_currency_xpath = ".//ul[@class='currency_list']//li[contains(@class,'currency_{0}')]".format(currency)
            selected_currency = currency_list.find_element_by_xpath(selected_currency_xpath) 
            selected_currency.click()
            
        except Exception as e:
            logging.exception(e, exc_info=True)

        

        # select language
        try:
            language_selector = self.__browser.find_element_by_xpath("//div[@id='user_form']//li[@data-id='language_selector']")
            language_selector.click()

            wait = WebDriverWait(self.__browser, 30)
            language_list = wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@id='current_language_foldout']")))
            selected_language_xpath = ".//ul[@class='language_flags']//li[@data-lang='{0}']".format(language)
            selected_language = language_list.find_element_by_xpath(selected_language_xpath) 
            selected_language.click()
            
        except Exception as e:
            logging.exception(e, exc_info=True)


        # close language window
        try:
            #wait = WebDriverWait(self.__browser, 10)
            #login_window = wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@class='fly-dropdown fly-dropdown--onload-shower fly-dropdown_bottom fly-dropdown_arrow-center']")))
            login_window_close_button = self.__browser.find_element_by_xpath("//div[@class='fly-dropdown fly-dropdown--onload-shower fly-dropdown_bottom fly-dropdown_arrow-center']//div[@class='bicon bicon-aclose lang-signup-prompt__close']")
            login_window_close_button.click()
        except Exception as e:
            #logging.exception(e, exc_info=True)
            pass


#region search property

    @timeit
    def __start_log_start_search(self, currency, language, destination_city, destination_country, check_in_date, check_out_date, no_adults, no_childrens, no_rooms, is_business_trip, get_only_avaliable):
        
        search_starttime = datetime.datetime.now()
        search_date = datetime.date.today()
        no_days_before_travel = int((datetime.datetime.strptime(check_in_date, '%Y-%m-%d').date() - datetime.datetime.now().date()).days)
        no_nights = int((datetime.datetime.strptime(check_out_date, '%Y-%m-%d').date() - datetime.datetime.strptime(check_in_date, '%Y-%m-%d').date()).days)


        # find if there is already a city in the dictionary if not insert
        try:
            
            current_city = self.__session.query(self.__city).filter(self.__city.city_name == destination_city, self.__city.country == destination_country).scalar()
            
            if current_city == None:
            
                current_city = self.__city(
                    city_name = destination_city,
                    country = destination_country,
                )

                self.__session.add(current_city)
                self.__session.commit()

                self.__current_city_id = current_city.city_id

            else:
                
                self.__current_city_id = current_city.city_id
        
        except Exception as e:
            logging.exception(e, exc_info=True)

        



        # save current search parameters into database
        current_search = self.__search(
                city_id = self.__current_city_id,
                search_starttime = search_starttime, 
                search_date = search_date,
                no_days_before_travel = no_days_before_travel,
                currency = currency, 
                language = language, 
                check_in_date = check_in_date, 
                check_out_date = check_out_date, 
                no_nights = no_nights,
                no_adults = no_adults, 
                no_childrens = no_childrens, 
                no_rooms = no_rooms, 
                is_business_trip = is_business_trip,
                get_only_avaliable = get_only_avaliable
            )
        self.__session.add(current_search)
        self.__session.commit()
        
        # assign last inserted search id
        self.__current_search_id = current_search.search_id


    @timeit
    def __stop_log_start_search(self):
        
        search_endtime = datetime.datetime.now()
        
        self.__session.query(self.__search).filter(self.__search.search_id == self.__current_search_id).update(
                                {
                                    "search_endtime" : search_endtime
                                }
                            )

        self.__session.commit()
        

    @timeit
    def __search_booking_property_list(self, destination_city, destination_country, check_in_date, check_out_date, no_adults, no_childrens, no_rooms, is_business_trip, get_only_avaliable):
        

        # select destination
        try:
            destination_element = self.__browser.find_element_by_xpath("//div[@data-component='search/destination/input']//input")
            destination = destination_city + ', ' + destination_country 
            destination_element.send_keys(destination)
            
            wait = WebDriverWait(self.__browser, 30)
            destination_suggestion_list = wait.until(EC.visibility_of_element_located((By.XPATH, "//ul[@class='c-autocomplete__list sb-autocomplete__list sb-autocomplete__list-with_photos -visible']")))
            first_destination_suggestion = destination_suggestion_list.find_element_by_xpath(".//li")
            first_destination_suggestion.click()

            #self.browser.implicitly_wait(5) # wait 5 seconds to make sure that page is updated
        except Exception as e:
            logging.exception(e, exc_info=True)

        
        # by default the select date popup might appear
        # click on empty area to reset focus and close any popup
        self.__click_on_empty_area()




        # select dates
        self.__select_dates(check_in_date, "checkin")
        self.__click_on_empty_area()
        self.__select_dates(check_out_date, 'checkout')
        self.__click_on_empty_area()
        #self.browser.implicitly_wait(5)
         
        
        # specify number of people and number of rooms
        try:
            # click on the group details button
            group_details_window_button = self.__browser.find_element_by_xpath("//div[@data-component='search/group/group-with-modal']")
            group_details_window_button.click()
            
            # wait till the group details window will popup
            wait = WebDriverWait(self.__browser, 30)
            wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@id='xp__guests__inputs-container']")))
            
            self.__select_group_details_number(no_adults, "__field-adults")
            self.__select_group_details_number(no_childrens, "-children ")
            self.__select_group_details_number(no_rooms, "__field-rooms")
            
            self.__click_on_empty_area()

        except Exception as e:
            logging.exception(e, exc_info=True)


        # specify type of stay
        # select business trip if specified
        if is_business_trip == True:
            try:
                is_business_trip_button = self.__browser.find_element_by_xpath("//div[@data-component='search/travel-purpose/checkbox']")
                is_business_trip_button.click()
            except Exception as e:
                logging.exception(e, exc_info=True)


        self.__click_on_empty_area()



        # click on search button
        try:
            search_button = self.__browser.find_element_by_xpath("//div[@class='xp__button']//button[contains(@class, 'sb-searchbox__button')]")
            search_button.click()
        except Exception as e:
            logging.exception(e, exc_info=True)


        # make sure the list will be loaded
        time.sleep(10)


        # wait and select only avaliable properties if needed 
        if get_only_avaliable == True:
            
            try:

                only_avaliable_button = self.__browser.find_element_by_xpath("//div[@id='filter_out_of_stock']//a")
                only_avaliable_button.click()

                # make sure the list will be loaded
                time.sleep(10)

            except Exception as e:
                logging.exception(e, exc_info=True)
                

    @timeit
    def __select_group_details_number(self, selected_number, group_details_type):
        
        group_details_number_type_xpath = "//div[@class='sb-group__field sb-group{0}']".format(group_details_type)
        current_number_group_details_number_type_xpath = group_details_number_type_xpath + "//span[@class='bui-stepper__display']"

        # set up number
        try:
            
            current_group_details_number = self.__check_current_group_details_number(current_number_group_details_number_type_xpath)
            while selected_number != current_group_details_number:
                
                if selected_number > current_group_details_number:
                    # substract
                    current_operation_button_group_details_number_type_xpath = group_details_number_type_xpath + "//button[@data-bui-ref='input-stepper-add-button']"
                    current_operation_button_group_details_number_type_button = self.__browser.find_element_by_xpath(current_operation_button_group_details_number_type_xpath)
                    current_operation_button_group_details_number_type_button.click()
            
                elif selected_number < current_group_details_number:
                    # add
                    current_operation_button_group_details_number_type_xpath = group_details_number_type_xpath + "//button[@data-bui-ref='input-stepper-subtract-button']"
                    current_operation_button_group_details_number_type_button = self.__browser.find_element_by_xpath(current_operation_button_group_details_number_type_xpath)
                    current_operation_button_group_details_number_type_button.click()
    
                current_group_details_number = self.__check_current_group_details_number(current_number_group_details_number_type_xpath)


        except Exception as e:
            logging.exception(e, exc_info=True)
        
    @timeit
    def __check_current_group_details_number(self, current_number_group_details_number_type_xpath):
        
        try:
            current_number_group_details_number_type_element = self.__browser.find_element_by_xpath(current_number_group_details_number_type_xpath)
            current_number_group_details_number_type = int(current_number_group_details_number_type_element.text)
            return current_number_group_details_number_type
        except Exception as e:
            logging.exception(e, exc_info=True)

    @timeit
    def __select_dates(self, selected_date, date_type):
        
        calendar_date_type_xpath = "//div[@data-mode='{0}']".format(date_type)
        
        # select dates
        try:
            select_checkin_date_button = self.__browser.find_element_by_xpath(calendar_date_type_xpath)
            select_checkin_date_button.click()           
            
            wait = WebDriverWait(self.__browser, 30)
            select_date_calendar_form = wait.until(EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, 'bui-calendar__main')]")))
            
            #selected_date_xpath = ".//table[@class='bui-calendar__dates']//tr[@class='bui-calendar__row']//td[@data-date='{0}']".format(selected_date)
            selected_date_xpath = ".//td[@data-date='{0}']".format(selected_date)
            
            selected_date_found = 0
            number_of_retries = 0
            while selected_date_found == 0 and number_of_retries <= self.__booking_select_dates_max_no_retries:
                try:

                    time.sleep(5)

                    selected_date_button = select_date_calendar_form.find_element_by_xpath(selected_date_xpath)

                    time.sleep(5)

                    selected_date_button.click()
                    selected_date_found = 1
                except Exception as e:
                    
                    # selected date not found, we should move to the next month
                    try:
                        next_month_button = select_date_calendar_form.find_element_by_xpath(".//div[@data-bui-ref='calendar-next']")
                        next_month_button.click()

                        number_of_retries = number_of_retries + 1 
                        continue
                    except Exception as e:
                        logging.exception(e, exc_info=True) # if the button will not be find it's an error for sure
                    #logging.exception(e, exc_info=True) # no need to raise exception, it can be that the date won't be find

            if number_of_retries == self.__booking_select_dates_max_no_retries:
                raise ValueError("Maximum number of retries to select given date has been reached")
        except Exception as e:
            logging.exception(e, exc_info=True)

    @timeit
    def __click_on_empty_area(self):
        # click on a default place to close any open popups
        try:
            empty_area = self.__browser.find_element_by_xpath("//span[@class='sb-searchbox__title-text']")
            empty_area.click()
        except Exception as e:
            logging.exception(e, exc_info=True)


#endregion

    
#region get property list

    @timeit
    def __get_property_list(self, no_pages_limit):
                
        continue_to_next_page = True
        page_number = 1

        while continue_to_next_page == True:
        
            # make sure the list will be loaded
            time.sleep(10)

            # just in case close the map view if it will appear
            try:
                close_map_view_button = self.__browser.find_element_by_xpath("//div[@class='map_full_overlay__close' and @style='display: block;']")
                close_map_view_button.click()
            except:
                pass # not an error, it happens sometimes

            self.__get_property()

            # once done go to next page
            try:

                next_page_button = self.__browser.find_element_by_xpath("//div[@class='bui-pagination results-paging']//li[@class='bui-pagination__item bui-pagination__next-arrow']")
                next_page_button.click()
                continue_to_next_page = True

                # if there is a limit set on number of pages to be parsed, 
                # check and stop if on that page
                if no_pages_limit == page_number and no_pages_limit != -1:
                    continue_to_next_page = False

                page_number = page_number + 1

            except:
                continue_to_next_page = False
                continue

            

 

        

    @timeit
    def __get_property(self):

        try:
                
            page_no = None

            # get all info from single page
            booking_property_list = self.__browser.find_elements_by_xpath("//div[contains(@class, 'sr_item  sr_item_new sr_item_default sr_property_block')]")
            # get page number
            try:
                page_no = int(self.__browser.find_element_by_xpath("//div[@class='bui-pagination results-paging']//li[@class='bui-pagination__item bui-pagination__item--active sr_pagination_item current']//div[@class='bui-u-inline']").text)    
            except Exception as e:
                logging.exception(e, exc_info=True)

            for booking_property in booking_property_list:

                # get all info from single property
                booking_property_id = None
                property_name = None
                property_offer_url = None
                property_url = None
                property_type_badge = None
                hotel_rating_star = None
                hotel_own_rating = None
                booking_rating_star = None
                booking_partner = None
                coordinates_long = None
                coordinates_lat = None
                location_name = None
                no_reviews = None
                review_score = None
                original_price = None
                promo_price = None
                proposed_room_type = None
                is_avaliable = None


                # get hotel name
                try:
                    booking_property_id = int(booking_property.get_attribute("data-hotelid").strip())
                except Exception as e:
                    logging.exception(e, exc_info=True)


                # get hotel name
                try:
                    property_name = booking_property.find_element_by_xpath(".//div[@class='sr-hotel__title-wrap']//h3//span[contains(@class, 'sr-hotel__name')]").text
                except Exception as e:
                    logging.exception(e, exc_info=True)


                # check if property is avaliable
                try:
                    booking_property.find_element_by_xpath(".//div[@class='fe_banner fe_banner__accessible fe_banner__scale_small fe_banner__w-icon fe_banner__red fe_banner__sr_soldout_property ']")
                    is_avaliable = False # if found than property not avaliable
                except Exception as e:
                    is_avaliable = True # if not found than property avaliable
                    #logging.exception(e, exc_info=True) # this is not an error

                if is_avaliable:

                    
                    # get promo price
                    try:
                        _original_price = booking_property.find_element_by_xpath(".//div[@class='bui-price-display__original prco-inline-block-maker-helper']")
                        original_price = int(''.join(re.findall(r'\d+', str(_original_price.get_attribute("innerText")))))
                    except Exception as e:
                        pass
                        #logging.exception(e, exc_info=True) # not error, there might be just promo (standard) one price avaliable

                    # get promo price
                    try:
                        _promo_price = booking_property.find_element_by_xpath(".//div[@class='bui-price-display__value prco-inline-block-maker-helper']")
                        promo_price = int(''.join(re.findall(r'\d+', str(_promo_price.get_attribute("innerText")))))
                    except Exception as e:
                        logging.exception(e, exc_info=True)


                    try:
                        _proposed_room_type = booking_property.find_element_by_xpath(".//div[@class='roomNameInner']//a[@class='room_link']//strong")
                        proposed_room_type = str(_proposed_room_type.get_attribute("innerText")).strip()


                    except Exception as e:
                        logging.exception(e, exc_info=True)

                try:
                    _review_score = booking_property.find_element_by_xpath(".//div[@class='bui-review-score__badge']")
                    review_score = float(str(_review_score.get_attribute("innerText").strip().replace(",","."))) # this will be always separated by comma
                except Exception as e:
                    pass
                    # logging.exception(e, exc_info=True) # there might be no review score avaliable

                try:
                    _no_reviews = booking_property.find_element_by_xpath(".//div[@class='bui-review-score__text']")
                    no_reviews = int(''.join(re.findall(r'\d+', str(_no_reviews.get_attribute("innerText").strip()))))
                except Exception as e:
                    pass
                    # logging.exception(e, exc_info=True) # there might be no number of reviews avaliable


                try:
                    _location = booking_property.find_element_by_xpath(".//div[@class='sr_card_address_line']//a")
                    _location_span = booking_property.find_element_by_xpath(".//div[@class='sr_card_address_line']//a//span")
                    _location_name = str(_location.get_attribute("innerText"))
                    location_span = str(_location_span.get_attribute("innerText"))
                    location_name = _location_name.replace(location_span, "").strip()
                    coordinates = str(_location.get_attribute("data-coords")).split(",")
                    coordinates_long = float(coordinates[0])
                    coordinates_lat = float(coordinates[1])
                except Exception as e:
                    logging.exception(e, exc_info=True)


                try:
                    _property_offer_url = booking_property.find_element_by_xpath(".//div[@class='sr-hotel__title-wrap']//h3//a[@class='hotel_name_link url']")
                    property_offer_url = str(_property_offer_url.get_attribute("href"))
                    property_url = str(_property_offer_url.get_attribute("href")).split("?")[0]
                except Exception as e:
                    logging.exception(e, exc_info=True)


                try:
                    _booking_partner = booking_property.find_element_by_xpath(".//span[@class='sr-hotel__title-badges']//*[name()='svg' and contains(@class, 'thumbs_up_square')]")
                    booking_partner = True
                except Exception as e:
                    booking_partner = False


                try:
                    _hotel_own_rating = booking_property.find_element_by_xpath(".//span[@class='sr-hotel__title-badges']//*[name()='svg' and contains(@class, 'ratings_circles')]")
                    hotel_own_rating = int(str(_hotel_own_rating.get_attribute("class")).split("_")[-1])
             
                except Exception as e:
                    pass
                    # logging.exception(e, exc_info=True) # not an error, just not a partner



                try:
                    _hotel_rating_star = booking_property.find_element_by_xpath(".//span[@class='sr-hotel__title-badges']//*[name()='svg' and contains(@class, 'ratings_stars')]")
                    hotel_rating_star = int(str(_hotel_rating_star.get_attribute("class")).split("_")[-1])
                except Exception as e:
                    pass


  
                try:
                    __booking_rating_star = booking_property.find_elements_by_xpath(".//span[@class='sr-hotel__title-badges']//*[name()='svg' and contains(@class, 'square_rating')]")
                    _booking_rating_star = int(len(__booking_rating_star))
                    if (_booking_rating_star > 0):
                        booking_rating_star = _booking_rating_star
                except Exception as e:
                    logging.exception(e, exc_info=True) # not an error, just not a partner



                try:
                    _property_type_badge = booking_property.find_element_by_xpath(".//span[@class='bui-badge bh-property-type']")
                    property_type_badge = str(_property_type_badge.get_attribute("innerText"))
                except Exception as e:
                    pass



                current_property = self.__search_result(
                    search_id = self.__current_search_id,
                    city_id = self.__current_city_id,
                    booking_property_id = booking_property_id,
                    page_no = page_no,
                    property_name = property_name,
                    property_offer_url = property_offer_url,
                    property_url = property_url,
                    property_type_badge = property_type_badge,
                    hotel_rating_star = hotel_rating_star,
                    hotel_own_rating = hotel_own_rating,
                    booking_rating_star = booking_rating_star,
                    booking_partner = booking_partner,
                    coordinates_long = coordinates_long,
                    coordinates_lat = coordinates_lat,
                    location_name = location_name,
                    no_reviews = no_reviews,
                    review_score = review_score,
                    original_price = original_price,
                    promo_price = promo_price,
                    proposed_room_type = proposed_room_type,
                    is_avaliable = is_avaliable
                )

                # save property list to database
                self.__session.add(current_property)
                self.__session.commit()

        except Exception as e:
            logging.exception(e, exc_info=True)

#endregion







#region google maps stuff

    @timeit
    def __start_log_calculate_distance(self, _destination_id):
        
        calculate_distance_starttime = datetime.datetime.now()

        # save current search parameters into database
        current_calculate_distance = self.__calculate_distance(
                destination_id = _destination_id,
                calculate_distance_starttime = calculate_distance_starttime
            )
        self.__session.add(current_calculate_distance)
        self.__session.commit()
        
        # assign last inserted search id
        self.__current_calculate_distance_id = current_calculate_distance.calculate_distance_id

    @timeit
    def __stop_log_calculate_distance(self):
        
        calculate_distance_endtime = datetime.datetime.now()
        
        self.__session.query(self.__calculate_distance).filter(self.__calculate_distance.calculate_distance_id == self.__current_calculate_distance_id).update(
                                {
                                    "calculate_distance_endtime" : calculate_distance_endtime
                                }
                            )

        self.__session.commit()


    @timeit
    def calculate_and_save_distance_results(self, calculate_distance, api_key, calculate_distance_destinations):
        
        gmaps = googlemaps.Client(key=api_key)

        if calculate_distance == True:

            for calculate_distance_destination in calculate_distance_destinations:

                destination_lat = calculate_distance_destination["destination_lat"]
                destination_long = calculate_distance_destination["destination_long"]
                destination_city = calculate_distance_destination["destination_city"]
                destination_country = calculate_distance_destination["destination_country"]
                destination_name = calculate_distance_destination["destination_name"]
                force_recalculate = calculate_distance_destination["force_recalculate"]

                destination_location = "{0},{1}".format(destination_lat,destination_long)

                current_destination = self.__get_or_add_destination(destination_city, destination_country, destination_name, destination_long, destination_lat)
                current_destination_id = current_destination["destination_id"]

                self.__start_log_calculate_distance(current_destination_id)

                current_city_id = current_destination["city_id"]
                properties_in_destination = self.__session.query(self.__search_result).filter(self.__search_result.city_id == current_city_id).all()

                for property_in_destination in properties_in_destination:

                    # check if the calculation between given property and destination is already done
                    distance_results_already_exists = False
                    distance_results = self.__session.query(self.__distance_result).filter(self.__distance_result.booking_property_id == property_in_destination.booking_property_id, self.__distance_result.destination_id == current_destination_id, self.__distance_result.city_id == current_city_id).all()
                    if len(distance_results) > 0:
                        distance_results_already_exists = True

                    if distance_results_already_exists == False or force_recalculate == True:

                        booking_property_id = None 
                        destination_id = None
                        city_id = None
                        walking_response_status = None
                        walking_duration_seconds = None
                        walking_distance_meters = None
                        driving_response_status = None
                        driving_duration_seconds = None
                        driving_distance_meters = None
                        transit_reponse_status = None
                        transit_duration_seconds = None
                        transit_distance_meters = None

                        current_property_long = property_in_destination.coordinates_long
                        current_property_lat = property_in_destination.coordinates_lat
                        hotel_location = "{0},{1}".format(current_property_lat, current_property_long)

                        _directions_result_driving = gmaps.distance_matrix(
                                                origins = hotel_location, 
                                                destinations = destination_location,
                                                mode = "driving", 
                                                language = "en",
                                                units="metric"  
                                                )
                        directions_result_driving = self.__parse_distance_results(_directions_result_driving)

                        _directions_result_walking = gmaps.distance_matrix(
                                                origins = hotel_location, 
                                                destinations = destination_location,
                                                mode = "walking",  
                                                language = "en",
                                                units="metric"  
                                                )

                        directions_result_walking = self.__parse_distance_results(_directions_result_walking)


                        booking_property_id = property_in_destination.booking_property_id 
                        destination_id = current_destination_id
                        city_id = current_city_id
                        walking_response_status = directions_result_walking["status"]
                        walking_duration_seconds = directions_result_walking["duration_seconds"]
                        walking_distance_meters = directions_result_walking["distance_meters"]
                        driving_response_status = directions_result_driving["status"]
                        driving_duration_seconds = directions_result_driving["duration_seconds"]
                        driving_distance_meters = directions_result_driving["distance_meters"]
                        transit_reponse_status = None
                        transit_duration_seconds = None
                        transit_distance_meters = None

                        # save
                        current_distance_result = self.__distance_result(
                                    booking_property_id = booking_property_id, 
                                    destination_id = destination_id, 
                                    city_id = city_id, 
                                    walking_response_status = walking_response_status, 
                                    walking_duration_seconds = walking_duration_seconds, 
                                    walking_distance_meters = walking_distance_meters, 
                                    driving_response_status = driving_response_status, 
                                    driving_duration_seconds = driving_duration_seconds, 
                                    driving_distance_meters = driving_distance_meters, 
                                    transit_reponse_status = transit_reponse_status, 
                                    transit_duration_seconds = transit_duration_seconds, 
                                    transit_distance_meters = transit_distance_meters
                                )

                        self.__session.add(current_distance_result)
                        self.__session.commit()

                    else:
                        pass # force recalculation or do nothing
                
                self.__stop_log_calculate_distance()

        

            

    #@timeit # to much info
    def __parse_distance_results(self, distance_result):

        single_distance_result_status = None
        single_distance_result_distance_meters = None
        single_distance_result_duration_seconds = None

        # get
        try:
            response_status = distance_result["status"]

            if str(response_status) == 'OK':

                single_distance_result = distance_result["rows"][0]["elements"][0]
                single_distance_result_status = single_distance_result["status"]
                single_distance_result_distance_meters = single_distance_result["distance"]["value"]
                single_distance_result_duration_seconds = single_distance_result["duration"]["value"]

                return {"status" : single_distance_result_status,
                        "distance_meters" : single_distance_result_distance_meters,
                        "duration_seconds" : single_distance_result_duration_seconds}

            else:
                raise ValueError("There was a problem with Google Maps API. Response status: {0}".format(response_status))
        except Exception as e:
            logging.exception(e, exc_info=True)


        

    @timeit
    def __get_or_add_destination(self, destination_city, destination_country, destination_name, destination_long, destination_lat):

        current_destination_id = -1

        # add destination
        try:
            
            destination_city = self.__session.query(self.__city).filter(self.__city.city_name == destination_city, self.__city.country == destination_country).scalar()
            
            if destination_city != None:

                destination_city_id = destination_city.city_id

                # check if destination already exists
                current_destination = self.__session.query(self.__destination).filter(self.__destination.city_id == destination_city_id, self.__destination.destination_name == destination_name).scalar()
                if current_destination == None:
                      
                    current_destination = self.__destination(
                        city_id = destination_city_id,
                        destination_name = destination_name,
                        coordinates_long = destination_long,
                        coordinates_lat = destination_lat
                    )

                    self.__session.add(current_destination)
                    self.__session.commit()
                    current_destination_id = current_destination.destination_id
                else:
                    current_destination_id = current_destination.destination_id
                return {"destination_id" : current_destination_id, "city_id" : destination_city_id}

            else:
                raise ValueError('Destination needs to correspond the city and country that was already used to search')
        
        except Exception as e:
            logging.exception(e, exc_info=True)
            raise
