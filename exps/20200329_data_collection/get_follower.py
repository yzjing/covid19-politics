#!/usr/bin/env python
# coding: utf-8

import tweepy                   
import pickle
import argparse
import os
import time
from datetime import datetime

# ## List ids of interest:
# 
# Members of congress 34179516
# 
# New members of congress 816275409931210752
# 
# POTUS 1184094696232144897
# 
# Govenors 7560205
# 
# US representatives 6196793
# 
# Senators 4244910


def init_api():
    # load keys from a pickle file
    api_keys = pickle.load(open('api_keys.p', 'rb'))
    api_key = api_keys['consumer_key']
    api_secret_key = api_keys['consumer_secret']
    access_token = api_keys['access_key']
    access_token_secret = api_keys['access_secret']
    # Connect to Twitter API using the secrets
    auth = tweepy.OAuthHandler(api_key, api_secret_key)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
    return api


def get_follower(api, screen_name, outpath):
    date = datetime.today().strftime('%Y-%m-%d')
    outpath = outpath + date + '/'
    follower_id_list = []
    for page in tweepy.Cursor(api.followers_ids, screen_name=screen_name).pages():
        follower_id_list.extend(page)
        print('{} followers collected'.format(int(len(follower_id_list))))
    if not os.path.exists(outpath):
        os.makedirs(outpath)
    with open(outpath + '{}_follower.txt'.format(screen_name), 'w') as g:
        g.write(str(follower_id_list))

def get_list_members(api, list_id):
    members = []
    # without this you only get the first 20 list members
    for page in tweepy.Cursor(api.list_members, list_id=list_id).items():
        members.append(page)
    # create a list containing all usernames
    return [ m.screen_name for m in members ]


def main(args):
    args = parser.parse_args()
    api = init_api()
    members = get_list_members(api, args.list_id)
    for member in members:
        get_follower(api, member, args.outpath)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='example usage: $ python get_tweets.py --list_id 1184094696232144897 ')
    parser.add_argument('--list_id', nargs='?', type=str, help='ID of a twitter list to crawl')
    parser.add_argument('--outpath', nargs='?', default='./', type=str, help='path to store the output file, default is current directory')
    args = parser.parse_args()

    main(args)





