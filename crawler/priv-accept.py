#!/usr/bin/env python3

from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchFrameException, TimeoutException
import argparse
from urllib.parse import urlparse
from datetime import datetime
from selenium import webdriver
import traceback
import random
import os
import sys
import json
import time
import sqlite3
import shutil

# Parse Vars
parser = argparse.ArgumentParser()
parser.add_argument('--url', type=str, default='https://www.theguardian.com/')
parser.add_argument('--outfile', type=str, default='output.json')
parser.add_argument('--pretty_print', action='store_true')
parser.add_argument('--accept_words', type=str, default="accept_words.txt")
parser.add_argument('--chrome_binary', type=str, default=None)
parser.add_argument('--chrome_driver', type=str, default="./chromedriver")
parser.add_argument('--screenshot_dir', type=str, default=None)
parser.add_argument('--lang', type=str, default=None)
parser.add_argument('--timeout', type=int, default=5)
parser.add_argument('--connection_timeout', type=int, default=60)
parser.add_argument('--clear_cache', action='store_true')
parser.add_argument('--headless', action='store_true')
parser.add_argument('--docker', action='store_true')
parser.add_argument('--user_agent', type=str, default=None)
parser.add_argument('--try_scroll', action='store_true')
parser.add_argument('--full_net_log', action='store_true')
parser.add_argument('--pre_visit', action='store_true')
parser.add_argument('--chrome_extra_option', type=str, action='append', default=[])
parser.add_argument('--network_conditions', type=str, default=None)
parser.add_argument('--rum_speed_index', action='store_true')
parser.add_argument('--force_second_visit', action='store_true')
parser.add_argument('--force_click_data', action='store_true')
parser.add_argument('--visit_internals', action='store_true')
parser.add_argument('--num_internal', type=int, default=5)
parser.add_argument('--detect_topics', action='store_true')
parser.add_argument('--xvfb', action='store_true')

globals().update(vars(parser.parse_args()))

log_entries = []
GLOBAL_SELECTOR = "a, button, div, span, form, p"
RUM_SPEED_INDEX_FILE="rum-speedindex.js"
USER_AGENT_DEFAULT="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36"
stats = {}


