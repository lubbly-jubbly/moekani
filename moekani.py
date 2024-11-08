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

def get_db_conn(output_path):
    extracted_path = output_path + "/collection.anki2"
    return connect_to_db(extracted_path)

def print_model_data(cursor):
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
    cursor.execute("SELECT ntid, name, ord FROM fields WHERE ntid IN (?, ?, ?)", (wanikani_kanji_model_id, wanikani_vocab_model_id, moe_model_id))
    fields_data = cursor.fetchall()

    # Sort by ord
    fields_data = sorted(fields_data, key=lambda x: x[2])

    wanikani_kanji_field_names = []
    wanikani_vocab_field_names = []
    moe_field_names = []

    for ntid, name, ord in fields_data:
        if str(ntid) == wanikani_kanji_model_id:
            wanikani_kanji_field_names.append(name)
        elif str(ntid) == wanikani_vocab_model_id:
            wanikani_vocab_field_names.append(name)
        elif str(ntid) == moe_model_id:
            moe_field_names.append(name)

    return wanikani_kanji_field_names, wanikani_vocab_field_names, moe_field_names
    
def get_card_data_for_model(cursor, model_id, models):
    cursor.execute("SELECT id, mid, flds FROM notes WHERE mid=?", (model_id,))
    # cursor.execute("SELECT id, mid, flds FROM notes")

    notes = cursor.fetchall()
    model_data = models[model_id]
    field_names = [field['name'] for field in model_data['flds']]

    return [notes, field_names]

def get_notes_for_model(cursor, model_id):
    cursor.execute("SELECT id, mid, flds FROM notes WHERE mid=?", (model_id,))
    notes = cursor.fetchall()
    return notes

def format_card_data(notes, field_names):
    cards = []
    for note in notes:
        note_id = note[0]
        fields_data = note[2].split('\x1f') 
        note_fields = dict(zip(field_names, fields_data))
        note_fields['note_id'] = note_id

        cards.append(note_fields)

    return cards

def get_cards_for_model(cursor, model_id, field_names):
    notes = get_notes_for_model(cursor, model_id)
    return format_card_data(notes, field_names)

def get_all_notes(cursor):
    cursor.execute("SELECT id, mid, flds FROM notes")
    notes = cursor.fetchall()
    return notes

def print_all_table_fields(cursor):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    for table in tables:
        table_name = table[0]
        print(f"\nTable: {table_name}")
        
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        for column in columns:
            print(f"Column Name: {column[1]}, Type: {column[2]}")

def print_table_data(cursor, table_name):
    cursor.execute(f"SELECT * FROM {table_name}")
    column_names = [description[0] for description in cursor.description]
    decks_data = cursor.fetchall()
    for deck in decks_data:
        # Print field names and values together
        print(dict(zip(column_names, deck)))

wanikani_deck_path = "/Users/libbyrear/Documents/moekani decks/Wanikani.apkg"
moe_deck_path =  "/Users/libbyrear/Documents/moekani decks/TheMoeWay.apkg"
# output_path = "/Users/libbyrear/Documents/bucket/wanikani"
output_path = "/Users/libbyrear/Library/Application Support/Anki2 copy/User 1"
wanikani_output_path = output_path + "wanikani"
moe_output_path = output_path + "moe"

conn = get_db_conn(output_path)

cursor = conn.cursor()

# 2. Fetching deck models from database

wanikani_kanji_model_id = '1411914227416'
wanikani_vocab_model_id = '1413076182153'
moe_model_id = '1535432904222'

cursor.execute("SELECT ntid, name, ord FROM fields WHERE ntid IN (?, ?, ?)", (wanikani_kanji_model_id, wanikani_vocab_model_id, moe_model_id))
fields_data = cursor.fetchall()

# Sort by ord
fields_data = sorted(fields_data, key=lambda x: x[2])

wanikani_kanji_field_names = []
wanikani_vocab_field_names = []
moe_field_names = []

for ntid, name, ord in fields_data:
    if str(ntid) == wanikani_kanji_model_id:
        wanikani_kanji_field_names.append(name)
    elif str(ntid) == wanikani_vocab_model_id:
        wanikani_vocab_field_names.append(name)
    elif str(ntid) == moe_model_id:
        moe_field_names.append(name)
# print_decks_table_data(cursor)
# print_table_data(cursor, 'notes')
# 3. Fetching cards from database

# print_all_table_fields(cursor)
wanikani_kanji_cards = get_cards_for_model(cursor, wanikani_kanji_model_id, wanikani_kanji_field_names)
wanikani_vocab_cards = get_cards_for_model(cursor, wanikani_vocab_model_id, wanikani_vocab_field_names)
moe_cards = get_cards_for_model(cursor, moe_model_id, moe_field_names)

# 4. Find kanji

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


#  Add 'sort' field to wanikani decks

def add_sort_field_to_wanikani_model(model_id, field_names):
    ntid = int(model_id)
    name = "sort"
    ord = len(field_names)
    default_config = b'\x1a\x08Segoe UI \x10\xfa\x0f\x0c{"media":[]}'

    # cursor.execute(f"SELECT * FROM fields")
    # # column_names = [description[0] for description in cursor.description]
    # fields_data = cursor.fetchall()
    # print(fields_data)
    # fields_data.append('')

    # cursor.execute("INSERT INTO FIELDS (ntid, ord, name, config) VALUES (?, ?, ?, ?)", (ntid, ord, name, default_config))
    return

def add_sort_field_to_wanikani_notes(card_ids_ordered, field_names):
# Loop through the note_ids and update their 'sort' field
    for sort_index, note_id in enumerate(card_ids_ordered):
        # Fetch the existing fields for the note
        cursor.execute("SELECT flds FROM notes WHERE id = ?", (note_id,))
        note = cursor.fetchone()
        if note:
            fields_data = note[0].split('\x1f')  # Split the fields by the separator
            # Check if the 'sort' field exists; if not, we need to add it
            if len(fields_data) < len(field_names) + 1:
                fields_data.append('')  # Add an empty field if it's missing

            # Update the 'sort' field (last field in the list)
            fields_data[-1] = str(sort_index) 

            # Recombine the fields and update the note
            updated_fields = '\\x1f'.join(fields_data) | ''

            cursor.execute("UPDATE notes SET flds = ? WHERE id = ?", (updated_fields, note_id))

# add_sort_field_to_wanikani_model(wanikani_kanji_model_id, wanikani_kanji_field_names)
add_sort_field_to_wanikani_notes(wanikani_kanji_card_ids_ordered, wanikani_kanji_field_names)
notes = get_all_notes(cursor)
# notes2 = get_notes_for_model(wanikani_vocab_model_id)
conn.commit()
# print_table_data(cursor, 'notes')
cards = get_notes_for_model(cursor, wanikani_kanji_model_id)
print(cards[0:5])
# print_all_table_fields(cursor)
# print_table_data(cursor, 'fields')
# print(cards[0:6])
# def add_sort_field_to_wanikani_deck(model_id, card_ids_ordered):
#     model = wanikani_models[model_id]

#     field_names = [field['name'] for field in model['flds']]

#     add_sort_field_to_wanikani_model(model_id, model, field_names)
#     add_sort_field_to_wanikani_notes(card_ids_ordered, field_names)

#     cards = get_cards_for_model(wanikani_cursor, wanikani_kanji_model_id, wanikani_models)
#     print(cards[0:6])
#     wanikani_conn.commit()


# add_sort_field_to_wanikani_deck(wanikani_kanji_model_id, wanikani_kanji_card_ids_ordered)
