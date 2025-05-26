"""Copyright (c) 2025 Natsurii.

Created Date: Sunday, April 27th 2025, 7:10:41 pm
Author: Natsurii

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

1. Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in the
documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
contributors may be used to endorse or promote products derived from this
software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS AS
IS AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
THE POSSIBILITY OF SUCH DAMAGE.

HISTORY:
Date        By  Comments
----------  --- ----------------------------------------------------------
2025-04-27  NAT Initial file creation.
"""

import os
import platform
import time
from abc import ABC, abstractmethod
from enum import Enum

import requests
from selenium import webdriver

# Import Chrome-specific components
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService

# Import Firefox-specific components
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager  # Import for Firefox

from models.website import Website

# if platform.system() == "Windows":
#     CHROME_DRIVER_PATH = os.path.join(
#         os.path.dirname(__file__),
#         "chromedriver",
#         "chromedriver.exe",
#     )
# elif platform.system() == "Linux":
#     CHROME_DRIVER_PATH = None
#     raise NotImplementedError


class Scrapers(Enum):
    """Scraper Types Enum."""

    REQUESTS = 1
    SCRAPY = 2
    SELENIUM = 3
    FIREFOX = 4  # Added Firefox option


class Scraper(ABC):
    """Scraper abstract class."""

    @abstractmethod
    def scrape(self, url: Website) -> str:
        """Handle the webscraping to url.

        Args:
            url (Website): The url needed to be scraped.

        Returns:
            str: The scraped HTML in string.

        """


class RequestsScraper(Scraper):
    """Requests concrete scraper."""

    def __init__(self) -> None:
        """Scraper constructor."""
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",  # noqa: E501
        }

    def scrape(self, url: Website) -> str:
        """Scrape website using requests.

        Args:
            url (Website | str): The url of the website

        Returns:
            str: The content of the website

        """
        response = requests.get(str(url.url), timeout=30, headers=self.headers)
        response.raise_for_status()
        return response.text


class ScrapyScraper(Scraper):
    """Scrapy concrete Scraper."""

    def __init__(self) -> None:
        """Scrapy scraper constructor."""
        self.url: str = ""
        raise NotImplementedError

    def scrape(self, url: Website) -> str:
        """Scrape using scrapy.

        Args:
            url (Website): The url of the website needed to be scraped

        Raises:
            NotImplementedError: There is no implementation available.

        Returns:
            str: The scraped HTML in string.

        """
        raise NotImplementedError


class SeleniumScraper(Scraper):
    """Selenium Scraper Concrete Class (for Chrome)."""

    def __init__(self) -> None:
        """Initialize selenium scraper."""
        self.wait: float = 25.0
        self.scroll_down: bool = True
        self.scroll_down_until: float = 10.0

    def scrape(self, url: Website) -> str:
        """Scrape the given website url.

        Args:
            url (Website): The website needed to be scraped

        Returns:
            str: The html scraped in string.

        """
        chrome_options = ChromeOptions()  # Using ChromeOptions
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        # Use ChromeDriverManager to automatically download and manage the driver
        service = ChromeService(
            ChromeDriverManager().install()
        )  # Using ChromeService
        driver = webdriver.Chrome(service=service, options=chrome_options)
        try:
            driver.get(str(url.url))
            WebDriverWait(driver, self.wait).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            if self.scroll_down:
                scroll_pause = 1
                end_time = time.time() + self.scroll_down_until
                last_height = driver.execute_script(
                    "return document.body.scrollHeight"
                )

                while time.time() < end_time:
                    driver.execute_script(
                        "window.scrollTo(0, document.body.scrollHeight);"
                    )
                    time.sleep(scroll_pause)
                    new_height = driver.execute_script(
                        "return document.body.scrollHeight"
                    )
                    if new_height == last_height:
                        break
                    last_height = new_height
            return driver.page_source

        finally:
            driver.quit()


