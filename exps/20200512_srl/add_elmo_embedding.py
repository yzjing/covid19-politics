#!/usr/bin/env python
# coding: utf-8

# In[1]:


from allennlp.modules.elmo import Elmo, batch_to_ids
options_file = "https://allennlp.s3.amazonaws.com/models/elmo/2x4096_512_2048cnn_2xhighway/elmo_2x4096_512_2048cnn_2xhighway_options.json"
weight_file = "https://allennlp.s3.amazonaws.com/models/elmo/2x4096_512_2048cnn_2xhighway/elmo_2x4096_512_2048cnn_2xhighway_weights.hdf5"
import pandas as pd
from scipy.spatial.distance import cosine
import pickle
import argparse
import torch

parser = argparse.ArgumentParser(description='inputs and outputs')
parser.add_argument('--input_file', nargs='?', type=str, help="e.g. dem_srl_df.tsv")
parser.add_argument('--output_file', nargs='?',type=str, help="e.g. srl_elmo_dem.tsv")
args = parser.parse_args()

device = torch.device(1 if torch.cuda.is_available() else "cpu")
print('training on', device)

# Compute two different representation for each token.
# Each representation is a linear weighted combination for the
# 3 layers in ELMo (i.e., charcnn, the outputs of the two BiLSTM))
elmo = Elmo(options_file, weight_file, 1, dropout=0).to(device)

df = pd.read_csv(args.input_file, sep='\t')
all_text = df.Text.drop_duplicates().tolist()

batch_size = 16
start = 0
all_embeddings = []
print('start computing embeddings')
while start < len(all_text):
	print(start, start+batch_size)
	batch = all_text[start: start+batch_size]
	character_ids = batch_to_ids(batch).to(device)
	with torch.no_grad():
		emb = elmo(character_ids)['elmo_representations']
		for item in emb[0]:
		    all_embeddings.append(item.cpu().detach().numpy())
	start += batch_size

df_text_embeddings = pd.DataFrame(zip(all_text, all_embeddings), columns=['Text', 'Embeddings'])

df_srl_emb = pd.merge(df, df_text_embeddings, on='Text', how='inner')

pickle.dump(df_srl_emb, open(args.output_file, 'wb'))




