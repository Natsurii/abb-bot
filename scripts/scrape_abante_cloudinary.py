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
import uuid
from datetime import datetime
from io import BytesIO
from typing import Optional, List
import requests  # Keep requests for downloading images
from lxml import html
from pydantic import BaseModel, Field, HttpUrl
from supabase import create_client, Client
from models.website import Website
from scrapers.non_async import (
    Scraper,
    ScraperFactory,
    Scrapers,
    SeleniumScraper,  # For Chrome
    SeleniumFirefoxScraper,  # For Firefox ESR
)
from urllib.parse import urlparse
from dotenv import load_dotenv

import cloudinary
import cloudinary.uploader


from models.article import Article

# Load environment variables from .env file
load_dotenv()

# Supabase setup
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Cloudinary setup
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET")

# Configure Cloudinary
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True,  # Use HTTPS
)


def upload_image_to_cloudinary(image_url: str) -> Optional[str]:
    """
    Uploads an image from a URL to Cloudinary and returns the Cloudinary URL.

    Args:
        image_url: The URL of the image to upload.

    Returns:
        The Cloudinary URL of the uploaded image, or None on error.
    """
    try:
        # Cloudinary can fetch directly from URL
        upload_result = cloudinary.uploader.upload(
            file=image_url,
            folder="scraped_articles",
            resource_type="image",
        )

        return upload_result.get("secure_url")

    except Exception as e:
        print(f"Error uploading image to Cloudinary: {e}")
        return None


def insert_article(article: Article) -> Optional[dict]:
    """
    Inserts an Article object into the Supabase 'articles' table.
    """
    try:
        # Convert the Pydantic model to a dictionary
        # Use model_dump() for Pydantic v2
        article_data = article.model_dump()

        # Convert UUID and HttpUrl types to string before inserting into Supabase
        article_data["id"] = str(article_data["id"])
        if article_data["url"]:  # Check if URL exists before converting
            article_data["url"] = str(article_data["url"])
        # Retain s3_img key, but ensure it's converted to string if it holds a Cloudinary URL
        if article_data["s3_img"]:
            article_data["s3_img"] = str(article_data["s3_img"])

        # Insert the data into the 'articles' table
        # Supabase will automatically handle fields that are None
        response = supabase.table("articles").insert(article_data).execute()

        # If the insert was successful (no exception raised), response.data will contain the inserted row(s)
        return response.data

    except Exception as e:
        # This block will now catch any API errors from Supabase as well
        print(f"An error occurred during article insertion: {e}")
        return None


def update_article_image_in_supabase(
    article_id: str, cloudinary_url: str
) -> bool:
    """
    Updates the 's3_img' field of an existing article in Supabase.
    """
    try:
        response = (
            supabase.table("articles")
            .update({"s3_img": cloudinary_url})
            .eq("id", article_id)
            .execute()
        )
        if response.data:
            print(f"Successfully updated image for article ID {article_id}.")
            return True
        else:
            print(
                f"No data returned on image update for ID {article_id}. Possible issue or no changes."
            )
            return False
    except Exception as e:
        print(
            f"Error updating image for article ID {article_id} in Supabase: {e}"
        )
        return False


def process_article_html(html_str: str) -> List[Article]:
    """
    Processes HTML to extract article data, and return Article objects.
    Image upload is handled in main function now.
    """
    tree = html.fromstring(html_str)
    articles = []

    # Find article elements
    article_elements = tree.xpath(
        ".//article[contains(@class, 'elementor-post')]"
    )

    for article_element in article_elements:
        try:
            # Extract URL
            url_element = article_element.xpath(
                ".//a[@class='elementor-post__thumbnail__link']"
            )[0]
            url = url_element.get("href")

            # Extract title
            title_element = article_element.xpath(
                ".//h3[@class='elementor-post__title']/a"
            )[0]
            title = title_element.text_content().strip()

            # Extract image URL
            img_element = article_element.xpath(".//img")[0]
            img_url = img_element.get("src")

            # Create Article object WITHOUT s3_img initially
            article = Article(
                title=title,
                url=url,
                s3_img=None,  # Set to None initially, updated later
            )
            # Store the original img_url temporarily if needed for later upload
            # We'll attach it as a dynamic attribute to the Pydantic object for convenience
            article._original_img_url = img_url
            articles.append(article)
        except Exception as e:
            print(f"Error processing article element: {e}")
            continue
    return articles


