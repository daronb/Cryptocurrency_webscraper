import time
import config as CFG

from bs4 import BeautifulSoup
import requests

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

CHANNEL_OPTION = ['hot', 'top', 'new']
# Configurations
CHANNELS = CFG.CHANNELS
CHANNEL_CHOICE = CFG.CHANNEL_CHOICE
PAGES = CFG.PAGES


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
    post_date = post_input.find('time').attrs['datetime'].split('T')[0]

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

    for sort in ['new', 'top']:
        comment_data = []
        post_data = []

        page = requests.get(f'{user_url}/comments/?sort={sort}', headers=HEADERS)
        soup = BeautifulSoup(page.content, 'html.parser')

        for comment in soup.select('div[class*="thing"]'):
            title = comment.find(class_='title').text
            author = comment.select('a[class*="author"]')[0].text
            thread = comment.find(class_='subreddit hover').text
            date = comment.find(class_='live-timestamp').attrs['datetime'].split('T')[0]
            text = comment.find(class_='md').find('p').text
            comment_data.append({'title': title, 'author': author, 'thread': thread, 'date': date, 'text': text})

        page = requests.get(f'{user_url}/submitted/?sort={sort}', headers=HEADERS)
        soup = BeautifulSoup(page.content, 'html.parser')

        for post in soup.select('div[class*="thing"]'):
            thread = post.find(class_='subreddit hover may-blank').text
            last_post_data = get_post_data(post)
            last_post_data['thread'] = thread
            post_data.append(last_post_data)

        user_data[f'{sort} comments'] = comment_data
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
    comments_page_link = post_input.find('p', class_="title").find('a').attrs['href']
    comments_page_req = requests.get(BASE_URL + comments_page_link[1:], headers=HEADERS)
    comments_page = BeautifulSoup(comments_page_req.text, 'html.parser')

    comments_area = comments_page.find('div', class_='commentarea').find('div', class_='sitetable nestedlisting')
    comments = {}
    for index, comment in enumerate(comments_area.select('div[class*="thing"]')):
        if comment.attrs['class'][-1] == 'morechildren':
            continue
        author = comment.select('a[class*="author"]')[0].text
        comment_time = comment.find('time').attrs['datetime']
        sub_comments = comment.find('a', class_="numchildren").text.split()[0].replace('(', '')
        comment_ind = {'author': author,
                       'comment time': comment_time,
                       'sub comments': sub_comments}
        comments[index] = comment_ind

    return comments


def main():
    channel_data = {}
    users = {}

    for index, channel in enumerate(CHANNELS):
        posts_data = []

        full_url = f'{BASE_URL}r/{channel}/{CHANNEL_OPTION[CHANNEL_CHOICE]}'
        page = requests.get(full_url, headers=HEADERS)
        soup = BeautifulSoup(page.content, 'html.parser')

        counter = 0
        while counter < PAGES:
            for post in soup.select('div[class*="thing"]'):
                not_promotion = post.find('span', class_="promoted-span") is None
                not_announcement = post.find('span', class_="stickied-tagline") is None
                if not_promotion and not_announcement:
                    post_comments = get_comments(post)
                    post_data = get_post_data(post)
                    post_data['post comments'] = post_comments
                    posts_data.append(post_data)

                    username = post.select('a[class*="author"]')[0].text
                    if username not in users.keys():
                        users[username] = get_user_data(post.select('a[class*="author"]')[0].attrs['href'])
                    break

            soup = get_next_page(soup)
            counter += 1

        channel_data[f'{channel}'] = posts_data


if __name__ == '__main__':
    main()