# --- New SeleniumFirefoxScraper Class for ESR ---
class SeleniumFirefoxScraper(Scraper):
    """Selenium Scraper Concrete Class (for Firefox ESR)."""

    def __init__(self) -> None:
        """Initialize selenium firefox scraper for ESR."""
        self.wait: float = 25.0
        self.scroll_down: bool = True
        self.scroll_down_until: float = 10.0

        self.firefox_options = FirefoxOptions()
        self.firefox_options.add_argument(
            "-headless"
        )  # Firefox uses "-headless" for headless mode

        # --- IMPORTANT: Explicitly set the binary location for Firefox ESR ---
        # You need to find the exact path to your firefox-esr executable on your Linux system.
        # Common paths include: '/usr/bin/firefox-esr', '/usr/lib/firefox-esr/firefox', etc.
        # You can usually find it by running 'which firefox-esr' or 'whereis firefox-esr' in your terminal.

        # Placeholder path - **YOU MUST VERIFY AND ADJUST THIS PATH**
        firefox_esr_binary_path = "/usr/bin/firefox-esr"

        if not os.path.exists(firefox_esr_binary_path):
            error_msg = (
                f"Firefox ESR binary not found at '{firefox_esr_binary_path}'. "
                "Please ensure Firefox ESR is installed on your system "
                "and update 'firefox_esr_binary_path' in SeleniumFirefoxScraper's __init__ "
                "with the correct path."
            )
            print(f"ERROR: {error_msg}")
            raise FileNotFoundError(error_msg)

        self.firefox_options.binary_location = firefox_esr_binary_path
        # --- End of explicit binary setting ---

        # Geckodriver service (managed by webdriver_manager)
        # GeckoDriverManager will download a geckodriver compatible with the *specified* browser binary.
        self.service = FirefoxService(GeckoDriverManager().install())
        self.driver = None  # Initialize driver to None for reuse

    def scrape(self, url: Website) -> str:
        """Scrape the given website url using Firefox ESR.

        Args:
            url (Website): The website needed to be scraped

        Returns:
            str: The html scraped in string.

        """
        # Re-initialize driver if it's not active
        if self.driver is None:
            self.driver = webdriver.Firefox(
                service=self.service, options=self.firefox_options
            )
            self.driver.set_page_load_timeout(60)  # Set a generous timeout

        try:
            self.driver.get(str(url.url))
            WebDriverWait(self.driver, self.wait).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            if self.scroll_down:
                scroll_pause = 1
                end_time = time.time() + self.scroll_down_until
                last_height = self.driver.execute_script(
                    "return document.body.scrollHeight"
                )

                while time.time() < end_time:
                    self.driver.execute_script(
                        "window.scrollTo(0, document.body.scrollHeight);"
                    )
                    time.sleep(scroll_pause)
                    new_height = self.driver.execute_script(
                        "return document.body.scrollHeight"
                    )
                    if new_height == last_height:
                        break
                    last_height = new_height
            return self.driver.page_source

        finally:
            # Quit the driver after each scrape call.
            if self.driver:
                self.driver.quit()
                self.driver = None  # Reset for next use


class ScraperFactory:
    """Scraper Factory."""

    def __init__(
        self,
        scraper_type: Scrapers = Scrapers.REQUESTS,
    ) -> None:
        """Scraper Factory constructor."""
        self.scraper = scraper_type

    def get_scraper(self, scraper_type: Scrapers | None = None) -> Scraper:
        """Get concrete scraper."""
        if scraper_type is not None:
            self.scraper = scraper_type

        match self.scraper:
            case Scrapers.REQUESTS:
                return RequestsScraper()
            case Scrapers.SCRAPY:
                return ScrapyScraper()
            case Scrapers.SELENIUM:  # This will now specifically be for Chrome
                return SeleniumScraper()
            case Scrapers.FIREFOX:  # Added case for Firefox ESR
                return SeleniumFirefoxScraper()
            case _:
                msg = "Invalid supplied scraper."
                raise ValueError(msg)
