import os
import uuid
from datetime import datetime
from io import BytesIO
from typing import Optional, List
import boto3
from botocore.exceptions import NoCredentialsError
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


from models.article import Article

# Load environment variables from .env file
load_dotenv()

# Supabase setup
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# MinIO setup (or AWS S3 setup)
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL")  # New: MinIO Endpoint URL

if S3_ENDPOINT_URL:  # Check if MinIO endpoint is provided
    s3 = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT_URL,  # Use endpoint_url for MinIO
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )
else:  # Assume AWS S3 if no MinIO endpoint
    S3_LOCATION = os.environ.get("S3_LOCATION")
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=S3_LOCATION,
    )


def upload_image_to_s3(image_url: str) -> Optional[str]:
    """
    Uploads an image from a URL to S3 (or MinIO) and returns the URL.
    """
    try:
        # Download the image
        response = requests.get(image_url)
        response.raise_for_status()

        # Create a unique filename
        image_name = f"scraped/{uuid.uuid4()}.jpg"
        image_path = image_name

        # Upload the image
        s3.upload_fileobj(
            BytesIO(response.content),
            S3_BUCKET_NAME,
            image_path,
            ExtraArgs={"ACL": "public-read"},
        )
        if S3_ENDPOINT_URL:
            s3_url = f"{S3_ENDPOINT_URL}/{S3_BUCKET_NAME}/{image_path}"
        else:
            s3_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{image_path}"
        return s3_url

    except Exception as e:
        print(f"Error uploading image: {e}")
        return None


def insert_article(article: Article) -> Optional[dict]:
    """
    Inserts an Article object into the Supabase 'articles' table.
    """
    try:
        # Convert the Pydantic model to a dictionary
        article_data = article.model_dump()
        # Convert UUID to string before inserting into Supabase
        article_data["id"] = str(article_data["id"])  # Convert id to string
        article_data["url"] = str(article_data["url"])
        article_data["s3_img"] = str(article_data["s3_img"])
        # Insert the data into the 'articles' table
        response = supabase.table("articles").insert(article_data).execute()

        # Return the inserted data
        return response.data

    except Exception as e:
        print(f"An error occurred: {e}")
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

            # Upload image to S3/MinIO
            s3_image_url = upload_image_to_s3(img_url) if img_url else None

            # Create Article object
            article = Article(
                title=title,
                url=url,
                s3_img=s3_image_url,
            )
            articles.append(article)
        except Exception as e:
            print(f"Error processing article: {e}")
            continue
    return articles


def main():
    """
    Main function to scrape, process, and save articles to Supabase.
    """
    site = Website(url="https://www.abante.com.ph/category/news/")
    scraper: Scraper = ScraperFactory().get_scraper(Scrapers.SELENIUM)

    html_str = scraper.scrape(site)

    articles = process_article_html(html_str)

    for article in articles:
        inserted_data = insert_article(article)
        if inserted_data:
            print(f"Article '{article.title}' saved to Supabase.")
        else:
            print(f"Failed to save article '{article.title}' to Supabase.")


if __name__ == "__main__":
    import requests

    main()
