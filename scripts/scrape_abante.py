"""
Copyright (c) 2025 Natsurii.

Created Date: Monday, May 12th 2025, 1:13:50 pm
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
2025-05-12	NAT	Initial script creation
"""

from lxml import html
from models.website import Website
from scrapers.non_async import ScraperFactory, Scrapers

# site = Website(url="https://www.abante.com.ph/category/news/")
# scraper = ScraperFactory().get_scraper(Scrapers.SELENIUM)

# html = scraper.scrape(site)


# with open("abante_scrape2.html", "w+", encoding="utf-8") as file:
#     file.write(html)
html_str = ""
with open("abante_scrape2.html", "r", encoding="utf-8") as file:
    html_str = file.read()
tree = html.fromstring(html_str)

# Find all <a> elements with the class 'elementor-post__thumbnail__link'
links = tree.xpath(".//a[@class='elementor-post__thumbnail__link']")

# Print href or text
for link in links:
    href = link.get("href")
    print(href)
