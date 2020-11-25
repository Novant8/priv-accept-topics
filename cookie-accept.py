#!/usr/bin/env python3

# HOW TO CLEAN THE common.css FILE FROM "I DON T CARE ABOUT COOKIES"
# cat common-original.css | sed -e 's/{[^][]*}/,/g' | sed '/^$/d' | sed '/^\/\*/d' | sed '/^,$/d' | sed 's/,$//'  | awk '{printf("##%s\n", $0)}' > common-adb.txt

from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
import argparse
from urllib.parse import urlparse
from datetime import datetime
from selenium import webdriver
import os
import sys
import json
import time
import re

# Parse Vars
parser = argparse.ArgumentParser()
parser.add_argument('--url', type=str, default='https://www.repubblica.it')
parser.add_argument('--outfile', type=str, default='output.json')
parser.add_argument('--selectors', type=str, default="selectors.txt")
parser.add_argument('--accept_words', type=str, default="accept_words.txt")
parser.add_argument('--chrome_driver', type=str, default="./chromedriver")
parser.add_argument('--screenshot_dir', type=str, default=None)
parser.add_argument('--lang', type=str, default=None)
parser.add_argument('--timeout', type=int, default=5)
parser.add_argument('--clear_cache', action='store_true')
parser.add_argument('--headless', action='store_true')
parser.add_argument('--try_scroll', action='store_true')
parser.add_argument('--global_search', action='store_true')
parser.add_argument('--full_net_log', action='store_true')
parser.add_argument('--pre_visit', action='store_true')
globals().update(vars(parser.parse_args()))

log_entries = []
GLOBAL_SELECTOR = "a, button"
stats = {}


def main():
    global driver
    global url

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
    if lang is not None:
        stats["lang"] = lang
        options.add_experimental_option('prefs', {'intl.accept_languages': lang})
    if headless:
        options.headless = True
        options.add_argument("window-size=1920,1080")
        stats["headless"] = True
    driver = webdriver.Chrome(executable_path=chrome_driver, desired_capabilities=d, options=options)
    time.sleep(timeout)

    #  Go to the page, first visit
    stats["pre-visit"] = False
    if pre_visit:
        stats["pre-visit"] = True
        driver.get(url)
    log("Making First Visit to: {}".format(url))
    stats["target"] = url
    stats["start-time"] = time.time()

    start_time=time.time()
    driver.get(url)
    end_time=time.time()
    log("First Visit Selenium time [s]: {}".format(end_time-start_time))
    stats["first-visit-selenium-time"] = end_time-start_time
    log("Landed to: {}".format(driver.current_url))
    stats["first-visit-landing-page"] = driver.current_url
    time.sleep(timeout)
    stats["first-visit-timings"] = driver.execute_script("var performance = window.performance || {}; var timings = performance.timing || {}; return timings;")
    before_data = get_data(driver)
    make_screenshot("{}/all-first.png".format(screenshot_dir))

    # Click Banner
    log("Clicking Banner")
    banner_data = click_banner(driver)

    if not "clicked_element" in banner_data:
        iframe_contents = driver.find_elements_by_css_selector("iframe")
        for content in iframe_contents:
            driver.switch_to.frame(content)
            banner_data = click_banner(driver)
            driver.switch_to.default_content()
            if "clicked_element" in banner_data:
                break
    stats["has-scrolled"] = False
    if not "clicked_element" in banner_data and try_scroll:
        log("Trying with scroll")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        stats["has-scrolled"] = True
    stats["has-found-banner"] = "clicked_element" in banner_data
    time.sleep(timeout)
    click_data = get_data(driver)
    make_screenshot("{}/all-click.png".format(screenshot_dir))
    log("URL after click: {}".format(driver.current_url))
    stats["after-click-landing-page"] = driver.current_url

    #  Go to the page, second visit
    log("Making the Second Visit")
    stats["has-cleared-cache"] = False
    if clear_cache:
        clear_status()
        stats["has-cleared-cache"] = True
    # Clean last page
    driver.get("about:blank")
    _ = get_data(driver)
    if pre_visit:
        driver.get(url)

    start_time=time.time()
    driver.get(url)
    end_time=time.time()
    log("Second Visit Selenium time [s]: {}".format(end_time-start_time))
    stats["second-visit-selenium-time"] = end_time-start_time
    time.sleep(timeout)
    stats["second-visit-timings"] = driver.execute_script("var performance = window.performance || {}; var timings = performance.timing || {}; return timings;")
    after_data = get_data(driver)
    make_screenshot("{}/all-second.png".format(screenshot_dir))

    # Save
    data = {"first": before_data, "click": click_data, "second": after_data, "banner_data": banner_data,
            "log": log_entries, "stats": stats}
    json.dump(data, open(outfile, "w"), indent=4)

    # Quit
    driver.quit()
    log("All Done")


