#!/bin/bash   

python get_tweets.py --list_id 34179516 --outpath ../../data/members_of_congress_tweets/

python get_tweets.py --list_id 816275409931210752 --outpath ../../data/new_members_of_congress_tweets/

python get_tweets.py --list_id 1184094696232144897 --outpath ../../data/POTUS_tweets/

python get_tweets.py --list_id 7560205 --outpath ../../data/govenors_tweets/

python get_tweets.py --list_id 6196793 --outpath ../../data/us_representatives_tweets/

python get_tweets.py --list_id 4244910 --outpath ../../data/senators_tweets/
