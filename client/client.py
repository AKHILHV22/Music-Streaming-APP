import socket
import os
from tkinter import Tk, Label, Listbox, Button, messagebox, filedialog, ttk, Canvas, PhotoImage
from PIL import Image, ImageTk
import pygame
import threading
import json
import time
import struct
import io
from mutagen.mp3 import MP3
from mutagen.id3 import ID3

class MusicClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Music Streaming Client")
        self.root.geometry("800x700")  # Increased window size
        
        self.host = 'localhost'
        self.port = 12345
        self.client_socket = None
        self.connected = False
        self.current_file = None
        self.pause_position = 0  # Track pause position
        self.download_dir = "downloaded_music"
        self.playing = False
        self.paused = False
        self.lock = threading.Lock()
        self.current_image = None
        self.default_album_art = self._create_default_album_art()
        
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
        
        pygame.mixer.init()
        self.setup_ui()
    
    def _create_default_album_art(self):
        """Create a default album art image"""
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (300, 300), color='#1e1e1e')
        draw = ImageDraw.Draw(img)
        draw.ellipse((50, 50, 250, 250), fill='#333333')
        draw.text((100, 120), "Album Art", fill="white")
        return ImageTk.PhotoImage(img)
    
    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Connection Frame
        connection_frame = ttk.LabelFrame(main_frame, text="Connection", padding=10)
        connection_frame.pack(fill="x", pady=5)
        
        self.status_label = ttk.Label(connection_frame, text="Status: Disconnected", foreground="red")
        self.status_label.pack(side="left", padx=5)
        
        ttk.Button(connection_frame, text="Connect", command=self.connect).pack(side="left", padx=5)
        ttk.Button(connection_frame, text="Disconnect", command=self.disconnect).pack(side="left", padx=5)
        
        # Content Frame
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill="both", expand=True)
        
        # Album Art Frame (Left)
        self.album_frame = ttk.LabelFrame(content_frame, text="Now Playing", width=300, height=300)
        self.album_frame.pack(side="left", fill="y", padx=5, pady=5)
        self.album_frame.pack_propagate(False)
        
        self.album_canvas = Canvas(self.album_frame, bg="#1e1e1e", width=300, height=300)
        self.album_canvas.pack(fill="both", expand=True)
        self.album_canvas.create_image(150, 150, image=self.default_album_art)
        
        # Music List Frame (Right)
        list_frame = ttk.LabelFrame(content_frame, text="Available Music", padding=10)
        list_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        
        self.music_listbox = Listbox(list_frame, height=15, bg="white", fg="black")
        self.music_listbox.pack(fill="both", expand=True)
        
        ttk.Button(list_frame, text="Refresh List", command=self.refresh_list).pack(pady=5)
        
        # Controls Frame (Bottom)
        controls_frame = ttk.LabelFrame(main_frame, text="Controls", padding=10)
        controls_frame.pack(fill="x", pady=5)
        
        ttk.Button(controls_frame, text="Play", command=self.play_selected).pack(side="left", padx=5)
        ttk.Button(controls_frame, text="Pause", command=self.pause_music).pack(side="left", padx=5)
        ttk.Button(controls_frame, text="Stop", command=self.stop_playback).pack(side="left", padx=5)
        ttk.Button(controls_frame, text="Download", command=self.download_selected).pack(side="left", padx=5)
        
        # Song Info Frame
        self.song_info_frame = ttk.LabelFrame(main_frame, text="Song Information", padding=10)
        self.song_info_frame.pack(fill="x", pady=5)
        
        self.song_title = ttk.Label(self.song_info_frame, text="Title: Not Playing", font=("Arial", 10))
        self.song_title.pack(anchor="w")
        
        self.song_artist = ttk.Label(self.song_info_frame, text="Artist: Unknown", font=("Arial", 10))
        self.song_artist.pack(anchor="w")
        
        self.song_album = ttk.Label(self.song_info_frame, text="Album: Unknown", font=("Arial", 10))
        self.song_album.pack(anchor="w")
        
        # Status Bar
        self.status_bar = ttk.Label(main_frame, text="Ready", relief="sunken")
        self.status_bar.pack(fill="x", pady=5)
    
    def _extract_album_art(self, filepath):
        """Extract album art from MP3 file"""
        try:
            audio = MP3(filepath, ID3=ID3)
            if 'APIC:' in audio.tags:
                album_art = audio.tags['APIC:'].data
                img = Image.open(io.BytesIO(album_art))
                img = img.resize((300, 300), Image.LANCZOS)
                return ImageTk.PhotoImage(img)
        except Exception:
            pass
        return None
    
    def _update_album_art(self, filepath):
        """Update the album art display"""
        img = self._extract_album_art(filepath)
        if img:
            self.current_image = img  # Keep reference
            self.album_canvas.delete("all")
            self.album_canvas.create_image(150, 150, image=img)
        else:
            self.album_canvas.delete("all")
            self.album_canvas.create_image(150, 150, image=self.default_album_art)
    
    def _update_song_info(self, filepath):
        """Update song information display"""
        try:
            audio = MP3(filepath, ID3=ID3)
            title = audio.tags.get('TIT2', ['Unknown'])[0]
            artist = audio.tags.get('TPE1', ['Unknown'])[0]
            album = audio.tags.get('TALB', ['Unknown'])[0]
            
            self.song_title.config(text=f"Title: {title}")
            self.song_artist.config(text=f"Artist: {artist}")
            self.song_album.config(text=f"Album: {album}")
        except Exception:
            filename = os.path.basename(filepath)
            self.song_title.config(text=f"Title: {filename}")
            self.song_artist.config(text="Artist: Unknown")
            self.song_album.config(text="Album: Unknown")
    
    def connect(self):
        if self.connected:
            return
        
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(10)
            self.client_socket.connect((self.host, self.port))
            
            # Verify connection
            welcome = self._receive_message()
            if not welcome:
                raise ConnectionError("Connection failed")
            
            self.connected = True
            self.status_label.config(text=f"Status: Connected to {self.host}:{self.port}", foreground="green")
            self.status_bar.config(text="Connected to server")
            self.refresh_list()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect: {str(e)}")
            self.status_bar.config(text=f"Connection failed: {str(e)}")
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
    
    def _send_message(self, message):
        """Thread-safe message sending"""
        with self.lock:
            try:
                message = message.encode() if isinstance(message, str) else message
                self.client_socket.sendall(struct.pack('!I', len(message)) + message)
            except Exception as e:
                raise ConnectionError(f"Failed to send message: {str(e)}")

    def _receive_message(self):
        """Thread-safe message receiving"""
        with self.lock:
            try:
                # Get message length
                raw_len = self.client_socket.recv(4)
                if not raw_len:
                    return None
                msg_len = struct.unpack('!I', raw_len)[0]
                
                # Get message data
                return self.client_socket.recv(msg_len).decode()
            except Exception as e:
                raise ConnectionError(f"Failed to receive message: {str(e)}")

    def _receive_file(self, filepath):
        """Thread-safe file receiving"""
        with self.lock:
            try:
                # Get file size
                size_bytes = self.client_socket.recv(8)
                if not size_bytes or len(size_bytes) != 8:
                    raise ValueError("Invalid file size received")
                
                filesize = int.from_bytes(size_bytes, 'big')
                
                # Receive file data
                received = 0
                with open(filepath, 'wb') as f:
                    while received < filesize:
                        data = self.client_socket.recv(min(filesize - received, 4096))
                        if not data:
                            raise ConnectionError("Connection interrupted")
                        f.write(data)
                        received += len(data)
                        progress = int((received / filesize) * 100)
                        self.status_bar.config(text=f"Downloading {os.path.basename(filepath)}: {progress}%")
                
                return True
            except Exception as e:
                if os.path.exists(filepath):
                    os.remove(filepath)
                raise ConnectionError(f"File transfer failed: {str(e)}")

    def refresh_list(self):
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to the server first.")
            return
    
        try:
            self._send_message("LIST")
            response = self._receive_message()
            
            if not response:
                raise ValueError("No response from server")
            
            data = json.loads(response)
            if data.get('status') != 'OK':
                raise ValueError(data.get('message', 'Server error'))
            
            self.music_listbox.delete(0, 'end')
            for file in data.get('files', []):
                self.music_listbox.insert('end', file)
                
            self.status_bar.config(text=f"Found {len(data['files'])} songs")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get music list: {str(e)}")
            self.status_bar.config(text=f"Error: {str(e)}")
            self.disconnect()
    
    def play_selected(self):
        if self.paused:
            # Resume from paused position
            pygame.mixer.music.play(start=self.pause_position/1000)  # Convert to seconds
            self.paused = False
            self.status_bar.config(text="Resumed playback")
            return
        
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to the server first.")
            return
        
        selection = self.music_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a music file to play.")
            return
        
        filename = self.music_listbox.get(selection[0])
        temp_file = os.path.join(self.download_dir, f"temp_{filename}")
        
        try:
            # Stop any current playback
            self.stop_playback()
            
            # Request file from server
            self._send_message(f"PLAY:{filename}")
            response = self._receive_message()
            
            if response != "READY":
                raise ValueError(response)
            
            # Start download in background
            self.status_bar.config(text=f"Downloading {filename}...")
            threading.Thread(
                target=self._download_and_play,
                args=(filename, temp_file),
                daemon=True
            ).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to play music: {str(e)}")
            self.status_bar.config(text=f"Error: {str(e)}")
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def _download_and_play(self, filename, temp_file):
        try:
            # Download the file
            self._receive_file(temp_file)
            
            # Update album art and song info
            self._update_album_art(temp_file)
            self._update_song_info(temp_file)
            
            # Play the file
            self.current_file = temp_file
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            self.playing = True
            self.paused = False
            self.pause_position = 0
            self.status_bar.config(text=f"Playing: {filename}")
            
            # Wait for playback to finish
            while pygame.mixer.music.get_busy() and self.playing:
                    time.sleep(0.1)
            
            # Cleanup
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            self.status_bar.config(text="Ready")
            
        except Exception as e:
            self.status_bar.config(text=f"Error: {str(e)}")
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            messagebox.showerror("Error", f"Playback failed: {str(e)}")
                
    def pause_music(self):
        if self.playing:
            if self.paused:
                pygame.mixer.music.unpause()
                self.paused = False
                self.status_bar.config(text="Resumed playback")
            else:
                # Pause and remember position
                self.pause_position = pygame.mixer.music.get_pos()  # Get position in milliseconds
                pygame.mixer.music.pause()
                self.paused = True
                self.status_bar.config(text="Playback paused")

    def stop_playback(self):
        if self.playing or self.paused:
            pygame.mixer.music.stop()
            # Release the music file
            try:
                if hasattr(pygame.mixer.music, 'unload'):  # Newer pygame versions
                    pygame.mixer.music.unload()
                else:  # Older versions
                    pygame.mixer.music.stop()
                    pygame.mixer.music.set_endevent()
            except:
                pass
            
            # Clean up temp file
            if self.current_file and os.path.exists(self.current_file):
                try:
                    os.remove(self.current_file)
                except Exception as e:
                    print(f"Cleanup warning: {str(e)}")
            
            self.playing = False
            self.paused = False
            self.pause_position = 0
            self.status_bar.config(text="Playback stopped")

    def download_selected(self):
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to the server first.")
            return
        
        selection = self.music_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a music file to download.")
            return
        
        filename = self.music_listbox.get(selection[0])
        save_path = filedialog.asksaveasfilename(
            initialdir=self.download_dir,
            initialfile=filename,
            defaultextension=".mp3",
            filetypes=[("MP3 Files", "*.mp3"), ("WAV Files", "*.wav"), ("All Files", "*.*")]
        )
        
        if not save_path:
            return
        
        try:
            # Request file from server
            self._send_message(f"PLAY:{filename}")
            response = self._receive_message()
            
            if response != "READY":
                raise ValueError(response)
            
            # Download the file
            self._receive_file(save_path)
            
            messagebox.showinfo("Success", f"File saved to:\n{save_path}")
            self.status_bar.config(text="Download complete")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to download: {str(e)}")
            self.status_bar.config(text=f"Error: {str(e)}")
            if os.path.exists(save_path):
                os.remove(save_path)

    def disconnect(self):
        if not self.connected:
            return
        
        self.stop_playback()
        try:
            self.client_socket.close()
        except:
            pass
        self.client_socket = None
        self.connected = False
        self.status_label.config(text="Status: Disconnected", foreground="red")
        self.status_bar.config(text="Disconnected from server")

if __name__ == "__main__":
    root = Tk()
    client = MusicClient(root)
    root.mainloop()