def main():
    global driver
    global url
    global USER_AGENT_DEFAULT

    # Fix Url
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url

    # Enable browser logging and start driver
    log("Starting Driver")
    d = DesiredCapabilities.CHROME
    # d['loggingPrefs'] = { 'performance':'ALL' }
    d['goog:loggingPrefs'] = {'performance': 'ALL'}
    options = Options()
    stats["lang"] = "default"
    stats["headless"] = False

    if chrome_binary:
        options.binary_location = chrome_binary

    if user_agent is not None:
        USER_AGENT_DEFAULT = user_agent

    if detect_topics:
        # Enable Topics API
        options.add_argument("enable-privacy-sandbox-ads-apis")
        
    if lang is not None:
        stats["lang"] = lang
        options.add_experimental_option('prefs', {'intl.accept_languages': lang})
        
    if headless:
        options.headless = True
        options.add_argument("window-size=1920,1080")
        options.add_argument("user-agent={}".format(USER_AGENT_DEFAULT))
        stats["headless"] = True
        
    if not headless and user_agent is not None:
        options.add_argument("user-agent={}".format(USER_AGENT_DEFAULT))
        
    if docker:
        options.add_argument("no-sandbox")
        options.add_argument("disable-dev-shm-usage")

    for option in chrome_extra_option:
        options.add_argument(option)

    if xvfb:
        from pyvirtualdisplay import Display
        display = Display(visible=0, size=(1920, 1080))
        display.start()

    service = Service(executable_path=chrome_driver, desired_capabilities=d)
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(connection_timeout)
    time.sleep(timeout)

    if detect_topics:
        global user_data_dir
        driver.get("chrome://version")
        user_data_dir = "/".join(driver.find_element(By.ID, "profile_path").text.split("/")[:-1])
        log("Changed user dir to {}".format(user_data_dir)) 
        options.add_argument("user-data-dir={}".format(user_data_dir))
        get_data(driver)

    # Set network conditions
    if network_conditions:
        latency, download, upload = [int(e) for e in network_conditions.split(":")]
        driver.execute_cdp_cmd('Network.emulateNetworkConditions', {"latency": latency,
                                                                    "downloadThroughput": download,
                                                                    "uploadThroughput": upload,
                                                                    "offline": False})

    #  Go to the page, first visit
    stats["pre-visit"] = False
    if pre_visit:
        stats["pre-visit"] = True
        log("Making Pre-First Visit")
        driver.get(url)
        time.sleep(timeout)
        log("Getting data of pre-visit")
        get_data(driver)
        
    log("Making First Visit to: {}".format(url))
    stats["target"] = url
    stats["start-time"] = time.time()

    start_time=time.time()
    driver.get(url)
    end_time=time.time()
    
    if rum_speed_index:
        stats["collect-rum-speed-index"] = True
        rsi = driver.execute_script(open(RUM_SPEED_INDEX_FILE, "r").read() + "; return RUMSpeedIndex(); " )
        stats["first-visit-rum-speed-index"] = rsi
    
    log("First Visit Selenium time [s]: {}".format(end_time-start_time))
    stats["first-visit-selenium-time"] = end_time-start_time
    log("Landed to: {}".format(driver.current_url))
    stats["first-visit-landing-page"] = driver.current_url
    time.sleep(timeout)
    stats["first-visit-timings"] = driver.execute_script("var performance = window.performance || {}; var timings = performance.timing || {}; return timings;")
    log("Getting data of first visit")
    before_data, last_usage_time = get_data(driver)
    make_screenshot("{}/all-first.png".format(screenshot_dir))

    # Click Banner
    log("Searching Banner")
    banner_data = click_banner(driver)

    if not "clicked_element" in banner_data:
        iframe_contents = driver.find_elements(By.CSS_SELECTOR, "iframe")
        for content in iframe_contents:
            log("Switching to frame: {}".format(content.id) )
            try:
                driver.switch_to.frame(content)
                log("Searching Banner")
                banner_data = click_banner(driver)
                driver.switch_to.default_content()
                if "clicked_element" in banner_data:
                    break
            except NoSuchFrameException:
                driver.switch_to.default_content()
                log("Error in switching to frame")
                
    stats["has-scrolled"] = False
    banner_found = "clicked_element" in banner_data
    if not banner_found and try_scroll:
        log("Trying with scroll")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        log("Searching Banner")
        banner_data = click_banner(driver)
        stats["has-scrolled"] = True
        banner_found = "clicked_element" in banner_data
    stats["has-found-banner"] = banner_found
    
    click_data = None
    if banner_found or force_click_data:
        time.sleep(timeout)
        log("Getting data of post-click")
        click_data, last_usage_time = get_data(driver, after=last_usage_time)
        make_screenshot("{}/all-click.png".format(screenshot_dir))
        log("URL after click: {}".format(driver.current_url))
        stats["after-click-landing-page"] = driver.current_url

    after_data = None
    if banner_found or force_second_visit:
        #  Go to the page, second visit
        log("Making the Second Visit")
        stats["has-cleared-cache"] = False
        if clear_cache:
            clear_status()
            stats["has-cleared-cache"] = True
        # Clean last page
        driver.get("about:blank")
        get_data(driver)

        start_time=time.time()
        driver.get(url)
        end_time=time.time()
        if rum_speed_index:
            rsi = driver.execute_script(open(RUM_SPEED_INDEX_FILE, "r").read() + "; return RUMSpeedIndex(); " )
            stats["second-visit-rum-speed-index"] = rsi
            
        log("Second Visit Selenium time [s]: {}".format(end_time-start_time))
        stats["second-visit-selenium-time"] = end_time-start_time
        time.sleep(timeout)
        stats["second-visit-timings"] = driver.execute_script("var performance = window.performance || {}; var timings = performance.timing || {}; return timings;")
        log("Getting data of second visit")
        after_data, last_usage_time = get_data(driver, after=last_usage_time)
        make_screenshot("{}/all-second.png".format(screenshot_dir))
    else:
        log("Banner not found, skipping second visit")

    # Save data
    data = {"first": before_data, "click": click_data, "second": after_data, "banner_data": banner_data,
            "log": log_entries, "stats": stats, "internal": None}
    with open(outfile, "w") as file:
        json.dump(data, file, indent=4 if pretty_print else None)

    internal_data = None
    if visit_internals:
        log("Visiting Internal Pages")
        internal_urls = set()
        eles = driver.find_elements(By.XPATH, "//*[@href]")
        for elem in eles:
            url = elem.get_attribute('href').split("#")[0]
            #if url.startswith(driver.current_url) and url!=driver.current_url:
            domain_url = url.split("/")[2] if len (url.split("/")) >=3 else None
            landing_domain = driver.current_url.split("/")[2] if len (driver.current_url.split("/")) >=3 else None
            if domain_url == landing_domain and url!=driver.current_url:
                internal_urls.add(url)
        if len(internal_urls) >= num_internal:
            internal_urls_to_visit = random.sample(sorted(internal_urls), num_internal)
        else:
            log("Warning, only {} internal URLs to visit".format(len(internal_urls)) )
            internal_urls_to_visit = internal_urls
            
        for internal_url in internal_urls_to_visit:
            log("Visiting internal URL: {}".format(internal_url ))
            try:
                driver.get(internal_url)
                time.sleep(timeout)
            except TimeoutException:
                log("Warning, could not load URL {} before timeout.".format(internal_url))
        log("Getting data of internal page visits")
        internal_data, _ = get_data(driver, after=last_usage_time)

    # Save
    data = {"first": before_data, "click": click_data, "second": after_data, "banner_data": banner_data,
            "log": log_entries, "stats": stats, "internal":internal_data}
    with open(outfile, "w") as file:
        json.dump(data, file, indent=4 if pretty_print else None)

    # Quit
    if xvfb:
        display.stop()

    driver.quit()
    log("All Done")


