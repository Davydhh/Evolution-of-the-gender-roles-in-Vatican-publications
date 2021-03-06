import nltk
import spacy
import pickle
import matplotlib.pyplot as plt
import pandas as pd

from nltk.corpus import wordnet
from collections import defaultdict
from math import log
from gensim.models import Word2Vec
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import PCA

class Model:
    def __init__(self, data):
        self.data = data
        self.nlp = spacy.load("en_core_web_sm")
        self.woman_dict = ["female", "girl", "woman", "she", "sister", "mother", "mrs", "her", "nun", "daughter", "lady"]
        self.man_dict = ["male", "boy", "man", "he", "brother", "father", "mr", "his", "priest", "son"]

    def tokenize(self):
        self.parsed_data = []
        for d in self.data:
            text = [token.lemma_.lower() for token in self.nlp(d["text"])]
            self.parsed_data.append({"_id": d["_id"], "text": text, "pope": d["pope"], "year": int(d["year"])})

    def get_syns(self, dictionary):
        result = set()
        for w in dictionary:
            syns = wordnet.synsets(w)
            for s in syns:
                result.add(s.lemmas()[0].name().lower())
        return list(result)

    def count_words(self, dictionary, with_freq=False):
        counter = defaultdict(lambda: 0)
        for d in self.parsed_data:
            for w in dictionary:
                text = d["text"]
                count = text.count(w)
                if not with_freq:
                    counter[d["year"]] += count
                else:
                    # Use Laplace smoothing
                    counter[d["year"]] += log((count + 1) / (len(text) + len(set(text))))
        return counter

    def my_div(self, n, d):
        return n / d if d else n

    def get_ratio(self):
        ratios = []
        for y in self.woman_occurrences.keys():
            woman_occ = self.woman_occurrences[y]
            man_occ = self.man_occurrences[y]
            # print("For year {} woman occurrences are {} while man occurrences are {}".format(y, woman_occ, man_occ))
            ratio = round(self.my_div(man_occ, woman_occ))
            # print("The ration between man and woman occurences are {}".format(ratio), '\n')
            ratios.append(ratio)
        return ratios

    def plot_data(self, suptitle):
        plt.figure().tight_layout()
        plt.subplot(221)
        plt.plot(self.woman_occurrences.keys(), self.woman_occurrences.values(), color="red")
        plt.xlabel("years")
        plt.ylabel("occurrences")
        plt.title("Woman")
        plt.subplot(222)
        plt.plot(self.man_occurrences.keys(), self.man_occurrences.values())
        plt.xlabel("years")
        plt.ylabel("occurrences")
        plt.title("Man")
        plt.subplot(223)
        plt.plot(self.woman_occurrences.keys(), self.woman_occurrences.values(), color="red")
        plt.plot(self.woman_occurrences.keys(), self.man_occurrences.values())
        plt.xlabel("years")
        plt.ylabel("occurrences")
        plt.title("Man and Woman")
        plt.subplot(224)
        plt.plot(self.woman_occurrences.keys(), self.ratios, color="purple")
        plt.xlabel("years")
        plt.ylabel("ratio")
        plt.title("Ratio man-woman")
        plt.suptitle(suptitle)

        # plt.show()

    def generate_training_data(self):
        training_data = []
        for d in self.data:
            sentences = nltk.tokenize.sent_tokenize(d["text"])
            text = [[token.lemma_ for token in self.nlp(s) if token.lemma_.isalpha()] for s in sentences]
            training_data.extend(text)

        return training_data

    def get_most_similar(self, dictionary):
        most_similar = {}
        for word in dictionary:
            try:
                most_similar[word] = [w[0] for w in self.model.wv.most_similar(positive=word, topn=3)]
            except KeyError:
                pass

        return most_similar

    def scatter_words(self, dictionary, result, words, suptitle, title):
        for k, v in dictionary.items():
            if v[0] in words:
                index = self.model.wv.get_index(v[0])
                p1 = plt.scatter(result[index, 0], result[index, 1], c="b", marker=',')
                plt.annotate(v[0], xy=(result[index, 0], result[index, 1]))
            if k in words:
                index = self.model.wv.get_index(k)
                p2 = plt.scatter(result[index, 0], result[index, 1], s=80, c='r')
                plt.annotate(k, xy=(result[index, 0], result[index, 1]))
        plt.suptitle(suptitle)
        plt.title(title)
        plt.legend((p1, p2), ("most similar", "word"), loc='upper left', fontsize=8)

    def visualize_words(self, result, words):
        plt.figure().tight_layout()
        plt.subplot(121)
        self.scatter_words(self.woman_most_similar, result, words, "Word Embeddings representation", "Woman words")
        plt.subplot(122)
        self.scatter_words(self.man_most_similar, result, words, "Word Embeddings representation", "Man words")
            
        plt.show()

    def get_names(self):
        names = list({ent.text for d in self.data for ent in self.nlp(d["text"]).ents if ent.label_ == "PERSON"})

        for i, name in enumerate(names):
            if " " in name:
                words = name.split()
                names[i] = words[0]

        self.names = names

    def get_gender_names(self):
        df = pd.read_csv("dataset\\NationalNames.csv").drop(["Id", "Year", "Count"], axis=1)

        x = df["Name"]
        cv = CountVectorizer().fit(x)

        gender_model = pickle.load(open("models\\Multinomial Naive Bayes.sav", 'rb'))

        prediction = gender_model.predict(cv.transform(self.names).toarray())

        self.male_names = [self.names[i] for i, p in enumerate(prediction) if p == "M"]
        self.female_names = [self.names[i] for i, p in enumerate(prediction) if p == "F"]

    def word_embeddings(self):
        training_data = self.generate_training_data()
        self.model = Word2Vec(training_data, sg=1)
        
        self.woman_most_similar = self.get_most_similar(self.woman_dict)
        self.man_most_similar = self.get_most_similar(self.man_dict)

        woman_df = pd.DataFrame.from_dict(self.woman_most_similar, orient="index")
        man_df = pd.DataFrame.from_dict(self.man_most_similar, orient="index")

        # Visualize Word Embeddings
        X = self.model.wv.vectors
        pca = PCA(n_components=2)
        result = pca.fit_transform(X)
        words = list(self.model.wv.index_to_key)

        self.visualize_words(result, words)

        # Named Entity Recognition
        self.get_names()
        self.get_gender_names()

        self.female_name_most_similar = self.get_most_similar(self.female_names)
        self.male_name_most_similar = self.get_most_similar(self.male_names)

        female_name_df = pd.DataFrame.from_dict(self.female_name_most_similar, orient="index")
        male_name_df = pd.DataFrame.from_dict(self.male_name_most_similar, orient="index")

        print(woman_df, '\n')
        print(man_df, '\n')
        print(female_name_df, '\n')
        print(male_name_df, '\n')

    def run(self):
        # Tokenize and lemmatize corpus
        self.tokenize()

        self.woman_dict.extend(self.get_syns(self.woman_dict))
        self.man_dict.extend(self.get_syns(self.man_dict))

        # Basic word counter
        self.woman_occurrences = self.count_words(self.woman_dict)
        self.man_occurrences = self.count_words(self.man_dict)

        self.ratios = self.get_ratio()

        self.plot_data("Basic occurrences counter")

        ### Language Models
        ## Basics
        # Log probabilities with Laplace Smoothing
        self.woman_occurrences = self.count_words(self.woman_dict, with_freq=True)
        self.man_occurrences = self.count_words(self.man_dict, with_freq=True)

        self.ratios = self.get_ratio()

        self.plot_data("Occurrences with relative frequency")

        ## Word Embeddings
        self.word_embeddings()