# Reddit Cryptocurrency Web Scraper
This project is used to scrape old Reddit for information about Cryptocurrencies.

*This scraper can actually be used to scrape any topic from Reddit, just insert valid subreddit while running from terminal* 

<p>The web scraper gets the following information and stores all the data into a MySQL database.<br>
New data is inserted while existing data will be updated.</p>

#### Post Data

* Title 
* Author 
* Date posted
* Number of likes
* Number of comments
* Sentiment of the title - This is from an external API from HuggingFace

#### Comment Data
For each post that was scraped from the sub-reddit, the comments for that post are also scraped and contain the following information:
  * Author
  * Text
  * Points
  * Number of sub-comments
  * Date of comment
#### User Data
For each **post** that is scraped, the data of user of the post is also scraped, along with 25 of the user's new and top posts which will be stored in the posts table. 
User data contains the following:
  * Username
  * Comment Karma 
  * Post Karma
  
## Getting Started with the project
If you would like to run this project on your own you will need to go through the set-up as follows:
### Installations
You will need to install python 3 and MySQL

Install the required python modules from the requirements.txt file using:
```
pip install -r requirements.txt
```
Install chrome web-driver from:
https://chromedriver.chromium.org/downloads

add path in `config.py` file in `WEBDRIVER_PATH`.

Clone this GitHub Repo 
    
### SQL Database

The scraper stores the in an SQL database named `reddit_data`.<br>The database can be created by running the file named: `generate_tables.sql` in your MySQL workbench or on your MySQL terminal. 

This database contains the following tables:
* `user`
* `post`
* `comment`

The structure of the database can be found in the `EER diagram.mwb` file

The `user` table contains information about the specific Reddit user that posted on the subreddit.

The `post` table contains the information about the individual posts, such as the number of points, number of comments, when the post was made and where the post was scraped from.

The `comment` table contains the comments for the posts which were scraped from the sub-reddit page. Each child comment can be linked to its parent comment in the case that there are sub-comments

*MySQL was used for this project*


### Additional Information from an API
The post data was enriched by using a sentiment analysis API from HuggingFace.

The model can be found here: https://github.com/finiteautomata/pysentimiento/

In order to use the API, you need to create an account with **HuggingFace 🤗** and generate a new token which will be inputted into the scraper in the config file.

You can get a token from the HuggingFace website https://huggingface.co/pricing

The HuggingFace token is called `API_KEY` in the `config.py` file.

The information from this API is:
* positive_sentiment
* neutral_sentiment
* negative_sentiment


## How to Run the Code
The scraper comes with a CLI which is used to run the code via the command line.

If you need help with any of the arguments of the scraper you can run the following command:
` python3 scraper.py -h`. Running this will give instructions on how to run the code.

### CLI Documentation
The CLI has 5 parameters which you need to input in order to run the code. 

They are as follows:


1. `username`: username for SQL connection (string)
2. `password`: password for SQL connection (string)
3. `subreddit`: subreddit from which you want to scrape data (string)
4. `choice`: The view that you would like to select, this parameter has specific options
* The options are:
  * `new` - This will scrape the new posts (string)
  * `top` - This will scrape the top posts for a given timeframe. When using `top`, you will also need to specify the timeframe in this format: `top-timeframe` (string)
    * valid `timeframe`: day, week, month, year, all (all time)
    
5. `pages`: The number of pages that you would like to scrape (int)

An example of the CLI usage is as follows:<br>
`python3 scraper.py username password bitcoin top-week 2`