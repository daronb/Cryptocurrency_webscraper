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
    returns the soup of the next page
    Parameters
    ----------
    current_page : the current page from which to move

    Returns
    -------
    BeautifulSoup object of the next page to scrape
    """
    time.sleep(0.5)

    next_button = current_page.find("span", class_="next-button")

    if next_button:
        next_page_link = next_button.find("a").attrs['href']
        next_page = requests.get(next_page_link, headers=HEADERS)

        return BeautifulSoup(next_page.text, 'html.parser')


def get_data(post_input):
    """
    Returns the following data from an individual post:
    title, number of comments, number of likes, the date of the post
    Parameters
    ----------
    post_input : the post to get the data from

    Returns
    -------
    Tuple of the scraped data
    """

    title = post_input.find('p', class_="title").find('a').text
    comments = post_input.find('a', class_='comments').text.split()[0]
    comments = 0 if comments == "comment" else comments
    likes = post_input.find("div", class_="score likes").text
    likes = "None" if likes == "•" else likes
    post_date = post_input.find('time').attrs['datetime'].split('T')[0]

    return title, comments, likes, post_date


def main():
    data = list()

    for index, channel in enumerate(CHANNELS):
        data.append([])

        full_url = f'{BASE_URL}r/{channel}/{CHANNEL_OPTION[CHANNEL_CHOICE]}'
        page = requests.get(full_url, headers=HEADERS)
        soup = BeautifulSoup(page.content, 'html.parser')

        counter = 0
        while counter < PAGES:
            for post in soup.select('div[class*="thing"]'):
                not_promotion = post.find('span', class_="promoted-span") is None
                not_announcement = post.find('span', class_="stickied-tagline") is None
                if not_promotion and not_announcement:
                    data[index].append(get_data(post))

            soup = get_next_page(soup)
            counter += 1

    for index, currency_data in enumerate(data):
        print(CHANNELS[index].upper())
        for post_data in currency_data:
            print(post_data)


if __name__ == '__main__':
    main()
