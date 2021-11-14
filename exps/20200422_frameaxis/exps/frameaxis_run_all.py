#!/usr/bin/env python
# coding: utf-8



import sys
sys.path.insert(0, '../libs/semaxis')
from semaxis import CoreUtil
from semaxis import SemAxis
import pandas as pd
import logging
import pickle
import random
import numpy as np
import re
import glob
import os
import gc



logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ## Read data

def get_covid_tweets(df):
    all_covid_tweets = []
    all_bg_tweets = []
    for idx, row in df.iterrows():
        try:
            t = row['Text']
            if 'covid' in t or 'coronavirus' in t:
                all_covid_tweets.append(row)
            else:
                all_bg_tweets.append(row)
        except Exception as ex:
            continue
            
    return pd.DataFrame(all_covid_tweets), pd.DataFrame(all_bg_tweets)


def load_data(target_option='politician_covid', bg_option='general_covid'):

    if target_option == 'politician_covid':
        dem = pickle.load(open('../../../data/all_tweet_texts_dem.p', 'rb'))
        rep = pickle.load(open('../../../data/all_tweet_texts_rep.p', 'rb'))
        dem_covid, _ = get_covid_tweets(dem)
        rep_covid, _ = get_covid_tweets(rep)

    elif target_option == 'all_politician':
        dem = pickle.load(open('../../../data/all_tweet_texts_dem.p', 'rb'))
        rep = pickle.load(open('../../../data/all_tweet_texts_rep.p', 'rb'))

    else:
        logger.info('not valid option for target corpus')


    if bg_option == 'general_covid':
        moe_1 = pickle.load(open('../../../data/moe_sample_tweets_feb.p', 'rb'))
        moe_2 = pickle.load(open('../../../data/moe_sample_tweets_mar.p', 'rb'))
        moe_3 = pickle.load(open('../../../data/moe_sample_tweets_apr.p', 'rb'))
        moe_4 = pd.read_csv('../../../data/moe_may_to_aug_sample.tsv', sep='\t',lineterminator='\n')
        moe_4.columns = ['unnamed', 'Text', 'Time']
        moe_4 = moe_4[['Text', 'Time']]
        bg = pd.concat([moe_1, moe_2, moe_3, moe_4])

    elif bg_option == 'general':
        bg = pd.read_csv('../../../data/moe_feb_to_aug_general_sample.tsv', \
            sep='\t',lineterminator='\n')

    elif bg_option == 'politician_bg':
        dem = pickle.load(open('../../../data/all_tweet_texts_dem.p', 'rb'))
        rep = pickle.load(open('../../../data/all_tweet_texts_rep.p', 'rb'))
        _, dem_bg = get_covid_tweets(dem)
        _, rep_bg = get_covid_tweets(rep)
        bg = pd.concat([dem_bg, rep_bg])

    else:
        logger.info('not valid option for background corpus')

    dem_covid['Party'] = 'Dem'
    rep_covid['Party'] = 'Rep'
    bg['Party'] = 'Bg'
    covid_vocab = pickle.load(open('../../../data/all_covid_words.p', 'rb'))
    big_regex = re.compile('|'.join(map(re.escape, covid_vocab)))
    dem_covid['Text'] = dem_covid.apply(lambda row: big_regex.sub('covid', row['Text'].lower()), axis=1)
    rep_covid['Text'] = rep_covid.apply(lambda row: big_regex.sub('covid', row['Text'].lower()), axis=1)
    bg['Text'] = bg.apply(lambda row: big_regex.sub('covid', row['Text'].lower()), axis=1)
    for item in dem_covid.head(10).Text.tolist():
        print(item)
        print()
    df_all = pd.concat([dem_covid, rep_covid, bg])
    logger.info('data loaded, size: ', len(df_all))
    return df_all


def create_sa():
    # ## Create semaxis object

    # from gensim.test.utils import datapath, get_tmpfile
    # from gensim.models import KeyedVectors
    # from gensim.scripts.glove2word2vec import glove2word2vec
    # glove_file = '../../data/embeddings/glove.840B.300d.txt'
    # tmp_file = "../../data/embeddings/test_word2vec.txt"
    # output = glove2word2vec(glove_file, tmp_file)

    # %%time
    # sa = SemAxis(CoreUtil.load_embedding("glove/all_glove_gensim_word2vec.txt", is_binary=False), 
    #                axes_str=CoreUtil.load_wordnet_antonyms_axes())

    # pickle.dump(sa, open('sa_object.p', 'wb'))

    global sa
    sa = pickle.load(open('sa_object.p', 'rb'))
    logger.info('loaded semaxis object')
    return sa


