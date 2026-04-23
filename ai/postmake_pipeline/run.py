from from_crawling import get_info_crawling_data, get_shop_crawling_data
from prompt import Prompt
from chain import chain
import logging

import time

logger = logging.getLogger(__name__)

def run_batch():
    batch_count = 0
    while True:

                response = chain(data=row['content'], type=prompt)

                #push

                
