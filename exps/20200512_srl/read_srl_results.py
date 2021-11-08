#!/usr/bin/env python
# coding: utf-8

# In[25]:


import pandas as pd
import argparse

parser = argparse.ArgumentParser(description='inputs and outputs')
parser.add_argument('--input_file', nargs='?', type=str, help="e.g. all_tweet_rep_srl.txt")
parser.add_argument('--output_file', nargs='?',type=str, help="e.g. dem_srl_df.tsv")
args = parser.parse_args()

results = []


with open(args.input_file, 'r') as f:
	for line in f.readlines():
		results.append(eval(line))

all_texts = []
all_verbs = []

for entry in results:
    for verb in entry['verbs']:
        all_texts.append(entry['words'])
        all_verbs.append(verb)

srl_df = pd.DataFrame(zip(all_texts, all_verbs), columns=['Text', 'Verb_annotation'])
print(srl_df.head(2))
srl_df.to_csv(args.output_file, sep='\t', index=False)





