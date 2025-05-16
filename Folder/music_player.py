import os
import json
import random
import tkinter as tk
from tkinter import colorchooser, commondialog, constants, dnd, filedialog, font, messagebox, scrolledtext, simpledialog, ttk
import pygame
from datetime import timedelta
from PIL import Image, ImageTk
import time

class Song:
    def __init__(self, title, artist, album, file_path, duration=0):
        self.title = title
        self.artist = artist
        self.album = album
        self.file_path = file_path
        self.duration = duration

    def to_dict(self):
        return {
            'title': self.title,
            'artist': self.artist,
            'album': self.album,
            'file_path': self.file_path,
            'duration': self.duration
        }
        
    @classmethod
    def from_dict(cls, data):
        # Create a Song object from dictionary data.
        return cls(
            title=data['title'],
            artist=data['artist'],
            album=data['album'],
            file_path=data['file_path'],
            duration=data.get('duration', 0)  # Handle older saved files without duration
        )
        
    def __str__(self):
        # String representation of the song
        return f"{self.title} - {self.artist}"
        
    def __eq__(self, other):
        if not isinstance(other, Song):
            return False
        return self.file_path == other.file_path

# Global list to track all songs
_all_songs = []

class Playlist:
    """Class representing a playlist of songs."""
    
    # Class variable to track the "All Songs" playlist instance
    all_songs_playlist = None
    
    def __init__(self, name, songs=None):
        self.name = name
        self.songs = songs if songs is not None else []
        self.current_index = 0
        self.shuffle_mode = False
        self.repeat_mode = False
        self._original_order = list(range(len(self.songs)))
        self._shuffled_indices = list(range(len(self.songs)))
        self.queue = []  # Storing queue of songs to play next
        
        # Initialize the "All Songs" playlist if this is the first one with that name
        if name == "All Songs" and Playlist.all_songs_playlist is None:
            Playlist.all_songs_playlist = self
            # Add any existing songs to this playlist
            for song in _all_songs:
                if song not in self.songs:
                    self.songs.append(song)
                    self._original_order.append(len(self._original_order))
                    self._shuffled_indices.append(len(self._shuffled_indices))

    def add_song(self, song):
        """Add a song to the playlist."""
        # Add to the global collection if not already there
        if song not in _all_songs:
            _all_songs.append(song)
            
        # If All Songs playlist exists, add the song there too
        if Playlist.all_songs_playlist is not None and Playlist.all_songs_playlist != self:
            Playlist.all_songs_playlist.add_song(song)
        
        # Add to this playlist if not already present
        if song not in self.songs:
            self.songs.append(song)
            self._original_order.append(len(self._original_order))
            self._shuffled_indices.append(len(self._shuffled_indices))
            if self.shuffle_mode:
                # Re-shuffle to include the new song
                self._apply_shuffle()

    def remove_song(self, index):
        """Remove a song from the playlist by index."""
        if 0 <= index < len(self.songs):
            # Get the actual song being removed
            removed_song = self.songs[index]
            
            # Remove song from the list
            del self.songs[index]
            
            # Update original order by removing the corresponding entry
            # and adjusting all indices greater than the removed one
            removed_original_idx = None
            for i, orig_idx in enumerate(self._original_order):
                if orig_idx == index:
                    removed_original_idx = i
                elif orig_idx > index:
                    # Decrement indices that were after the removed song
                    self._original_order[i] -= 1
            
            if removed_original_idx is not None:
                del self._original_order[removed_original_idx]
            
            # Update shuffled indices in the same way
            removed_shuffled_idx = None
            for i, shuf_idx in enumerate(self._shuffled_indices):
                if shuf_idx == index:
                    removed_shuffled_idx = i
                elif shuf_idx > index:
                    # Decrement indices that were after the removed song
                    self._shuffled_indices[i] -= 1
            
            if removed_shuffled_idx is not None:
                del self._shuffled_indices[removed_shuffled_idx]
            
            # Adjust current index if necessary
            if index <= self.current_index and self.current_index > 0:
                self.current_index -= 1
            elif self.current_index >= len(self.songs):
                self.current_index = max(0, len(self.songs) - 1)

    def _apply_shuffle(self):
        """Apply shuffle to the playlist while preserving current song."""
        if not self.songs:
            return
            
        current_song = self.get_current_song()
        
        # Create a new shuffled list of indices
        self._shuffled_indices = list(range(len(self.songs)))
        random.shuffle(self._shuffled_indices)
        
        # Reorder the songs according to shuffled indices
        new_songs = [self.songs[i] for i in self._shuffled_indices]
        self.songs = new_songs
        
        # Update current index to point to the same song
        if current_song:
            try:
                self.current_index = self.songs.index(current_song)
            except ValueError:
                self.current_index = 0

    def _restore_original_order(self):
        """Restore original order of songs."""
        if not self.songs:
            return
            
        current_song = self.get_current_song()
        
        # Create mapping from shuffled indices back to original indices
        reverse_mapping = {shuffled: original for original, shuffled in enumerate(self._shuffled_indices)}
        
        # Sort by original indices
        sorted_indices = sorted(range(len(self.songs)), key=lambda i: reverse_mapping.get(i, i))
        self.songs = [self.songs[i] for i in sorted_indices]
        
        # Update current index to point to the same song
        if current_song:
            try:
                self.current_index = self.songs.index(current_song)
            except ValueError:
                self.current_index = 0
                
        # Reset shuffled indices
        self._shuffled_indices = list(range(len(self.songs)))

    def toggle_shuffle(self):
        """Toggle shuffle mode on/off."""
        self.shuffle_mode = not self.shuffle_mode
        
        if self.shuffle_mode:
            self._apply_shuffle()
        else:
            self._restore_original_order()
        return True

    def toggle_repeat(self):
        """Toggle repeat mode on/off."""
        self.repeat_mode = not self.repeat_mode
        return True

    def get_current_song(self):
        """Get the current song in the playlist."""
        if not self.songs or self.current_index >= len(self.songs):
            return None
        return self.songs[self.current_index]
    
    def next_song(self):
        """Move to the next song in the playlist."""
        if not self.songs:
            return None
                
        # Check if there are songs in the queue first
        if self.queue:
            next_song = self.queue.pop(0)
            # Find the index of this song in the playlist
            try:
                self.current_index = self.songs.index(next_song)
            except ValueError:
                # If song not in playlist, add it
                self.add_song(next_song)
                self.current_index = self.songs.index(next_song)
            return self.get_current_song()
                    
        # No songs in queue, move to next song in playlist
        if self.current_index < len(self.songs) - 1:
            self.current_index += 1
            return self.get_current_song()
        elif self.repeat_mode:
            # Loop back to beginning if repeat mode is on
            self.current_index = 0
            return self.get_current_song()
        else:
            # If we're at the end and repeat is off, don't change
            return None
                
        return self.get_current_song()
    
    def previous_song(self, current_position=0):
        """
        Move to the previous song in the playlist.
        If current_position > 5000ms (5 seconds), restart the current song instead.
        """
        if not self.songs:
            return None
        
        # If current song has played for more than 5 seconds, restart it
        if current_position > 5000:  # 5000 ms = 5 seconds
            return self.get_current_song()
            
        # Otherwise, move to the previous song
        if self.current_index > 0:
            self.current_index -= 1
        elif self.repeat_mode:
            self.current_index = len(self.songs) - 1
        else:
            return None
            
        return self.get_current_song()
    
    def add_to_queue(self, song):
        """Add a song to the queue."""
        self.queue.append(song)

    def get_queue(self):
        """Get the current queue of songs."""
        return self.queue

    def clear_queue(self):
        """Clear the queue."""
        self.queue = []

    def to_dict(self):
        """Convert playlist object to dictionary for saving."""
        return {
            'name': self.name,
            'songs': [song.to_dict() for song in self.songs],
            'current_index': self.current_index,
            'shuffle_mode': self.shuffle_mode,
            'repeat_mode': self.repeat_mode,
            'queue': [song.to_dict() for song in self.queue]
        }
    
    @classmethod
    def get_all_songs_playlist(cls):
        """Get or create the 'All Songs' playlist."""
        if cls.all_songs_playlist is None:
            cls.all_songs_playlist = cls("All Songs", _all_songs.copy())
        return cls.all_songs_playlist
    
    @classmethod
    def from_dict(cls, data):
        """Create a Playlist object from dictionary data."""
        songs = [Song.from_dict(song_data) for song_data in data['songs']]
        
        # Add all loaded songs to the global collection
        for song in songs:
            if song not in _all_songs:
                _all_songs.append(song)
                
        playlist = cls(name=data['name'], songs=songs)
        playlist.current_index = data['current_index']
        playlist.shuffle_mode = data['shuffle_mode']
        playlist.repeat_mode = data['repeat_mode']
        
        # Load queue if exists in saved data
        if 'queue' in data:
            playlist.queue = [Song.from_dict(song_data) for song_data in data['queue']]
            
        playlist._original_order = list(range(len(songs)))
        playlist._shuffled_indices = list(range(len(songs)))
        
        # If this is the "All Songs" playlist, set it as the class variable
        if data['name'] == "All Songs":
            cls.all_songs_playlist = playlist
            
        return playlist

