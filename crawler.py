import requests
import sys
import re
import MeCab
from bs4 import BeautifulSoup
from html.parser import HTMLParser
from urllib.parse import urlparse, parse_qs

docs = {}
words = {}

mecab_parser = MeCab.Tagger()

news_urls = {}
dir_urls = set()

BASE_HOST = "http://m.news.naver.com"

class LinkParser(HTMLParser):
    def __init__(self):
        super(self.__class__, self).__init__()

        self.link = {}

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for attr in attrs:
                if "href" == attr[0].lower():
                    if attr[1].startswith("/main.nhn?mode=LSD&sid1"):
                        self.link[attr[1]] = 2
                    elif "/read.nhn?" in attr[1]:
                        self.link[attr[1]] = 1
                    else:
                        self.link[attr[1]] = 0


def fetch(baseurl, sid):
    url = "%s&sid1=%s"%(baseurl, sid)
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    data_divs = soup.find_all('div', {"class": "newsct_article _news_article_body"})
    texts = []
    for div in data_divs:
        texts.append(re.sub(r'[?|(|)|<|>|$|!|,|\"|\'|“|=|-|`|\[|\]]',r'',div.text))

    ret = ' '.join(texts)
    worditems = set(ret.split())
    docs[url] = worditems

    for word in worditems:
        m = mecab_parser.parseToNode(word)
        while m:
            if m.feature.startswith('NN'):
                w = m.surface
                if w in words:
                    words[w].add(url)
                else:
                    words[w] = set([url])

            m = m.next


def url_normalize(url):
    o = urlparse(url)
    qs = parse_qs(o.query)

    sid1 = 0

    if 'sid1' in qs:
        sid1 = qs['sid1'][0]
        del qs['sid1']
    if 'mode' in qs:
        del qs['mode']

    s = [q + "=" + qs[q][0] for q in qs]
    return (BASE_HOST + "/read.nhn?" + '&'.join(s), int(sid1))


def collect_urls(url):
    resp = requests.get(url)
    link_parser = LinkParser()
    link_parser.feed(resp.text)

    dir_urls.add(url)
    for k in link_parser.link:
        v = link_parser.link[k]
        if v == 1:
            turl = k
            if k.startswith('http://') == False:
                turl = BASE_HOST + k
                
            turl = url_normalize(turl)
            if turl[1] > 0:
                news_urls[turl[0]] = turl[1]

        if v == 2:
            turl = k
            if k.startswith('http://') == False:
                turl = BASE_HOST + k

            if turl not in dir_urls:
                collect_urls(turl)


def crawls(targets):
    for url in news_urls:
        fetch(url, news_urls[url])
    
                
if __name__ == "__main__":
    seed_url = sys.argv[1]

    collect_urls(seed_url)
#    for url in news_urls:
#        print(url)


    crawls(news_urls)
    
    v = []
    for word in words:
        v.append((word, len(words[word])))

    print("docs: ", len(docs))
    print("words: ", len(v))
    k = sorted(v, key=lambda x: x[1])
    for i in k:
        print(i)
