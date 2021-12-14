import logging

BASE_URL = "https://old.reddit.com/"
HEADERS = {'User-Agent': 'Mozilla/5.0'}

API_KEY = 'PLEASE INSERT API KEY HERE'
API_URL = "https://api-inference.huggingface.co/models/finiteautomata/beto-sentiment-analysis"

USER_FIELDS = 'user_name, post_karma, comment_karma, date_joined'
POST_FIELDS = '''user_id, title, likes, comments, date_posted, sub_reddit, post_source, post_option, 
                 positive_sentiment, neutral_sentiment, negative_sentiment'''
COMMENT_FIELDS = '''post_id, author, text, points, comment_date, sub_comments,
                    reddit_parent_id, reddit_comment_id, reddit_post_id'''

UPDATE_COMMENT_QUERY = """update reddit_data.comment a 
                          join reddit_data.comment b on a.reddit_parent_id = b.reddit_comment_id
                          set a.parent_comment_id = b.comments_id
                          where a.comments_id > 0;"""

VIEWS = ['new', 'top']

UNSUPPORTED_FORMAT = 'format not supported'
CLI_DESCRIPTION = '''
    --------------------------------
            REDDIT WEB-SCRAPER
    --------------------------------
    Use this to scrape posts, comments & user data 
    from any subreddit on reddit.
    The data will be saved in a MySQL database'''
CLI_USERNAME_HELP = 'Your username for your MySQL database where the scraped data will be stored'
CLI_PASSWORD_HELP = 'Your password for your MySQL database where the scraped data will be stored'
CLI_SUBREDDIT_HELP = 'The name of the subreddit that you want to scrape'
CLI_CHOICE_HELP = '''The settings of posts selected on the subreddit page: [new, top]
    In case of top please add "-" followed by specification of range [day, week, month, year, all]'''
CLI_PAGES_HELP = 'The number of pages to scrape, there are 25 posts on each page'

WEBDRIVER_PATH = 'PLEASE INSERT CHROME WEB-DRIVER PATH HERE'

LOG_FILE_NAME = 'scraper_log.log'
LOGGING_LEVEL = logging.INFO
