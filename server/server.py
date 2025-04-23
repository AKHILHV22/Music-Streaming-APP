import socket
import threading
import os
import json
import time
import struct

class MusicServer:
    def __init__(self):
        self.host = '0.0.0.0'
        self.port = 12345
        self.server_socket = None
        self.running = False
        self.clients = []
        self.music_dir = "music_files"
        
        if not os.path.exists(self.music_dir):
            os.makedirs(self.music_dir)
        
        print(f"Music Server starting on {self.host}:{self.port}")
        print(f"Music files directory: {os.path.abspath(self.music_dir)}")
        print(f"Available files: {os.listdir(self.music_dir)}")
        self.start_server()
    
    def start_server(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            print(f"Server is listening for connections...")
            
            accept_thread = threading.Thread(target=self.accept_clients, daemon=True)
            accept_thread.start()
            
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stop_server()
                
        except Exception as e:
            print(f"Failed to start server: {str(e)}")
            self.stop_server()
    
    def stop_server(self):
        print("\nShutting down server...")
        self.running = False
        for client in self.clients:
            try:
                client.close()
            except:
                pass
        self.clients = []
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None
        
        print("Server stopped successfully")
        os._exit(0)
    
    def accept_clients(self):
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                client_socket.settimeout(30.0)  # Increased timeout
                self.clients.append(client_socket)
                print(f"\nNew connection from {addr}")
                threading.Thread(target=self.handle_client, args=(client_socket, addr), daemon=True).start()
            except Exception as e:
                if self.running:
                    print(f"Error accepting connection: {str(e)}")
                break
    
    def handle_client(self, client_socket, addr):
        try:
            # Send welcome message
            self._send_message(client_socket, json.dumps({
                'status': 'OK',
                'message': 'Welcome to Music Server'
            }))
            
            while self.running:
                try:
                    # Receive request
                    request = self._receive_message(client_socket)
                    if not request:
                        break
                    
                    print(f"Received request from {addr}: {request}")
                    
                    if request == "LIST":
                        files = [f for f in os.listdir(self.music_dir) if f.endswith(('.mp3', '.wav'))]
                        self._send_message(client_socket, json.dumps({
                            'status': 'OK',
                            'files': files
                        }))
                    
                    elif request.startswith("PLAY:"):
                        filename = request.split(":")[1]
                        filepath = os.path.join(self.music_dir, filename)
                        
                        if os.path.exists(filepath):
                            self._send_message(client_socket, "READY")
                            self.send_file(client_socket, filepath)
                        else:
                            self._send_message(client_socket, json.dumps({
                                'status': 'ERROR',
                                'message': f'File not found: {filename}'
                            }))
                    
                except socket.timeout:
                    print(f"Timeout with client {addr}")
                    break
                except ConnectionResetError:
                    print(f"Client {addr} disconnected")
                    break
                except Exception as e:
                    print(f"Error handling client {addr}: {str(e)}")
                    break
                    
        except Exception as e:
            print(f"Error with client {addr}: {str(e)}")
        finally:
            try:
                client_socket.close()
            except:
                pass
            if client_socket in self.clients:
                self.clients.remove(client_socket)
            print(f"Connection closed with {addr}")

    def _send_message(self, sock, message):
        """Send a length-prefixed message"""
        try:
            message = message.encode() if isinstance(message, str) else message
            sock.sendall(struct.pack('!I', len(message)) + message)
        except Exception as e:
            raise ConnectionError(f"Failed to send message: {str(e)}")

    def _receive_message(self, sock):
        """Receive a length-prefixed message"""
        try:
            # First 4 bytes contain message length
            raw_len = sock.recv(4)
            if not raw_len:
                return None
            msg_len = struct.unpack('!I', raw_len)[0]
            
            # Receive the actual message
            return b''.join([sock.recv(msg_len)]).decode()
        except Exception as e:
            raise ConnectionError(f"Failed to receive message: {str(e)}")

    def send_file(self, client_socket, filepath):
        try:
            filename = os.path.basename(filepath)
            filesize = os.path.getsize(filepath)
            
            # Send file size first
            client_socket.sendall(filesize.to_bytes(8, 'big'))
            
            # Send file data in chunks
            with open(filepath, 'rb') as f:
                while True:
                    data = f.read(4096)
                    if not data:
                        break
                    client_socket.sendall(data)
            
            print(f"File {filename} sent successfully")
        except Exception as e:
            print(f"Error sending file: {str(e)}")
            raise

if __name__ == "__main__":
    server = MusicServer()