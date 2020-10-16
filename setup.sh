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

echo "Download stuff"

fileid="1DuxqfFluLo_eMqY6PHZPJ2ePngz8C90y"
filename="char_vocab.txt"
curl -c ./cookie -s -L "https://drive.google.com/uc?export=download&id=${fileid}" > /dev/null
curl -Lb ./cookie "https://drive.google.com/uc?export=download&confirm=`awk '/download/ {print $NF}' ./cookie`&id=${fileid}" -o ${filename}
rm cookie
mv char_vocab.txt ext/e2e/data/char_vocab.txt

cd ext
./load_java_dependencies.sh
echo "Download embeddings to data, char_vocab.txt and model to logs"
echo "Download Mate-Tools Model https://docs.google.com/uc?export=download&id=0B-qbj-8rtoUMLUg5NGpBVW9JNkE and place it into ext/mate-model/parser-ger.model" 
echo "Go to folder ext/e2e and run setup_all.sh, edit script for macOS"