import time
import re
import pymysql.cursors
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
import sys
import argparse
import config as cfg
import logging

# internet constants
BASE_URL = cfg.BASE_URL
HEADERS = cfg.HEADERS
API_URL = cfg.API_URL
API_KEY = cfg.API_KEY
# SQL queries constants
USER_FIELDS = cfg.USER_FIELDS
POST_FIELDS = cfg.POST_FIELDS
COMMENT_FIELDS = cfg.COMMENT_FIELDS
UPDATE_COMMENT_QUERY = cfg.UPDATE_COMMENT_QUERY
# CLI constants
CLI_DESCRIPTION = cfg.CLI_DESCRIPTION
CLI_USERNAME_HELP = cfg.CLI_USERNAME_HELP
CLI_PASSWORD_HELP = cfg.CLI_PASSWORD_HELP
CLI_SUBREDDIT_HELP = cfg.CLI_SUBREDDIT_HELP
CLI_CHOICE_HELP = cfg.CLI_CHOICE_HELP
CLI_PAGES_HELP = cfg.CLI_PAGES_HELP
# miscellaneous
VIEWS = cfg.VIEWS
UNSUPPORTED_FORMAT = cfg.UNSUPPORTED_FORMAT
CONVERT_THOUSAND = 1000

logging.basicConfig(filename=cfg.LOG_FILE_NAME,
                    format='%(asctime)s-%(levelname)s-FILE:%(filename)s-FUNC:%(funcName)s-LINE:%(lineno)d-%(message)s',
                    level=cfg.LOGGING_LEVEL)


# ----- DB population functions -----
def insert_user(data, connection):
    """
    Inserts the user's data into SQL and returns the unique user_id for SQL

    Parameters
    ----------
    data : user data
    connection : connection to SQL database

    Returns
    -------
    user_id
    """
    user_name = list(data.keys())[-1]
    logging.info(f"inserting user '{user_name}'")

    with connection.cursor() as cursor:
        place_holder = ', '.join(["" + '%s' + ""] * len(USER_FIELDS.split(',')))
        sql = f"""INSERT INTO reddit_data.user ({USER_FIELDS}) VALUES ({place_holder})
        on duplicate key update post_karma = values(post_karma), comment_karma = values(comment_karma);"""
        vals = (user_name, data[user_name]['post karma'], data[user_name]['comment karma'], data[user_name]['age'])

        cursor.execute(sql, vals)
        connection.commit()

        user_id = cursor.lastrowid
        # in case the user already exists (user_id == 0), retrieve existing user_id from the DB
        if user_id == 0:
            get_user_id_sql = f"select user_id from reddit_data.user where user_name = '{user_name}';"
            cursor.execute(get_user_id_sql)
            user_id = cursor.fetchone()[0]
            logging.debug(f"user {user_id} is in database")

        # insert the user's posts data into SQL
        insert_user_posts(data, user_id, connection)

        logging.info(f"inserting user '{user_name} - done'")
        logging.debug(f'inserted user id: {user_id}')
        return user_id


def insert_user_posts(data, user_id, connection):
    """
    inserts the user's posts into SQL

    Parameters
    ----------
    data : user post data
    user_id : user_id to link to user in SQL
    connection : connection to SQL database
    """
    user_name = list(data.keys())[-1]

    with connection.cursor() as cursor:
        logging.info(f"inserting user '{user_name}' new posts")
        place_holder = ', '.join(["" + '%s' + ""] * len(POST_FIELDS.split(',')))
        sql = f"""INSERT INTO reddit_data.post ({POST_FIELDS}) VALUES ({place_holder}) 
        on duplicate key update likes = values(likes), comments = values(comments);"""
        # inserting users new posts
        for post in data[user_name]['new posts']:
            vals = (user_id, post['title'], int(post['likes']), int(post['comments']), post['post date'],
                    post['subreddit'], post['post_source'], post['post_option'],
                    post['positive_sentiment'], post['neutral_sentiment'], post['negative_sentiment'])

            cursor.execute(sql, vals)
        connection.commit()
        logging.info(f"inserting user '{user_name}' new posts - done")

        logging.info(f"inserting user '{user_name}' top posts")
        for post in data[user_name]['top posts']:
            vals = (user_id, post['title'], int(post['likes']), int(post['comments']),
                    post['post date'], post['subreddit'], post['post_source'], post['post_option'],
                    post['positive_sentiment'], post['neutral_sentiment'], post['negative_sentiment'])

            cursor.execute(sql, vals)
        connection.commit()
        logging.info(f"inserting user '{user_name}' top posts - done")


