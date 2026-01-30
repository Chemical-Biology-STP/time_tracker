"""
Flask server manager for bundled server execution.
"""

import os
import sys
import subprocess
import threading
import time
from pathlib import Path


class ServerManager:
    """Manages the bundled Flask server process."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.process = None
        self.is_running = False
        self.port = 5001
        self._monitor_thread = None
    
    def get_server_path(self) -> Path:
        """Get the path to the bundled server executable."""
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            base_path = Path(sys._MEIPASS)
            server_name = "TimeTrackerServer.exe" if sys.platform == "win32" else "TimeTrackerServer"
            server_path = base_path / server_name
            
            if not server_path.exists():
                # Try alongside the executable
                exe_dir = Path(sys.executable).parent
                server_path = exe_dir / server_name
            
            return server_path
        else:
            # Running from source - look for the server script
            return Path(__file__).parent.parent / "server_standalone.py"
    
    def start_server(self, port: int = 5001):
        """Start the Flask server."""
        if self.is_running:
            return
        
        self.port = port
        server_path = self.get_server_path()
        
        if not server_path.exists():
            print(f"Server not found at {server_path}")
            return
        
        try:
            # Determine how to run the server
            if server_path.suffix == ".py":
                # Running from source
                cmd = [sys.executable, str(server_path)]
            else:
                # Running compiled executable
                cmd = [str(server_path)]
            
            # Set environment for port
            env = os.environ.copy()
            env["PORT"] = str(port)
            
            # Start server process
            self.process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            self.is_running = True
            
            # Start monitor thread
            self._monitor_thread = threading.Thread(target=self._monitor_process, daemon=True)
            self._monitor_thread.start()
            
            # Wait a moment for server to start
            time.sleep(1)
            
            print(f"Server started on port {port}")
            
        except Exception as e:
            print(f"Failed to start server: {e}")
            self.is_running = False
    
    def stop_server(self):
        """Stop the Flask server."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as e:
                print(f"Error stopping server: {e}")
            finally:
                self.process = None
                self.is_running = False
                print("Server stopped")
    
    def _monitor_process(self):
        """Monitor the server process."""
        if self.process:
            self.process.wait()
            self.is_running = False
    
    @classmethod
    def shared(cls) -> "ServerManager":
        """Get the shared instance."""
        return cls()
