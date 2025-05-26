import os
import uuid
from datetime import datetime
from typing import Optional, List
import requests
from lxml import html
from supabase import create_client, Client
from scrapers.non_async import (
    Scraper,
    ScraperFactory,
    Scrapers,
    SeleniumScraper,
)
from dotenv import load_dotenv

from models.website import (
    Website,
)  # Ensure Website model is imported from your models

import re

# Load environment variables from .env file
load_dotenv()

# Supabase setup
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)


def get_articles_with_missing_info() -> List[dict]:
    """
    Queries Supabase to find articles where author, content, tags, or published_at is NULL.
    Returns a list of dictionaries, where each dictionary represents an article.
    """
    try:
        response = (
            supabase.table("articles")
            .select("*")
            .or_(
                "author.is.null,content.is.null,tags.is.null,published_at.is.null"
            )
            .limit(1)
            .execute()
        )  # Limit to 1 to process one at a time for demonstration

        # The 'data' attribute contains the results
        return response.data
    except Exception as e:
        print(f"Error querying Supabase for missing info: {e}")
        return []


def scrape_missing_info(url: str) -> dict:
    """
    Scrapes the given URL for author, content, tags, and published date.
    Uses SeleniumScraper if a dynamic page.
    """
    print(f"Scraping URL: {url}")
    scraper: Scraper = ScraperFactory().get_scraper(Scrapers.SELENIUM)

    site_obj = Website(url=url)
    html_content = scraper.scrape(site_obj)

    tree = html.fromstring(html_content)
    scraped_data = {}

    # --- Scrape Author ---
    author_element = tree.xpath(
        '//aside[contains(@class, "elementor-element-65438cc")]//h2[@class="elementor-heading-title"]/text()'
    )
    scraped_data["author"] = (
        author_element[0].strip() if author_element else "Abante News"
    )

    # --- Scrape Content ---
    content_paragraphs = tree.xpath(
        '//div[@data-widget_type="theme-post-content.default"]//p'
    )  # Get the paragraph elements

    full_content = []
    for p_element in content_paragraphs:
        # Get all text nodes within the paragraph, including those nested in other tags if any
        paragraph_text = " ".join(p_element.xpath(".//text()")).strip()
        if paragraph_text:
            full_content.append(paragraph_text)

    # Join the collected paragraphs
    raw_content = "\n".join(full_content)

    # Remove "ADVERTISEMENT" case-insensitively and clean up multiple newlines/spaces
    cleaned_content = re.sub(
        r"\s*ADVERTISEMENT\s*", "", raw_content, flags=re.IGNORECASE
    )
    cleaned_content = (
        re.sub(r"\n+", "\n", cleaned_content).strip()
    )  # Replace multiple newlines with single, then strip leading/trailing

    scraped_data["content"] = cleaned_content if cleaned_content else None

    if scraped_data["content"]:
        sentences = scraped_data["content"].split(".")
        scraped_data["summary"] = (
            ". ".join(sentences[:2]).strip() + "." if sentences else None
        )

    # --- Scrape Tags ---
    tag_elements = tree.xpath(
        '//span[contains(@class, "elementor-post-info__terms-list")]/a/text()'
    )
    scraped_data["tags"] = (
        [tag.strip() for tag in tag_elements] if tag_elements else []
    )

    # --- Scrape Published At ---
    published_at_element = tree.xpath(
        '//li[@itemprop="datePublished"]//time/text()'
    )
    if published_at_element:
        try:
            date_str = published_at_element[0].strip()
            scraped_data["published_at"] = datetime.strptime(
                date_str, "%B %d, %Y"
            ).isoformat()
        except ValueError as ve:
            print(f"Could not parse date '{date_str}': {ve}")
            scraped_data["published_at"] = None
    else:
        scraped_data["published_at"] = None

    return scraped_data


def update_article_in_supabase(article_id: str, update_data: dict) -> bool:
    """
    Updates an article in Supabase with the provided data.
    """
    try:
        # Supabase update expects a dictionary of columns to update
        response = (
            supabase.table("articles")
            .update(update_data)
            .eq("id", article_id)
            .execute()
        )

        # Check if data was updated successfully
        if response.data:
            print(f"Successfully updated article ID {article_id}.")
            return True
        else:
            print(
                f"No data returned on update for ID {article_id}. Possible issue or no changes."
            )
            return False
    except Exception as e:
        print(f"Error updating article ID {article_id} in Supabase: {e}")
        return False


def main():
    """
    Main function to find missing articles, scrape info, and update Supabase.
    """
    print("Searching for articles with missing information...")
    articles_to_update = get_articles_with_missing_info()

    if not articles_to_update:
        print(
            "No articles found with missing author, content, tags, or published date."
        )
        return

    print(
        f"Found {len(articles_to_update)} article(s) with missing information. Processing..."
    )

    for article_record in articles_to_update:
        article_id = article_record.get("id")
        article_url = article_record.get("url")
        article_title = article_record.get("title")

        if not article_url:
            print(f"Article ID {article_id} has no URL. Skipping.")
            continue

        print(
            f"\nProcessing article: '{article_title}' (ID: {article_id}, URL: {article_url})"
        )

        scraped_info = scrape_missing_info(article_url)
        print(f"Scraped Info: {scraped_info}")

        # Prepare update data, only including non-None values from scraping
        update_payload = {
            k: v for k, v in scraped_info.items() if v is not None
        }

        # Ensure tags are not empty list if scraped_info["tags"] was empty (Supabase needs actual null for None)
        if "tags" in update_payload and not update_payload["tags"]:
            update_payload[
                "tags"
            ] = []  # Send empty list if no tags found, not None

        if update_payload:
            success = update_article_in_supabase(article_id, update_payload)
            if success:
                print(
                    f"Article '{article_title}' successfully updated in Supabase."
                )
            else:
                print(
                    f"Failed to update article '{article_title}' in Supabase."
                )
        else:
            print(
                f"No new information scraped for article '{article_title}'. Skipping update."
            )


if __name__ == "__main__":
    main()
