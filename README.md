# Music Streaming Application 🎵
![image](https://github.com/user-attachments/assets/2ea3776e-95a6-4778-8c64-ba3e2bbb7085)


A client-server music streaming system with GUI client and multi-threaded server.

## Key Features ✨

### Core Systems 
⚡ **High-Performance Server**
- Custom TCP protocol with length-prefixed messaging
- Multi-threaded client handling (50+ concurrent connections)
- Zero-copy file transfer implementation

⚡ **Advanced Networking**
- Thread-safe socket communication
- Connection timeout/retry mechanisms
- Structured binary data packing/unpacking

### Client Application 
🎨 **User Interface**
- Tkinter-based GUI with playback controls
- Album art visualization
- Real-time metadata display

🔊 **Audio Playback**
- Pygame mixer integration
- Play/pause/stop functionality
- Streaming buffer management

## Technology Stack 🛠️
- **Language:** Python 3.8+
- **Networking:** `socket`, `struct`
- **Concurrency:** `threading`
- **Audio Processing:** `pygame`, `mutagen`
- **GUI:** `tkinter`, `Pillow`