class MusicPlayer:
    """Main class handling music playback and playlist management."""
    
    def __init__(self):
        # Initialize pygame mixer
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
        self.playlists = []
        self.current_playlist = None
        self.is_playing = False
        self.is_paused = False
        self.current_position = 0
        self.volume = 0.7  # Default volume (0.0 to 1.0)
        pygame.mixer.music.set_volume(self.volume)
        self.play_start_time = 0  # Track when playback started
        
        # Create data directory if it doesn't exist
        self.data_dir = os.path.join(os.path.expanduser("~"), ".music_player")
        os.makedirs(self.data_dir, exist_ok=True)
        self.data_file = os.path.join(self.data_dir, "music_data.json")
        
        # Load saved data if available
        self.load_data()
        
        # Ensure we have an "All Songs" playlist
        self.ensure_all_songs_playlist()
        
        # Set up an end event handler
        self.end_event_set = False
        self.setup_end_event()

    def setup_end_event(self):
        """Set up the end event handler for auto-playing next song."""
        pygame.mixer.music.set_endevent(pygame.USEREVENT + 1)
        self.end_event_set = True

    def check_events(self):
        """Check for pygame events like song ending."""
        song_changed = False
        for event in pygame.event.get():
            if event.type == pygame.USEREVENT + 1:  # Song ended
                # Only try to play next song if we're still in playing state
                if self.is_playing and not self.is_paused:
                    # Reset position before playing next song
                    self.current_position = 0
                    song_changed = self.next_song()
        return song_changed

    def ensure_all_songs_playlist(self):
        """Make sure we have an All Songs playlist."""
        all_songs_playlist = Playlist.get_all_songs_playlist()
        
        # Check if it's already in our playlists
        for playlist in self.playlists:
            if playlist.name == "All Songs":
                return
                
        # If not, add it to our playlists
        self.add_playlist(all_songs_playlist)

    def add_song(self, song):
        """Add a song to the global collection and the All Songs playlist."""
        if song not in _all_songs:
            _all_songs.append(song)
        
        # Add to All Songs playlist
        all_songs_playlist = Playlist.get_all_songs_playlist()
        all_songs_playlist.add_song(song)

    def add_playlist(self, playlist):
        """Add a playlist to the player."""
        # Check if playlist with same name already exists
        for existing in self.playlists:
            if existing.name == playlist.name:
                return False
                
        self.playlists.append(playlist)
        if not self.current_playlist:
            self.current_playlist = playlist
        return True

    def remove_playlist(self, index):
        """Remove a playlist by index."""
        if 0 <= index < len(self.playlists):
            playlist = self.playlists[index]
            # Don't allow removing the All Songs playlist
            if playlist.name == "All Songs":
                return False
                
            # If we're removing the current playlist, set another one as current
            if self.current_playlist == playlist:
                # Find another playlist to set as current
                for p in self.playlists:
                    if p != playlist:
                        self.current_playlist = p
                        break
                else:
                    self.current_playlist = None
                
                # Pause playback if we removed the current playlist
                self.pause()
                        
            # Now remove the playlist
            self.playlists.remove(playlist)
            return True
        return False
    def load_playlist(self, playlist):
        """Load a playlist as the current playlist."""
        if playlist in self.playlists:
            self.current_playlist = playlist
            return True
        return False

    def play(self):
        """Play the current song in the current playlist."""
        if not self.current_playlist:
            return False
                
        current_song = self.current_playlist.get_current_song()
        if not current_song:
            return False
                
        # Check if file exists
        if not os.path.exists(current_song.file_path):
            messagebox.showerror("Error", f"File not found: {current_song.file_path}")
            return False
                
        try:
            if self.is_paused:
                # Resume playback
                pygame.mixer.music.unpause()
                self.is_paused = False
                self.is_playing = True
                # Adjust play_start_time to account for the time spent paused
                self.play_start_time = time.time() - (self.current_position / 1000.0)
            else:
                # Stop any current playback
                pygame.mixer.music.stop()
                
                # Start playing from the beginning or saved position
                pygame.mixer.music.load(current_song.file_path)
                start_pos = self.current_position / 1000.0 if self.current_position > 0 else 0
                pygame.mixer.music.play(start=start_pos)
                
                self.is_playing = True
                self.is_paused = False
                self.play_start_time = time.time() - start_pos
                
                # Reset position if starting a new song
                if self.current_position == 0:
                    self.current_position = 0
                    
            return True
        except Exception as e:
            messagebox.showerror("Playback Error", f"Error playing {current_song.title}: {str(e)}")
            return False

    def pause(self):
        """Pause the current playback."""
        if self.is_playing and not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True
            # Save current position
            self.current_position = self.get_current_position()
            return True
        return False

    def stop(self):
        """Stop the current playback."""
        pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
        self.current_position = 0
        return True

    def next_song(self):
        """Play the next song in the playlist."""
        if not self.current_playlist:
            return False
            
        next_song = self.current_playlist.next_song()
        if next_song:
            # Stop current playback
            self.stop()
            
            # Reset position for the new song
            self.current_position = 0
            
            # Play the new song
            return self.play()
        else:
            # No next song available
            return False

    def previous_song(self):
        """Play the previous song in the playlist."""
        if not self.current_playlist:
            return False
            
        current_pos = self.get_current_position()
        prev_song = self.current_playlist.previous_song(current_pos)
        if prev_song:
            # Stop current playback
            self.stop()
            
            # Reset position for the new song
            self.current_position = 0
            
            # Play the new song
            return self.play()
        else:
            # No previous song available
            return False

    def set_volume(self, volume):
        """Set the playback volume (0.0 to 1.0)."""
        self.volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.volume)
        return True

    def get_current_position(self):
        """Get the current playback position in milliseconds."""
        if self.is_paused:
            return self.current_position
        elif self.is_playing:
            try:
                # Calculate position based on time elapsed since playback started
                elapsed = (time.time() - self.play_start_time) * 1000  # Convert to ms
                return int(elapsed)
            except Exception as e:
                print(f"Error getting position: {e}")
                return 0
        return 0

    def get_song_length(self):
        """Get the length of the current song in milliseconds."""
        if not self.current_playlist:
            return 0
            
        current_song = self.current_playlist.get_current_song()
        if not current_song:
            return 0
            
        # If we already have the duration, return it
        if current_song.duration > 0:
            return current_song.duration * 1000  # Convert seconds to ms
            
        # Otherwise try to get it
        try:
            # This is more reliable than pygame.mixer.Sound
            audio = pygame.mixer.Sound(current_song.file_path)
            length = audio.get_length() * 1000  # Convert to ms
            
            # Cache the duration for future use
            current_song.duration = length / 1000  # Store in seconds
            return length
        except Exception as e:
            print(f"Error getting song length: {e}")
            return 0

    def seek(self, position_ms):
        """Seek to a specific position in the current song."""
        if not self.is_playing and not self.is_paused:
            return False
            
        current_song = self.current_playlist.get_current_song()
        if not current_song:
            return False
            
        # Ensure position is within bounds
        song_length = self.get_song_length()
        position_ms = max(0, min(position_ms, song_length))
        
        # Convert to seconds for pygame
        position_sec = position_ms / 1000.0
        
        # Store current state
        was_paused = self.is_paused
        
        # Stop and restart at new position
        pygame.mixer.music.stop()
        pygame.mixer.music.load(current_song.file_path)
        pygame.mixer.music.play(start=position_sec)
        
        # Restore state
        if was_paused:
            pygame.mixer.music.pause()
            self.is_paused = True
        else:
            self.is_playing = True
            self.is_paused = False
            
        # Update position tracking
        self.current_position = position_ms
        self.play_start_time = time.time() - position_sec
        
        return True

    def toggle_shuffle(self):
        """Toggle shuffle mode for the current playlist."""
        if self.current_playlist:
            return self.current_playlist.toggle_shuffle()
        return False

    def toggle_repeat(self):
        """Toggle repeat mode for the current playlist."""
        if self.current_playlist:
            return self.current_playlist.toggle_repeat()
        return False

    def save_data(self):
        """Save playlists and songs to a JSON file."""
        data = {
            'playlists': [playlist.to_dict() for playlist in self.playlists],
            'current_playlist_index': self.playlists.index(self.current_playlist) if self.current_playlist else -1
        }
        
        try:
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving data: {e}")
            return False

    def load_data(self):
        """Load playlists and songs from a JSON file."""
        if not os.path.exists(self.data_file):
            return False
            
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                
            # Clear existing data
            self.playlists = []
            
            # Load playlists
            for playlist_data in data['playlists']:
                playlist = Playlist.from_dict(playlist_data)
                self.playlists.append(playlist)
                
            # Set current playlist
            current_playlist_index = data.get('current_playlist_index', -1)
            if 0 <= current_playlist_index < len(self.playlists):
                self.current_playlist = self.playlists[current_playlist_index]
            elif self.playlists:
                self.current_playlist = self.playlists[0]
                
            return True
        except Exception as e:
            print(f"Error loading data: {e}")
            return False

