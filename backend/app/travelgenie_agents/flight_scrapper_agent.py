from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
from datetime import datetime
from selenium.common.exceptions import TimeoutException
from prettytable import PrettyTable
import pandas as pd
import undetected_chromedriver as uc
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class FlightSearcher:
    def __init__(self, from_city, to_city, departure_date, return_date):
        """Initialize the flight searcher with trip details."""
        self.from_city = from_city
        self.to_city = to_city
        self.departure_date = departure_date
        self.return_date = return_date
        self.driver = None
        # self.options = Options()
        self.options = uc.ChromeOptions()
        self.options.add_argument("--start-maximized")
        # self.options.add_argument("--window-position=10000,10000")  # Move it offscreen
        logger.info(f"Initializing flight search", from_city=from_city, to_city=to_city, departure=departure_date, return_date=return_date)
    
    def start_browser(self):
        """Launch the browser and navigate to Kayak."""
        logger.info("Launching Chrome browser")
        # self.driver = webdriver.Chrome(options=self.options)
        self.driver = uc.Chrome(options=self.options)
        self.driver.get("https://www.kayak.com/flights")
        logger.info("Navigated to Kayak flights page")
        time.sleep(2)
        
    def handle_popups(self):
        """Handle any initial popups like cookie notices."""
        logger.debug("Checking for popups")
        try:
            wait = WebDriverWait(self.driver, 5)
            understand_button = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[.//div[text()='I understand']]")
            ))
            understand_button.click()
            logger.info("Closed 'I understand' popup")
        except Exception:
            logger.debug("No popups found or already handled")
    
    def clear_existing_cities(self):
        """Clear any pre-selected cities."""
        logger.debug("Clearing any pre-selected cities")
        try:
            close_buttons = WebDriverWait(self.driver, 5).until(
                EC.presence_of_all_elements_located((By.XPATH, "//div[@class='c_neb-item-close']"))
            )
            for btn in close_buttons:
                try:
                    btn.click()
                    time.sleep(0.5)
                except:
                    pass
            logger.info("Cleared pre-selected cities")
        except:
            logger.debug("No pre-selected cities to clear")
    
    def set_from_city(self):
        """Set the departure city."""
        logger.info(f"Setting departure city", city=self.from_city)
        try:
            from_input = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@aria-label='Flight origin input']"))
            )
            from_input.click()
            from_input.clear()
            from_input.send_keys(self.from_city)
            time.sleep(2)  # Let dropdown load
            
            from_option_xpath = "//ul[contains(@id,'flight-origin-smarty-input-list')]//li[@role='option'][1]"
            from_option = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, from_option_xpath))
            )
            from_option.click()
            logger.info(f"Set departure city successfully", city=self.from_city)
            time.sleep(2)
        except Exception as e:
            logger.error(f"Error setting departure city", error=str(e), city=self.from_city)
    
    def set_to_city(self):
        """Set the destination city."""
        logger.info(f"Setting destination city", city=self.to_city)
        try:
            to_input = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@aria-label='Flight destination input']"))
            )
            to_input.click()
            to_input.clear()
            to_input.send_keys(self.to_city)
            time.sleep(2)  # Let dropdown load
            
            to_option_xpath = "//ul[contains(@id,'flight-destination-smarty-input-list')]//li[@role='option'][1]"
            to_option = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, to_option_xpath))
            )
            to_option.click()
            logger.info(f"Set destination city successfully", city=self.to_city)
            time.sleep(2)
        except Exception as e:
            logger.error(f"Error setting destination city", error=str(e), city=self.to_city)
    
    def select_departure_date(self):
        """Select the departure date on the calendar."""
        logger.info(f"Selecting departure date", date=self.departure_date)
        try:
            departure_date_obj = datetime.strptime(self.departure_date, "%Y-%m-%d")
            aria_label = departure_date_obj.strftime("%B %#d, %Y")
            
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "OV9e-cal-wrapper"))
            )
            
            date_xpath = f"//div[@role='button' and contains(@aria-label, '{aria_label}')]"
            date_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, date_xpath))
            )
            date_button.click()
            logger.info(f"Selected departure date", date=aria_label)
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error selecting departure date", error=str(e), date=self.departure_date)
    
    def select_return_date(self):
        """Select the return date on the calendar."""
        logger.info(f"Selecting return date", date=self.return_date)
        try:
            return_date_obj = datetime.strptime(self.return_date, "%Y-%m-%d")
            aria_label = return_date_obj.strftime("%B %#d, %Y")
            
            logger.debug("Opening return date selector")
            return_box = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and @aria-label='Return']"))
            )
            return_box.click()
            time.sleep(1)
            
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "OV9e-cal-wrapper"))
            )
            
            date_xpath = f"//div[@role='button' and contains(@aria-label, '{aria_label}')]"
            date_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, date_xpath))
            )
            date_button.click()
            logger.info(f"Selected return date", date=aria_label)
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error selecting return date", error=str(e), date=self.return_date)
    
    def click_search(self):
        """Click the search button to initiate the flight search."""
        logger.info("Initiating flight search")
        try:
            search_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[@role='button' and @aria-label='Search']")
                )
            )
            search_button.click()
            logger.info("Search button clicked")
            time.sleep(2)
        except Exception as e:
            logger.error(f"Error clicking search button", error=str(e))
    
    def switch_to_results_tab(self):
        """Switch to the results tab that opens after search."""
        logger.debug("Switching to results tab")
        self.driver.switch_to.window(self.driver.window_handles[-1])
        logger.info("Switched to results tab")
    
    def extract_flight_data(self):
        """Extract flight information from the search results."""
        logger.info("Extracting flight data")
        wait = WebDriverWait(self.driver, 40)
        
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".nrc6-inner")))
            logger.info("Flight results loaded successfully")
            
            flight_cards = self.driver.find_elements(By.CSS_SELECTOR, '[aria-label^="Result item"]')
            
            if not flight_cards:
                logger.warning("No flight results found")
                return None
            
            logger.info(f"Found flight options", count=len(flight_cards))
            flights = []
            
            for card in flight_cards:
                try:
                    legs = card.find_elements(By.CSS_SELECTOR, "li.hJSA-item")
                    all_legs = []
                    
                    for leg in legs:
                        departure_time = leg.find_element(By.CSS_SELECTOR, ".VY2U .vmXl span:nth-child(1)").text
                        arrival_time = leg.find_element(By.CSS_SELECTOR, ".VY2U .vmXl span:nth-child(3)").text
                        airline = leg.find_element(By.CSS_SELECTOR, ".VY2U .c_cgF").text
                        duration = leg.find_element(By.CSS_SELECTOR, ".xdW8 .vmXl").text
                        stops = leg.find_element(By.CSS_SELECTOR, ".JWEO .vmXl span").text
                        from_airport = leg.find_elements(By.CSS_SELECTOR, ".jLhY-airport-info span")[0].text
                        to_airport = leg.find_elements(By.CSS_SELECTOR, ".jLhY-airport-info span")[1].text
                        
                        try:
                            stop_detail = leg.find_element(By.CSS_SELECTOR, ".JWEO .c_cgF span span").get_attribute("title")
                        except:
                            stop_detail = "N/A"
                        
                        all_legs.append({
                            "from": from_airport,
                            "to": to_airport,
                            "airline": airline,
                            "depart": departure_time,
                            "arrive": arrival_time,
                            "duration": duration,
                            "stops": stops,
                            "stop_detail": stop_detail,
                            "date": self.departure_date if len(flights) % 2 == 0 else self.return_date
                        })
                    
                    try:
                        price = card.find_element(By.CSS_SELECTOR, ".f8F1-price-text").text
                    except:
                        price = "N/A"
                    
                    flights.append({
                        "legs": all_legs,
                        "price": price
                    })
                
                except Exception as e:
                    logger.warning(f"Error parsing flight card", error=str(e))
            
            # Convert to DataFrame
            flight_rows = []
            for i, flight in enumerate(flights, start=1):
                for leg in flight['legs']:
                    row = {
                        "Option": i,
                        "From": leg['from'],
                        "To": leg['to'],
                        "Airline": leg['airline'],
                        "Depart": leg['depart'],
                        "Arrive": leg['arrive'],
                        "Duration": leg['duration'],
                        "Stops": leg['stops'],
                        "Stop Detail": leg['stop_detail'],
                        "Date": leg['date'],
                        "Price": flight['price']
                    }
                    flight_rows.append(row)
            
            df_flights = pd.DataFrame(flight_rows)
            logger.info("Flight data extraction complete", flight_count=len(flights))
            
            json_results = df_flights.to_dict(orient="records")
            return json_results
        
        except TimeoutException:
            logger.error("Timeout! Couldn't load flight results")
            self.driver.save_screenshot("flight_results_timeout.png")
            logger.info("Screenshot saved", filename="flight_results_timeout.png")
            return None
    
    def print_flight_table(self, flights):
        """Print a formatted table of flight options."""
        if not flights or flights.empty:
            logger.warning("No flight data to display")
            return
        
        logger.info("Flight Results Summary")
        
        # Group by Option to get unique flights
        options = flights['Option'].unique()
        
        for option in options:
            option_flights = flights[flights['Option'] == option]
            price = option_flights['Price'].iloc[0]
            logger.info(f"Option {int(option)}: {price}")
            
            for _, flight in option_flights.iterrows():
                logger.debug(f"Flight detail", airline=flight['Airline'], from_airport=flight['From'], to_airport=flight['To'], depart=flight['Depart'], arrive=flight['Arrive'])
    
    def close_browser(self):
        """Close the browser."""
        logger.info("Closing browser")
        if self.driver:
            self.driver.quit()
    
    def run_search(self):
        """Execute the complete flight search process."""
        logger.info("STARTING FLIGHT SEARCH")
        
        try:
            self.start_browser()
            self.handle_popups()
            self.clear_existing_cities()
            self.set_from_city()
            self.set_to_city()
            self.select_departure_date()
            self.select_return_date()
            self.click_search()
            self.switch_to_results_tab()
            flights = self.extract_flight_data()

            if flights:
                logger.info("Flight search completed successfully")
                return {
                    "status": "success",
                    "flights": flights
                }
            else:
                logger.warning("No flights found")
                return {
                    "status": "error",
                    "message": "No flights found"
                }
            
        except Exception as e:
            logger.exception("Error during flight search")
        finally:
            self.close_browser()
            logger.info("FLIGHT SEARCH PROCESS ENDED")


# Usage example
if __name__ == "__main__":
    logger.info("Welcome to the Flight Search Tool")
    
    # You can replace these with user inputs
    searcher = FlightSearcher(
        from_city="Las Vegas",
        to_city="New York",
        departure_date="2025-4-10",
        return_date="2025-4-17"
    )
    
    flight_details = searcher.run_search()
    logger.info("Flight search result", result=flight_details)
