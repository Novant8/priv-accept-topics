#!/usr/bin/env python3
from banner_clicker import KeywordBannerClicker
from web_crawler.banner_crawler import BannerCrawler
from web_crawler.web_crawler import WebCrawler
from web_driver.chrome_web_driver import ChromeWebDriver
from web_driver.firefox_web_driver import FirefoxWebDriver
from lib.log import setup_logging, getLogger, getLogLevel

from web_driver import WebDriver
import argparse
import json
import trio

from api_interceptor import APICallInterceptor, CDPCallInterceptor, EmptyCallInterceptor
from api_collectors.topics import TopicsApiCallCollector
from api_collectors.protected_audience import ProtectedAudienceApiCallCollector
from api_collectors.private_state_tokens import PrivateStateTokensApiCallCollector
from api_collectors.attribution_reporting import AttributionReportingApiCallCollector
from api_collectors.related_website_sets import RelatedWebsiteSetsApiCallCollector
from api_collectors.shared_storage import SharedStorageApiCallCollector
from api_collectors.fenced_frames import FencedFramesApiCallCollector
from api_collectors.fedcm import FedCMApiCallCollector
from api_collectors.private_aggregation import PrivateAggregationApiCallCollector

# Parse Vars
parser = argparse.ArgumentParser()
parser.add_argument('--url', type=str, default='https://www.theguardian.com/')
parser.add_argument('--outfile', type=str, default='output.json')
parser.add_argument('--pretty_print', action='store_true')
parser.add_argument('--accept_words', type=str, default="accept_words.txt")
parser.add_argument('--deny', action='store_true')
parser.add_argument('--deny_words', type=str, default="deny_words.txt")
parser.add_argument('--option_words', type=str, default="option_words.txt")
parser.add_argument('--browser', type=str, default="chrome", choices=["chrome", "firefox"])
parser.add_argument('--chrome_binary', type=str, default=None)
parser.add_argument('--firefox_binary', type=str, default=None)
parser.add_argument('--chrome_driver', type=str, default="./chromedriver")
parser.add_argument('--firefox_driver', type=str, default="./geckodriver")
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
parser.add_argument('--extra_option', '--chrome_extra_option', '--firefox_extra_option', dest='extra_option', type=str, action='append', default=[])
parser.add_argument('--network_conditions', type=str, default=None)
parser.add_argument('--rum_speed_index', action='store_true')
parser.add_argument('--force_second_visit', action='store_true')
parser.add_argument('--force_click_data', action='store_true')
parser.add_argument('--visit_internals', action='store_true')
parser.add_argument('--num_internal', type=int, default=5)
parser.add_argument('--detect_topics', action='store_true', deprecated=True)
parser.add_argument('--disable_privacy_sandbox', action='store_true')
parser.add_argument('--custom_chromium', action='store_true')
parser.add_argument('--xvfb', action='store_true')
parser.add_argument('--loglevel', type=str, default="info", choices=[ "debug", "info", "warning", "error", "critical" ])

def init_api_call_interceptor(driver: WebDriver, custom_chromium: bool = False, browser: str = "chrome") -> APICallInterceptor:
    if browser == "firefox":
        return EmptyCallInterceptor()

    collectors = [
        TopicsApiCallCollector(custom_chromium),
        ProtectedAudienceApiCallCollector(),
        PrivateStateTokensApiCallCollector(),
        AttributionReportingApiCallCollector(),
        RelatedWebsiteSetsApiCallCollector(),
        SharedStorageApiCallCollector(),
        FencedFramesApiCallCollector(),
        FedCMApiCallCollector(),
        PrivateAggregationApiCallCollector()
    ]
    return CDPCallInterceptor(driver, collectors)

def init_crawler(args: argparse.Namespace, driver: WebDriver) -> WebCrawler:
    interceptor = init_api_call_interceptor(driver, args.custom_chromium, args.browser)
    banner_clicker = KeywordBannerClicker(
        name="deny" if args.deny else "accept",
        driver=driver,
        keyword_file=args.deny_words if args.deny else args.accept_words,
        option_keyword_file=args.option_words,
        args=args
    )

    return BannerCrawler(args, driver, interceptor, banner_clicker)

def init_web_driver(args: argparse.Namespace) -> WebDriver:
    if args.browser == "chrome":
        return ChromeWebDriver(args)
    else:
        return FirefoxWebDriver(args)

async def main(args: argparse.Namespace):

    # Setup XVFB if specified
    if args.xvfb:
        from pyvirtualdisplay import Display
        display = Display(visible=0, size=(1920, 1080))
        display.start()

    global driver
    driver = init_web_driver(args)
    crawler = init_crawler(args, driver)
    data = await crawler.crawl_website(args.url)

    # Save data in output
    with open(args.outfile, "w") as file:
        json.dump(data, file, indent=4 if args.pretty_print else None)
    
    # Quit
    if args.xvfb:
        display.stop()
    driver.quit()

    logger.info("Done")

if __name__ == "__main__":
    global driver
    driver: WebDriver = None
    
    args = parser.parse_args()
    
    setup_logging(getLogLevel(args.loglevel))
    global logger
    logger = getLogger(__name__)
    
    #try:
    trio.run(main, args)
    #except Exception as e:
    #    exc_type, exc_obj, exc_tb = sys.exc_info()
    #    logger.error("Exception at line {}: {}".format(exc_tb.tb_lineno, e))
    #    logger.info("Quitting")
    #    try:
    #        if driver is not None:
    #            driver.quit()
    #    except NameError:
    #        pass
    #    exit(1)