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
