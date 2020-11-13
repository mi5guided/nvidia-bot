import json
import secrets
import time
from os import path
from price_parser import parse_price

from amazoncaptcha import AmazonCaptcha
from chromedriver_py import binary_path  # this will get you the path variable
from furl import furl
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from utils import selenium_utils
from utils.json_utils import InvalidAutoBuyConfigException
from utils.logger import log
from utils.selenium_utils import options, enable_headless, wait_for_element
from price_parser import parse_price

WALMART_URL = "https://www.walmart.com/"

CHECKOUT_URL = "https://www.walmart.com/cart"

SIGNIN_URL = "https://www.walmart.com/account/login"

AUTOBUY_CONFIG_PATH = "walmart_config.json"

SIGN_IN_TITLES = [
    "Login",
]

LOGGED_IN = "Account"

HOME_PAGE_TITLES = [
    "Walmart.com | Save Money. Live Better.",
]

ITEM_PAGE = "https://www.walmart.com/ip/{item}"

SHOPING_CART_TITLES = CHECKOUT_URL

CAPTCHA_TITLE = "Verify your identity"

CHECKOUT_TITLE = "Choose delivery or pickup"

CHOOSE_ADDRESS = "Choose delivery address"

IN_PERSON = "Enter pickup person"

ORDER_COMPLETE_TITLES = [
    "Amazon.com Thanks You",
    "Amazon.ca Thanks You",
    "AmazonSmile Thanks You",
    "Thank you",
    "Amazon.fr Merci",
    "Merci",
    "Amazon.es te da las gracias",
    "Amazon.fr vous remercie.",
    "Grazie da Amazon.it",
]

ADD_TO_CART_TITLE = "Item added to cart - Walmart.com"

class Walmart:
    def __init__(self, item, notification_handler):
        self.notification_handler = notification_handler
        self.item = item
        options.add_argument(f"user-data-dir=.profile-wal")
        try:
            self.driver = webdriver.Chrome(executable_path=binary_path, options=options)
            self.wait = WebDriverWait(self.driver, 10)
        except Exception:
            log.error("Another instance of chrome is running, close that and try again.")
            exit(1)
        if path.exists(AUTOBUY_CONFIG_PATH):
            with open(AUTOBUY_CONFIG_PATH) as json_file:
                try:
                    config = json.load(json_file)
                    self.username = config["username"]
                    self.password = config["password"]
                    self.cvv = config["cvv"]
                    #self.walmart_website = config.get("walmart_website", "walmart.com")
                except Exception:
                    log.error(
                        "walmart_config.json file not formatted properly: https://github.com/Hari-Nagarajan/nvidia-bot/wiki/Usage#json-configuration"
                    )
        else:
            log.error(
                "No config file found, see here on how to fix this: https://github.com/Hari-Nagarajan/nvidia-bot/wiki/Usage#json-configuration"
            )
            exit(0)

        #for key in AMAZON_URLS.keys():
        #    AMAZON_URLS[key] = AMAZON_URLS[key].format(domain=self.amazon_website)
        self.driver.get(SIGNIN_URL)
        #log.info("Waiting for login page.")
        #self.check_if_captcha(self.wait_for_pages, SIGN_IN_TITLES)
        #selenium_utils.wait_for_any_title(self.driver, "Account")
        title = self.driver.title
        log.info(item)

        if title in LOGGED_IN:
            log.info("Already logged in")
        else:
            log.info("Lets log in.")

            self.driver.get(SIGNIN_URL)
            log.info("Wait for Sign In page")
            self.login()
            log.info("Waiting 15 seconds.")
            time.sleep(
                15
            )  # We can remove this once I get more info on the phone verification page.

    def login(self):

        try:
            log.info("Email")
            self.driver.find_element_by_xpath('//*[@id="email"]').send_keys(
                self.username + Keys.RETURN
            )
        except:
            log.info("Email not needed.")
            pass

        log.info("Password")
        self.driver.find_element_by_xpath('//*[@id="password"]').send_keys(
            self.password + Keys.RETURN
        )

        log.info("Remember me checkbox")
        selenium_utils.button_click_using_xpath(self.driver, '//*[@id="remember-me"]')

        if self.driver.find_elements_by_xpath('//*[@id="global-error"]'):
            log.error("Login failed, check your username in walmart_config.json")
            time.sleep(240)
            exit(1)

        log.info(f"Logged in as {self.username}")

    def run_item(self, delay=3, test=False):
        log.info("Checking stock for items.")
        while not self.something_in_stock():
            time.sleep(delay)
        self.notification_handler.send_notification(
            "Your items on Walmart.com were found!", True
        )
        try:
            captcha = self.driver.find_element_by_xpath('//*[@id="recaptcha-anchor"]/div[1]')
            if captcha:
                self.on_captcha_page()
        except:
            pass
        self.checkout(test=test)

    def something_in_stock(self):
        f = furl(ITEM_PAGE.format(item=self.item))
        self.driver.get(f.url)
        if self.driver.title in CAPTCHA_TITLE:
            self.on_captcha_page()
        #add_to_cart = self.driver.find_element_by_xpath('//*[@id="add-on-atc-container"]/div[1]/section/div[1]/div[3]/button/span/span')
        #add_to_cart = self.driver.find_element_by_xpath('//*[@id="add-on-atc-container"]/div[1]/section/div[1]/div[3]')
        add_to_cart = self.driver.find_element_by_xpath('//*[@id="add-on-atc-container"]/div[1]/section/div[1]')
        if add_to_cart:
            add_to_cart.click()
            return True

    def wait_for_pages(self, page_titles, t=30):
        log.debug(f"wait_for_pages({page_titles}, {t})")
        try:
            title = selenium_utils.wait_for_any_title(self.driver, page_titles, t)
            if not title in page_titles:
                log.error(
                    "{} is not a recognized title, report to #tech-support or open an issue on github".format()
                )
            pass
        except Exception as e:
            log.debug(e)
            pass

