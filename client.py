import socket
from threading import Thread, Event
import sys
import time
import os

# Check command line arguments
if len(sys.argv) != 3:
    print("\n===== Error usage, python3 client.py SERVER_IP(127.0.0.1) SERVER_PORT ======\n")
    exit(0)

# Server address information
serverHost = sys.argv[1]
serverPort = int(sys.argv[2])
serverAddress = (serverHost, serverPort)

# Global variables
clientSocket = None
clientAlive = False
username = None
auth_in_progress = False 

password_prompt_event = Event()
register_prompt_event = Event()


class ReceiveThread(Thread): # Thread to receive messages from the server (UDP)
    def __init__(self, socket):
        Thread.__init__(self)
        self.socket = socket
        self.alive = True
    
    def run(self):
        global clientAlive, auth_in_progress, username
        while self.alive and clientAlive:
            try:
                data, _ = self.socket.recvfrom(1024)
                message = data.decode()
                
                #Some response from server, most go "else" side
                if message == "Please enter your password":
                    password_prompt_event.set()

                elif message == "Please enter a new password to register":
                    register_prompt_event.set()

                elif message.startswith("SUCCESS_LOGIN"):
                    parts = message.split()
                    username = message.split(' ')[-1]
                    auth_in_progress = False
                    password_prompt_event.clear()
                    print(f"\n===== Logged in as {username} =====")

                elif message.startswith("SUCCESS_REG"):
                    parts = message.split()
                    username = message.split(' ')[-1]
                    auth_in_progress = False
                    register_prompt_event.clear()
                    print(f"\n===== Registered and logged in as {username} =====")

                elif message.startswith("SUCCESS_MSG"):
                    thread_title = message.split(' ')[-1]
                    print(f"\n[Thread {thread_title}] Message sent successfully")

                elif message.startswith("SUCCESS_BROADCAST"):
                    print("\n[Broadcast] Message sent to all users")

                elif message.startswith("ERROR"):
                    print(f"\n===== {message} =====")
                    auth_in_progress = False
                    password_prompt_event.clear
                    register_prompt_event.clear
                else:
                    print(f"\n{message}\n> ", end="")
                
            except Exception as e:
                print(f"\n===== Error receiving message: {e} =====")
                clientAlive = False
                break
            
# function to connect to the server
def connect_to_server():
    global clientSocket, clientAlive, receiveThread
    try:
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        clientAlive = True
        
        # Start receive thread
        receiveThread = ReceiveThread(clientSocket)
        receiveThread.daemon = True
        receiveThread.start()
        print(f"===== Connected to server at {serverHost}:{serverPort} =====")
        return True
        
    except Exception as e:
        print(f"===== Error creating socket: {e} =====")
        return False

# function to login in (what ever login or register)
def login():
    global auth_in_progress

    auth_in_progress = True
    username_input = input("Enter username: ").strip()
    clientSocket.sendto(f"LOGIN {username_input}".encode(), serverAddress)
    print("Wait for server...\n")

# funtion to create a thread
def create_thread(thread_title):
    global username, clientSocket
    
    if not username:
        print("===== You must log in first =====")
        return False
    
    if not clientAlive or not clientSocket:
        print("===== Not connected to server =====")
        return False
    
    command = f"CRT {thread_title}"
    try:
        clientSocket.sendto(command.encode(), serverAddress)
        return True
    except Exception as e:
        print(f"===== Error creating thread: {e} =====")
        return False

# function to list all threads
def list_threads():
    if not username:
        print("===== You must login first! =====")
        return
    
    try:
        clientSocket.sendto(f"LST".encode(), serverAddress)
    except Exception as e:
        print(f"===== Error sending LST command: {e} =====")

# function to read a thread
def read_thread(thread_title):
    if not username:
        print("===== You must log in first =====")
        return

    if not clientAlive or not clientSocket:
        print("===== Not connected to server =====")
        return

    try:
        clientSocket.sendto(f"RDT {thread_title}".encode(), serverAddress)
    except Exception as e:
        print(f"===== Error sending RDT command: {e} =====")

# function to send a message to a thread
def send_thread_message(thread_title, message):
    if not username:
        print("===== You must log in first =====")
        return False
    if not clientAlive or not clientSocket:
        print("===== Not connected to server =====")
        return
    
    # Format the MSG command with recipient and message
    command = f"MSG {thread_title} {message}"
    
    try:
        # Send the command to the server
        clientSocket.sendto(command.encode(), serverAddress)
        return True
        
    except Exception as e:
        print(f"===== Error sending thread message: {e} =====")
        return False

# function to delete a message from a thread
def delete_message(thread_title, msg_number):
    if not username:
        print("===== You must log in first =====")
        return

    if not clientAlive or not clientSocket:
        print("===== Not connected to server =====")
        return

    try:
        clientSocket.sendto(f"DLT {thread_title} {msg_number}".encode(), serverAddress)
    except Exception as e:
        print(f"===== Error sending DLT command: {e} =====")

