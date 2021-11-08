#!/usr/bin/env python
# coding: utf-8

# In[1]:


import json
import pandas as pd
from datetime import datetime, timezone
from dateutil.parser import parse
import os
import pickle
from langdetect import detect


# In[2]:


file_path = '/l/nx/user/jingy/covid19/moe_general_sample/'


tweet_list = []

for file in os.listdir(file_path):
	data = open(file_path+file).readlines()
	print('read data from: '+file)
	for line in data:
		tweet = json.loads(line)
		try:
			if detect(tweet['text']) == 'en':
				tweet_list.append([tweet['text'], tweet['created_at']])
		except:
			pass

df = pd.DataFrame(tweet_list, columns=['text', 'time'])
df.to_csv('moe_general_tweets_feb_to_aug.tsv', sep='\t')

df['time'] = df['time'].apply(lambda x: parse(x).replace(tzinfo=None))

def get_time_df(sy,sm,sd, ey,em,ed):
	df_mon = df[df['time'].apply(lambda x: x > datetime(sy,sm,sd) and x < datetime(ey,em,ed))]
	print(len(df_mon))
	if len(df_mon) > 10000:
		df_mon = df_mon.sample(10000)
	return df_mon


feb = get_time_df(2020, 2, 1, 2020,3,1)
mar = get_time_df(2020, 3, 1, 2020,4,1)
apr = get_time_df(2020, 4, 1, 2020,5,1)
may = get_time_df(2020, 5, 1, 2020,6,1)
jun = get_time_df(2020, 6, 1, 2020,7,1)
jul = get_time_df(2020, 7, 1, 2020,8,1)
aug = get_time_df(2020, 8, 1, 2020,9,1)

df_sample = pd.concat([feb, mar, apr, may, jun, jul, aug])
df_sample.to_csv('moe_feb_to_aug_general_sample.tsv', sep='\t')




