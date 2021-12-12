import textwrap
import time
import re
import pymysql.cursors
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
import sys
import argparse



BASE_URL = "https://old.reddit.com/"
HEADERS = {'User-Agent': 'Mozilla/5.0'}

COMMENT_ID_SPLIT = -1


def user_insert_to_sql(data, connection):
    """
    Inserts the user's data into SQL and returns the unique user_id for SQL
    :param data: user data
    :param connection: SQL connection
    :return: user_id
    """
    with connection.cursor() as cursor:
        fields = 'user_name, post_karma, comment_karma, date_joined'

        place_holder = ', '.join(["" + '%s' + ""] * len(fields.split(',')))

        sql = f"""INSERT INTO reddit_data.user ({fields}) VALUES ({place_holder})
        on duplicate key update post_karma = values(post_karma), comment_karma = values(comment_karma);"""

        user_name = list(data.keys())[-1]

        vals = (user_name,
                data[user_name]['post karma'],
                data[user_name]['comment karma'],
                data[user_name]['age'])

        cursor.execute(sql, vals)

        connection.commit()
        user_id = cursor.lastrowid

        if user_id == 0:
            get_user_id_sql = f"select user_id from reddit_data.user where user_name = '{user_name}';"
            cursor.execute(get_user_id_sql)
            user_id = cursor.fetchone()[0]

        print(f'created user {user_id}')

        return user_id


def insert_user_post_to_sql(data, user_id, connection):
    """
    inserts the user's posts into SQL

    :param data: user post data
    :param user_id: user_id to link to user in SQL
    :param connection: sql connection
    """
    print('starting insert process')
    with connection.cursor() as cursor:

        fields = 'user_id, title, likes, comments, date_posted, sub_reddit, post_source, post_option'
        place_holder = ', '.join(["" + '%s' + ""] * len(fields.split(',')))

        sql = f"""INSERT INTO reddit_data.post ({fields}) VALUES ({place_holder}) 
        on duplicate key update likes = values(likes), comments = values(comments);"""

        user_name = list(data.keys())[-1]

        for post in data[user_name]['new posts']:
            vals = (user_id, post['title'],
                    int(post['likes']), int(post['comments']),
                    post['post date'], post['subreddit'], post['post_source'], post['post_option'])

            cursor.execute(sql, vals)
        connection.commit()

        for post in data[user_name]['top posts']:
            vals = (user_id, post['title'],
                    int(post['likes']), int(post['comments']),
                    post['post date'], post['subreddit'], post['post_source'], post['post_option'])

            cursor.execute(sql, vals)
        connection.commit()


def insert_to_sql(data, connection):
    """
    returns the soup object of the next page

    Parameters
    ----------
    current_page : the current page from which to move

    Returns
    -------
    soup object of the next page to scrape
    """
    print('starting insert process')
    with connection.cursor() as cursor:
        fields = 'user_id, title, likes, comments, date_posted, sub_reddit, post_source, post_option'
        place_holder = ', '.join(["" + '%s' + ""] * len(fields.split(',')))

        sql = f"""INSERT INTO reddit_data.post ({fields}) VALUES ({place_holder}) 
        on duplicate key update likes = values(likes), comments = values(comments),post_id=LAST_INSERT_ID(post_id);"""

        vals = (int(data['user_id']), data['title'],
                int(data['likes']), int(data['comments']),
                data['post date'], data['subreddit'], data['post_source'], data['post_option'])

        cursor.execute(sql, vals)
        connection.commit()

        post_id = cursor.lastrowid
        print(f'inserted post {post_id}')

        comment_fields = 'post_id, author, text, points, comment_date, sub_comments, reddit_parent_id, reddit_comment_id, reddit_post_id'
        comment_place_holder = ', '.join(["" + '%s' + ""] * len(comment_fields.split(',')))

        comment_sql = f"""INSERT INTO reddit_data.comment ({comment_fields}) VALUES ({comment_place_holder}) 
        on duplicate key update sub_comments = values(sub_comments);"""

        if data['post comments']:
            comment_data = data['post comments']

            for comment in comment_data:
                comment = comment_data[comment]
                comment_vals = (post_id, comment['author'], comment['text'], comment['points'],
                                comment['comment time'], int(comment['sub comments']),
                                comment['parent_comment_id'], comment['child_comment_id'],
                                comment['comment_post_id'])

                cursor.execute(comment_sql, comment_vals)
            connection.commit()

            update_sql = """update reddit_data.comment a 
                    join reddit_data.comment b on a.reddit_parent_id = b.reddit_comment_id
                    set a.parent_comment_id = b.comments_id
                    where a.comments_id > 0;"""

            cursor.execute(update_sql)
            connection.commit()

        print(f'inserted comments for post {post_id}')


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