# function to edit a message in a thread
def edit_message(thread_title, msg_number, new_text):
    if not username:
        print("===== You must log in first =====")
        return
    if not clientAlive or not clientSocket:
        print("===== Not connected to server =====")
        return
    try:
        clientSocket.sendto(f"EDT {thread_title} {msg_number} {new_text}".encode(), serverAddress)
    except Exception as e:
        print(f"===== Error sending EDT command: {e} =====")

# function to remove a thread
def remove_thread(thread_title):
    if not username:
        print("===== You must log in first =====")
        return

    if not clientAlive or not clientSocket:
        print("===== Not connected to server =====")
        return

    try:
        clientSocket.sendto(f"RMV {thread_title}".encode(), serverAddress)
    except Exception as e:
        print(f"===== Error sending RMV command: {e} =====")

# function to upload a file (client to server, udp first and then tcp)
def upload_file(thread_title, file_path):
    global username, clientSocket, serverAddress

    if not username:
        print("===== You must log in first =====")
        return

    if not os.path.exists(file_path):
        print(f"===== File '{file_path}' does not exist =====")
        return

    file_name = os.path.basename(file_path)
    cmd = f"UPD {thread_title} {file_name}"

    # set a new UDP socket for control channel (I dont know if it is necessary, because I cannot get the handshake with clientSocket)
    ctrl = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ctrl.settimeout(5)

    try:
        # handshake with server(UDP)
        ctrl.sendto(cmd.encode(), serverAddress)

       # wait for READY <port>(UDP)
        data, _ = ctrl.recvfrom(1024)
        resp = data.decode().strip()
        if not resp.startswith("READY"):
            print(f"===== Unexpected server response: {resp} =====")
            return

        tcp_port = int(resp.split()[1])
        # send file (TCP)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as t:
            t.connect((serverAddress[0], tcp_port))
            
            t.sendall(f"{username}\n".encode())

            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(1024)
                    if not chunk:
                        break
                    t.send(chunk)

        # wait for final confirmation(UDP)
        data, _ = ctrl.recvfrom(1024)
        print(data.decode().strip())

    except socket.timeout:
        print("===== Upload handshake timed out =====")
    finally:
        ctrl.close()

# function to download a file (server to client, udp first and then tcp)
def download_file(thread_title, filename):
    global username, clientSocket, serverAddress

    if not username:
        print("===== You must log in first =====")
        return

    ctrl = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ctrl.settimeout(5)

    try:
        ctrl.sendto(f"DWN {thread_title} {filename}".encode(), serverAddress)

        data, _ = ctrl.recvfrom(1024)
        resp = data.decode().strip()
        if not resp.startswith("READY"):
            print(f"===== Unexpected server response: {resp} =====")
            return

        tcp_port = int(resp.split()[1])

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as t:
            t.connect((serverAddress[0], tcp_port))
            with open(filename, "wb") as f:
                while True:
                    chunk = t.recv(1024)
                    if not chunk:
                        break
                    f.write(chunk)

        data, _ = ctrl.recvfrom(1024)
        print(data.decode().strip())

    except socket.timeout:
        print("===== Download handshake timed out =====")
    finally:
        ctrl.close()

# function to exit the chat
def exit_chat():
    global clientAlive
    
    if not clientAlive or not clientSocket:
        print("===== Not connected to server =====")
        return
    
    try:
        if clientSocket:
            clientSocket.sendto("EXIT".encode(), serverAddress)
            ReceiveThread.alive = False
        
    except Exception as e:
        print(f"===== Error during exit: {e}, connection may not be released, please try again=====")
    finally:
        # Set clientAlive to False
        clientAlive = False
        
        # Clean up resources (close socket)
        if clientSocket:
            clientSocket.close()
        print("===== Disconnected from server =====")

def display_menu():
    """
    Display all the available commands
    """
    print("\n===== Available Commands =====")
    print("/LOGIN: Log in a account and then type in a username")
    print("/CRT <threadtitle>: Create a new thread")
    print("/LST: List all threads")
    print("/MSG <threadtitle> <message>: Post a message")
    print("/DLT <threadtitle> <number>: Delete a message")
    print("/RDT <threadtitle>: Read a thread")
    print("/EDT <threadtitle> <number> <message>: Edit a message")
    print("/UPD <threadtitle> <filename>: Upload file")
    print("/DWN <threadtitle> <filename>: Download file")
    print("/RMV <threadtitle>: Remove threads, you can just remover yours thread")
    print("/XIT: Exit")
    print("/HELP: Find available commands")
    print("==============================\n")