class MusicPlayerGUI:
    """Graphical user interface for the music player."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Music Player")
        self.root.geometry("800x600")
        self.root.minsize(800, 600)
        
        # Create the music player
        self.player = MusicPlayer()
        
        # Set up the UI
        self.setup_ui()
        
        # Start the update loop
        self.update_ui()
        
    def setup_ui(self):
        """Set up the user interface."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Split into left (playlists) and right (songs) panes
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Left pane - Playlists
        playlists_frame = ttk.Frame(paned_window)
        paned_window.add(playlists_frame, weight=1)
        
        # Playlists label frame
        playlists_label_frame = ttk.LabelFrame(playlists_frame, text="Playlists")
        playlists_label_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Playlists listbox with scrollbar
        playlists_scrollbar = ttk.Scrollbar(playlists_label_frame)
        playlists_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.playlists_listbox = tk.Listbox(playlists_label_frame, yscrollcommand=playlists_scrollbar.set)
        self.playlists_listbox.pack(fill=tk.BOTH, expand=True)
        playlists_scrollbar.config(command=self.playlists_listbox.yview)
        
        # Bind double-click on playlist
        self.playlists_listbox.bind("<Double-1>", self.on_playlist_double_click)
        
        # Playlist buttons frame
        playlist_buttons_frame = ttk.Frame(playlists_frame)
        playlist_buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Add and Remove playlist buttons
        ttk.Button(playlist_buttons_frame, text="New Playlist", command=self.create_playlist).pack(side=tk.LEFT, padx=5)
        ttk.Button(playlist_buttons_frame, text="Remove Playlist", command=self.remove_playlist).pack(side=tk.LEFT, padx=5)
        
        # Right pane - Songs
        songs_frame = ttk.Frame(paned_window)
        paned_window.add(songs_frame, weight=2)
        
        # Songs label frame
        songs_label_frame = ttk.LabelFrame(songs_frame, text="Songs")
        songs_label_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Songs listbox with scrollbar
        songs_scrollbar = ttk.Scrollbar(songs_label_frame)
        songs_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.songs_listbox = tk.Listbox(songs_label_frame, yscrollcommand=songs_scrollbar.set)
        self.songs_listbox.pack(fill=tk.BOTH, expand=True)
        songs_scrollbar.config(command=self.songs_listbox.yview)
        
        # Bind double-click on song
        self.songs_listbox.bind("<Double-1>", self.on_song_double_click)
        
        # Song buttons frame
        song_buttons_frame = ttk.Frame(songs_frame)
        song_buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Import song button
        ttk.Button(song_buttons_frame, text="Import Songs", command=self.import_songs).pack(side=tk.LEFT, padx=5)
        ttk.Button(song_buttons_frame, text="Remove Song", command=self.remove_song).pack(side=tk.RIGHT, padx=5)
        
        # Playback controls frame
        controls_frame = ttk.LabelFrame(main_frame, text="Playback Controls")
        controls_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Now playing label
        self.now_playing_var = tk.StringVar(value="Not Playing")
        now_playing_label = ttk.Label(controls_frame, textvariable=self.now_playing_var, font=("Arial", 10, "bold"))
        now_playing_label.pack(pady=5)
        
        # Progress bar
        progress_frame = ttk.Frame(controls_frame)
        progress_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.current_time_var = tk.StringVar(value="0:00")
        ttk.Label(progress_frame, textvariable=self.current_time_var).pack(side=tk.LEFT)
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Scale(progress_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                      variable=self.progress_var, command=self.on_progress_change)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.total_time_var = tk.StringVar(value="0:00")
        ttk.Label(progress_frame, textvariable=self.total_time_var).pack(side=tk.LEFT)
        
        # Playback buttons
        buttons_frame = ttk.Frame(controls_frame)
        buttons_frame.pack(pady=5)
        
        # Load button icons
        self.play_icon = self.load_icon("play.png", (24, 24))
        self.pause_icon = self.load_icon("pause.png", (24, 24))
        self.stop_icon = self.load_icon("stop.png", (24, 24))
        self.prev_icon = self.load_icon("previous.png", (24, 24))
        self.next_icon = self.load_icon("next.png", (24, 24))
        self.shuffle_icon = self.load_icon("shuffle.png", (24, 24))
        self.repeat_icon = self.load_icon("repeat.png", (24, 24))
        
        # Create buttons with icons
        ttk.Button(buttons_frame, image=self.prev_icon, command=self.player.previous_song).pack(side=tk.LEFT, padx=5)
        
        self.play_pause_button = ttk.Button(buttons_frame, image=self.play_icon, command=self.toggle_play_pause)
        self.play_pause_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(buttons_frame, image=self.stop_icon, command=self.player.stop).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, image=self.next_icon, command=self.player.next_song).pack(side=tk.LEFT, padx=5)
        
        # Shuffle and repeat buttons
        self.shuffle_button = ttk.Button(buttons_frame, image=self.shuffle_icon, command=self.toggle_shuffle)
        self.shuffle_button.pack(side=tk.LEFT, padx=5)
        
        self.repeat_button = ttk.Button(buttons_frame, image=self.repeat_icon, command=self.toggle_repeat)
        self.repeat_button.pack(side=tk.LEFT, padx=5)
        
        # Volume control
        volume_frame = ttk.Frame(controls_frame)
        volume_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(volume_frame, text="Volume:").pack(side=tk.LEFT)
        
        self.volume_var = tk.DoubleVar(value=self.player.volume * 100)
        volume_scale = ttk.Scale(volume_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                variable=self.volume_var, command=self.on_volume_change)
        volume_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Status bar
        self.status_bar = ttk.Label(main_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Update the UI with current data
        self.update_playlists_display()
        self.update_songs_display()
        
    def load_icon(self, filename, size=(16, 16)):
        """Load an icon image, or return a placeholder if not found."""
        try:
            # Try to load from the icons directory
            icon_path = os.path.join(os.path.dirname(__file__), "icons", filename)
            if os.path.exists(icon_path):
                img = Image.open(icon_path)
                img = img.resize(size, Image.LANCZOS)
                return ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"Error loading icon {filename}: {e}")
            
        # Return a placeholder if icon not found
        return None
        
    def update_ui(self):
        """Update the UI periodically."""
        # Check for song end events
        song_changed = self.player.check_events()
        
        # Update the progress bar and time display
        if self.player.is_playing:
            current_pos = self.player.get_current_position()
            song_length = self.player.get_song_length()
            
            if song_length > 0:
                # Update progress bar - only if user is not currently dragging it
                if not self.progress_bar.instate(['pressed']):
                    progress_percent = (current_pos / song_length) * 100
                    self.progress_var.set(progress_percent)
                
                # Update time display
                current_time = str(timedelta(milliseconds=current_pos)).split('.')[0]
                if current_time.startswith('0:'):
                    current_time = current_time[2:]
                self.current_time_var.set(current_time)
                
                total_time = str(timedelta(milliseconds=song_length)).split('.')[0]
                if total_time.startswith('0:'):
                    total_time = total_time[2:]
                self.total_time_var.set(total_time)
            
            # Update now playing display if song changed
            if song_changed:
                self.update_now_playing()
                self.update_songs_display()  # Update to highlight current song
        
        # Update play/pause button state
        if self.player.is_playing and not self.player.is_paused:
            self.play_pause_button.config(image=self.pause_icon)
        else:
            self.play_pause_button.config(image=self.play_icon)
            
        # Schedule the next update
        self.root.after(100, self.update_ui)
        
    def update_playlists_display(self):
        """Update the playlists listbox with current playlists."""
        self.playlists_listbox.delete(0, tk.END)
        for playlist in self.player.playlists:
            self.playlists_listbox.insert(tk.END, f"{playlist.name} ({len(playlist.songs)} songs)")
            
        # Highlight the current playlist
        if self.player.current_playlist:
            current_index = self.player.playlists.index(self.player.current_playlist)
            self.playlists_listbox.selection_set(current_index)
            self.playlists_listbox.see(current_index)
            
    def update_songs_display(self):
        """Update the songs listbox with songs from the current playlist."""
        self.songs_listbox.delete(0, tk.END)
        
        if not self.player.current_playlist:
            return
            
        for song in self.player.current_playlist.songs:
            duration_str = ""
            if song.duration > 0:
                minutes = int(song.duration) // 60
                seconds = int(song.duration) % 60
                duration_str = f" [{minutes}:{seconds:02d}]"
                
            self.songs_listbox.insert(tk.END, f"{song.title} - {song.artist}{duration_str}")
            
        # Highlight the current song
        current_index = self.player.current_playlist.current_index
        if 0 <= current_index < len(self.player.current_playlist.songs):
            self.songs_listbox.selection_set(current_index)
            self.songs_listbox.see(current_index)
            
    def update_now_playing(self):
        """Update the now playing display."""
        if self.player.is_playing or self.player.is_paused:
            current_song = self.player.current_playlist.get_current_song()
            if current_song:
                self.now_playing_var.set(f"Now Playing: {current_song.title} - {current_song.artist}")
                return
                
        self.now_playing_var.set("Not Playing")
        
    def on_playlist_double_click(self, event):
        """Handle double-click on a playlist to load it."""
        selection = self.playlists_listbox.curselection()
        if not selection:
            return
            
        index = selection[0]
        if 0 <= index < len(self.player.playlists):
            playlist = self.player.playlists[index]
            self.player.load_playlist(playlist)
            self.update_songs_display()
            self.status_bar.config(text=f"Loaded playlist: {playlist.name}")
            
    def on_song_double_click(self, event):
        """Handle double-click on a song to play it."""
        selection = self.songs_listbox.curselection()
        if not selection:
            return
            
        index = selection[0]
        if self.player.current_playlist and 0 <= index < len(self.player.current_playlist.songs):
            # Stop any current playback
            self.player.stop()
            
            # Set the current index and play
            self.player.current_playlist.current_index = index
            success = self.player.play()
            
            if success:
                self.update_now_playing()
                current_song = self.player.current_playlist.get_current_song()
                self.status_bar.config(text=f"Now playing: {current_song.title}")
            else:
                self.status_bar.config(text="Error playing song")
                
    def on_progress_change(self, value):
        """Handle user changing the progress bar position."""
        if not self.player.is_playing and not self.player.is_paused:
            return
            
        # Convert value to float and calculate position
        value = float(value)
        song_length = self.player.get_song_length()
        position_ms = (value / 100) * song_length
        
        # Only seek if the user is actually dragging the slider
        # This check was causing issues - we'll use a different approach
        self.player.seek(position_ms)
            
    def on_volume_change(self, value):
        """Handle user changing the volume slider."""
        value = float(value) / 100  # Convert to 0-1 range
        self.player.set_volume(value)
        
    def toggle_play_pause(self):
        """Toggle between play and pause states."""
        if self.player.is_playing:
            if self.player.is_paused:
                success = self.player.play()  # Resume
                if success:
                    self.status_bar.config(text="Playback resumed")
            else:
                success = self.player.pause()
                if success:
                    self.status_bar.config(text="Playback paused")
        else:
            # Start playing the current song
            success = self.player.play()
            if success:
                self.update_now_playing()
                self.status_bar.config(text="Playback started")
            else:
                self.status_bar.config(text="No song to play")
                
    def toggle_shuffle(self):
        """Toggle shuffle mode for the current playlist."""
        if self.player.toggle_shuffle():
            shuffle_state = "on" if self.player.current_playlist.shuffle_mode else "off"
            self.status_bar.config(text=f"Shuffle mode: {shuffle_state}")
            self.update_songs_display()
            
    def toggle_repeat(self):
        """Toggle repeat mode for the current playlist."""
        if self.player.toggle_repeat():
            repeat_state = "on" if self.player.current_playlist.repeat_mode else "off"
            self.status_bar.config(text=f"Repeat mode: {repeat_state}")
            
    def create_playlist(self):
        """Create a new playlist."""
        name = simpledialog.askstring("New Playlist", "Enter playlist name:")
        if name:
            # Check if name already exists
            for playlist in self.player.playlists:
                if playlist.name == name:
                    messagebox.showerror("Error", "A playlist with this name already exists.")
                    return
                    
            # Create and add the playlist
            new_playlist = Playlist(name)
            if self.player.add_playlist(new_playlist):
                self.update_playlists_display()
                self.player.save_data()
                self.status_bar.config(text=f"Created playlist: {name}")
            else:
                self.status_bar.config(text="Failed to create playlist")
                
    def remove_playlist(self):
        """Remove the selected playlist."""
        selection = self.playlists_listbox.curselection()
        if not selection:
            return
            
        index = selection[0]
        if 0 <= index < len(self.player.playlists):
            playlist = self.player.playlists[index]
            
            # Don't allow removing the All Songs playlist
            if playlist.name == "All Songs":
                messagebox.showerror("Error", "Cannot remove the All Songs playlist.")
                return
                
            # Confirm deletion
            if messagebox.askyesno("Confirm Delete", f"Delete playlist '{playlist.name}'?"):
                if self.player.remove_playlist(index):
                    self.update_playlists_display()
                    self.update_songs_display()
                    self.player.save_data()
                    self.status_bar.config(text=f"Removed playlist: {playlist.name}")
                else:
                    self.status_bar.config(text="Failed to remove playlist")
                    
    def remove_song(self):
        """Remove the selected song from the current playlist."""
        selection = self.songs_listbox.curselection()
        if not selection or not self.player.current_playlist:
            return
            
        index = selection[0]
        if 0 <= index < len(self.player.current_playlist.songs):
            song = self.player.current_playlist.songs[index]
            
            # Confirm deletion
            if messagebox.askyesno("Confirm Delete", f"Remove '{song.title}' from '{self.player.current_playlist.name}'?"):
                # If this is the currently playing song, stop playback
                if self.player.is_playing and self.player.current_playlist.current_index == index:
                    self.player.stop()
                    
                # Remove the song
                self.player.current_playlist.remove_song(index)
                
                # Update the display
                self.update_songs_display()
                self.update_now_playing()
                self.status_bar.config(text=f"Removed song: {song.title}")
                
                # Save the updated data
                self.player.save_data()
                    
    def import_songs(self):
        """Import songs from files."""
        file_paths = filedialog.askopenfilenames(
            title="Select Music Files",
            filetypes=[
                ("Audio Files", "*.mp3 *.wav *.ogg *.flac"),
                ("All Files", "*.*")
            ]
        )
        
        if not file_paths:
            return
            
        imported_count = 0
        for file_path in file_paths:
            # Extract song info from filename
            filename = os.path.basename(file_path)
            name, _ = os.path.splitext(filename)
            
            # Try to parse artist and title from filename (assuming "Artist - Title" format)
            parts = name.split(" - ", 1)
            if len(parts) == 2:
                artist, title = parts
            else:
                # If can't parse, use filename as title and "Unknown" as artist
                title = name
                artist = "Unknown"
                
            # Create song object
            song = Song(title=title, artist=artist, album="Unknown", file_path=file_path)
            
            # Add to player and current playlist
            self.player.add_song(song)
            if self.player.current_playlist and self.player.current_playlist.name != "All Songs":
                self.player.current_playlist.add_song(song)
                
            imported_count += 1
            
        # Update UI
        self.update_songs_display()
        self.player.save_data()
        self.status_bar.config(text=f"Imported {imported_count} songs")
        
    def on_closing(self):
        """Handle window closing event."""
        # Stop playback
        self.player.stop()
        
        # Save data
        self.player.save_data()
        
        # Close the window
        self.root.destroy()

def main():
    # Initialize pygame with proper settings
    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
    
    # Create the main window
    root = tk.Tk()
    app = MusicPlayerGUI(root)
    
    # Set up closing event
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Start the main loop
    root.mainloop()

if __name__ == "__main__":
    main()