def clear_status():
    driver.execute_cdp_cmd('Network.clearBrowserCache', {})
    if not headless:
        driver.get("chrome://net-internals/#sockets")
        driver.find_element(By.ID, "sockets-view-flush-button").click()
        driver.get("chrome://net-internals/#dns")
        driver.find_element(By.ID, "dns-view-clear-cache").click()
    else:
        log("Warning: cannot clean DNS and socket cache in headless mode.")


def get_data(driver, after = 0):

    #data = {"urls": [],"cookies": driver.get_cookies()}  # Worse than next line
    if full_net_log:
        data = { "requests": [], "responses": [], "responses-extra": [],
                "cookies": driver.execute_cdp_cmd('Network.getAllCookies', {})}
    else:
        data = { "urls": [],
                "cookies": driver.execute_cdp_cmd('Network.getAllCookies', {})}

    log = driver.get_log('performance')

    for entry in log:
        message = json.loads(entry["message"])
        if full_net_log:
            if message["message"]["method"] == "Network.responseReceived":
                data["responses"].append(message["message"]["params"])
            elif message["message"]["method"] == "Network.responseReceivedExtraInfo":
                data["responses-extra"].append(message["message"]["params"])
            elif message["message"]["method"] == "Network.requestWillBeSent":
                data["requests"].append(message["message"]["params"])
        else:
            if message["message"]["method"] == "Network.responseReceived":
                url = message["message"]["params"]["response"]["url"]
                data["urls"].append(url)

    last_usage_time = None
    if detect_topics:
        try:
            data["topics_api_usages"], last_usage_time = get_topics_api_usages(after)
        except FileNotFoundError:
            data["topics_api_usages"] = []
        
    return data, last_usage_time


