import openai
import logging
import chatdb_utils
from datetime import datetime

logging.basicConfig(filename='BotData/openai_log.txt', level=logging.INFO, format='%(asctime)s:%(message)s')

def get_api_key():
    with open('api_key.txt', 'r') as file:
        api_key = file.read().replace('\n', '')
    return api_key

# Establish your OpenAI API Key
openai.api_key = get_api_key()

def log_openai_interaction(time, content, response, tokens_used):
    log_message = f"\n{'*' * 20}\nTime: {time}\nContent Sent: {content}\nResponse: {response}\nTokens Used: {tokens_used}\n{'*' * 20}"
    logging.info(log_message)

def get_response_from_bot(message, conn):
    # 'personality.txt' contains the system role prompt for the OpenAI API
    with open("BotData/personality.txt", "r") as file:
        # Open file, remove any leading/trailing whitespaces
        system_prompt = file.read().strip()

    # Define the system role message using the content from the 'personality.txt' file
    system = {
        'role': 'system',
        'content': system_prompt
    }

    # Summarize the recent conversation
    summary = summarize_conversation(conn, format_conversation(chatdb_utils.get_last_n_chats(conn, 10)))

    # Add summary to the conversation history
    conversation_summary = {
        'role': 'assistant',
        'content': f"What follows is a summary of the most recent conversation you have had with the user. Use it as context for your answer, if relevant: {summary}"
    }
    # Defining the user role message using the message passed to this function
    user = {
        'role': 'user',
        'content': message
    }
    # Search chat history for related context
    related_context = chatdb_utils.search_chat_history(conn, message)
    new_context = summarize_search(related_context, message)
    # If related_context is not empty, define the context message
    if related_context:
        context = {
            'role': 'assistant',
            'content': f"Here is some information from past conversations that may be relevant to the query: {new_context}"
        }
        #Creating a conversation history by combining the system, conversation summary, context, and user messages
        conversation_history = [system, conversation_summary, context, user]
    else:
        # Exclude context from the conversation history
        conversation_history = [system, conversation_summary, user]
    # Generate a response from the API
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=conversation_history,
        max_tokens=500,
        n=1,
        temperature=0.6,
    )
    # Log the OpenAI interaction
    log_openai_interaction(datetime.now(), conversation_history, response.choices[0].message['content'],
                           response['usage']['total_tokens'])
    # Extracting the generated response from the API's return object
    # The response is in the 'content' field of the 'message' field of the first choice
    return response.choices[0].message['content']

def get_timestamp():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def format_conversation(rows):
    conversation = ""
    for row in rows:
        id, timestamp, sender, message, _ = row  # Ignore vector data
        if sender == 'Brandon':
            conversation += f"User: {message}\n"
        else:
            conversation += f"AI: {message}\n"
    return conversation

def format_for_openAI(convo):
    # Format the messages into the format expected by OpenAI
    formatted_messages = []
    for msg in convo:
        role = 'user' if msg[2] == 'User' else 'assistant'
        formatted_messages.append({
            'role': role,
            'content': msg[3]  # Using only the message text
        })
    return formatted_messages

def summarize_conversation(conn, message):

    # Fetch the last 10 messages from the chat history
    formatted_messages = format_for_openAI(chatdb_utils.get_last_n_chats(conn, 10))

    # Read the system role prompt from a file
    with open("BotData/personality.txt", "r") as file:
        system_prompt = file.read().strip()

    system = {
        'role': 'system',
        'content': system_prompt
    }
    # Add the system prompt to the beginning of the conversation history
    conversation_history = [system] + formatted_messages
    # Create the instruction for the API to summarize the conversation
    instruction = {
        'role': 'system',
        'content': "You are about to lose your memory. Above is a transcript of your last conversation. Write a summary for yourself that you can use to recall its contents later."
    }
    # Add the instruction to the conversation history
    conversation_history.append(instruction)

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=conversation_history,
        max_tokens=150,
        n=1,
        temperature=0.6,
    )
    log_openai_interaction(datetime.now(), conversation_history, response.choices[0].message['content'], response['usage']['total_tokens'])
    return response.choices[0].message['content']

def summarize_search(results, query):
    system_prompt = "You are an AI assistant. Your task is to summarize any information relevant to the given query from the provided conversation history."

    # Read the system role prompt from a file
    system = {
        'role': 'system',
        'content': system_prompt
    }

    # Define the query message
    query_msg = {
        'role': 'user',
        'content': query
    }

    # Define the conversation history message
    conv_hist_msg = {
        'role': 'assistant',
        'content': f"The following conversation history might contain information relevant to your query: {results}"
    }
    conversation_history = [system, query_msg, conv_hist_msg]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=conversation_history,
        max_tokens=250,
        n=1,
        temperature=0.6,
    )

    log_openai_interaction(datetime.now(), conversation_history, response.choices[0].message['content'], response['usage']['total_tokens'])
    return response.choices[0].message['content']
