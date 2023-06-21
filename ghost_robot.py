import chatdb_utils
import bot_utils

def main():
    # establish connection
    conn = chatdb_utils.create_connection()
    # create table
    chatdb_utils.create_table(conn)
    # Define commands
    commands = {
        "@recentchat": lambda conn=conn: chatdb_utils.get_last_n_chats(conn, 2),
        "@forget": lambda conn=conn: chatdb_utils.delete_recent_entries(conn),
        "@amnesia": lambda conn=conn: chatdb_utils.delete_all_chats(conn),
        "@summarize": lambda conn=conn: bot_utils.summarize_conversation(bot_utils.format_conversation(chatdb_utils.get_last_n_chats(conn, 10))),
        "@updatevectors": lambda conn=conn: chatdb_utils.update_vectors_in_database(conn),
        # add more commands here
        }

    while True:
        # prompt for user input
        user_message = input("You: ")
        # check for commands
        if user_message in commands:
            result = commands[user_message](conn)
            print(result)
            continue
        # get current timestamp
        timestamp = bot_utils.get_timestamp()
        # get response from AI bot
        ai_message = bot_utils.get_response_from_bot(user_message, conn)
        # store user message
        chatdb_utils.insert_chat(conn, (timestamp, 'Brandon', user_message))
        # store AI message
        chatdb_utils.insert_chat(conn, (timestamp, 'AI', ai_message))
        # print AI response
        print("AI: ", ai_message)

if __name__ == '__main__':
    main()