def big_table_bias(df):
    # # big table for bias
    logger.info('creating big table for bias')
    COLUMNS = [str(c) for c in sorted(sa.axes.keys()) if len(c) == 2]
    with open("big_table_by_average.tsv", "w") as fo_a, open("big_table_by_kurtosis.tsv", "w") as fo_k:
        fo_a.write("party\ttext\t{}\n".format("\t".join(COLUMNS)))
        fo_k.write("party\ttext\t{}\n".format("\t".join(COLUMNS)))
        for loop_index, (row_index, row) in enumerate(df.iterrows()):
            if loop_index % (1000) == 0:
                logger.info(loop_index)
            try:
                _, mean, kurtosis = sa.compute_document_mean_kurtosis_with_tf([row['Text']], min_freq = 1)
            except ValueError as ve:
    #             logger.exception("no vocab")
                continue
            except:
                logger.exception("???")
                continue
            fo_a.write("{}\t{}\t{}\n".format(row['Party'], row['Text'], "\t".join([str(v) for v in mean])))
            fo_k.write("{}\t{}\t{}\n".format(row['Party'], row['Text'], "\t".join([str(v) for v in kurtosis])))

def big_table_intensidy(df):
    # # big table for intensity
    logger.info('creating big table for intensity')
    COLUMNS = [str(c) for c in sorted(sa.axes.keys()) if len(c) == 2]

    with open("big_table_by_second_moment_with_corpus_mean.tsv", "w") as fo_k:
        fo_k.write("party\ttext\t{}\n".format("\t".join(COLUMNS)))
        df_corpus = pd.read_csv("big_table_by_average.tsv", sep="\t",quoting=3, error_bad_lines=False)
        df_corpus.dropna(inplace=True)
        corpus_mean = np.mean(df_corpus.drop(
            columns=[c for c in df_corpus.columns if '(' not in c]).values, axis=0)
        for loop_index, (row_index, row) in enumerate(df.iterrows()):
            if loop_index % (1000) == 0:
                logger.info(loop_index)
            try:
                sm = sa.compute_document_second_moment_with_tf([row['Text']], corpus_mean, min_freq = 1)  
            except ValueError as ve:
    #             logger.exception("no vocab")
                continue
            except:
                logger.exception("???")
                continue
            fo_k.write("{}\t{}\t{}\n".format(row['Party'], row['Text'], "\t".join([str(v) for v in sm[0]])))


def bootstrap_sig_average():
    # ## Bootstrap avg
    logger.info('bootstrapping average')

    df_bias = pd.read_csv('big_table_by_average.tsv', sep='\t', quoting=3, error_bad_lines=False)

    N = 1000
    mode = "average"
    logger.info(mode)
    try:
        os.mkdir(mode)
    except:
        pass

    COLUMNS = [c for c in df_bias.columns if '(' in c]

    df_bias = df_bias[df_bias['party'].isin(['Bg', 'Dem', 'Rep'])]
    df_bias.dropna(inplace=True)

    for party, a_count in df_bias['party'].value_counts().iteritems():
        logger.info("{}...".format(party))
        with open("{}/bootstrap_{}_average_by_party.tsv".format(mode, party), "w") as fo:
            fo.write("{}\n".format("\t".join(COLUMNS)))
            A = df_bias.drop(columns=[c for c in df_bias.columns if '(' not in c]).values
            for i in range(N):
                if i % 100 == 0:
                    logger.info(i)
                fmean = np.mean(A[np.random.choice(A.shape[0], a_count, replace=False), :], axis=0)
                fo.write("{}\n".format("\t".join([str(v) for v in (fmean)])))        


    BOOTSTRAP_TEMPLATE = "{}/bootstrap_{}_{}_by_party.tsv"
    OUT_TEMPLATE = "{}/significant_axes_{}_{}_by_party.tsv"
    OUT_TEMPLATE2 = "{}/effect_size_significant_axes_{}_{}_by_party.tsv"

    for party, a_count in df_bias['party'].value_counts().iteritems():
        
        results = []        
        logger.info("{}...".format(party))
        
        df_actual = df_bias.query('party==@party')
        df_bootstrap = pd.read_csv(BOOTSTRAP_TEMPLATE.format(mode, party, mode), sep="\t").dropna()

        for axis in COLUMNS:
            actual = np.mean(df_actual[axis], axis=0)
            significance = sum(abs(df_bootstrap[axis]) > abs(actual))/float(N)
            results.append([axis, actual-np.mean(df_bootstrap[axis], axis=0), significance])

        pd.DataFrame(sorted(results, key=lambda x:x[2]), 
                     columns = ["axis", "diff_a_b", "p"]
                    ).to_csv(OUT_TEMPLATE.format(mode, party, mode), sep="\t", index=False)

        pd.DataFrame(sorted(results, key=lambda x:abs(x[1]), reverse=True), 
             columns = ["axis", "diff_a_b", "p"]
            ).query('p <= 0.05').to_csv(OUT_TEMPLATE2.format(mode, party, mode), sep="\t", index=False)