def clear_status():
    driver.execute_cdp_cmd('Network.clearBrowserCache', {})
    if not headless:
        driver.get("chrome://net-internals/#sockets")
        driver.find_element_by_id("sockets-view-flush-button").click()
        driver.get("chrome://net-internals/#dns")
        driver.find_element_by_id("dns-view-clear-cache").click()
    else:
        log("Warning: cannot clean DNS and socket cache in headless mode.")


def get_data(driver):

    #data = {"urls": [],"cookies": driver.get_cookies()}  # Worse than next line
    if full_net_log:
        data = { "requests": [], "responses": [],
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
            elif message["message"]["method"] == "Network.requestWillBeSent":
                data["requests"].append(message["message"]["params"])
        else:
            if message["message"]["method"] == "Network.responseReceived":
                url = message["message"]["params"]["response"]["url"]
                data["urls"].append(url)

    return data


def make_screenshot(path):
    if screenshot_dir is not None:
        if not os.path.exists(screenshot_dir):
            os.makedirs(screenshot_dir)
        try:
            driver.save_screenshot(path)
        except Exception as e:
            log("Exception in making screenshot: {}".format(e))


def click_banner(driver):

    accept_words_list = []
    for w in open(accept_words, "r").read().splitlines():
        if not w.startswith("#") and not w == "":
            accept_words_list.append(w)

    banner_data = {"matched_containers": [], "candidate_elements": []}

    if global_search:
        contents = driver.find_elements_by_css_selector(GLOBAL_SELECTOR)
    else:
        selectors_css = parse_rules(selectors, urlparse(driver.current_url).netloc)
        contents = driver.find_elements_by_css_selector(selectors_css)
    if len(contents) == 0:
        log("Warning, no banner found")
        return banner_data

    if len(contents) > 1:
        log("Warning, more than a cookie banner detected.")
    candidate = None

    if not global_search:
        for i, c in enumerate(contents):
            banner_data["matched_containers"].append({"id": c.id,
                                                      "tag_name": c.tag_name,
                                                      "text": c.text,
                                                      "size": c.size,
                                                      "selected": True if i == 0 else False,
                                                      })

            if screenshot_dir is not None:
                if not os.path.exists(screenshot_dir):
                    os.makedirs(screenshot_dir)
                try:
                    c.screenshot("{}/matched-container-{}.png".format(screenshot_dir, i))
                except Exception as e:
                    log("Exception in making screenshot: {}".format(e))


        # Try Links, add the element itself in case
        links = []
        for c in contents:
            links += c.find_elements_by_tag_name("a")
            if c.tag_name == "a":
                links.append(c)

        for c in links:
            if c.text.lower().strip(" ✓›!") in accept_words_list:
                candidate = c
                banner_data["candidate_elements"].append({"id": c.id,
                                                          "tag_name": c.tag_name,
                                                          "text": c.text,
                                                          "size": c.size,
                                                          })

        # Try buttons, add the element itself in case
        btns = []
        for c in contents:
            btns += c.find_elements_by_tag_name("button")
            if c.tag_name == "button":
                btns.append(c)

        for c in btns:
            if c.text.lower().strip(" ✓›!") in accept_words_list:
                candidate = c
                banner_data["candidate_elements"].append({"id": c.id,
                                                          "tag_name": c.tag_name,
                                                          "text": c.text,
                                                          "size": c.size,
                                                          })
    else:
        for c in contents:
            if c.text.lower().strip(" ✓›!") in accept_words_list:
                candidate = c
                banner_data["candidate_elements"].append({"id": c.id,
                                                          "tag_name": c.tag_name,
                                                          "text": c.text,
                                                          "size": c.size,
                                                          })
                break
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

            candidate.click()
            banner_data["clicked_element"] = candidate.id
        except:
            pass
    else:
        log("Warning, no matching candidate")

    return banner_data


def match_domains(domain, match):
    labels_domains = domain.strip(".").split(".")
    labels_match = match.strip(".").split(".")
    return labels_match == labels_domains[-len(labels_match):]


def parse_rules(file_name, target_domain=""):
    selectors = []
    for line in open(file_name, "r").read().splitlines():

        if not line.startswith("!") and "##" in line:

            selector = re.search("(?<=##).+$", line).group(0)

            domain_rules = re.search("^[a-zA-Z0-9-\\.~,]+(?=##)", line)

            if domain_rules is not None:
                domains = domain_rules.group(0).split(",")
                found_positive = False
                found_negative = False

                for domain in domains:
                    if domain.startswith("~") and match_domains(target_domain, domain[1:]):
                        found_negative = True
                    elif match_domains(target_domain, domain):
                        found_positive = True

                if found_positive and not found_negative:
                    selectors.append(selector)

            else:
                selectors.append(selector)

    return ", ".join(selectors)


def log(str):
    print(datetime.now().strftime("[%Y-%m-%d %H:%M:%S]"), str)
    log_entries.append((datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str))


if __name__ == "__main__":

    try:
        main()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        log("Exception at line {}: {}".format(exc_tb.tb_lineno, e))
        log("Quitting")
        driver.quit()
