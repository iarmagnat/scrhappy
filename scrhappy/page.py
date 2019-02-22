from urllib.parse import urlparse

import requests
import re
import spacy

from bs4 import BeautifulSoup
from spacy_lefff import LefffLemmatizer, POSTagger
from collections import Counter
from nltk.tokenize import word_tokenize
from nltk import pos_tag

nlp_french = spacy.load('fr')
nlp_en = spacy.load('en')
french_lemmatizer = LefffLemmatizer()
nlp_french.add_pipe(french_lemmatizer, name='lefff', before="ner")

class RobotsForbiddenPage(Exception):
    pass

class Page:
    """dans page: url, page_parent, nom de domaine, urls internes, url externes, mot_clef,"""

    def __init__(self, url, site):
        self.url = url
        self.site = site
        self._links = []
        self.in_links = set()
        self._request = None
        self._parsed = False
        self._text = ""
        self._remarkable = ""
        self._entities = False
        self.site.pages.append(self)
        self.language = ""

    def set_language(self):
        soup = self.soup

        language = "en"

        DC = soup.find("meta", attrs={"name": "DC.language"})
        lang = soup.find("html").get("lang")
        if soup.find("meta", attrs={"name": "DC.language"}):
            language = DC.get('content')[:2].lower()
        elif lang:
            language = lang.lower()

        self.language = language

    def parse(self):
        self.set_language()
        soup = self.soup

        robot_meta = soup.find("meta", attrs={"name": "robots"})
        if robot_meta and robot_meta.get("content") in ["noindex", "nofollow", "none"]:
            # In all fairness, a custom behaviour for nofollow should be implemented because it means
            # parse the page but do not follow links.
            raise RobotsForbiddenPage(f"Page at {self.url} was blocked because ot robots meta tag")

        for link in soup("a"):
            loc = link.get('href')
            if loc and "/" in loc:
                self._links.append(loc)
                parsed = urlparse(loc)
                if not re.match(r"^https?(?!.*{%s}).*$" % self.site.root, loc):
                    if loc[0] != "/" and not parsed.netloc:
                        parsed = urlparse(self.url + loc)
                    elif loc[0] == "/" and not parsed.netloc:
                        parsed = urlparse(f"{self.site.protocol}://{self.site.root}{loc}")
                    self.site.url_add(f"{self.site.protocol}://{self.site.root}{parsed.path}")

    @property
    def soup(self):
        # https://www.crummy.com/software/BeautifulSoup/bs4/doc/#encodings
        # no need to worry about encoding!
        return BeautifulSoup(self.request, 'lxml')

    @property
    def request(self):
        if not self._request:
            request = requests.get(self.url)
            self._request = request.text
            request.raise_for_status()
        return self._request

    @property
    def links(self):
        if not self._parsed:
            self.parse()
        return self._links

    def get_links(self, mode="all"):
        if mode == "all":
            return self.links
        elif mode == 'internal':
            links = []
            for link in self.links:
                if not re.match(r"^https?(?!.*{%s}).*$" % self.site.root, link):
                    links.append(link)
            return links
        elif mode == 'external':
            links = []
            for link in self.links:
                if re.match(r"^https?(?!.*{%s}).*$" % self.site.root, link):
                    links.append(link)
            return links
        else:
            raise NotImplemented(f"mode {mode} not implemented")

    @property
    def text(self):
        """récupère le contenu de la page"""
        if not self._text:
            h_tags = ["h{}".format(i) for i in range(1, 6)]

            p_text = [x.text.replace("\n", " ") for x in self.soup.find_all("p") if re.match(r"\w+", x.text)]

            # TODO: Unused for now
            # div_text = {}
            #
            # for d in h_tags:
            #     div_text[d] = [x.text.replace("\n", " ") for x in self.soup.find_all(d)]
            # div_text["strong"] = [x.text.replace("\n", " ") for x in self.soup.find_all("strong")]
            # self._remarkable = div_text

            self._text = " ".join(p_text)
        return self._text

    @property
    def lemmes(self):
        tokens = word_tokenize(self.text)
        tokens = [w.lower() for w in tokens]

        print(tokens)
        return tokens

    # p_tag = pos_tag(tokens)

    # print(lemmes)

    @property
    def entities(self):
        if not self._entities:

            if not self.language:
                self.set_language()

            if self.language == "fr":
                nlp = nlp_french
            else:
                nlp = nlp_en

            doc = nlp(self.text)

            self._entities = []
            for entity in doc.ents:
                self._entities.append(entity.text)

        return self._entities
