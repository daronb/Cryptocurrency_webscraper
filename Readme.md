# Reddit Cryptocurrency Web Scraper
This project is used to scrape old Reddit for information about Cryptocurrencies.
*This scraper can actually be used to scrape any topic from Reddit, just insert valid subreddit while running from terminal* 
***The scraper will get the following information:***
#### Channel data:
* Title of the post
* Author of the post
  * Previous posts of the author
* Date of the post
* Number of likes
* Number of comments, including for each comment:
  * Author
  * Text
  * Points
  * Number of sub-comments
  * Date of comment
#### User data:
  * Username
  * Comment Karma 
  * Post Karma
  * Posts
    * New (25)
    * Top (25)
## Installation
Install the required modules from the requirements.txt file using:
```python
pip install -r requirements.txt
```
Install chrome web-driver from:
https://chromedriver.chromium.org/downloads

add path in config.py file in 'WEBDRIVER_PATH'.
    
## CLI Documentation
username: 
* username for SQL connection
password:
* password for SQL connection
subreddit:
* subreddit to scrape data from
choice:
* The view that you would like to select. 
* The options are:
  * New 
  * Top
    * range of time to search top posts in
    * day, week, month, year, all (all time)
pages:
* Scrapes this many pages or the maximum number of posts if there are not that many pages.
## SQL Database
The scraper stores the in an SQL database which can be created using the file named: generate_tables.sql
This database contains the following tables:
* user
* post
* comment

The structure of the database can be found in the EER diagram.mwb file

The user table contains information about the specific Reddit user that posted on the subreddit.

The post table contains the information about the individual posts, such as the number of points, number of comments, when the post was made and where the post was scraped from.

The comment table contains the comments for the posts which were scraped from the sub-reddit page. Each child comment can be linked to its parent comment in the case that there are sub-comments

## Additional information from an API
The post data was enriched by using a sentiment analysis API from HuggingFace.

The model can be found here: https://github.com/finiteautomata/pysentimiento/

In order to use the API, you need to create an account with HuggingFace and generate a new token which will be inputted into the scraper in the config file.

You can get a token from the HuggingFace website https://huggingface.co/pricing

The HuggingFace token is called API_KEY in the config.py file.

The information from this API is:
* positive_sentiment
* neutral_sentiment
* negative_sentiment