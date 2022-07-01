from seleniumwire import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import const
from log import create_logger
import logging
import os


'''
Twitter Space's m3u8 is obtained from accessing the driver's request
The process involves clicking the "Play Recording" button, then clicking the "Got it" button that pops up(kinda like accept these cookies)
And then lastly click the "Play Button" to start playing the space and capturing the xhr request sent for the audio
Strangely the "Got it" button will be timed out and since it blocks/gray out the screen the clicking on "Play Button" gets intercepted(it becomes a pause button when this exception occurs)
But everything still works. Therefore the "[info] Timed out finding button continuing..." and "[warning] Message: element click intercepted: Element..." will most likely pop up
'''


def get_m3u8(space_url):
    SELENIUM_WAIT_TIME = int(const.SLEEP_TIME/2)

    logger = create_logger("logfile.log")

    # Create a new instance of the Chrome driver
    try:
        print(" "*50, end='\r')
        logging.getLogger('WDM').\
            setLevel(logging.ERROR)
        os.environ['WDM_LOG'] = "false"
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--mute-audio')
        chrome_options.add_argument('--lang=en-US')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    except WebDriverException as driverError:
        logger.error(driverError)
        try:
            driver.quit()
        except NameError:
            return None
        return None

    # Go to the twitter space page
    # e.g. space_url = https://twitter.com/i/spaces/1mnGedeXloNKX
    driver.get(space_url)
    logger.debug("Found a live space")

    # Get and click the play recording button
    try:
        play_recording_element = WebDriverWait(driver, SELENIUM_WAIT_TIME).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[aria-label*='Join a space']")))
        play_recording_element[0].click()
    except WebDriverException as e:
        if len(str(e.msg)) == 0:
            logger.debug("Something weird happened, continuing...")
        else:
            logger.error(e)
        driver.quit()
        return None

    # Access requests via the `requests` attribute
    m3u8 = None
    try:
        req = driver.wait_for_request('dynamic_playlist.m3u8\?type=live', timeout=10)
        m3u8 = req.url.replace('dynamic', 'master').removesuffix('?type=live')
    except TimeoutException as timeOutError:
        if len(str(timeOutError.msg)) == 0:
            logger.debug("Timed out finding m3u8 request")
        else:
            logger.error(timeOutError)
    driver.quit()
    return m3u8


if __name__ == "__main__":
    # e.g. space_url = https://twitter.com/i/spaces/1mnGedeXloNKX
    space_url = input("Space Url: ")
    result = get_m3u8(space_url)
    print(result)
