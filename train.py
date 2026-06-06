import spacy
import json
import random
from spacy.tokens import DocBin
from spacy.training import Example

def prepare_data(data_path, output_path):
    """Convierte el JSON en el formato binario que SpaCy entiende."""
    nlp = spacy.blank("es")  # Modelo en español
    textcat = nlp.add_pipe("textcat")
    
    with open(data_path, 'r') as f:
        data = json.load(f)

    for item in data:
        doc = nlp.make_doc(item["text"])
        cats = {label: 0.0 for label in ["STOCK_QUERY", "SALES_QUERY", "CONFIG_CHANGE"]}
        cats[item["label"]] = 1.0
        doc.cats = cats
        
    # Guardar para entrenamiento
    db = DocBin()
    for item in data:
        doc = nlp.make_doc(item["text"])
        cats = {label: 0.0 for label in ["STOCK_QUERY", "SALES_QUERY", "CONFIG_CHANGE"]}
        cats[item["label"]] = 1.0
        doc.cats = cats
        db.add(doc)
    db.to_disk(output_path)
    print(f"Datos preparados en: {output_path}")

if __name__ == "__main__":
    prepare_data("data/data.json", "train.spacy")