def insert_subreddit_post(data, connection):
    """
    inserts a post and its comments into SQL

    Parameters
    ----------
    data : the post data along with its comments
    connection : connection to SQL database
    """
    logging.info('inserting subreddit post')

    with connection.cursor() as cursor:
        place_holder = ', '.join(["" + '%s' + ""] * len(POST_FIELDS.split(',')))
        sql = f"""INSERT INTO reddit_data.post ({POST_FIELDS}) VALUES ({place_holder}) 
        on duplicate key update likes = values(likes), comments = values(comments);"""

        vals = (int(data['user_id']), data['title'], int(data['likes']), int(data['comments']), data['post date'],
                data['subreddit'], data['post_source'], data['post_option'],
                data['positive_sentiment'], data['neutral_sentiment'], data['negative_sentiment'])
        cursor.execute(sql, vals)
        connection.commit()
        logging.info('inserting subreddit post - done')

        # retrieve post id for updating corresponding comments
        sql = f"""select post_id from post
        where user_id={int(data['user_id'])} and date_posted='{data['post date']}' and sub_reddit='{data['subreddit']}'
        and post_source = '{data['post_source']}' and post_option = '{data['post_option']}';"""
        cursor.execute(sql)
        post_id = cursor.fetchone()[0]
        # insert comments if there are any
        comment_data = data['post comments']
        if comment_data:
            insert_comment(comment_data, post_id, connection)

        print(f'inserted post {post_id}')


def insert_comment(data, post_id, connection):
    """
    inserts posts comments into SQL

    Parameters
    ----------
    data : dictionary of comments data
    post_id : post id
    connection : connection to SQL database
    """
    logging.info('inserting comments data')

    with connection.cursor() as cursor:
        comment_place_holder = ', '.join(["" + '%s' + ""] * len(COMMENT_FIELDS.split(',')))
        comment_sql = f"""INSERT INTO reddit_data.comment ({COMMENT_FIELDS}) VALUES ({comment_place_holder}) 
                    on duplicate key update sub_comments = values(sub_comments);"""

        for comment in data:
            comment_vals = (post_id, comment['author'], comment['text'], comment['points'],
                            comment['comment time'], int(comment['sub comments']),
                            comment['parent_comment_id'], comment['child_comment_id'],
                            comment['comment_post_id'])

            cursor.execute(comment_sql, comment_vals)
        connection.commit()
        # linking child comments and parent comments
        cursor.execute(UPDATE_COMMENT_QUERY)
        connection.commit()
        logging.debug('updated comments tree indices')

        logging.info('inserting comments data - done')


# ----- page redirection functions -----
def get_next_page(current_page):
    """
    returns the soup object of the next page

    Parameters
    ----------
    current_page : the current page from which to move

    Returns
    -------
    soup object of the next page to scrape
    """
    time.sleep(0.5)

    next_button = current_page.find("span", class_="next-button")
    if next_button:
        next_page_link = next_button.find("a").attrs['href']
        next_page = requests.get(next_page_link, headers=HEADERS)

        return BeautifulSoup(next_page.text, 'html.parser')


def give_consent(url):
    """
    return users main page (in case of NSFW content)

    Parameters
    ----------
    url : users main page 'over 18' redirection url

    Returns
    -------
    users main page soup object
    """
    driver = webdriver.Chrome(cfg.WEBDRIVER_PATH)
    driver.get(url)
    time.sleep(2)

    driver.find_element_by_xpath("//div[@class='buttons']//button[@value='yes']").click()
    html = driver.page_source

    return BeautifulSoup(html)


