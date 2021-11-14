from sklearn.feature_extraction.text import CountVectorizer
from collections import defaultdict
import numpy as np
from nltk.corpus import stopwords
import math
import operator
from .core import CoreUtil
import logging


class SemAxis:
    def __init__(self, embedding, axes_str=CoreUtil.load_conceptnet_antonyms_axes()):
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                            datefmt='%m-%d %H:%M',
                            filemode="w")
        self.logger = logging.getLogger(__name__)                
        self.embedding = embedding
        self.axes = self._build_axes_on_embedding(axes_str)
        self.axes_tfm_nn = None

    
    def _build_axes_on_embedding(self, axes_str):
        mapped_axes = {}
        for axis in axes_str:
            try:
                mapped_axes[axis] = CoreUtil.map_axis_to_vec(self.embedding, axis)
            except KeyError:
                self.logger.error("{} axis is not included in embedding".format(axis), exc_info=True)

        return mapped_axes
    
    def embedding_vector_size(self):
        return self.embedding.vector_size

    def compute_word_score(self, w):
        results = {}
        w_vec = self.embedding.wv[w]
        for axis_name in self.axes:
            results[axis_name] = CoreUtil.get_score(w_vec, self.axes[axis_name])
        return results

    def _compute_with_document(self, document, filter_stopword = True, min_freq = 10, power=1):
        vectorizer = CountVectorizer()
        transformed_data = vectorizer.fit_transform(document)
        tf = zip(vectorizer.get_feature_names(), np.ravel(transformed_data.sum(axis=0)))

        axis2score = defaultdict(float)
        word_count = 0
        for (term, frequency) in tf:
            if frequency < min_freq:
                continue
            if filter_stopword and (term in stopwords.words('english')):
                continue

            try:
                w_vec = self.embedding.wv[term]
            except:
                continue

            for axis_name in self.axes:
                score = CoreUtil.get_score(w_vec, self.axes[axis_name])
                axis2score[axis_name] += math.pow(score,power) * frequency
            word_count += frequency
        return [[r[0][0], r[0][1], r[1]/word_count] 
                for r in sorted(axis2score.items(), key=operator.itemgetter(1), reverse=True)]

    def compute_document_score(self, document, filter_stopword = True, min_freq = 10):
        return self._compute_with_document(document, filter_stopword, min_freq, 1)

    def compute_document_strength(self, document, filter_stopword = True, min_freq = 10):
        return self._compute_with_document(document, filter_stopword, min_freq, 2)

    def compute_document_raw(self, document, filter_stopword = True, min_freq = 10):
        vectorizer = CountVectorizer()
        transformed_data = vectorizer.fit_transform(document)
        tf = zip(vectorizer.get_feature_names(), np.ravel(transformed_data.sum(axis=0)))

        axis2score = defaultdict(lambda: defaultdict(int))
        for (term, frequency) in tf:
            if frequency < min_freq:
                continue
            if filter_stopword and (term in stopwords.words('english')):
                continue

            try:
                w_vec = self.embedding.wv[term]
            except:
                continue

            for axis_name in self.axes:
                score = CoreUtil.get_score(w_vec, self.axes[axis_name])
                axis2score[axis_name][score] += frequency

        return axis2score

    def _prepare_matrix_computation(self, document, filter_stopword, min_freq):
        vectorizer = CountVectorizer()
        transformed_data = vectorizer.fit_transform(document)

        terms_filtered = []
        frequencies_filtered = []
        words = []
        frequencies = np.ravel(transformed_data.sum(axis=0))
        for w_index, w in enumerate(vectorizer.get_feature_names()):
            if w in self.embedding.wv:
                if frequencies[w_index] < min_freq or (filter_stopword 
                    and (w in stopwords.words('english'))):
                    continue
                terms_filtered.append(self.embedding.wv[w])
                frequencies_filtered.append(frequencies[w_index])
                words.append(w)

        if self.axes_tfm_nn is None:
            self.axes_mat = np.array([self.axes[k] for k in sorted(self.axes)])

        return terms_filtered, frequencies_filtered, words

    def compute_document_mean_kurtosis_with_tf(self, document, filter_stopword = True, min_freq = 10):
        terms_filtered, frequencies_filtered, _ =  self._prepare_matrix_computation(document, filter_stopword, min_freq)  
        import tensorflow as tf        
        tf.reset_default_graph()
        with tf.Session() as sess:
            self.axes_tfm_nn = tf.nn.l2_normalize(tf.constant(self.axes_mat), axis = 1)    
            frequencies_vec = tf.constant(frequencies_filtered, dtype=np.float32)
            term_filtered_tfm_nn = tf.nn.l2_normalize(tf.constant(np.array(terms_filtered)), axis = 1)

            result = tf.matmul(self.axes_tfm_nn, term_filtered_tfm_nn,
                             adjoint_b = True # transpose second matrix
                             )
            ws = tf.multiply(result, frequencies_vec)
            mean = tf.reduce_sum(ws, 1)/tf.reduce_sum(frequencies_vec)
            ss = tf.reduce_sum(tf.multiply(tf.square(result), frequencies_vec), 1)/tf.reduce_sum(frequencies_vec)
            ms = tf.square(mean)
            # std = tf.sqrt(ss-ms)
            diff = result-tf.reshape(mean, [-1,1])
            moment4 = tf.reduce_sum(tf.multiply(tf.pow(diff, 4), frequencies_vec), 1)/tf.reduce_sum(frequencies_vec)
            moment2 = tf.reduce_sum(tf.multiply(tf.pow(diff, 2), frequencies_vec), 1)/tf.reduce_sum(frequencies_vec)
            kurtosis = moment4 / tf.square(moment2) - 3    
            mean, kurtosis = sess.run([mean, kurtosis])

        return sorted(self.axes.keys()), mean, kurtosis


    def _get_top_mask(self, t, k):
        import tensorflow as tf
        top_k = tf.math.top_k(t, k)
        tpivots = tf.reduce_min(top_k.values, axis=1)
        tpivots_ft = tf.reshape(tpivots, [-1,1])
        return tf.greater_equal(t, tpivots_ft) 

    def _apply_mask(self, test, frequencies_vec, mask_percent):
        import tensorflow as tf
        k = round(int(test.shape[1])/100*mask_percent)

        top_mask = self._get_top_mask(test, k)
        bot_mask = self._get_top_mask(-1*test, k)
        mask = tf.math.logical_or(top_mask, bot_mask)
        zeros = tf.zeros(test.shape)

        multiply = [test.shape[0]]
        r_matrix = tf.reshape(tf.tile(frequencies_vec, multiply), [ multiply[0], tf.shape(frequencies_vec)[0]])
        masked_frequencies_tsr = tf.where(mask, r_matrix, zeros)
        
        return tf.where(mask, test, zeros), masked_frequencies_tsr      

    def compute_document_mean_kurtosis_with_tf_mask(self, document, filter_stopword = True, min_freq = 10, mask_percent = 5):
        terms_filtered, frequencies_filtered, _ =  self._prepare_matrix_computation(document, filter_stopword, min_freq)  
        import tensorflow as tf        
        tf.reset_default_graph()
        with tf.Session() as sess:
            self.axes_tfm_nn = tf.nn.l2_normalize(tf.constant(self.axes_mat), axis = 1)    
            frequencies_vec = tf.constant(frequencies_filtered, dtype=np.float32)
            term_filtered_tfm_nn = tf.nn.l2_normalize(tf.constant(np.array(terms_filtered)), axis = 1)

            test = tf.matmul(self.axes_tfm_nn, term_filtered_tfm_nn,
                             adjoint_b = True # transpose second matrix
                             )
            result, masked_frequencies_tsr = self._apply_mask(test, frequencies_vec, mask_percent)
            
            ws = tf.multiply(result, masked_frequencies_tsr)
            mean = tf.reduce_sum(ws, 1)/tf.reduce_sum(masked_frequencies_tsr, 1)
            # ss = tf.reduce_sum(tf.multiply(tf.square(result), masked_frequencies_tsr), 1)/tf.reduce_sum(masked_frequencies_tsr, 1)
            # ms = tf.square(mean)
            # std = tf.sqrt(ss-ms)
            diff = result-tf.reshape(mean, [-1,1])
            moment4 = tf.reduce_sum(tf.multiply(tf.pow(diff, 4), masked_frequencies_tsr), 1)/tf.reduce_sum(masked_frequencies_tsr, 1)
            moment2 = tf.reduce_sum(tf.multiply(tf.pow(diff, 2), masked_frequencies_tsr), 1)/tf.reduce_sum(masked_frequencies_tsr, 1)
            kurtosis = moment4 / tf.square(moment2) - 3    
            mean, kurtosis = sess.run([mean, kurtosis])

        return sorted(self.axes.keys()), mean, kurtosis


    def compute_document_mean_with_tf(self, document, filter_stopword = True, min_freq = 10):
        terms_filtered, frequencies_filtered, _ =  self._prepare_matrix_computation(document, filter_stopword, min_freq)  
               
        # self.logger.debug(terms_filtered)
        import tensorflow as tf        
        tf.reset_default_graph()
        with tf.Session() as sess:
            self.axes_tfm_nn = tf.nn.l2_normalize(tf.constant(self.axes_mat), axis = 1)    
            frequencies_vec = tf.constant(frequencies_filtered, dtype=np.float32)
            term_filtered_tfm_nn = tf.nn.l2_normalize(tf.constant(np.array(terms_filtered)), axis = 1)

            result = tf.matmul(self.axes_tfm_nn, term_filtered_tfm_nn,
                             adjoint_b = True # transpose second matrix
                             )
            ws = tf.multiply(result, frequencies_vec)
            mean = tf.reduce_sum(ws, 1)/tf.reduce_sum(frequencies_vec)
            mean = sess.run([mean])

        return mean

    def compute_document_kurtosis_with_tf(self, document, corpus_mean, filter_stopword = True, min_freq = 10):
        terms_filtered, frequencies_filtered, _ =  self._prepare_matrix_computation(document, filter_stopword, min_freq)  
        import tensorflow as tf        
        tf.reset_default_graph()
        with tf.Session() as sess:
            self.axes_tfm_nn = tf.nn.l2_normalize(tf.constant(self.axes_mat), axis = 1)    
            frequencies_vec = tf.constant(frequencies_filtered, dtype=np.float32)
            term_filtered_tfm_nn = tf.nn.l2_normalize(tf.constant(np.array(terms_filtered)), axis = 1)

            result = tf.matmul(self.axes_tfm_nn, term_filtered_tfm_nn,
                             adjoint_b = True # transpose second matrix
                             )
            ws = tf.multiply(result, frequencies_vec)
            # mean = tf.reduce_sum(ws, 1)/tf.reduce_sum(frequencies_vec)
            mean = tf.constant(corpus_mean, dtype=np.float32)
            # ss = tf.reduce_sum(tf.multiply(tf.square(result), frequencies_vec), 1)/tf.reduce_sum(frequencies_vec)
            # ms = tf.square(mean)
            # std = tf.sqrt(ss-ms)
            diff = result-tf.reshape(mean, [-1,1])
            moment4 = tf.reduce_sum(tf.multiply(tf.pow(diff, 4), frequencies_vec), 1)/tf.reduce_sum(frequencies_vec)
            moment2 = tf.reduce_sum(tf.multiply(tf.pow(diff, 2), frequencies_vec), 1)/tf.reduce_sum(frequencies_vec)
            kurtosis = moment4 / tf.square(moment2) - 3    
            kurtosis = sess.run([kurtosis])

        return sorted(self.axes.keys()), kurtosis

    def compute_document_second_moment_with_tf(self, document, corpus_mean, filter_stopword = True, min_freq = 10):
        terms_filtered, frequencies_filtered, _ =  self._prepare_matrix_computation(document, filter_stopword, min_freq)  
        import tensorflow as tf        
        tf.reset_default_graph()
        with tf.Session() as sess:
            self.axes_tfm_nn = tf.nn.l2_normalize(tf.constant(self.axes_mat), axis = 1)    
            frequencies_vec = tf.constant(frequencies_filtered, dtype=np.float32)
            term_filtered_tfm_nn = tf.nn.l2_normalize(tf.constant(np.array(terms_filtered)), axis = 1)

            result = tf.matmul(self.axes_tfm_nn, term_filtered_tfm_nn,
                             adjoint_b = True # transpose second matrix
                             )
            ws = tf.multiply(result, frequencies_vec)
            # mean = tf.reduce_sum(ws, 1)/tf.reduce_sum(frequencies_vec)
            # if corpus_mean:
            mean = tf.constant(corpus_mean, dtype=np.float32)
            # else:
            #     mean = tf.reduce_sum(ws, 1)/tf.reduce_sum(frequencies_vec)
                
            # ss = tf.reduce_sum(tf.multiply(tf.square(result), frequencies_vec), 1)/tf.reduce_sum(frequencies_vec)
            # ms = tf.square(mean)
            # std = tf.sqrt(ss-ms)
            diff = result-tf.reshape(mean, [-1,1])
            # moment4 = tf.reduce_sum(tf.multiply(tf.pow(diff, 4), frequencies_vec), 1)/tf.reduce_sum(frequencies_vec)
            moment2 = tf.reduce_sum(tf.multiply(tf.pow(diff, 2), frequencies_vec), 1)/tf.reduce_sum(frequencies_vec)
            # kurtosis = moment4 / tf.square(moment2) - 3    
            moment2 = sess.run([moment2])

        return moment2
    

    def word_contribution(self, document, axis, filter_stopword = True, min_freq = 10):
        terms_filtered, frequencies_filtered, words =  self._prepare_matrix_computation(document, filter_stopword, min_freq)  
        axis_mat = np.array([self.axes[axis]])
        import tensorflow as tf        
        tf.reset_default_graph()
        with tf.Session() as sess:
            axis_tfm_nn = tf.nn.l2_normalize(tf.constant(axis_mat), axis = 1)

            frequencies_vec = tf.constant(frequencies_filtered, dtype=np.float32)
            term_freq_tfm_nn = tf.nn.l2_normalize(tf.constant(np.array(terms_filtered)), axis = 1)
            result = tf.matmul(axis_tfm_nn, term_freq_tfm_nn,
                             adjoint_b = True # transpose second matrix
                             )
            ws = tf.multiply(result, frequencies_vec)
            contrib = ws/tf.reduce_sum(frequencies_vec)
            contrib = sess.run([contrib])
        return contrib, words


    def word_contribution_with_mask(self, document, axis, filter_stopword = True, min_freq = 10, mask_percent = 5):
        terms_filtered, frequencies_filtered, words =  self._prepare_matrix_computation(document, filter_stopword, min_freq)  
        axis_mat = np.array([self.axes[axis]])
        import tensorflow as tf        
        tf.reset_default_graph()
        with tf.Session() as sess:
            axis_tfm_nn = tf.nn.l2_normalize(tf.constant(axis_mat), axis = 1)
            frequencies_vec = tf.constant(frequencies_filtered, dtype=np.float32)
            term_freq_tfm_nn = tf.nn.l2_normalize(tf.constant(np.array(terms_filtered)), axis = 1)

            test = tf.matmul(axis_tfm_nn, term_freq_tfm_nn,
                             adjoint_b = True # transpose second matrix
                             )
            result, masked_frequencies_tsr = self._apply_mask(test, frequencies_vec, mask_percent)

            ws = tf.multiply(result, masked_frequencies_tsr)
            contrib = ws/tf.reduce_sum(masked_frequencies_tsr, 1)
            contrib = sess.run([contrib])
        return contrib, words        




    def word_contribution_to_second_moment(self, document, axis, corpus_mean, filter_stopword = True, min_freq = 10):
        terms_filtered, frequencies_filtered, words =  self._prepare_matrix_computation(document, filter_stopword, min_freq)  
        axis_mat = np.array([self.axes[axis]])
        import tensorflow as tf        
        tf.reset_default_graph()
        with tf.Session() as sess:
            axis_tfm_nn = tf.nn.l2_normalize(tf.constant(axis_mat), axis = 1)
            frequencies_vec = tf.constant(frequencies_filtered, dtype=np.float32)
            term_freq_tfm_nn = tf.nn.l2_normalize(tf.constant(np.array(terms_filtered)), axis = 1)

            result = tf.matmul(axis_tfm_nn, term_freq_tfm_nn,
                             adjoint_b = True # transpose second matrix
                             )
            ws = tf.multiply(result, frequencies_vec)
            mean = tf.constant(corpus_mean, dtype=np.float32)
            # else:
            #     mean = tf.reduce_sum(ws, 1)/tf.reduce_sum(frequencies_vec)
                
            # ss = tf.reduce_sum(tf.multiply(tf.square(result), frequencies_vec), 1)/tf.reduce_sum(frequencies_vec)
            # ms = tf.square(mean)
            # std = tf.sqrt(ss-ms)
            diff = result-tf.reshape(mean, [-1,1])
            # moment4 = tf.reduce_sum(tf.multiply(tf.pow(diff, 4), frequencies_vec), 1)/tf.reduce_sum(frequencies_vec)
            contrib = tf.multiply(tf.pow(diff, 2), frequencies_vec)/tf.reduce_sum(frequencies_vec)
            # kurtosis = moment4 / tf.square(moment2) - 3    
            contrib = sess.run([contrib])
        return contrib, words     