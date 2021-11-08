#!/usr/bin/env python
# coding: utf-8

import tweepy                   
import csv
import pickle
import argparse
import os
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


def get_all_tweets(api, screen_name, outpath):
    date = datetime.today().strftime('%Y-%m-%d')
    outpath = outpath + date + '/'
    # initialize a list to hold all the Tweets
    alltweets = []
    # make initial request for most recent tweets 
    # (200 is the maximum allowed count)
    new_tweets = api.user_timeline(screen_name = screen_name,count=200, tweet_mode="extended")
    # save most recent tweets
    alltweets.extend(new_tweets)
    # save the id of the oldest tweet less one to avoid duplication
    oldest_tweet_id = alltweets[-1].id
    # keep grabbing tweets until there are no tweets left
    while len(new_tweets) > 0:
        # all subsequent requests use the max_id param to prevent
        # duplicates
        new_tweets = api.user_timeline(screen_name = screen_name,count=200,max_id=oldest_tweet_id-1,\
                                     tweet_mode="extended")
        # save most recent tweets
        alltweets.extend(new_tweets)
        # update the id of the oldest tweet less one
        oldest_tweet_id = alltweets[-1].id 
    ### END OF WHILE LOOP ###
    print("Collected tweets from {}".format(screen_name))

    if not os.path.exists(outpath):
        os.makedirs(outpath)
    pickle.dump(alltweets, open(outpath + '%s_tweets.p' % screen_name, 'wb'))

    # transform the tweepy tweets into a 2D array that will 
    # populate the csv
    # outtweets = [[tweet.id_str, tweet.created_at, tweet.text, tweet.favorite_count,tweet.in_reply_to_screen_name, tweet.retweeted] for tweet in alltweets]
    # # write the csv
    # if not os.path.exists(outpath):
    #     os.makedirs(outpath)
    # with open(outpath + '%s_tweets.csv' % screen_name, 'w') as f:
    #     writer = csv.writer(f)
    #     writer.writerow(["id","created_at","text","likes","in reply to","retweeted"])
    #     writer.writerows(outtweets)
    pass




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
    # save tweets of people in a list
    for member in members:
        try:
            get_all_tweets(api, member, args.outpath)
        except Exception as ex:
            print(ex)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='example usage: $ python get_tweets.py --list_id 1184094696232144897 ')
    parser.add_argument('--list_id', nargs='?', type=str, help='ID of a twitter list to crawl')
    parser.add_argument('--outpath', nargs='?', default='./', type=str, help='path to store the output file, default is current directory')
    args = parser.parse_args()

    main(args)





