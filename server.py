import socket
from threading import Thread, Lock #multiple threads
import sys, time
import os

# Check command line arguments
if len(sys.argv) != 2:
    print("\n===== Error usage, python3 server.py SERVER_PORT ======\n")
    exit(0)

# gloabl variables for login (multiple threads)
credentials = {}  # {username: password}
pending_auth = {}  # {clientAddress: (username, is_new_user)}

# Server address information
serverHost = "127.0.0.1"  # Localhost
serverPort = int(sys.argv[1])
serverAddress = (serverHost, serverPort)

# Define socket for the server
serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
serverSocket.bind(serverAddress)

# Dictionary to store active users: {username: (clientSocket, clientAddress)}
activeUsers = {}
#addrToUser = {} not in used
# Lock for thread-safe operations on shared resources
file_lock = Lock()
activeUsersLock = Lock()

# Function to load credentials from a file
def load_credentials():
    with open("credentials.txt", "r") as f:
        for line in f:
            line = line.strip()
            if line:
                user, pwd = line.split(' ', 1)
                credentials[user] = pwd

# Function to load users              
def get_username_by_address(clientAddress):
    for user, addr in activeUsers.items():
        if addr == clientAddress:
            return user
    return None

# Function to handle client connections
def setup_server():
    global activeUsers

    # Load credentials from file first
    if not os.path.exists("credentials.txt"):
        print("===== Error: credentials.txt not found =====")
        exit(1)
    load_credentials()

    print(f"===== Chat Server is running on {serverHost}:{serverPort} =====")

    while True:
        data, clientAddress = serverSocket.recvfrom(1024)
        message = data.decode().strip()
        
        # main used function
        handle_command(message, clientAddress, activeUsers)