def make_screenshot(path):
    if screenshot_dir is not None:
        if not os.path.exists(screenshot_dir):
            os.makedirs(screenshot_dir)
        try:
            driver.save_screenshot(path)
        except Exception as e:
            log("Exception in making screenshot: {}".format(e))


def get_signature(element):

    def props_to_dict(e):
        props = {"tag": e.tag_name }
        for attr in e.get_property('attributes'):
            props[attr['name']] = attr['value']
        return props
        
    signature = []
    current = element
    while True:
        signature.insert(0, props_to_dict(current))
        
        if current.tag_name == "html":
            break
        current = current.find_element(By.XPATH, '..')
        if current == None:
            break
        
    return signature   
    

def click_banner(driver):

    accept_words_list = set()
    for w in open(accept_words, "r").read().splitlines():
        if not w.startswith("#") and not w == "":
            accept_words_list.add(w)

    banner_data = {"matched_containers": [], "candidate_elements": []}
    contents = driver.find_elements(By.CSS_SELECTOR, GLOBAL_SELECTOR)

    candidate = None


    for c in contents:
        try:
            if c.text.lower().strip(" ✓›!\n") in accept_words_list:
                candidate = c
                banner_data["candidate_elements"].append({"id": c.id,
                                                          "tag_name": c.tag_name,
                                                          "text": c.text,
                                                          "size": c.size,
                                                          "signature": get_signature(c),
                                                          })
                break
        except:
            log("Exception in processing element: {}".format (c.id) )
            
    # Click the candidate
    if candidate is not None:
        try: # in some pages element is not clickable


            if screenshot_dir is not None:
                if not os.path.exists(screenshot_dir):
                    os.makedirs(screenshot_dir)
                try:
                    candidate.screenshot("{}/clicked_element.png".format(screenshot_dir))
                except Exception as e:
                    log("Exception in making screenshot: {}".format(e))
            log("Clicking text: {}".format (candidate.text.lower().strip(" ✓›!\n")) )
            candidate.click()
            banner_data["clicked_element"] = candidate.id
            log("Clicked: {}".format (candidate.id) )
            
        except:
            log("Exception in candidate click")
    else:
        log("Warning, no matching candidate")

    return banner_data

def get_topics_api_usages(after = 0):
    # Copy real DB (locked by current Chrome window) to temporary location
    real_db_path = "{}/Default/BrowsingTopicsSiteData".format(user_data_dir)
    tmp_db_path = "BrowsingTopicsSiteData"
    shutil.copy(real_db_path, tmp_db_path)

    # Fetch browsing topics data from temporary database
    sql = "SELECT context_origin_url, caller_source, usage_time\
           FROM browsing_topics_api_usages_complete, browsing_topics_api_hashed_to_unhashed_domain\
           WHERE browsing_topics_api_usages_complete.hashed_context_domain = browsing_topics_api_hashed_to_unhashed_domain.hashed_context_domain\
           AND usage_time > ?"
    conn = sqlite3.connect(tmp_db_path, uri=True)
    cur = conn.cursor()
    res = cur.execute(sql, [after])
    usages = []
    last_usage_time = 0
    for context_origin_url, caller_source, usage_time in res.fetchall():
        if usage_time > last_usage_time:
            last_usage_time = usage_time
        usages.append({ "context_origin_url": context_origin_url, "caller_source": caller_source, "usage_time": usage_time })
    conn.close()

    # Delete temporary database
    os.remove(tmp_db_path)

    return usages, last_usage_time

def match_domains(domain, match):
    labels_domains = domain.strip(".").split(".")
    labels_match = match.strip(".").split(".")
    return labels_match == labels_domains[-len(labels_match):]


def log(str):
    print(datetime.now().strftime("[%Y-%m-%d %H:%M:%S]"), str)
    log_entries.append((datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str))


if __name__ == "__main__":

    try:
        main()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        log("Exception at line {}: {}".format(exc_tb.tb_lineno, e))
        traceback.print_exception(exc_type, exc_obj, exc_tb)
        log("Quitting")
        driver.quit()
        exit(1)