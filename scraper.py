import time
import config as CFG
import re
import pymysql.cursors
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
# from webdrivermanager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By


"""
settings:
---------
channel - coin
time period
number of pages
min number of up-votes to scrape - solved by top
hot/new/top
"""

BASE_URL = "https://old.reddit.com/"
HEADERS = {'User-Agent': 'Mozilla/5.0'}

CHANNEL_OPTION = ['top', 'new']
# Configurations
CHANNELS = CFG.CHANNELS
CHANNEL_CHOICE = CFG.CHANNEL_CHOICE
PAGES = CFG.PAGES
# CHROME_PATH = CFG.CHROME_PATH

COMMENT_ID_SPLIT = -1


USER_NAME = 'root'
PASSWORD = PASSWORD



def user_insert_to_sql(data,index, connection):

    with connection.cursor() as cursor:

        fields = 'user_name, post_karma, comment_karma, date_joined'

        place_holder = ', '.join(["" + '%s' + ""] * len(fields.split(',')))

        sql = f"""INSERT INTO reddit_data.user ({fields}) VALUES ({place_holder})
        on duplicate key update post_karma = values(post_karma) and comment_karma = values(comment_karma);"""

        user_name = list(data.keys())[index]

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

    print('starting insert process')
    with connection.cursor() as cursor:

        fields = 'user_id, title, likes, comments, date_posted, sub_reddit, post_source, post_option'
        place_holder = ', '.join(["" + '%s' + ""] * len(fields.split(',')))

        sql = f"""INSERT INTO reddit_data.post ({fields}) VALUES ({place_holder}) 
        on duplicate key update likes = values(likes) and comments = values(comments);"""

        user_name = list(data.keys())[0]

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

        comment_fields = 'post_id, author, text, comment_date, sub_comments, reddit_parent_id, reddit_comment_id, reddit_post_id'
        comment_place_holder = ', '.join(["" + '%s' + ""] * len(comment_fields.split(',')))

        comment_sql = f"""INSERT INTO reddit_data.comment ({comment_fields}) VALUES ({comment_place_holder}) 
        on duplicate key update sub_comments = values(sub_comments);"""

        comment_data = data['post comments']

        for comment in comment_data:
            comment = comment_data[comment]
            comment_vals = (post_id, comment['author'], comment['text'],
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

    title = post_input.find('p', class_="title").find('a').text
    comments = post_input.find('a', class_='comments').text.split()[0]
    comments = 0 if comments == "comment" else comments
    likes = post_input.find("div", class_="score likes").text
    likes = "None" if likes == "•" else likes
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
        driver = webdriver.Chrome()
        driver.get(user_url)
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
        # comment_data = []
        post_data = []

        # page = requests.get(f'{user_url}/comments/?sort={sort}', headers=HEADERS)
        # soup = BeautifulSoup(page.content, 'html.parser')

        # for comment in soup.select('div[class*="thing"]'):
        #     title = comment.find(class_='title').text
        #     author = comment.select('a[class*="author"]')[0].text
        #     thread = comment.find(class_='subreddit hover').text
        #     date = comment.find(class_='live-timestamp').attrs['datetime'].split('T')[0]
        #     if comment.find(class_='md').find('p'):
        #         text = comment.find(class_='md').find('p').text
        #     else:
        #         text = comment.find(class_='md').select('li')[0].text
        #     comment_data.append({'title': title, 'author': author, 'thread': thread, 'date': date, 'text': text})

        page = requests.get(f'{user_url}/submitted/?sort={sort}', headers=HEADERS)
        soup = BeautifulSoup(page.content, 'html.parser')

        if soup.find(class_='pagename selected').text == 'over 18?':
            driver = webdriver.Chrome()
            driver.get(user_url)
            driver.find_element_by_xpath("//div[@class='buttons']//button[@value='yes']").click()
            html = driver.page_source
            soup = BeautifulSoup(html)

        for post in soup.select('div[class*="thing"]'):
            subreddit = post.find(class_='subreddit hover may-blank').text
            last_post_data = get_post_data(post)
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
        re.split('[-_]', comments_page.find('div', class_="sitetable linklisting").findChildren('div')[0].attrs['id'])[
            -1]
    comments = {}

    for index, comment in enumerate(comments_area.select('div[class*="thing"]')):

        if comment.attrs['class'][-1] in ['morechildren', 'morerecursion']:
            continue
        if 'deleted' in comment.attrs['class']:
            continue

        parent_id = re.split('[-_]', comment.parent.attrs['id'])[COMMENT_ID_SPLIT]
        child_id = re.split('[-_]', comment.attrs['id'])[COMMENT_ID_SPLIT]

        author = comment.select('a[class*="author"]')[0].text if comment.select('a[class*="author"]') else 'deleted'

        comment_time = comment.find('time').attrs['datetime']
        sub_comments = comment.find('a', class_="numchildren").text.split()[0].replace('(', '')
        if comment.find(class_='md').find('p'):
            text = comment.find(class_='md').find('p').text
        else:
            text = comment.find(class_='md').select('li')[0].text

        comment_ind = {'author': author,
                       'text': text,
                       'comment time': comment_time,
                       'sub comments': sub_comments,
                       'parent_comment_id': parent_id,
                       'child_comment_id': child_id,
                       'comment_post_id': comment_post_id}

        comments[index] = comment_ind

    return comments


def main(connection):

    channel_data = {}
    users = {}

    for index, channel in enumerate(CHANNELS):
        posts_data = []

        full_url = f'{BASE_URL}r/{channel}/{CHANNEL_OPTION[CHANNEL_CHOICE]}'
        page = requests.get(full_url, headers=HEADERS)
        soup = BeautifulSoup(page.content, 'html.parser')

        counter = 0
        i = 0
        while counter < PAGES:
            for post in soup.select('div[class*="thing"]'):
                not_promotion = post.find('span', class_="promoted-span") is None
                not_announcement = post.find('span', class_="stickied-tagline") is None
                if not_promotion and not_announcement:

                    username = post.select('a[class*="author"]')[0].text
                    if username not in users.keys():
                        users[username] = get_user_data(post.select('a[class*="author"]')[0].attrs['href'])
                        user_id = user_insert_to_sql(users,i, connection)
                        insert_user_post_to_sql(users, user_id, connection)

                    else:

                        with connection.cursor() as cursor:
                            # Read a single record
                            sql = f"""select user_id from user where user_name = {username};"""
                            cursor.execute(sql)
                            user_id = cursor.fetchone()

                        print(user_id)

                    post_comments = get_comments(post)
                    post_data = get_post_data(post)
                    post_data['subreddit'] = channel
                    post_data['user_id'] = user_id
                    post_data['post comments'] = post_comments
                    post_data['post_option'] = CHANNEL_OPTION[CHANNEL_CHOICE]
                    post_data['post_source'] = 'subreddit'

                    posts_data.append(post_data)

                    insert_to_sql(post_data, connection)

                    i += 1
            soup = get_next_page(soup)
            counter += 1

        channel_data[f'{channel}'] = posts_data


if __name__ == '__main__':

    connection = pymysql.connect(host='localhost',
                                 user=USER_NAME,
                                 password=PASSWORD,
                                 database='reddit_data')

    main(connection)

    connection.close()