def parse_user_input(user_input):
    if not user_input:
        return
    
    if not user_input.startswith('/'):
        print(f"===== Unknown command, please /help to find avilable commands=====")
    # Check if input starts with a command (/)
    if user_input.startswith('/'):
        # Parse the command and arguments
        parts = user_input[1:].split(' ', 1)
        command = parts[0].lower()
        
        # Call the appropriate function based on the command
        if command == "login":
            login()
        
        elif command == "crt":
            if len(parts) < 2 or not parts[1].strip():
                print("===== Usage: /CRT <thread title> =====")
                return
            thread_title = parts[1]
            create_thread(thread_title)

        elif command == "lst":
            list_threads()

        elif command == "rmv":
            if len(parts) < 2 or not parts[1].strip():
                print("===== Usage: /RMV <thread title> =====")
                return
            thread_title = parts[1]
            remove_thread(thread_title)

        elif command == "msg":
            if len(parts) < 2 or not parts[1].strip():
                print("===== Usage: /msg <thread title> <message> =====")
                return
                
            msg_parts = parts[1].split(' ', 1)
            if len(msg_parts) < 2 or not msg_parts[1].strip():
                print("===== Usage: /msg <thread title> <message> =====")
                return
                
            thread_title = msg_parts[0]
            message = msg_parts[1]
            send_thread_message(thread_title, message)

        elif command == "rdt":
            if len(parts) < 2 or not parts[1].strip():
                print("===== Usage: /RDT <thread title> =====")
                return
            thread_title = parts[1]
            read_thread(thread_title)

        elif command == "dlt":
            if len(parts) < 2 or not parts[1].strip():
                print("===== Usage: /DLT <thread title> <message number> =====")
                return
            dlt_parts = parts[1].split(' ', 1)
            if len(dlt_parts) < 2 or not dlt_parts[1].strip():
                print("===== Usage: /DLT <thread title> <message number> =====")
                return
            thread_title, msg_num = dlt_parts[0], dlt_parts[1]
            delete_message(thread_title, msg_num)

        elif command == "edt":
            if len(parts) < 2 or not parts[1].strip():
                print("===== Usage: /EDT <thread title> <message number> <new message> =====")
                return
            edt_parts = parts[1].split(' ', 2)
            if len(edt_parts) < 3 or not edt_parts[2].strip():
                print("===== Usage: /EDT <thread title> <message number> <new message> =====")
                return
            thread_title, msg_num, new_text = edt_parts[0], edt_parts[1], edt_parts[2]
            edit_message(thread_title, msg_num, new_text)
            
        elif command == "rmv":
            if len(parts) < 2 or not parts[1].strip():
                print("===== Usage: /RMV <thread title> =====")
                return
            thread_title = parts[1].strip()
            remove_thread(thread_title)

        elif command == "upd": 
            if len(parts) < 2 or not parts[1].strip():
                print("===== Usage: /UPD <thread title> <filename> =====")
            else:
                upd_parts = parts[1].split(' ', 1)
                if len(upd_parts) < 2 or not upd_parts[1].strip():
                    print("===== Usage: /UPD <thread title> <filename> =====")
                else:
                    thread_title = upd_parts[0]
                    filename = upd_parts[1]
                    upload_file(thread_title, filename)

        elif command == "dwn":  
            if len(parts) < 2 or not parts[1].strip():
                print("===== Usage: /DWN <thread title> <filename> =====")
            else:
                dwn_parts = parts[1].split(' ', 1)
                if len(dwn_parts) < 2 or not dwn_parts[1].strip():
                    print("===== Usage: /DWN <thread title> <filename> =====")
                else:
                    thread_title = dwn_parts[0]
                    filename = dwn_parts[1]
                    download_file(thread_title, filename)
            
        elif command == "exit":
            exit_chat()
            
        elif command == "help":
            display_menu()
            
        else:
            print(f"===== Unknown command: {command}, please /help to find avilable commands=====")
            
            
def main():
    global clientAlive
    
    print("===== Welcome to the Chat Application =====")
    
    # Connect to the server
    if not connect_to_server():
        print("Failed to connect to server. Exiting...")
        return
    
    # Display menu of available commands
    display_menu()
    
    # Main loop for user interaction
    try:
        while clientAlive:
            if password_prompt_event.is_set():
                password = input("Please enter your password: ").strip()
                clientSocket.sendto(f"PASSWORD {password}".encode(), serverAddress)
                password_prompt_event.clear()
                continue

            elif register_prompt_event.is_set():
                password = input("Please create a new password: ").strip()
                clientSocket.sendto(f"PASSWORD {password}".encode(), serverAddress)
                register_prompt_event.clear()
                continue
            
            elif auth_in_progress:
                time.sleep(0.1)
                continue
        
            user_input = input("> ")
            parse_user_input(user_input) # go to prase command

    except KeyboardInterrupt:
        print("\nExiting chat application...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up resources
        if clientSocket:
            clientSocket.close()

if __name__ == "__main__":
    main()
