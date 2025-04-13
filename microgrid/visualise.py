import json
import os
import webbrowser
import tempfile
import shutil
import subprocess
import time
import socket
import threading
import http.server
import socketserver

# Path to the visualisation folder
VISUALISE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "visualise")

# Function to find an available port
def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

# HTTP Server class that can be stopped
class StoppableHTTPServer(threading.Thread):
    def __init__(self, directory, port=8000):
        super().__init__(daemon=True)
        self.directory = directory
        self.port = port
        self.server = None
        self.running = False
        
    def run(self):
        handler = http.server.SimpleHTTPRequestHandler
        os.chdir(self.directory)  # Change to the directory to serve
        self.server = socketserver.TCPServer(("", self.port), handler)
        self.running = True
        print(f"Serving at http://localhost:{self.port}")
        self.server.serve_forever()
        
    def stop(self):
        if self.server:
            self.running = False
            self.server.shutdown()
            self.server.server_close()

def visualise(json_file_path, output_dir, open_browser=True):
    """
    Create a visualization of a microgrid network by copying the visualization files and JSON data.
    Serves the files using a local HTTP server to avoid CORS issues.
    
    Args:
        json_file_path (str, optional): Path to the JSON file containing network data.
        output_dir (str, optional): Directory where the visualization files should be saved. If None, a temporary directory is created.
        open_browser (bool, optional): Whether to open the HTML file in a browser. Defaults to True.
    
    Returns:
        str: Path to the output directory.
    """
    # Create output directory if it doesn't exist
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        print(f"Error creating output directory: {e}")
        return None
    
    # Copy the visualization files (HTML, CSS, JS) to the output directory
    try:
        for filename in ['index.html', 'styles.css', 'script.js']:
            source_path = os.path.join(VISUALISE_DIR, filename)
            dest_path = os.path.join(output_dir, filename)
            shutil.copy2(source_path, dest_path)
            print(f"Copied {filename} to {dest_path}")
    except Exception as e:
        print(f"Error copying visualization files: {e}")
        return None
    
    # Copy the JSON file to the output directory as data.json
    try:
        if json_file_path:
            # Copy the JSON file to data.json in the output directory
            dest_json_path = os.path.join(output_dir, 'data.json')
            shutil.copy2(json_file_path, dest_json_path)
            print(f"Copied JSON data to {dest_json_path}")
    except Exception as e:
        print(f"Error handling JSON data: {e}")
    
    print(f"Visualization saved to: {output_dir}")
    
    # Start a local HTTP server to serve the files
    if open_browser:
        try:
            port = find_free_port()
            server = StoppableHTTPServer(output_dir, port)
            server.start()
            
            # Open the browser
            url = f"http://localhost:{port}/index.html"
            print(f"Opening visualization at {url}")
            webbrowser.open(url)
            
            # Keep the server running until user interrupts
            print("Press Ctrl+C to stop the server and exit")
            try:
                while server.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping server...")
                server.stop()
                print("Server stopped")
        except Exception as e:
            print(f"Error starting HTTP server: {e}")

    
    return output_dir


# Command-line interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Create a visualization of a microgrid network from a JSON file.')
    parser.add_argument('json_file', help='Path to the JSON file containing network data')
    parser.add_argument('--output', '-o', help='Directory where the visualization files should be saved')
    parser.add_argument('--no-browser', action='store_true', help='Do not open the HTML file in a browser')
    parser.add_argument('--no-server', action='store_true', help='Do not start a local HTTP server (may cause CORS issues)')
    
    args = parser.parse_args()
    visualise(json_file_path=args.json_file, output_dir=args.output, open_browser=not args.no_browser)
