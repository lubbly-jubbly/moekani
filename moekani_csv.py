
import sqlite3
import zipfile 
import json
import re
import csv 

# Steps to work this script:
# 1. Add field to anki: Browse > Fields... > Add > Moe_Sort_Order (or whatever you want to call it) > Ok
# 2. Export anki notes as text file: File > Export... > Export format: Notes in plain text (.txt), Include: [WaniKani deck], tick all boxes > Export... > Any folder
# 3. Import text file to google sheets: File > Import > Separator Type: Tab
# 4. Export as csv: File > Download > csv. Save to wanikani_kanji_csv_path
# 5. Run script (uncomment desired function call)
# 6. Check all good with WaniKani_Vocab_New.csv / WaniKani_Kanji_New.csv
# 7. In anki, go to file > Import... > Choose file > 
#   Field separator: comma
#   Choose correct Notetype and Deck
#   Check fields
#   Add Tags field which is empty for some reason
#   Check that Existing Notes: Update
#   > Import. It should say X cardsfound in existing notes were updated.
# 8. Go to Browse for deck. Add new Moe_Sort_Order field to the browse table columns, and click to sort by it in ascending order.
# 9. Save the deck in this order: Cmd A (select all cards) > Cards > Reposition... > 
#   Leave Randomise order unticked and Shift position of existing cards ticked. > Ok



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


moe_deck_path =  "/Users/libbyrear/Documents/moekani decks/TheMoeWay.apkg"
wanikani_kanji_csv_path = "/Users/libbyrear/Documents/moekani decks/WaniKani_Kanji.csv"
wanikani_kanji_csv_output_path = "/Users/libbyrear/Documents/moekani decks/output/WaniKani_Kanji_New.csv"
wanikani_vocab_csv_path = "/Users/libbyrear/Documents/moekani decks/WaniKani_Vocab.csv"
wanikani_vocab_csv_output_path = "/Users/libbyrear/Documents/moekani decks/output/WaniKani_Vocab_New.csv"
moe_output_path = "/Users/libbyrear/Documents/moekani decks/output/moe"

# Get wankikani kanji csv as list
def open_csv_as_list(path):
    with open(path, newline='') as f:
        reader = csv.reader(f)
        return list(reader)

wanikani_kanji_cards = open_csv_as_list(wanikani_kanji_csv_path)
wanikani_vocab_cards = open_csv_as_list(wanikani_vocab_csv_path)

# Get moe cards
moe_cursor = get_db_cursor(moe_deck_path, moe_output_path)
moe_models = get_models(moe_cursor)
moe_cards = get_cards_for_model(moe_cursor, 'Tango Card Format', moe_models)

# Find the kanji in moe deck
def find_kanji(expression):
    kanji_pattern = re.compile(r'[\u4E00-\u9FFF]')
    return kanji_pattern.findall(expression)

# Find the kanji combos in moe deck
def find_kanji_combos(expression):
        kanji_pattern = re.compile(r'[\u4E00-\u9FFF]+')
        kanji_matches = kanji_pattern.findall(expression)
        return list(set(kanji_matches))

def add_sort_field_to_kanji_csv():
    wanikani_kanji_cards = open_csv_as_list(wanikani_kanji_csv_path)

    # Find the kanji in the moe deck, ordered by appearance in moe deck
    kanji_ordered = []
    for card in moe_cards:
        kanji_in_card = find_kanji_combos(card['Expression'])
        for kanji in kanji_in_card:
            kanji_ordered.append(kanji)
        
    kanji_ordered_unique = list(dict.fromkeys(kanji_ordered))

    # Find the desired order of the wanikani deck corresponding 
    # to the kanji order of appearance in moe deck
    wanikani_kanji_card_ids_ordered = []
    for kanji in kanji_ordered_unique:
        for card in wanikani_kanji_cards:
            if card[3] == kanji:
                wanikani_kanji_card_ids_ordered.append(card[0])
                break

    add_sort_field_to_card_list(wanikani_kanji_cards, wanikani_kanji_card_ids_ordered)

    export_to_csv(wanikani_kanji_csv_output_path, wanikani_kanji_cards)

def add_sort_field_to_vocab_csv():
    wanikani_vocab_cards = open_csv_as_list(wanikani_vocab_csv_path)

    def trim_kana(phrase):
        return re.sub(r'^[\u3040-\u30FFー〜]+|[\u3040-\u30FFー〜]+$', '', phrase)

    for wanikani_card in wanikani_vocab_cards[6:len(wanikani_vocab_cards)]:
        trimmed_vocab = trim_kana(wanikani_card[3])
        for moe_card_index, moe_card in enumerate(moe_cards):
            # Use regex to ensure trimmed_vocab is surrounded only by kana, not kanji (and thus likely part of a larger word)
            pattern = fr'(?:[^\u4E00-\u9FFF]|^){re.escape(trimmed_vocab)}(?:[^\u4E00-\u9FFF]|$)'
            if re.search(pattern, moe_card['Expression']):
                wanikani_card[-2] = moe_card_index
                break
        # If wanikani vocab word not found in moe deck, assign it a high sort number
        if wanikani_card[-2] == '':
            wanikani_card[-2] = len(wanikani_vocab_cards)
        # Delete the id etc fields (which are not anki card fields)
        del wanikani_card[:3]
  
    export_to_csv(wanikani_vocab_csv_output_path, wanikani_vocab_cards)

def add_sort_field_to_card_list(cards, ordered_card_ids):
    for card in cards[6:len(cards)]:
        card_id = card[0]
        sort_index = ordered_card_ids.index(card_id) if card_id in ordered_card_ids else len(cards)
        card[-2] = sort_index
        del card[:3]

def export_to_csv(output_path, card_list):
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(card_list)

add_sort_field_to_vocab_csv()
# add_sort_field_to_kanji_csv()