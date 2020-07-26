# coding=utf-8
import tldextract
from scrapy.dupefilters import BaseDupeFilter
from scrapy.utils.reqser import request_to_dict


class RFPagePerDomainFilter(BaseDupeFilter):
    '''
    Redis-based request number filter
    '''

    def __init__(self, server, key, page_limit, timeout):
        '''
        Initialize page number filter

        @param server: the redis connection
        @param key: the key to store the fingerprints
        @param page_limit: the number of pages that when reached stops the particular domain crawl
        @param timeout: number of seconds a given key will remain once idle
        '''
        self.server = server
        # key_start equals: self.spider.name + ':pagecountfilter'
        self.key_start = key
        self.page_limit = page_limit
        self.timeout = timeout
        # set up tldextract
        self.extract = tldextract.TLDExtract()

    def request_page_limit_reached(self, request, spider):
        # Collect items composing the redis key
        # grab the tld of the request
        req_dict = request_to_dict(request, spider)
        ex_res = self.extract(req_dict['url'])
        domain = "{d}.{s}".format(d=ex_res.domain, s=ex_res.suffix)

        # grab the crawl id
        crawl_id = request.meta['crawlid']

        # Compose the redis key
        composite_key = self.key_start + ':' + domain + ':' + crawl_id

        # Add new key if it doesn't exist
        if not self.server.exists(composite_key):
            self.server.set(composite_key, 0)

        # Stop incrementing the key when the limit is reached
        page_count = int(self.server.get(composite_key))
        if page_count >= self.page_limit:
            return True

        # Increment key
        page_count = int(self.server.incr(composite_key))
        # Expire key
        self.server.expire(composite_key, self.timeout)

        return page_count >= self.page_limit

    def close(self, reason):
        '''
        Delete data on close. Called by scrapy's scheduler
        '''
        self.clear()

    def clear(self):
        '''
        The page number per domain has a TTL so you shouldn't clear it
        '''
        pass
        #self.server.delete(self.key)
