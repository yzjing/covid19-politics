#!/usr/bin/env python
# coding: utf-8

# In[41]:


import paths
import os
import json
import gzip
import pandas as pd
from langdetect import detect
import pickle
import random


# In[44]:


paths = paths.Paths()


months = ['feb', 'mar', 'apr']
for month in months:
    all_tweets = []
    print('working on: ', month)
    for i in range(1,9):
        temp_path = paths.get_rawfilenames(i)
        if month in temp_path[0]:
            tweet_cnt = 0
            files = random.sample(temp_path, 10)
            for file in files:
                with gzip.open(file) as f:
                    for line in f:
                        tweet = json.loads(line)        
                        text = tweet['text']
                        time = tweet['created_at']
                        try:
                            if detect(text) == 'en':
                                all_tweets.append([text, time])
                                tweet_cnt += 1
                        except Exception as ex:
                            print(ex)
                print('completed: ', file, 'number of tweets: ', tweet_cnt)
    print('completed: ', month, 'total tweets: ', tweet_cnt)
    all_tweets = pd.DataFrame(all_tweets, columns = ['Text', 'Time'])
    print(all_tweets.head(2))
    pickle.dump(all_tweets, open('../../data/moe_sample_tweets_{}.p'.format(month), 'wb'))


