from seleniumwire import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException, ElementClickInterceptedException, WebDriverException, TimeoutException
import const
from log import create_logger

'''
Twitter Space's m3u8 is obtained from accessing the driver's request
The process involves clicking the "Play Recording" button, then clicking the "Got it" button that pops up(kinda like accept these cookies)
And then lastly click the "Play Button" to start playing the space and capturing the xhr request sent for the audio
Strangely the "Got it" button will be timed out and since it blocks/gray out the screen the clicking on "Play Button" gets intercepted(it becomes a pause button when this exception occurs)
But everything still works. Therefore the "[info] Timed out finding button continuing..." and "[warning] Message: element click intercepted: Element..." will most likely pop up
'''

def get_m3u8(space_url):
    SELENIUM_WAIT_TIME = int(const.SLEEP_TIME/2)
    OTHER_WAIT_TIME = int(SELENIUM_WAIT_TIME/2)

    logger = create_logger("logfile.log")

    # Create a new instance of the Chrome driver
    try:
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--mute-audio')
        driver = webdriver.Chrome(options=chrome_options)
    except WebDriverException as driverError:
        logger.error(driverError)
        driver.quit()
        return None

    # Go to the twitter space page
    # e.g. space_url = https://twitter.com/i/spaces/1mnGedeXloNKX
    driver.get(space_url)
    logger.info("Found a live space")

    # Get and click the play recording button
    try:
        play_recording_element = WebDriverWait(driver, SELENIUM_WAIT_TIME).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "css-18t94o4.css-1dbjc4n.r-1awozwy.r-9tfo2e.r-sdzlij.r-6koalj.r-18u37iz.r-1777fci.r-1ny4l3l.r-1f1sjgu.r-o7ynqc.r-6416eg.r-13qz1uu")))
        play_recording_element[0].click()
    except WebDriverException as e:
        if len(str(e.msg)) == 0:
            logger.debug("Something weird happened, continuing...")
        else:
            logger.error(e)
        driver.quit()
        return None

    # If space doesn't automatically play get and click the Got It button that may come up
    try:
        got_it_button_element = WebDriverWait(driver, OTHER_WAIT_TIME).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "css-18t94o4.css-1dbjc4n.r-1udnf30.r-1uusn97.r-h3s6tt.r-1ny4l3l.r-1udh08x.r-o7ynqc.r-6416eg.r-13qz1uu")))
        got_it_button_element[0].click()
    except TimeoutException as timeOutError:
        if len(str(timeOutError.msg)) == 0:
            logger.debug("Timed out finding button continuing...")
        else:
            logger.error(timeOutError)
            # print(f"[error] {timeOutError}")
    except NoSuchElementException as noElementError:
        logger.error(noElementError)
    except ElementNotInteractableException as notInteractableError:
        # This error will most likely appear because play button was intercepted, triggered and found first
        # therefore this button click is not needed but warning will still be displayed
        logger.warning(notInteractableError)

    # If space doesn't automatically play get and after the click the Got It button
    # Get and click on the play button to start the twitter space
    try:
        play_button_element = WebDriverWait(driver, OTHER_WAIT_TIME).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "css-18t94o4.css-1dbjc4n.r-1niwhzg.r-sdzlij.r-1phboty.r-rs99b7.r-1pi2tsx.r-19yznuf.r-64el8z.r-1ny4l3l.r-o7ynqc.r-6416eg.r-lrvibr")))
        play_button_element[0].click()
    except ElementClickInterceptedException as clickInterceptedError:
        # This error will most likely occur because the click got executed before the Got It button above
        # Which probably caused this clicking action to occur again hence click intercepted
        logger.warning(clickInterceptedError)
    except ElementNotInteractableException as notInteractableError:
        logger.error(notInteractableError)
    except TimeoutException as timeOutError:
        if len(str(timeOutError.msg)) == 0:
            logger.debug("Timed out finding play button continuing...")
        else:
            logger.error(timeOutError)

    # Access requests via the `requests` attribute
    m3u8 = None
    for request in driver.requests:
        if request.response:
            if "m3u8" in request.url:
                m3u8 = request.url.replace('dynamic', 'master').removesuffix('?type=live')
                break
    driver.quit()
    return m3u8


if __name__ == "__main__":
    # e.g. space_url = https://twitter.com/i/spaces/1mnGedeXloNKX
    space_url = input("Space Url: ")
    result = get_m3u8(space_url)
    print(result)