def get_post_data(post_input):
    """
    Returns the following data from an individual post soup object:
    title, number of comments, number of likes, the date of the post

    Parameters
    ----------
    post_input : the post soup object to get the data from

    Returns
    -------
    dictionary of the scraped data
    """
    if post_input.find('p', class_="title"):
        title = post_input.find('p', class_="title").find('a').text
        comments = post_input.find('a', class_='comments').text.split()[0]
        comments = 0 if comments == "comment" else comments
        likes = post_input.find("div", class_="score likes").text
        if likes[-1] == 'k':
            likes = int(float(likes[:-1]) * 1000)
        likes = 0 if likes == "•" else likes

        post_date = post_input.find('time').attrs['datetime']

        return {'title': title, 'comments': comments, 'likes': likes, 'post date': post_date}


def get_user_data(user_url):
    """
    returns user data dictionary from user_url in the following format:
    new comments list, top comments list, new posts list, top posts list

    Parameters
    ----------
    user_url : url of the user

    Returns
    -------
    dictionary of the user data
    """
    user_data = {}

    page = requests.get(user_url, headers=HEADERS)
    soup = BeautifulSoup(page.content, 'html.parser')

    if soup.find(class_='pagename selected').text == 'over 18?':
        driver = webdriver.Chrome('C:/Users/haimk/chromedriver.exe')
        driver.get(user_url)
        time.sleep(2)
        driver.find_element_by_xpath("//div[@class='buttons']//button[@value='yes']").click()
        html = driver.page_source
        soup = BeautifulSoup(html)

    post_karma = soup.find(class_='karma').text
    comment_karma = soup.find(class_='karma comment-karma').text
    age = soup.find(class_='age').contents[1].attrs['datetime']

    user_data['post karma'] = int(post_karma.replace(',', ''))
    user_data['comment karma'] = int(comment_karma.replace(',', ''))
    user_data['age'] = age

    for sort in ['new', 'top']:
        post_data = []

        page = requests.get(f'{user_url}/submitted/?sort={sort}', headers=HEADERS)
        soup = BeautifulSoup(page.content, 'html.parser')

        if soup.find(class_='pagename selected').text == 'over 18?':
            driver = webdriver.Chrome('C:/Users/haimk/chromedriver.exe')
            driver.get(user_url)
            driver.find_element_by_xpath("//div[@class='buttons']//button[@value='yes']").click()
            html = driver.page_source
            soup = BeautifulSoup(html)

        for post in soup.select('div[class*="thing"]'):
            subreddit = post.find(class_='subreddit hover may-blank').text if post.find(
                class_='subreddit hover may-blank') else 'missing'
            last_post_data = get_post_data(post)
            # check if a post existed
            if last_post_data:
                last_post_data['post_source'] = 'user'
                last_post_data['post_option'] = sort
                last_post_data['subreddit'] = subreddit
                post_data.append(last_post_data)

        # user_data[f'{sort} comments'] = comment_data
        user_data[f'{sort} posts'] = post_data

    return user_data


def get_comments(post_input):
    """
    returns a dictionary of the following information for each comment made on the post_input soup:
    author of the comment, date of the comment, number of sub-comments

    Parameters
    ----------
    post_input : soup object of post

    Returns
    -------
    dictionary containing comment information
    """
    comments_page_link = post_input.find('a', class_="bylink comments may-blank").attrs['href']
    comments_page_req = requests.get(comments_page_link, headers=HEADERS)
    comments_page = BeautifulSoup(comments_page_req.text, 'html.parser')
    comments_area = comments_page.find('div', class_='commentarea').find('div', class_='sitetable nestedlisting')
    comment_post_id = \
        re.split('[-_]', comments_page.find('div', class_="sitetable linklisting").findChildren('div')[0].attrs['id'])[-1]
    comments = {}

    for index, comment in enumerate(comments_area.select('div[class*="thing"]')):

        if comment.attrs['class'][-1] in ['morechildren', 'morerecursion']:
            continue
        if 'deleted' in comment.attrs['class']:
            continue

        parent_id = re.split('[-_]', comment.parent.attrs['id'])[COMMENT_ID_SPLIT]
        child_id = re.split('[-_]', comment.attrs['id'])[COMMENT_ID_SPLIT]

        author = comment.select('a[class*="author"]')[0].text if comment.select('a[class*="author"]') else 'deleted'
        # get the points of the comment

        points = comment.find('span', class_='score unvoted').text.split()[0] if comment.find('span', class_='score unvoted') else 0
        if points and points[-1] == 'k':
            points = int(float(points[:-1]) * 1000)

        comment_time = comment.find('time').attrs['datetime']
        sub_comments = comment.find('a', class_="numchildren").text.split()[0].replace('(', '')
        if comment.find(class_='md').find('p'):
            text = comment.find(class_='md').find('p').text
        else:
            text = 'format not supported'

        comment_ind = {'author': author,
                       'text': text,
                       'points': points,
                       'comment time': comment_time,
                       'sub comments': sub_comments,
                       'parent_comment_id': parent_id,
                       'child_comment_id': child_id,
                       'comment_post_id': comment_post_id}

        comments[index] = comment_ind

    return comments


