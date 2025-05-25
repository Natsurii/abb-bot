import os
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
    SeleniumScraper,
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
        # Download the image content
        response = requests.get(image_url, stream=True)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Upload the image to Cloudinary
        # We can pass the raw content or the URL directly
        upload_result = cloudinary.uploader.upload(
            file=image_url,  # Cloudinary can fetch directly from URL
            folder="scraped_articles",  # Optional: organize uploads in a folder
            resource_type="image",  # Ensure it's treated as an image
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


def process_article_html(html_str: str) -> List[Article]:
    """
    Processes HTML to extract article data, upload images, and return Article objects.
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

            # Upload image to Cloudinary
            cloudinary_image_url = (
                upload_image_to_cloudinary(img_url) if img_url else None
            )

            # Create Article object
            article = Article(
                title=title,
                url=url,
                s3_img=cloudinary_image_url,  # Assign to s3_img
            )
            articles.append(article)
        except Exception as e:
            print(f"Error processing article element: {e}")
            continue
    return articles


def main():
    """
    Main function to scrape, process, and save articles to Supabase.
    """
    site = Website(url="https://www.abante.com.ph/category/news/")
    scraper: Scraper = ScraperFactory().get_scraper(Scrapers.SELENIUM)

    print(f"Scraping URL: {site.url}")
    html_str = scraper.scrape(site)
    print("Scraping complete.")

    print("Processing articles from HTML...")
    articles = process_article_html(html_str)
    print(f"Found {len(articles)} articles.")

    for article in articles:
        print(f"Attempting to insert article: '{article.title}'")
        inserted_data = insert_article(article)
        if inserted_data:
            print(f"Article '{article.title}' saved to Supabase.")
        else:
            print(f"Failed to save article '{article.title}' to Supabase.")


if __name__ == "__main__":
    main()
