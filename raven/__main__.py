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

    # Definer our handler method for restricting access by client ip
    def restrict_access(self):
        if not self.allowed_ip:
            # No IP restriction, allow access
            return True  
        
        # Obtain client ip
        client_ip = ip_address(self.client_address[0])

        # Parse through each entry in allowed_ips
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
            
        # If none of the addresses check out, send a 403
        self.send_response(403)
        self.end_headers()
        return False

    # Define our GET handler method
    def do_GET(self):
        if self.path == '/':
            # Check access restrictions
            if not self.restrict_access():  
                return

            # Send HTTP response status code 200 back to the client
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
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
            # Check access restrictions
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
                            # Extract filename from Content-Disposition header
                            headers, data = part.split(b'\r\n\r\n', 1)
                            content_disposition = headers.decode()
                            filename = re.search(r'filename="(.+)"', content_disposition).group(1)

                            # Sanitize the filename
                            filename = sanitize_filename(filename)

                            # Organize uploads into subfolders by remote client IP
                            if self.organize_uploads and self.client_address:
                                client_ip = self.client_address[0]
                                upload_folder = os.path.join(self.upload_folder, client_ip)
                                os.makedirs(upload_folder, exist_ok=True)
                                file_path = os.path.join(upload_folder, filename)
                            else:
                                upload_folder = self.upload_folder  # Use the original upload folder
                                file_path = os.path.join(upload_folder, filename)

                            # Generate a unique filename in case the file already exists
                            file_path = prevent_clobber(upload_folder, filename)

                            # Save the uploaded file in binary mode
                            with open(file_path, 'wb') as f:
                                f.write(data)

                            # Send HTTP response status code 200 back to the client
                            self.send_response(200)
                            self.end_headers()
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

                            # Print the path where the uploaded file was saved
                            now = datetime.now().strftime("%d/%b/%Y %H:%M:%S")
                            print(f"{self.client_address[0]} - - [{now}] \"File saved {file_path}\"")
                            return
                except Exception as e:
                    print(f"Error processing the uploaded file: {str(e)}")

            # Send HTTP response status code 400 back to the client
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'No file uploaded.')


# Normalizes the filename, then remove any characters that are not letters, numbers, underscores, dots, or hyphens
def sanitize_filename(filename):
    pass1 = os.path.normpath(filename)
    final = re.sub(r'[^\w.-]', '_', pass1)
    return final


# Appends a file name with an incrementing number if it happens to exist already
def prevent_clobber(upload_folder, filename):
    file_path = os.path.join(upload_folder, filename)
    counter = 1

    while os.path.exists(file_path):
        base_name, file_extension = os.path.splitext(filename)
        new_filename = f"{base_name}_{counter}{file_extension}"
        file_path = os.path.join(upload_folder, new_filename)
        counter += 1

    return file_path


def main():
    # Build the parser
    parser = argparse.ArgumentParser(
        description="A lightweight file upload service used for penetration testing and incident response.",
        usage="python3 raven.py <listening_ip> <listening_port> [--allowed-ip <allowed_client_ip>] [--upload-folder <upload_directory>] [--organize-uploads]"
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

    # Initializing variables
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

        # Create our HTTP request handler with the new parameter
        server = socketserver.TCPServer((host, port), lambda *args, **kwargs: FileUploadHandler(*args, **kwargs, upload_folder=upload_folder, allowed_ip=allowed_ip, organize_uploads=organize_uploads))

        # Output HTTP request handler details
        print(f"[*] Serving HTTP on {host} port {port} (http://{host}:{port}/)")

        # Output additional details
        if allowed_ip:
            print(f"[*] Listener access is restricted to {allowed_ip}")
        else:
            print(f"[*] Listener access is unrestricted")

        if organize_uploads:
            print(f"[*] Uploads will be organized by client IP in {upload_folder}")
        else:
            print(f"[*] Uploads will be saved in {upload_folder}")

        # Start our HTTP request handler
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
