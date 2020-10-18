if [ ! -d "ext/e2e" ] 
then
    git clone https://github.com/ChristianHesels/e2e-german.git
    mv e2e-german ext/e2e
fi
if [ ! -d "ext/CorZu_v2.0" ]
then
    git clone https://github.com/ChristianHesels/CorZu.git
    mv CorZu ext/CorZu_v2.0
fi
if [ ! -d "ext/e2e/evaluate/scorer" ]
then
    git clone https://github.com/conll/reference-coreference-scorers.git
    mv reference-coreference-scorers ext/e2e/evaluate/scorer
fi
python3 -c "import nltk; nltk.download('punkt')"
mkdir -p ext/e2e/data
mkdir -p ext/e2e/logs
mkdir -p ext/e2e/logs/props
echo "Download stuff"

fileid="1DuxqfFluLo_eMqY6PHZPJ2ePngz8C90y"
filename="char_vocab.txt"
curl -c ./cookie -s -L "https://drive.google.com/uc?export=download&id=${fileid}" > /dev/null
curl -Lb ./cookie "https://drive.google.com/uc?export=download&confirm=`awk '/download/ {print $NF}' ./cookie`&id=${fileid}" -o ${filename}
rm cookie
mv char_vocab.txt ext/e2e/data/char_vocab.txt
pip3 install -r requirements.txt
cd ext
./load_java_dependencies.sh
cd e2e
pip3 install -r requirements.txt
echo "Download E2E-German Model:"
echo "https://drive.google.com/file/d/1L-kKxzlC0pPr_tJzRyi9xoTOKSPQXfNb/view?usp=sharing"
echo "Extract and move 'final' content to ext/e2e/logs/props"
echo "--------------------------------"
echo "Download GloVe Word Embeddings:"
echo "https://drive.google.com/file/d/1nN_qc3qHtPecxek0LsYf544ipJpfXEfj/view?usp=sharing"
echo "Extract and move to ext/e2e/data"