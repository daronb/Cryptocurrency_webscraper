# Reddit Cryptocurrency Web Scraper

This project is used to scrape old Reddit for information about Cryptocurrencies.

*This scraper can actually be used to scrape any topic from Reddit, just change the channels in the config.py file* 

***The scraper will get the following information:***

#### Channel data:
* Title of the post
* Author of the post
  * All previous posts and comments of the author after a set date
* Date of the post
* Number of likes
* Number of comments, including for each comment:
  * Author
  * Number of sub-comments
  * Date of comment
#### User data:
  * Username
  * Comments
    * New 
    * Top
  * Posts
    * New
    * Top
## Installation

Install the required modules from the requirements.txt file using:

```python
pip install -r requirements.txt
```
    
## Documentation

1. CHANNELS: 
* These are the Reddit channels that you want to scrape
2. CHANNEL_CHOICE:
* The view that you would like to select. 
* The options are:
        
        0. Hot
        1. Top
        2. New 
3. PAGES:
* Scrapes this many pages or the maximum number of posts if there are not that many pages.