def bootstrap_sig_second_moment():
    # ## Bootstrap second moment
    logger.info('bootstrapping second moment')

    df_intensity = pd.read_csv('big_table_by_second_moment_with_corpus_mean.tsv', sep='\t')

    df_intensity = df_intensity[df_intensity['party'].isin(['Bg', 'Dem', 'Rep'])]
    df_intensity.dropna(inplace=True)

    N = 1000
    mode = "second_moment"
    logger.info(mode)
    try:
        os.mkdir(mode)
    except:
        pass

    COLUMNS = [c for c in df_intensity.columns if '(' in c]

    for party, a_count in df_intensity['party'].value_counts().iteritems():
        logger.info("{}...".format(party))
        with open("{}/bootstrap_{}_second_moment_with_corpus_mean_by_party.tsv".format(mode, party), "w") as fo:
            fo.write("{}\n".format("\t".join(COLUMNS)))
            A = df_intensity.drop(columns=[c for c in df_intensity.columns if '(' not in c]).values

            for i in range(N):
                if i % 100 == 0:
                    logger.info(i)
                fmean = np.mean(A[np.random.choice(A.shape[0], a_count, replace=False), :], axis=0)
                fo.write("{}\n".format("\t".join([str(v) for v in (fmean)])))        


    # ## Significant axes second moment

    BOOTSTRAP_TEMPLATE = "{}/bootstrap_{}_second_moment_with_corpus_mean_by_party.tsv"
    OUT_TEMPLATE = "{}/significant_axes_{}_second_moment_with_corpus_mean_by_party.tsv"
    OUT_TEMPLATE2 = "{}/effect_size_significant_axes_{}_second_moment_with_corpus_mean_by_party.tsv"

    for party, a_count in df_intensity['party'].value_counts().iteritems():

        results = []        
        logger.info("{}...".format(party))
        
        df_actual = df_intensity.query('party==@party')
        df_bootstrap = pd.read_csv(BOOTSTRAP_TEMPLATE.format(mode, party), sep="\t").dropna()
        for axis in COLUMNS:
            actual = np.mean(df_actual[axis], axis=0)
            significance = sum(abs(df_bootstrap[axis]) > abs(actual))/float(N)
            results.append([axis, actual-np.mean(df_bootstrap[axis], axis=0), significance])

        pd.DataFrame(sorted(results, key=lambda x:x[2]), 
                     columns = ["axis", "diff_a_b", "p"]
                    ).to_csv(OUT_TEMPLATE.format(mode, party), sep="\t", index=False)

        pd.DataFrame(sorted(results, key=lambda x:abs(x[1]), reverse=True), 
             columns = ["axis", "diff_a_b", "p"]
            ).query('p <= 0.05').to_csv(OUT_TEMPLATE2.format(mode, party), sep="\t", index=False)


if __name__ == "__main__":
    df_all = load_data(target_option='politician_covid', bg_option='politician_bg')
    create_sa()
    big_table_bias(df_all)
    big_table_intensidy(df_all)
    bootstrap_sig_average()
    bootstrap_sig_second_moment()