def cli_parser():
    """
    Gets the CLI arguments for the scraper
    :return:
    arguments
    """
    parser = argparse.ArgumentParser(
        prog='SCRAPER',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent('''
                        --------------------------------
                                REDDIT WEB-SCRAPER
                        --------------------------------
                         Use this to scrape posts, comments & user data 
                         from any subreddit on reddit.
                         The data will be saved in a MySQL database 
                         '''))

    parser.add_argument('username', type=str,
                        help='Your username for your MySQL database where the scraped data will be stored',
                        default='root')
    parser.add_argument('password', type=str,
                        help='Your password for your MySQL database where the scraped data will be stored', default='')
    parser.add_argument('subreddit', type=str, help='The name of the subreddit that you want to scrape')
    parser.add_argument('choice', type=str, help='The settings of posts selected on the subreddit page: [new, top]\nIn case of top please add "-" followed by specification of range [day, week, month, year, all]')
    parser.add_argument('pages', type=int, help='The number of pages to scrape, there are 25 posts on each page')

    args = parser.parse_args()
    return args


def main(connection):

    users = {}

    # for index, channel in enumerate(CHANNELS):
    posts_data = []

    # get the URL for the subreddit that will be scraped and create a soup object
    # choice_list = CHOICE.split('-')
    # choice_url = choice_list[0] if len(choice_list) == 1 else f'{choice_list[0]}/?t={choice_list[1]}'
    # full_url = f'{BASE_URL}r/{SUBREDDIT}/{choice_url}'
    choice_url = CHOICE if TIMEFRAME is None else f'{CHOICE}/?t={TIMEFRAME}'
    full_url = f'{BASE_URL}r/{SUBREDDIT}/{choice_url}'
    print(f'scraping {full_url}')
    page = requests.get(full_url, headers=HEADERS)
    soup = BeautifulSoup(page.content, 'html.parser')

    counter = 0
    while counter < PAGES:
        # search for each "thing" which is a post/comment in the HTML
        for post in soup.select('div[class*="thing"]'):
            # check that the post is not promotional or an announcement, we only want real posts
            not_promotion = post.find('span', class_="promoted-span") is None
            not_announcement = post.find('span', class_="stickied-tagline") is None
            if not_promotion and not_announcement:
                # get the username of the poster
                username = post.select('a[class*="author"]')[0].text
                # check if we have scraped this user in this session, if not then get their data
                if username not in users.keys():
                    # get the data for the user
                    users[username] = get_user_data(post.select('a[class*="author"]')[0].attrs['href'])
                    # insert the user data into SQL
                    user_id = user_insert_to_sql(users, connection)
                    # insert the user's posts data into SQL
                    insert_user_post_to_sql(users, user_id, connection)

                else:
                    # if got the user already, get their user_id from the SQL db
                    with connection.cursor() as cursor:
                        # Read a single record
                        sql = f"""select user_id from user where user_name = '{username}';"""
                        cursor.execute(sql)
                        user_id = cursor.fetchone()[0]


                # Get the post data
                post_data = get_post_data(post)
                post_data['subreddit'] = SUBREDDIT
                post_data['user_id'] = user_id
                post_data['post_option'] = CHOICE
                post_data['post_source'] = 'subreddit'
                # get all the comments of the post
                post_comments = get_comments(post) if int(post_data['comments']) > 0 else None
                post_data['post comments'] = post_comments

                posts_data.append(post_data)
                # insert the post and its comments into the SQL db
                insert_to_sql(post_data, connection)

        # get the next page
        soup = get_next_page(soup)
        counter += 1

    print('Done scraping!')



if __name__ == '__main__':

    args = cli_parser()
    # check number of arguments inserted is valid (.py file is argument too)
    if len(sys.argv) < 6:
        print(f'{6 - len(sys.argv)} missing arguments. expected 5 arguments')
        sys.exit()
    elif len(sys.argv) > 6:
        print(f'{len(sys.argv) - 6} extra arguments. expected 5 arguments')
        sys.exit()
    # check if subreddit exists
    full_url = f'{BASE_URL}r/{args.subreddit}'
    if not requests.get(full_url, headers=HEADERS):
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

    USER_NAME = args.username
    PASSWORD = args.password
    PAGES = args.pages
    SUBREDDIT = args.subreddit
    CHOICE = args.choice.split('-')[0]
    TIMEFRAME = None if len(args.choice.split('-')) == 1 else args.choice.split('-')[1]

    connection = pymysql.connect(host='localhost',
                                 user=USER_NAME,
                                 password=PASSWORD,
                                 database='reddit_data')

    print('connection to SQL server - success')
    main(connection)

    connection.close()
