import sqlite3
import spacy
from sqlite3 import Error
from numpy.linalg import norm
import numpy as np
from sentence_transformers import SentenceTransformer
import sys

class LazyLoader:
    def __init__(self):
        self._nlp = None
        self._model = None

    @property
    def nlp(self):
        if self._nlp is None:
            import spacy
            self._nlp = spacy.load('en_core_web_md')
        return self._nlp

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer('all-MiniLM-L6-v2')#multi-qa-mpnet-base-dot-v1
        return self._model

lazy_loader = LazyLoader()

def create_connection():
    conn = None
    try:
        conn = sqlite3.connect('BotData/chatlog.sqlite')
        print(sqlite3.version)
    except Error as e:
        print(f"Error occurred: {e}")
        raise  # Re-raise the exception so it can be handled elsewhere
    if not conn:
        raise Exception("Failed to create a database connection.")
    return conn

def create_table(conn):
    try:
        sql = ''' CREATE TABLE IF NOT EXISTS chat_history (
                                          id integer PRIMARY KEY,
                                          timestamp text NOT NULL,
                                          sender text NOT NULL,
                                          message text NOT NULL,
                                          vector text NOT NULL
                                      ); '''
        conn.execute(sql)
    except Error as e:
        print(e)

def compute_vector(message):
    return ','.join(str(x) for x in lazy_loader.model.encode([message], show_progress_bar=False)[0])

def preprocess_message(message):
    doc = lazy_loader.nlp(message.lower())
    return ' '.join([token.text for token in doc if not token.is_punct])


def insert_chat(conn, chat):
    _, _, message = chat
    if not message.startswith("@"):
        # preprocess the message
        message = preprocess_message(message)
        vector = compute_vector(message)
        sql = ''' INSERT INTO chat_history(timestamp, sender, message, vector)
                  VALUES(?,?,?,?) '''
        cur = conn.cursor()
        cur.execute(sql, chat[:2] + (message, vector,))
        conn.commit()
        return cur.lastrowid

def get_last_n_chats(conn, n):
    cur = conn.cursor()
    # SQL command to select the last N rows
    sql = f'''SELECT * FROM (
                SELECT * FROM chat_history ORDER BY id DESC LIMIT {n}
            ) sub
            ORDER BY id ASC'''
    # execute the SQL command
    cur.execute(sql)
    # fetch all rows of result
    rows = cur.fetchall()
    return rows

def delete_recent_entries(conn):
    # Get IDs of two most recent entries
    cur = conn.cursor()
    cur.execute("SELECT id FROM chat_history ORDER BY id DESC LIMIT 2")
    rows = cur.fetchall()

    # Delete these entries
    for row in rows:
        cur.execute("DELETE FROM chat_history WHERE id = ?", (row[0],))

    # Commit the transaction
    conn.commit()

def delete_all_chats(conn):
        cur = conn.cursor()
        # SQL command to delete all records
        sql = ''' DELETE FROM chat_history '''
        # execute the SQL command
        cur.execute(sql)
        # commit the changes
        conn.commit()
        print("All chats deleted from database.")

def string_to_vector(vector_string):
    return np.fromstring(vector_string, sep=',')

def cosine_similarity(a, b):
    return np.dot(a, b) / (norm(a) * norm(b))


def search_chat_history(conn, query):
    cur = conn.cursor()
    cur.execute("SELECT * FROM chat_history")
    rows = cur.fetchall()
    user_vector = lazy_loader.model.encode([query], show_progress_bar=False)[0]
    similar_msgs = []

    for i in range(len(rows)):
        if rows[i][2] == 'Brandon':
            msg_vector = string_to_vector(rows[i][4])  # Use string_to_vector to convert string to vector
            similarity = cosine_similarity(user_vector, msg_vector)
            #print(f"Message: {rows[i][3]}, Similarity: {similarity}")  # for debugging
            if similarity > 0.5:
                role_user = 'user'
                content_user = rows[i][3].replace("Brandon: ", "")  # Remove the username from the content
                similar_msgs.append(
                    {'role': role_user, 'content': content_user, 'similarity': similarity})  # include similarity here

                # Add the following assistant message, if exists
                if i < len(rows) - 1:  # Check if there's a message after the current one
                    role_assistant = 'assistant'
                    content_assistant = rows[i + 1][3]
                    similar_msgs.append(
                        {'role': role_assistant, 'content': content_assistant, 'similarity': similarity})

    similar_msgs = sorted(similar_msgs, key=lambda x: x['similarity'], reverse=True)

    # Take only the top 5 messages
    top_5_msgs = similar_msgs[:5]
    top_5_msgs_without_similarity = [{k: v for k, v in msg.items() if k != 'similarity'} for msg in top_5_msgs]

    return top_5_msgs_without_similarity

def update_vectors_in_database(conn):
    cur = conn.cursor()
    # Select all rows in the database
    cur.execute("SELECT * FROM chat_history")
    rows = cur.fetchall()

    # For each row, update the vector
    for row in rows:
        new_vector = compute_vector(row[3])  # Assuming the message is in the fourth column
        cur.execute("UPDATE chat_history SET vector = ? WHERE id = ?", (new_vector, row[0]))

    # Commit the changes
    conn.commit()