# Function to handle client commands
def handle_command(message, clientAddress, activeUsers):

    print(f"[SERVER] Received from {clientAddress}: {message}")

    parts = message.split(' ', 1)
    command = parts[0].upper() if len(parts) > 0 else ""
    args = parts[1] if len(parts) > 1 else ""

    if command == "LOGIN":
        if not args:
            serverSocket.sendto(f"ERROR: Usage: LOGIN username".encode(), clientAddress)
            return
        
        username = args.strip()
        # Check if username is valid and lock it
        with activeUsersLock:
            if username in activeUsers:
                response = f"ERROR: User {username} is already logged in"
                serverSocket.sendto(response.encode(), clientAddress)
                return
            # Check if username is already in use
            elif username in credentials:
                pending_auth[clientAddress] = (username, False)
                response = "Please enter your password"
            else:
                pending_auth[clientAddress] = (username, True)
                response = "Please enter a new password to register"
            serverSocket.sendto(response.encode(), clientAddress)
    
    elif command == "PASSWORD":
        if clientAddress not in pending_auth:
            return
        username, is_new = pending_auth[clientAddress]
        password = args.strip()
        # Check if password is valid
        if not is_new:
            if credentials.get(username) == password:
                # Check if user is already logged in
                with activeUsersLock:
                    activeUsers[username] = clientAddress
                response = f"SUCCESS_LOGIN: Logged in as {username}"
                broadcast_message(f"SYSTEM: {username} joined", activeUsers, exclude=username)
            else:
                response = "ERROR: Incorrect password"
            serverSocket.sendto(response.encode(), clientAddress)
            del pending_auth[clientAddress]

        else:
            # Register new user
            with file_lock:
                with open("credentials.txt", "a") as f:
                    f.write(f"{username} {password}\n")
                credentials[username] = password

                with activeUsersLock:
                    activeUsers[username] = clientAddress

                response = f"SUCCESS_REG: Registered as {username}"
                broadcast_message(f"SYSTEM: {username} joined", activeUsers, exclude=username)
            serverSocket.sendto(response.encode(), clientAddress)
            del pending_auth[clientAddress]

    elif command == "CRT":
        if not args:
            serverSocket.sendto(f"ERROR: Usage: /CRT threadtitle".encode(), clientAddress)
            return
        thread_title = args.strip()
        creator_username = get_username_by_address(clientAddress)

        if not creator_username:
            serverSocket.sendto(f"ERROR: You must log in first".encode(), clientAddress)
            return
        # check if thread title is valid
        if os.path.exists(thread_title):
            serverSocket.sendto(f"ERROR: Thread '{thread_title}' already exists.".encode(), clientAddress)
        else:
            try:
                with open(thread_title, 'w') as thread_file:
                    # Write the creator's username as the first line(with no number)
                    thread_file.write(f"{creator_username}\n")
                serverSocket.sendto(f"Thread '{thread_title}' created successfully.".encode(), clientAddress)
                
            except Exception as e:
                serverSocket.sendto(f"Error creating thread: {e}".encode(), clientAddress)

    elif command == "LST":
        thread_files = [
            f for f in os.listdir() 
            #filter out files that are not threads
            if os.path.isfile(f) 
            and not f.startswith("credentials") 
            and not f.endswith(".py")
            and "-" not in f
        ]
        if thread_files:
            response = "The list of active threads:\n" + "\n".join(thread_files)
        else:
            response = "No threads available."
        serverSocket.sendto(response.encode(), clientAddress)
    
    elif command == "RMV":
        if not args:
            serverSocket.sendto(f"ERROR: Usage: /RMV <thread title>".encode(), clientAddress)
            return

        thread_title = args.strip()
        username = get_username_by_address(clientAddress)
        if not username:
            serverSocket.sendto(f"ERROR: You must log in first".encode(), clientAddress)
            return

        if not os.path.exists(thread_title):
            serverSocket.sendto(f"ERROR: Thread '{thread_title}' does not exist.".encode(), clientAddress)
        else:
            with open(thread_title, 'r') as f:
                creator = f.readline().strip()
            if creator != username:
                serverSocket.sendto(f"ERROR: You are not the creator of thread '{thread_title}'.".encode(), clientAddress)
            else:
                os.remove(thread_title)
                serverSocket.sendto(f"Thread '{thread_title}' removed successfully.".encode(), clientAddress)

    elif command == "MSG":
        username = get_username_by_address(clientAddress)
        if not username:
            serverSocket.sendto(f"ERROR: You must log in first".encode(), clientAddress)
            return

        if not args:
            serverSocket.sendto(f"ERROR: Usage: /MSG <thread title> <message>".encode(), clientAddress)
            return

        msg_parts = args.split(' ', 1)
        if len(msg_parts) < 2:
            serverSocket.sendto(f"ERROR: Usage: /MSG <thread title> <message>".encode(), clientAddress)
            return

        thread_title, content = msg_parts[0], msg_parts[1]

        if not os.path.exists(thread_title):
            serverSocket.sendto(f"ERROR: Thread '{thread_title}' does not exist.".encode(), clientAddress)
            return

        try:
            with open(thread_title, 'r') as f:
                lines = f.readlines()

            last_message_number = 0
            for line in reversed(lines[1:]):   # jump the first line with creator's username
                token = line.split(' ', 1)[0]
                if token.isdigit():
                    last_message_number = int(token)  # get the last message start with "number"
                    break
            with open(thread_title, 'a') as f_append:
                message_number = last_message_number + 1
                message = f"{message_number} {username}: {content}\n"
                f_append.write(message)

            serverSocket.sendto(f"SUCCESS_MSG: Message added to thread '{thread_title}'".encode(), clientAddress)
        except Exception as e:
            serverSocket.sendto(f"ERROR: Failed to send message to thread '{thread_title}': {e}".encode(), clientAddress)

    elif command == "RDT":
        if not args:
            serverSocket.sendto(f"ERROR: Usage: /RDT <thread title>".encode(), clientAddress)
            return

        thread_title = args.strip()
        if not os.path.exists(thread_title):
            serverSocket.sendto(f"ERROR: Thread '{thread_title}' does not exist.".encode(), clientAddress)
            return

        # read the thread file and also jump the first line
        try:
            with open(thread_title, 'r') as f:
                lines = f.readlines()
            content = ''.join(lines[1:]) if len(lines) > 1 else "No messages in thread."
            serverSocket.sendto(content.encode(), clientAddress)
        except Exception as e:
            serverSocket.sendto(f"ERROR: Could not read thread '{thread_title}': {e}".encode(), clientAddress)

    elif command == "DLT":
        if not args:
            serverSocket.sendto(f"ERROR: Usage: /DLT <thread title> <message number>".encode(), clientAddress)
            return

        parts = args.split(' ', 1)
        if len(parts) < 2:
            serverSocket.sendto(f"ERROR: Usage: /DLT <thread title> <message number>".encode(), clientAddress)
            return

        thread_title, num_str = parts[0], parts[1]
        username = get_username_by_address(clientAddress)
        if not username:
            serverSocket.sendto(f"ERROR: You must log in first".encode(), clientAddress)
            return

        if not os.path.exists(thread_title):
            serverSocket.sendto(f"ERROR: Thread '{thread_title}' does not exist.".encode(), clientAddress)
            return

        try:
            with open(thread_title, 'r') as f:
                lines = f.readlines()
        except Exception as e:
            serverSocket.sendto(f"ERROR: Could not open thread '{thread_title}': {e}".encode(), clientAddress)
            return

        # not enough messages to delete
        if len(lines) <= 1:
            serverSocket.sendto(f"ERROR: No messages to delete".encode(), clientAddress)
            return

        # get the message number
        try:
            idx = int(num_str)
        except ValueError:
            serverSocket.sendto(f"ERROR: Message number must be an integer".encode(), clientAddress)
            return

        # get the message number as well
        if idx < 1 or idx > len(lines) - 1:
            serverSocket.sendto(f"ERROR: Invalid message number".encode(), clientAddress)
            return

        # check the message author
        msg_line = lines[idx]
        sender_token = msg_line.split(' ', 2)[1]   
        sender = sender_token[:-1]                
        if sender != username:
            serverSocket.sendto(f"ERROR: You can only delete your own messages".encode(), clientAddress)
            return

        # delete the message and rewrite the file msg number
        new_lines = [lines[0]]  # keep the first line
        for i, line in enumerate(lines[1:], start=1):
            if i == idx:
                continue
            body = line.split(' ', 1)[1]  # "username: message\n"
            new_lines.append(f"{len(new_lines)} {body}")

        # rewrite the file
        try:
            with open(thread_title, 'w') as f:
                f.writelines(new_lines)
            serverSocket.sendto(f"SUCCESS_DLT: Message {idx} deleted from '{thread_title}'".encode(), clientAddress)
        except Exception as e:
            serverSocket.sendto(f"ERROR: Failed to delete message: {e}".encode(), clientAddress)

    elif command == "EDT":
        if not args:
            serverSocket.sendto(f"ERROR: Usage: /EDT <thread title> <message number> <new message>".encode(), clientAddress)
            return

        parts2 = args.split(' ', 2)
        if len(parts2) < 3:
            serverSocket.sendto(f"ERROR: Usage: /EDT <thread title> <message number> <new message>".encode(), clientAddress)
            return

        thread_title, num_str, new_text = parts2[0], parts2[1], parts2[2]
        username = get_username_by_address(clientAddress)
        if not username:
            serverSocket.sendto(f"ERROR: You must log in first".encode(), clientAddress)
            return

        if not os.path.exists(thread_title):
            serverSocket.sendto(f"ERROR: Thread '{thread_title}' does not exist.".encode(), clientAddress)
            return

        try:
            with open(thread_title, 'r') as f:
                lines = f.readlines()
        except Exception as e:
            serverSocket.sendto(f"ERROR: Could not open thread '{thread_title}': {e}".encode(), clientAddress)
            return

        # at least one message should be there
        if len(lines) <= 1:
            serverSocket.sendto(f"ERROR: No messages to edit".encode(), clientAddress)
            return

        try:
            idx = int(num_str)
        except ValueError:
            serverSocket.sendto(f"ERROR: Message number must be an integer".encode(), clientAddress)
            return
        if idx < 1 or idx > len(lines) - 1:
            serverSocket.sendto(f"ERROR: Invalid message number".encode(), clientAddress)
            return

        msg_line = lines[idx]
        sender = msg_line.split(' ', 2)[1].rstrip(':')
        if sender != username:
            serverSocket.sendto(f"ERROR: You can only edit your own messages".encode(), clientAddress)
            return

        new_lines = [lines[0]]
        for i, line in enumerate(lines[1:], start=1):
            if i == idx:
                new_lines.append(f"{len(new_lines)} {username}: {new_text}\n")
            else:
                body = line.split(' ', 1)[1]
                new_lines.append(f"{len(new_lines)} {body}")

        try:
            with open(thread_title, 'w') as f:
                f.writelines(new_lines)
            serverSocket.sendto(f"SUCCESS_EDT: Edited message {idx} in '{thread_title}'".encode(), clientAddress)
        except Exception as e:
            serverSocket.sendto(f"ERROR: Failed to edit message: {e}".encode(), clientAddress)

    elif command == "RMV":
        if len(parts) != 2:
            serverSocket.sendto(b"ERROR: Invalid RMV command", clientAddress)
            return

        thread_title = parts[1]
        thread_filename = f"{thread_title}.txt"

        if not username:
            serverSocket.sendto(b"ERROR: You must log in first", clientAddress)
            return

        if not os.path.exists(thread_filename):
            serverSocket.sendto(b"ERROR: Thread does not exist", clientAddress)
            return

        with file_lock:
            with open(thread_filename, "r") as f:
                first_line = f.readline().strip()
            if first_line != f"Creator: {username}":
                serverSocket.sendto(b"ERROR: You are not the thread creator", clientAddress)
                return

            os.remove(thread_filename)

            uploaded_files_dir = f"{thread_title}_files"
            if os.path.exists(uploaded_files_dir):
                for file in os.listdir(uploaded_files_dir):
                    os.remove(os.path.join(uploaded_files_dir, file))
                os.rmdir(uploaded_files_dir)

            serverSocket.sendto(f"Thread {thread_title} removed successfully".encode(), clientAddress)
        
    elif command == "UPD":
        if not args or len(args.split(" ")) < 2:
            serverSocket.sendto("ERROR: Usage: /UPD <thread title> <filename>".encode(), clientAddress)
            return
        # save the client address first, so that tcp cannot cover it
        udp_addr = clientAddress

        thread_title, filename = args.split(" ", 1)

        if not os.path.exists(thread_title):
            serverSocket.sendto(f"ERROR: Thread '{thread_title}' does not exist.".encode(), udp_addr)
            return
        
        full_filename = f"{thread_title}-{filename}"
        if os.path.exists(full_filename):
            serverSocket.sendto(f"ERROR: File '{filename}' already uploaded to thread '{thread_title}'".encode(), clientAddress)
            return

        # set up TCP socket for file transfer
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.bind(('', 0))
        tcp_socket.listen(1)
        tcp_port = tcp_socket.getsockname()[1]

        # tell the client to connect to this port
        serverSocket.sendto(f"READY {tcp_port}".encode(), udp_addr)

        conn, _ = tcp_socket.accept()
        conn_file = conn.makefile('rb') 
        username_line = conn_file.readline().decode().strip()
        username = username_line  
 
        full_filename = f"{thread_title}-{filename}"
        with open(full_filename, 'wb') as f:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                f.write(data)
        conn.close()
        tcp_socket.close()

        with open(thread_title, 'a') as tf:
            tf.write(f"{username} uploaded {filename}\n")

        serverSocket.sendto(
            f"SUCCESS_UPD: File '{filename}' uploaded to thread '{thread_title}'".encode(),
            udp_addr
        )
        
    elif command == "DWN":
        if not args:
            serverSocket.sendto("ERROR: Usage: /DWN <thread title> <filename>".encode(), clientAddress)
            return
        try:
            thread_title, filename = args.split(" ", 1)
            full_filename = f"{thread_title}-{filename}"

            if not os.path.exists(full_filename):
                serverSocket.sendto("ERROR: File not found.".encode(), clientAddress)
                return

        # set up TCP socket for file transfer
            tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_socket.bind(('', 0))
            tcp_socket.listen(1)
            tcp_port = tcp_socket.getsockname()[1]

        # tell the client to connect to this port(same as upload)
            serverSocket.sendto(f"READY {tcp_port}".encode(), clientAddress)

            conn, _ = tcp_socket.accept()
            with open(full_filename, "rb") as f:
                while True:
                    data = f.read(1024)
                    if not data:
                        break
                    conn.send(data)

            conn.close()
            tcp_socket.close()

            serverSocket.sendto(f"SUCCESS_DWN: File '{filename}' downloaded successfully".encode(), clientAddress)
        except Exception as e:
            serverSocket.sendto(f"ERROR: {str(e)}".encode(), clientAddress)


    elif command == "BROADCAST":
        # not in used, just in used for server announcement, client can only receive
        username = get_username_by_address(clientAddress)

        if not username:
            serverSocket.sendto(f"ERROR: You must log in first".encode(), clientAddress)
            return

        if not args:
            serverSocket.sendto(f"ERROR: Usage: /BROADCAST message".encode(), clientAddress)
            return

        broadcast_message(f"BROADCAST from {username}: {args}", activeUsers, exclude=username)
        serverSocket.sendto(f"SUCCESS_BROADCAST: Broadcast sent".encode(), clientAddress)

    elif command == "EXIT":
        username = get_username_by_address(clientAddress)
        if not username:
            serverSocket.sendto(f"ERROR: You must log in first".encode(), clientAddress)
            return

        if username in activeUsers:
            del activeUsers[username]
            broadcast_message(f"SYSTEM: {username} left", activeUsers)
        serverSocket.sendto(f"Connection closed".encode(), clientAddress)

    else:
        serverSocket.sendto(f"ERROR: Unknown command, please check available commands: /help".encode(), clientAddress)
    
    print(f"[SERVER] current activeUsers: {activeUsers}") # check who is online

# function to broadcast messages to all users
def broadcast_message(message, activeUsers, exclude=None):
    for user, addr in activeUsers.items():
        if user == exclude:
            continue
        serverSocket.sendto(message.encode(), addr)

# Start the server if this is the main module
if __name__ == "__main__":
    try:
        setup_server()
    except KeyboardInterrupt:
        print("\n===== Server shutting down(KeyboardInterrupt) =====")