#    def check_if_captcha(self, func, args):
#        try:
#            func(args)
#        except Exception as e:
#            log.debug(str(e))
#            if self.on_captcha_page():
#                log.warning(f"Stuck on captcha, need assistance...")
#                time.sleep(30)
#            else:
#                log.debug(self.driver.title)
#                log.error(
#                    f"An error happened, please submit a bug report including a screenshot of the page the "
#                    f"selenium browser is on. There may be a file saved at: walmart-{func.__name__}.png"
#                )
#                self.driver.save_screenshot(f"walmart-{func.__name__}.png")
#                self.driver.save_screenshot("screenshot.png")
#                self.notification_handler.send_notification(
#                    f"Error on {self.driver.title}", True
#                )
#                time.sleep(60)
#                self.driver.close()
#                log.debug(e)
#                pass

    def on_captcha_page(self):
        try:
            if self.driver.title in CAPTCHA_TITLE:
                log.warning(f"Stuck on captcha, need assistance...")
                time.sleep(120)
                #return False
                
            if self.driver.find_element_by_xpath(
                '//*[@id="recaptcha-anchor"]/div[1]'
            ):
                return True
        except Exception:
            pass
        return False
    
    #def wait_for_pyo_page(self):
    #    self.check_if_captcha(self.wait_for_pages, CHECKOUT_TITLES + SIGN_IN_TITLES)
    #
    #    if self.driver.title in SIGN_IN_TITLES:
    #        log.info("Need to sign in again")
    #        self.login()

    def finalize_order_button(self, test, retry=0):
        button_xpaths = [
            '//*[@id="bottomSubmitOrderButtonId"]/span/input',
            '//*[@id="placeYourOrder"]/span/input',
            '//*[@id="submitOrderButtonId"]/span/input',
            '//input[@name="placeYourOrder1"]',
        ]
        button = None
        for button_xpath in button_xpaths:
            try:
                if (
                    self.driver.find_element_by_xpath(button_xpath).is_displayed()
                    and self.driver.find_element_by_xpath(button_xpath).is_enabled()
                ):
                    button = self.driver.find_element_by_xpath(button_xpath)
            except NoSuchElementException:
                log.debug(f"{button_xpath}, lets try a different one.")

        if button:
            log.info(f"Clicking Button: {button.text}")
            if not test:
                button.click()
            return
        else:
            if retry < 3:
                log.info("Couldn't find button. Lets retry in a sec.")
                time.sleep(5)
                self.finalize_order_button(test, retry + 1)
            else:
                log.info(
                    "Couldn't find button after 3 retries. Open a GH issue for this."
                )

    def wait_for_order_completed(self, test):
        if not test:
            self.check_if_captcha(self.wait_for_pages, ORDER_COMPLETE_TITLES)
        else:
            log.info(
                "This is a test, so we don't need to wait for the order completed page."
            )

    def checkout(self, test):
        log.info("Clicking continue.")
        self.wait_for_pages(ADD_TO_CART_TITLE)
        self.driver.save_screenshot("screenshot.png")
        self.notification_handler.send_notification("Starting Checkout", True)
        self.on_captcha_page()
        try:
            self.driver.find_element_by_xpath(
                '//*[@id="cart-root-container-content-skip"]/div[1]/div/div[2]/div/div/div/div/div[3]/div/div/div[2]/div[1]/div[2]/div/button[1]'
            ).click()
        except:
            self.driver.find_element_by_xpath(
            '//*[@id="cart-root-container-content-skip"]/div[1]/div/div[3]/div/div/div/div/div[3]/div/div/div[2]/div[1]/div[2]/div/button[1]'
            ).click()
        #self.driver.find_element_by_xpath('//*[@id="cart-root-container-content-skip"]/div[1]/div/div[2]/div/div/div/div/div[3]/div/div/div[2]/div[1]/div[2]/div/button[2]').click()
        log.info("Waiting for Cart Page")
        try:
            #captcha = self.driver.find_element_by_xpath('//*[@id="recaptcha-anchor"]/div[1]')
            #if captcha:
            #    self.on_captcha_page()
            if self.on_captcha_page():
                pass
        except:
            pass
        self.driver.save_screenshot("screenshot.png")
        self.notification_handler.send_notification("Cart Page", True)

        log.info("clicking checkout.")
        try:
            if self.driver.title in CHECKOUT_TITLE:
                try:
                    self.driver.find_element_by_xpath(
                        '//*[@id="shipping-button-0"]'
                    ).click()
                    self.wait_for_pages(CHOOSE_ADDRESS)
                    self.driver.find_element_by_xpath(
                        '/html/body/div[1]/div/div[1]/div/div[1]/div[3]/div/div/div/div[2]/div[1]/div[2]/div/div/div/div[3]/div/div/div/div/div[3]/div[2]/button'
                    ).click()
                    self.wait_for_pages(CHOOSE_PAYMENT)
                    cvv_check = self.driver.find_element_by_xpath('//*[@id="cvv-confirm"]')
                    if cvv_check:
                        cvv_check.send_keys(self.cvv + Keys.RETURN)

                    self.driver.find_element_by_xpath(
                        '/html/body/div[1]/div/div[1]/div/div[1]/div[3]/div/div/div/div[3]/div[1]/div[2]/div/div/div/div[3]/div[2]/div/button'
                    ).click()
                    
                except:
                    self.driver.find_element_by_xpath(
                        '//*[@id="pickup-button-0"]'
                    ).click()
                

        except:
            if self.driver.title in IN_PERSON:
                self.driver.find_element_by_xpath(
                    '/html/body/div[1]/div/div[1]/div/div[1]/div[3]/div/div/div/div[2]/div[1]/div[2]/div/div/div/form/div/div[3]/div/div/button'
                ).click
            else:
                self.driver.save_screenshot("screenshot.png")
                self.notification_handler.send_notification(
                    "Failed to checkout. Returning to stock check.", True
                )
                log.info("Failed to checkout. Returning to stock check.")
                self.run_item(test=test)


        log.info("Waiting for Place Your Order Page")
        self.wait_for_pyo_page()

        log.info("Finishing checkout")
        self.driver.save_screenshot("screenshot.png")
        self.notification_handler.send_notification("Finishing checkout", True)

        self.finalize_order_button(test)

        log.info("Waiting for Order completed page.")
        self.wait_for_order_completed(test)

        log.info("Order Placed.")
        self.driver.save_screenshot("screenshot.png")
        self.notification_handler.send_notification("Order Placed", True)

        time.sleep(20)
