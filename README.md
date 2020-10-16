
# Contextual PropsDE

What is Contextual PropsDE?
------------
Contextual PropsDE is an extension to PropsDE. 
Instead of creating relations of each sentence, it uses E2E-German or CorZu for Coreference-Resolution and maps the coreferences to the antities to create a knowledge graph. This knowledge graph is saved to a Neo4j Graph database, where it can be used for information retrieval.

[PropsDE](https://github.com/UKPLab/props-de)

[original English version](https://github.com/gabrielStanovsky/props) 

[online demo for English and German](http:/www.cs.biu.ac.il/~stanovg/props.html)  

Contact person: Christian Hesels, s0553310@htw-berlin.de


> This repository contains experimental software and is published for the sole purpose of giving additional background details on the respective publication. 


Prerequisites
-------------

* python >= 3 (tested with 3.6.9)
* java >= 7 (JAVA_HOME has to be set)
* pip3 >= 9
* docker >= 19

Installation
------------

1. Clone this repository and navigate into the root folder.

        git clone https://github.com/ChristianHesels/contextual-props-de.git
		cd contextual-props-de

2. Run the setup Script to install all dependencies and python requirements.

		./setup.sh
		
3. Download the GloVe Word Embeddings and copy them into ext/e2e/data (2.5 GB) (Only for E2E-German).

		https://drive.google.com/file/d/1nN_qc3qHtPecxek0LsYf544ipJpfXEfj/view?usp=sharing
	
		
4. Download the trained E2E-German model (650 MB) and copy it to ext/e2e/logs with the name props (Only for E2E-German).

		https://drive.google.com/file/d/1L-kKxzlC0pPr_tJzRyi9xoTOKSPQXfNb/view?usp=sharing



Running
-------------

First start the Dependency Parser ParZu and the Neo4j Database with Docker:

- *docker-compose build* (first time)
- *docker-compose up* (first time)

Then start the python3 script with the coreference-resolution system you want to use (corzu or e2e):

- *props_corzu_e2e.py corzu*
- *props_corzu_e2e.py e2e*

E2E-German takes a longer time to load and needs at least 16 GB of RAM, because of the large word embeddings. The props_corzu_e2e.py Script is used for test purposes only, because E2E-German needs Elmo-Embeddings for it's full potential. Elmo can be trained with *https://github.com/ChristianHesels/bilm-tf* and used with the seperate implementation of E2E-German *https://github.com/ChristianHesels/e2e-german*.