# ----- data retrieval functions -----
def get_post_data(post_input, view, user_id=None):
    """
    Returns the following data from an individual post soup object:
        title, number of comments, number of likes, the date of the post

    Parameters
    ----------
    post_input : post soup object
    view : page view of scraped post
    user_id : id of post author

    Returns
    -------
    dictionary of post data
    """
    title = post_input.find('p', class_="title").find('a').text
    comments = post_input.find('a', class_='comments').text.split()[0]
    likes = post_input.find("div", class_="score likes").text
    post_date = post_input.find('time').attrs['datetime']
    # fix features
    comments = 0 if comments == "comment" else comments
    if likes[-1] == 'k':
        likes = int(float(likes[:-1]) * CONVERT_THOUSAND)
    elif likes == "•":
        likes = 0
    # different features for subreddit and user posts
    if user_id:  # subreddit post
        subreddit = f'r/{arg_subreddit}'
        post_source = 'subreddit'
        post_comments = get_comments_data(post_input) if int(comments) > 0 else None
    else:  # user post
        subreddit = post_input.find(class_='subreddit hover may-blank').text if post_input.find(
            class_='subreddit hover may-blank') else 'missing'
        post_source = 'user'
        post_comments = None
    # get post sentiment from API
    positive_sentiment, neutral_sentiment, negative_sentiment = get_sentiment(title, API_KEY)

    return {'user_id': user_id, 'subreddit': subreddit, 'post_option': view, 'post_source': post_source,
            'title': title, 'comments': comments, 'post comments': post_comments, 'likes': likes,
            'post date': post_date, 'positive_sentiment': positive_sentiment, 'neutral_sentiment': neutral_sentiment,
            'negative_sentiment': negative_sentiment}


def get_user_data(url):
    """
    returns user data dictionary from url in the following format:
        new comments list, top comments list, new posts list, top posts list

    Parameters
    ----------
    url : url of the user main page

    Returns
    -------
    dictionary of the user data
    """
    user_data = {}

    logging.info('getting user data')
    page = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(page.content, 'html.parser')
    # get pass 'over 18' redirection
    if soup.find(class_='pagename selected').text == 'over 18?':
        logging.debug('encountered over 18 redirection')
        soup = give_consent(url)
    # users meta features
    post_karma = soup.find(class_='karma').text
    comment_karma = soup.find(class_='karma comment-karma').text
    age = soup.find(class_='age').contents[1].attrs['datetime']

    user_data['post karma'] = int(post_karma.replace(',', ''))
    user_data['comment karma'] = int(comment_karma.replace(',', ''))
    user_data['age'] = age
    # users posts
    for view in VIEWS:
        posts_url = f'{url}/submitted/?sort={view}'
        user_data[f'{view} posts'] = get_user_posts_data(posts_url, view)

    logging.info('getting user data - done')
    return user_data


def get_user_posts_data(url, view):
    """
    return list of user posts from specified view

    Parameters
    ----------
    url : posts url
    view : posts view (new, top)

    Returns
    -------
    list of posts
    """
    posts_data = []
    logging.info(f'getting user {view} posts')

    page = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(page.content, 'html.parser')
    # get pass 'over 18' redirection
    if soup.find(class_='pagename selected').text == 'over 18?':
        soup = give_consent(url)

    for post in soup.select('div[class*="thing"]'):
        post_data = get_post_data(post, view=view)
        posts_data.append(post_data)

    logging.info(f'getting user {view} posts - done')
    return posts_data


