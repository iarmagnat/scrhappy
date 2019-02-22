import re

import requests
from urllib.parse import urlparse

from requests import HTTPError

from scrhappy.page import Page, RobotsForbiddenPage


class Site(object):
    """
dans site: mot clef, urls interne, url externe, nom de domaine, document_matrix
"""

    def __init__(self, root, protocol="http", depth=300):
        self.protocol = protocol
        self._depth = depth
        self.root = root
        # This is pre-filled so that / and just the root url are not parsed as different urls
        self._urls = {f"{protocol}://{root}", f"{protocol}://{root}/"}
        self._parsed = {f"{protocol}://{root}"}
        self.pages = []
        self.disallow_rules = []
        robots = requests.get(f"{protocol}://{root}/robots.txt")
        if robots.ok:
            for line in robots.iter_lines():
                if line[:10] == b'Disallow: ':
                    # The robots.txt MAY not be encoded in UTF-8 'cause screw standards you know.
                    # If it's the case, well screw you I'm scrapping the whole site!
                    try:
                        # We prepare the rule to be used as regex later
                        self.disallow_rules.append(
                            line[10:].decode("utf-8", "strict").replace(" ", "").replace("*", ".*")
                        )
                    except UnicodeDecodeError:
                        pass

    # Now out of order (this was to streamline the code and focus and the text parsing)
    # def scrap(self):
    #     with mp.Pool(mp.cpu_count())as pool:
    #         while self._parsed != self.urls:
    #             diff = self.urls - self._parsed
    #             new_pages = pool.map(self._page_if_need(self), diff)
    #             self.update(new_pages)
    #
    #     return self.urls, self.get_links()

    def scrap_mono(self):
        while self._parsed != self._urls:
            for url in self._urls - self._parsed:
                self.page_if_need(url)
            # self.update(new)
        return self._urls, self.get_links()

    # Now useless (this was to streamline the code)
    # def update(self, new_pages):
    #     for page in new_pages:
    #         self.pages.append(page)
    #         self.urls.update(page.in_links)
    #         self._parsed.add(page.url)

    def url_add(self, url):
        # We check if the crawling depth has been reached
        # the "- 2" is there to account for the 2 pre-filled urls in the __init__
        if len(self._urls) - 2 < self._depth:

            # we check the robots.txt rules
            for rule in self.disallow_rules:
                if re.search(rule, urlparse(url).path):
                    print(f"not adding {url} because of robots.txt rule: {rule}")
                    return

            self._urls.add(url)

    @staticmethod
    def _page_if_need(instance):
        return instance.page_if_need

    def page_if_need(self, url):
        page = Page(url, self)
        try:
            page.parse()
        except RobotsForbiddenPage as e:
            print(str(e))
        except HTTPError as e:
            status_code = e.response.status_code
            if status_code == 401:
                # in case of a forbidden error on a url that is not included in the robots.txt,
                # we add an exception in our disallow ruleset
                parsed = urlparse(url)
                self.disallow_rules.append(f"{parsed.path}.*")
            else:
                print(e)
        self._parsed.add(url)
        return page

    def get_links(self, mode="all"):
        links = set()
        if mode in ['internal', 'all']:
            links.add(f"{self.protocol}://{self.root}")
        for page in self.pages:
            links.update(page.get_links(mode=mode))
        return links

    @property
    def entities(self):
        e = set()
        for page in self.pages:
            e.update(page.entities)

        return e
