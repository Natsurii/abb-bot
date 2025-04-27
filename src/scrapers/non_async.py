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
Date      	By	Comments
----------	---	----------------------------------------------------------
2025-04-27	NAT	Initial file creation.
"""

from abc import ABC, abstractmethod
from enum import Enum

import requests

from models.website import Website


class Scrapers(Enum):
    """Scraper Types Enum."""

    REQUESTS = 1
    SCRAPY = 2


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

    def scrape(self, url: Website | str) -> str:
        """Scrape website using requests.

        Args:
            url (Website | str): The url of the website

        Returns:
            str: The content of the website

        """
        if isinstance(url, str):
            url = Website(url=url)
        response = requests.get(url.url, timeout=30, headers=self.headers)
        response.raise_for_status()
        return response.text


class ScrapyScraper(Scraper):
    """Scrapy concrete Scraper."""

    def __init__(self) -> None:
        """Scrapy scraper constructor."""
        self.url: str = ""
        raise NotImplementedError

    def scrape(self, url: Website | str) -> str:
        """Scrape using scrapy.

        Args:
            url (Website): The url of the website needed to be scraped

        Raises:
            NotImplementedError: There is no implementation available.

        Returns:
            str: The scraped HTML in string.

        """
        if isinstance(url, str):
            self.url: str = Website(url=url).url
        raise NotImplementedError


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
            case _:
                msg = "Invalid supplied scraper."
                raise ValueError(msg)