def get_comments_data(post_input):
    """
    returns a list of comment dictionaries with the following information for each comment:
        author of the comment, date of the comment, number of sub-comments

    Parameters
    ----------
    post_input : soup object of post

    Returns
    -------
    list of comments
    """
    comments = list()
    logging.info('getting comment data')

    comments_url = post_input.find('a', class_="bylink comments may-blank").attrs['href']
    page = requests.get(comments_url, headers=HEADERS)
    soup = BeautifulSoup(page.text, 'html.parser')

    reddit_post_id = soup.find('div', class_="sitetable linklisting").findChildren('div')[0].attrs['id']
    comment_post_id = re.split('[-_]', reddit_post_id)[-1]

    comments_area = soup.find('div', class_='commentarea').find('div', class_='sitetable nestedlisting')
    for comment in comments_area.select('div[class*="thing"]'):
        # skip comment elements that are expansion button or deleted
        expand = comment.attrs['class'][-1] in ['morechildren', 'morerecursion']
        deleted = 'deleted' in comment.attrs['class']
        if expand or deleted:
            continue

        author = comment.select('a[class*="author"]')[0].text if comment.select('a[class*="author"]') else 'deleted'
        text = comment.find(class_='md').find('p').text if comment.find(class_='md').find('p') else UNSUPPORTED_FORMAT
        points = comment.find('span', class_='score unvoted').text.split()[0] \
            if comment.find('span', class_='score unvoted') else '0'
        comment_time = comment.find('time').attrs['datetime']
        sub_comments = comment.find('a', class_="numchildren").text.split()[0].replace('(', '')
        parent_id = re.split('[-_]', comment.parent.attrs['id'])[-1]
        child_id = re.split('[-_]', comment.attrs['id'])[-1]
        # fix features
        points = int(float(points[:-1]) * CONVERT_THOUSAND) if points[-1] == 'k' else points

        comments.append({'author': author, 'text': text, 'points': points, 'comment time': comment_time,
                         'sub comments': sub_comments, 'parent_comment_id': parent_id, 'child_comment_id': child_id,
                         'comment_post_id': comment_post_id})

    logging.info('getting comment data - done')
    return comments


def get_sentiment(text, key):
    """
    Gets the positive and negative sentiment of a post from reddit

    Parameters
    ----------
    text : text to analyse and get the sentiment
    key : HuggingFace API key

    Returns
    -------
    tuple of the positive, neutral and negative sentiment for the text
    """
    logging.debug('getting sentiment analysis')
    headers = {"Authorization": f"Bearer {key}"}
    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": text}, timeout=2)
        output = response.json()[0]
    except requests.exceptions.Timeout:
        # no sentiment is available
        logging.warning('API call timeout')
        return -1, -1, -1

    logging.debug('getting sentiment analysis done')
    return output[0]['score'], output[1]['score'], output[2]['score']


# ----- scraping functions -----
def scrape_page(soup, connection):
    """
    scrapes and stores contents of subreddit page

    Parameters
    ----------
    soup : soup object of page on subreddit
    connection : SQL connection
    """
    users = {}
    logging.info('started scraping a new page')

    for post in soup.select('div[class*="thing"]'):
        # check that the post is not promotional or an announcement, we only want real posts
        not_promotion = post.find('span', class_="promoted-span") is None
        not_announcement = post.find('span', class_="stickied-tagline") is None
        if not_promotion and not_announcement:
            # check if we have scraped this user in this session, if not then get their data
            username = post.select('a[class*="author"]')[0].text
            if username not in users.keys():  # if user was not scraped recently
                logging.debug(f"user '{username}' is not in cache")
                users[username] = get_user_data(post.select('a[class*="author"]')[0].attrs['href'])
                user_id = insert_user(users, connection)

            else:  # if user is scraped already, get user_id from DB
                logging.debug(f"user '{username}' is in cache")
                with connection.cursor() as cursor:
                    sql = f"""select user_id from user where user_name = '{username}';"""
                    cursor.execute(sql)
                    user_id = cursor.fetchone()[0]

            logging.info('getting subreddit post data')
            post_data = get_post_data(post, view=arg_choice, user_id=user_id)
            logging.info('getting subreddit post data - done')
            insert_subreddit_post(post_data, connection)
    logging.info('finished scraping page')


