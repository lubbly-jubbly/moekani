import sqlite3
import zipfile 
import json
import re

# 1. Extract decks and connect to the db for each deck

def extract_apkg(apkg_path, output_dir):
    with zipfile.ZipFile(apkg_path, 'r') as zip_ref:
        zip_ref.extractall(output_dir)

def connect_to_db(db_path):
    conn = sqlite3.connect(db_path)
    return conn

def get_db_cursor(deck_path, output_path):
    extract_apkg(deck_path, output_path)

    extracted_path = output_path + "/collection.anki2"

    conn = connect_to_db(extracted_path)

    return conn.cursor()

def get_models_readable(cursor):
    cursor.execute("SELECT models FROM col")
    models_json = cursor.fetchone()[0]

    models = json.loads(models_json)

    for model_id, model_data in models.items():
        model_name = model_data['name']
        fields = model_data['flds']
        field_names = [field['name'] for field in fields]

        print(f"Model: {model_name}")
        print(f"ID: {model_id}")
        print(f"Field Names: {field_names}")
        print("---")

def get_models(cursor):
    cursor.execute("SELECT models FROM col")
    models_json = cursor.fetchone()[0] 

    return json.loads(models_json)

def get_model_id_from_model_name(model_name, models):
    model_id = None
    for model_id, model_data in models.items():
        if model_data['name'] == model_name:
            return model_id
    if model_id is None:
        raise ValueError("Model named {model_name} not found!")
    
def get_card_data_for_model(cursor, model_id, models):
    cursor.execute("SELECT id, mid, flds FROM notes WHERE mid=?", (model_id,))
    # cursor.execute("SELECT id, mid, flds FROM notes")

    notes = cursor.fetchall()
    model_data = models[model_id]
    field_names = [field['name'] for field in model_data['flds']]

    return [notes, field_names]

def format_card_data(notes, field_names):
    cards = []
    print(notes)
    for note in notes:
        note_id = note[0]
        fields_data = note[2].split('\x1f') 
        note_fields = dict(zip(field_names, fields_data))
        note_fields['note_id'] = note_id

        cards.append(note_fields)

    return cards

def get_cards_for_model(cursor, model_name, models):
    model_id = get_model_id_from_model_name(model_name, models)
    [notes, field_names] = get_card_data_for_model(cursor, model_id, models)
    return format_card_data(notes, field_names)

def get_all_notes(cursor):
    cursor.execute("SELECT id, mid, flds FROM notes")
    notes = cursor.fetchall()
    return notes


wanikani_deck_path = "/Users/libbyrear/Documents/moekani decks/Wanikani.apkg"
moe_deck_path =  "/Users/libbyrear/Documents/moekani decks/TheMoeWay.apkg"
output_path = "/Users/libbyrear/Documents/bucket/"
wanikani_output_path = output_path + "wanikani"
moe_output_path = output_path + "moe"

wanikani_cursor = get_db_cursor(wanikani_deck_path, wanikani_output_path)
moe_cursor = get_db_cursor(moe_deck_path, moe_output_path)

# 2. Fetching wanikani deck from database 
wanikani_models = get_models(wanikani_cursor)

wanikani_kanji_cards = get_cards_for_model(wanikani_cursor, 'Japanese - WK - Kanji', wanikani_models)
wanikani_vocab_cards = get_cards_for_model(wanikani_cursor, 'Japanese - WK - Vocab', wanikani_models)

# 3. Fetching Moe Way deck from database
moe_models = get_models(moe_cursor)

moe_cards = get_cards_for_model(moe_cursor, 'Tango Card Format', moe_models)
print(moe_cards)
# 4. 

def find_kanji(expression):
    kanji_pattern = re.compile(r'[\u4E00-\u9FFF]')
    return kanji_pattern.findall(expression)

kanji_ordered = []
for card in moe_cards:
    kanji_in_card = find_kanji(card['Expression'])
    for kanji in kanji_in_card:
        kanji_ordered.append(kanji)
    
kanji_ordered_unique = list(dict.fromkeys(kanji_ordered))

# Find the order of the wanikani deck corresponding to the kanji order
wanikani_kanji_card_ids_ordered = []

for kanji in kanji_ordered_unique:
    for card in wanikani_kanji_cards:
        if card['Kanji'] == kanji:
            wanikani_kanji_card_ids_ordered.append(card['note_id'])
            break

# Order the wanikani deck using the order obtained

# ??????????
# 