def main():
    """
    Main function to scrape, process, and save articles to Supabase,
    handling image uploads and updates to avoid duplicates.
    """
    site = Website(url="https://www.abante.com.ph/category/news/")

    if platform.system() == "Windows":
        scraper: Scraper = ScraperFactory().get_scraper(Scrapers.SELENIUM)
    elif platform.system() == "Linux":
        scraper: Scraper = ScraperFactory().get_scraper(
            Scrapers.FIREFOX
        )  # Use Firefox ESR scraper

    print(f"Scraping URL: {site.url}")
    html_str = scraper.scrape(site)
    print("Scraping complete.")

    print("Processing articles from HTML...")
    articles = process_article_html(
        html_str
    )  # This now returns articles with s3_img=None
    print(f"Found {len(articles)} articles.")

    for article in articles:
        print(f"\nProcessing article: '{article.title}' (URL: {article.url})")

        # 1. Check if article already exists in Supabase by URL
        existing_article_response = (
            supabase.table("articles")
            .select("id, s3_img")
            .eq("url", str(article.url))
            .limit(1)
            .execute()
        )

        existing_data = existing_article_response.data
        existing_article_id = None
        existing_s3_img = None

        if existing_data:
            existing_article_id = existing_data[0].get("id")
            existing_s3_img = existing_data[0].get("s3_img")
            print(
                f"Article already exists in Supabase (ID: {existing_article_id})."
            )

            # If image is missing, proceed to upload and update
            if not existing_s3_img:
                print(
                    "Existing article has no image URL. Attempting to upload image."
                )

                # Use the original image URL stored during initial parsing
                original_img_url = getattr(article, "_original_img_url", None)
                if original_img_url:
                    cloudinary_url = upload_image_to_cloudinary(
                        original_img_url
                    )
                    if cloudinary_url:
                        update_article_image_in_supabase(
                            existing_article_id, cloudinary_url
                        )
                    else:
                        print(
                            f"Failed to upload image for existing article '{article.title}'."
                        )
                else:
                    print(
                        f"No original image URL found for existing article '{article.title}'. Skipping image upload."
                    )
            else:
                print(
                    "Existing article already has an image URL. Skipping image upload."
                )
        else:
            # 2. If article does NOT exist, insert it (s3_img is None from process_article_html)
            print("Article does not exist in Supabase. Attempting to insert.")
            inserted_data = insert_article(article)  # Insert with s3_img=None

            if inserted_data:
                new_article_id = inserted_data[0].get("id")
                print(
                    f"Article '{article.title}' inserted successfully (ID: {new_article_id})."
                )

                # 3. After successful insertion, upload image and update the record
                original_img_url = getattr(article, "_original_img_url", None)
                if original_img_url:
                    print(
                        "Attempting to upload image for newly inserted article."
                    )
                    cloudinary_url = upload_image_to_cloudinary(
                        original_img_url
                    )
                    if cloudinary_url:
                        update_article_image_in_supabase(
                            new_article_id, cloudinary_url
                        )
                    else:
                        print(
                            f"Failed to upload image for newly inserted article '{article.title}'."
                        )
                else:
                    print(
                        f"No original image URL found for newly inserted article '{article.title}'. Skipping image upload."
                    )
            else:
                print(
                    f"Failed to insert article '{article.title}' into Supabase."
                )


if __name__ == "__main__":
    main()