def scrape_subreddit(connection):
    """
    scrapes and stores contents of subreddit

    Parameters
    ----------
    connection : connection to SQL database
    """
    choice_url = arg_choice if arg_timeframe is None else f'{arg_choice}/?t={arg_timeframe}'
    main_page_url = f'{BASE_URL}r/{arg_subreddit}/{choice_url}'
    logging.info(f'started scraping {main_page_url}')

    page = requests.get(main_page_url, headers=HEADERS)
    soup = BeautifulSoup(page.content, 'html.parser')

    for i in range(arg_pages):
        if soup:
            scrape_page(soup, connection)

        # get the next page, return None if there are no more pages
        soup = get_next_page(soup)

    logging.info('scraping done!')


# ----- CLI functions -----
def cli_parser():
    """
    Gets the CLI arguments for the scraper

    Returns
    -------
    arguments set by the user
    """

    parser = argparse.ArgumentParser(prog='SCRAPER', formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=CLI_DESCRIPTION)

    parser.add_argument('username', type=str, help=CLI_USERNAME_HELP, default='root')
    parser.add_argument('password', type=str, help=CLI_PASSWORD_HELP, default='root')
    parser.add_argument('subreddit', type=str, help=CLI_SUBREDDIT_HELP)
    parser.add_argument('choice', type=str, help=CLI_CHOICE_HELP, default='top-week')
    parser.add_argument('pages', type=int, help=CLI_PAGES_HELP, default=5)

    return parser.parse_args()


def validate_args(args):
    """
    validates CLI arguments, if invalid stop the program
    Parameters
    ----------
    args : CLI arguments
    """
    # check number of arguments inserted is valid (.py file is argument too)
    if len(sys.argv) < 6:
        print(f'{6 - len(sys.argv)} missing arguments. expected 5 arguments')
        sys.exit()
    elif len(sys.argv) > 6:
        print(f'{len(sys.argv) - 6} extra arguments. expected 5 arguments')
        sys.exit()
    # check if subreddit exists
    subreddit_url = f'{BASE_URL}r/{args.subreddit}'
    if not requests.get(subreddit_url, headers=HEADERS):
        print(f'subreddit {args.subreddit} doesn\'t exist, please type a valid one')
        sys.exit()
    # check if choice argument is valid
    choice_list = args.choice.split('-')
    if choice_list[0] not in ['new', 'top']:
        print(f'{choice_list[0]} is invalid. please enter valid subreddit choice: [new, top]')
        sys.exit()
    if choice_list[0] == 'new' and len(choice_list) > 1:
        print('do not enter any specification if you want to scrape new posts\nformat is: new')
        sys.exit()
    if choice_list[0] == 'top' and len(choice_list) == 1:
        print('please enter specification for scraping top: [day, week, month, year, all]\nFormat is: top-[specification]')
        sys.exit()
    if choice_list[0] == 'top' and choice_list[1] not in ['day', 'week', 'month', 'year', 'all']:
        print(f'{choice_list[1]} is not valid. please enter valid specification for scraping top: [day, week, month, year, all]\nFormat is: top-[specification]')
        sys.exit()
    # check if number of pages is valid
    if args.pages < 1:
        print(f'{args.pages} is invalid. please enter a positive integer number of pages to scrape')
        sys.exit()
    logging.info('CLI args validated')


if __name__ == '__main__':
    CLI_args = cli_parser()
    validate_args(CLI_args)

    arg_user_name = CLI_args.username
    arg_password = CLI_args.password
    arg_pages = CLI_args.pages
    arg_subreddit = CLI_args.subreddit
    arg_choice = CLI_args.choice.split('-')[0]
    arg_timeframe = None if len(CLI_args.choice.split('-')) == 1 else CLI_args.choice.split('-')[1]

    sql_connection = pymysql.connect(host='localhost',
                                     user=arg_user_name,
                                     password=arg_password,
                                     database='reddit_data')
    logging.info('connection to SQL server - success')

    scrape_subreddit(sql_connection)

    sql_connection.close()
