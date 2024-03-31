# Documentation for the scraper functionalities

# How to use

# Progress Report
## Progress
* Finished implemented a webscraping pipeline for the CVH datasets
* Scraped 180 entities in first batch 
* Have set up a scraping automation pipeline with crontab and shellscript to perform the ETL process.

## Problem
* Error Handling for scraper code
* Headless option to be able to run the code on a VM
* Currently the CVH's index is meaningless, scraping from the start gives you only the a small subset.

## Plan
* SE the scraper code
* Complete headless option scraper
* Identify handwritten datasets (by year maybe?)
* Scraper more samples (10000)
* Capusalize it with docker.
