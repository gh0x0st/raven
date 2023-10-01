#!/usr/bin/env python3

import argparse
import errno
import os
import re
import sys
import http.server
import socketserver
from datetime import datetime
from ipaddress import ip_network, ip_address


# Instantiate our FileUploadHandler class
class FileUploadHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.upload_folder = kwargs.pop('upload_folder', None)
        self.allowed_ip = kwargs.pop('allowed_ip', None)
        self.organize_uploads = kwargs.pop('organize_uploads', False)
        super().__init__(*args, **kwargs)

    # Define our handler method for restricting access by client ip
    def restrict_access(self):
        if not self.allowed_ip:
            # Access is permitted by default
            return True  
        
        # Obtain the client ip
        client_ip = ip_address(self.client_address[0])

        # Cycle through each entry in allowed_ips for permitted access
        allowed_ips = self.allowed_ip.split(',')
        for ip in allowed_ips:
            ip = ip.strip()     
            # Check if the entry is in CIDR notation
            if '/' in ip:
                try:
                    network = ip_network(ip, strict=False)
                    if client_ip in network:
                        return True
                except ValueError:
                    pass
            elif client_ip == ip_address(ip):
                return True
            
        # The client ip is not permitted access to the handler
        # Respond back to the client with a 403 status code
        self.send_response(403)
        self.end_headers()
        return False

    # Define our GET handler method
    def do_GET(self):
        if self.path == '/':
            # Check if we are restricting access
            if not self.restrict_access():  
                return

            # Respond back to the client with a 200 status code
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            # Send an HTML response to the client with the upload form
            self.wfile.write(b"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Raven File Upload</title>
            </head>
            <body>
                <form method="POST" enctype="multipart/form-data">
                    <input type="file" name="file">
                    <input type="submit" value="Upload">
                </form>
            </body>
            </html>
            """)

    # Define our POST handler method
    def do_POST(self):
        if self.path == '/':
            # Check if we are restricting access
            if not self.restrict_access():  
                return

            # Inspect incoming multipart/form-data content
            content_type = self.headers['Content-Type']
            if content_type.startswith('multipart/form-data'):
                try:
                    # Extract and parse multipart/form-data content
                    content_length = int(self.headers['Content-Length'])
                    form_data = self.rfile.read(content_length)

                    # Extract the boundary from the content type header
                    boundary = content_type.split('; ')[1].split('=')[1]

                    # Split the form data using the boundary
                    parts = form_data.split(b'--' + boundary.encode())

                    for part in parts:
                        if b'filename="' in part:
                            # Extract the filename from Content-Disposition header
                            headers, data = part.split(b'\r\n\r\n', 1)
                            content_disposition = headers.decode()
                            filename = re.search(r'filename="(.+)"', content_disposition).group(1)

                            # Sanitize the filename based on our requirements
                            filename = sanitize_filename(filename)

                            # Organize uploads into subfolders by client IP otherwise use the default
                            if self.organize_uploads and self.client_address:
                                client_ip = self.client_address[0]
                                upload_folder = os.path.join(self.upload_folder, client_ip)
                                os.makedirs(upload_folder, exist_ok=True)
                                file_path = os.path.join(upload_folder, filename)
                            else:
                                upload_folder = self.upload_folder  
                                file_path = os.path.join(upload_folder, filename)

                            # Generate a unique filename in case the file already exists
                            file_path = prevent_clobber(upload_folder, filename)

                            # Save the uploaded file in binary mode so we don't corrupt any content
                            with open(file_path, 'wb') as f:
                                f.write(data)

                            # Respond back to the client with a 200 status code
                            self.send_response(200)
                            self.end_headers()

                            # Send an HTML response to the client for redirection
                            self.wfile.write(b"""
                            <!DOCTYPE html>
                            <html>
                            <head>
                                <meta http-equiv="refresh" content="3;url=/">
                            </head>
                            <body>
                                <p>File uploaded successfully. Redirecting in 3 seconds...</p>
                            </body>
                            </html>
                            """)

                            # Print the path where the uploaded file was saved to the terminal
                            now = datetime.now().strftime("%d/%b/%Y %H:%M:%S")
                            print(f"{self.client_address[0]} - - [{now}] \"File saved {file_path}\"")
                            return
                except Exception as e:
                    print(f"Error processing the uploaded file: {str(e)}")

            # Something bad happened if we get to this point
            # Error details are provided by http.server on the terminal
            # Respond back to the client with a 400 status code
            self.send_response(400)
            self.end_headers()


# Normalizes the filename, then remove any characters that are not letters, numbers, underscores, dots, or hyphens
def sanitize_filename(filename):
    normalized = os.path.normpath(filename)
    sanitized = re.sub(r'[^\w.-]', '_', normalized)
    return sanitized


# Appends a file name with an incrementing number if it happens to exist already
def prevent_clobber(upload_folder, filename):
    file_path = os.path.join(upload_folder, filename)
    counter = 1
    # Keep iterating until a unique filename is found
    while os.path.exists(file_path):
        base_name, file_extension = os.path.splitext(filename)
        new_filename = f"{base_name}_{counter}{file_extension}"
        file_path = os.path.join(upload_folder, new_filename)
        counter += 1

    return file_path


# Generates the epilog content for argparse, providing usage examples
def generate_epilog():
    examples = [
        "examples:",
        "  Start the HTTP server on all available network interfaces, listening on port 443",
        "  raven 0.0.0.0 443\n",
        "  Start the HTTP server on a specific interface (192.168.0.12), listening on port 443, and restrict access to 192.168.0.4",
        "  raven 192.168.0.12 443 --allowed-ip 192.168.0.4\n",
        "  Start the HTTP server on a specific interface (192.168.0.12), listening on port 443, restrict access to 192.168.0.4, and save uploaded files to /tmp:",
        "  raven 192.168.0.12 443 --allowed-ip 192.168.0.4 --upload-folder /tmp\n",
        "  Start the HTTP server on a specific interface (192.168.0.12), listening on port 443, restrict access to 192.168.0.4, and save uploaded files to /tmp organized by remote client IP",
        "  raven 192.168.0.12 443 --allowed-ip 192.168.0.4 --upload-folder /tmp --organize-uploads",
    ]
    return "\n".join(examples)


def main():
    # Build the parser
    parser = argparse.ArgumentParser(
        description="A lightweight file upload service used for penetration testing and incident response.",
        usage="python3 raven.py <listening_ip> <listening_port> [--allowed-ip <allowed_client_ip>] [--upload-folder <upload_directory>] [--organize-uploads]",
        epilog=generate_epilog(),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Configure our arguments
    parser.add_argument("host", help="The IP address for our http handler to listen on")
    parser.add_argument("port", type=int, help="The port for our http handler to listen on")
    parser.add_argument("--allowed-ip", help="Restrict access to our http handler by IP address (optional)")
    parser.add_argument("--upload-folder", default=os.getcwd(), help="Designate the directory to save uploaded files to (default: current working directory)")
    parser.add_argument("--organize-uploads", action="store_true", help="Organize file uploads into subfolders by remote client IP")

    # Parse the command-line arguments
    args = parser.parse_args()

    # Check if no arguments were provided
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    # Initializing configuration variables
    host = args.host
    port = args.port
    allowed_ip = args.allowed_ip
    upload_folder = args.upload_folder
    organize_uploads = args.organize_uploads
    server = None

    try:
        # Check if the specified upload folder exists, if not try to create it
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        # Create an HTTP server instance with our custom request handling
        server = socketserver.TCPServer((host, port), lambda *args, **kwargs: FileUploadHandler(*args, **kwargs, upload_folder=upload_folder, allowed_ip=allowed_ip, organize_uploads=organize_uploads))

        # Print our handler details to the terminal
        print(f"[*] Serving HTTP on {host} port {port} (http://{host}:{port}/)")

        # Print additional details to the terminal
        if allowed_ip:
            print(f"[*] Listener access is restricted to {allowed_ip}")
        else:
            print(f"[*] Listener access is unrestricted")

        if organize_uploads:
            print(f"[*] Uploads will be organized by client IP in {upload_folder}")
        else:
            print(f"[*] Uploads will be saved in {upload_folder}")

        # Start the HTTP server and keep it running until we stop it
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, exiting.")
    except OSError as ose:
        if ose.errno == errno.EADDRNOTAVAIL:
            print(f"[!] The IP address '{host}' does not appear to be available on this system")
        else:
            print(f"[!] {str(ose)}")
    except Exception as ex:
           print(f"[!] {str(ex)}") 
    finally:
        if server:
            server.server_close()


if __name__ == '__main__':
    main()
