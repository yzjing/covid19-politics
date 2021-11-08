from allennlp.predictors import Predictor
from allennlp.models.archival import load_archive
from contextlib import ExitStack
import argparse
import json
import pickle
import re


def get_predictor():
    p = Predictor.from_path("https://s3-us-west-2.amazonaws.com/allennlp/models/srl-model-2018.05.25.tar.gz")
    pickle.dump(p, open('predictor.p', 'wb'))

def run(batch_data,
        predictor,
        output_file,
        ):
    
    def _run_predictor_batch(batch_data):
        if len(batch_data) == 1:
            result = predictor.predict_json(batch_data[0])
            results = [result]
        else:
            results = predictor.predict_batch_json(batch_data)

        for model_input, output in zip(batch_data, results):
            string_output = predictor.dump_line(output)
            output_file.write(string_output)

    _run_predictor_batch(batch_data)



def get_covid_tweets(df):
    covid_vocab = pickle.load(open('../../data/all_covid_words.p', 'rb'))
    big_regex = re.compile('|'.join(map(re.escape, covid_vocab)))
    all_covid_tweets = []
    all_bg_tweets = []
    for idx, row in df.iterrows():
        try:
            line = row['Text'].lower()
            if 'covid' in line or 'coronavirus' in line:
                processed_line = big_regex.sub('covid', line)
                all_covid_tweets.append(processed_line)
            else:
                all_bg_tweets.append(line)
        except Exception as ex:
            continue
    return all_covid_tweets, all_bg_tweets

    
def run_document(party='dem'):
    predictor = pickle.load(open('predictor.p', 'rb'))
    data = pickle.load(open('../../data/all_tweet_texts_{}.p'.format(party), 'rb')) 
    covid_data, _ = get_covid_tweets(data)
    print('covid tweets: ', len(covid_data))
    input_sentences = []
    for line in covid_data:
        line = line.replace('\n', '')
        line = [sent+'.' for sent in line.split('.') if len(sent) > 3]
        input_sentences.extend(line)
    batch_data = [{'sentence': sent} for sent in input_sentences]
    start = 0
    batch_size = 5
    with ExitStack() as stack:
        output_file = stack.enter_context(open('all_tweet_{}_srl.txt'.format(party), 'a'))
        while start < len(batch_data):  
            print(start, start+batch_size)      
            run(batch_data[start:start+batch_size], predictor, output_file)
            start += batch_size

def main():
    run_document(party='dem')
    run_document(party='rep')


if __name__ == '__main__':
    main()