# Raven

Raven is a Python tool that extends the capabilities of the `http.server` Python module by offering a self-contained file upload web server. While the common practice is to use `python3 -m http.server 80` to serve files for remote client downloads, Raven addresses the need for a similar solution when you need the ability to receive files from remote clients. This becomes especially valuable in scenarios such as penetration testing and incident response procedures when protocols such as SMB may not be a viable option.

### Key Features

While the majority of the hard work is already being handled by the http.server module, it presents us with an opportunity to implement additional security and ease of use features without overcomplicating the overall implementation. These features currently include:

- **IP Access Restrictions**: Optionally grants the ability to restrict access based on client IP addresses. You can define this access via a single IP, a comma-delimited list or by using CIDR notation.

- **Organized Uploads**: Optionally organizes uploaded files into subfolders based on the remote client's IP address in a named or current working directory. Otherwise the default behavior will upload files in the current working directory.

- **File Sanitation**: Sanitizes the name of each uploaded file prior to being saved to disk to help prevent potential abuse.

- **Clobbering**: Verifies that the file does not already exist before it's written to disk. If it already exists, an incrementing number is appended to the filename to prevent clashes and ensure no data is overwritten.

- **Detailed Logging**: Raven provides detailed logging of file uploads and interaction with the http server, including the status codes sent back to a client, its IP address, timestamp, and the saved file's location in the event a file is uploaded.

## Usage

Raven is straightforward to use and includes simple command-line arguments to manage the included feature sets:

```bash
python3 raven.py <listening_ip> <listening_port> [--allowed-ip <allowed_client_ip>] [--upload-folder <folder>] [--organize-uploads]
```

* <listening_ip>: The IP address for our http handler to listen on
* <listening_port>: The port for our http handler to listen on
* --allowed-ip <allowed_client_ip>:Restrict access to our http handler by IP address (optional)
* --upload-folder <folder>: "Designate the directory to save uploaded files to (default: current working directory)
* --organize-uploads: Organize file uploads into subfolders by remote client IP

## Installation

Install from GitHub

1. Clone the Repository

   ```bash
   git clone https://github.com/gh0x0st/raven.git
   cd raven
   ```
   
2. Install using pip3

   ```bash
   pip3 install .
   ```

3. Add /home/USER/./local/bin to your PATH environment variable

   ```bash
   echo 'export PATH="/home/kali/.local/bin:$PATH"' >> ~/.zshrc
   source ~/.zshrc
   ```

## Examples

Start the HTTP server on all available network interfaces, listening on port 443:

`raven 0.0.0.0 443`

Start the HTTP server on all on a specific interface (192.168.0.12), listening on port 443 and restrict access to 192.168.0.4:

`raven 192.168.0.12 443 --allowed-ip 192.168.0.4`

Start the HTTP server on all on a specific interface (192.168.0.12), listening on port 443, restrict access to 192.168.0.4 and save uploaded files to /tmp:

`raven 192.168.0.12 443 --allowed-ip 192.168.0.4 --upload-folder /tmp`

Start the HTTP server on all on a specific interface (192.168.0.12), listening on port 443, restrict access to 192.168.0.4 and save uploaded files to /tmp organized by remote client ip:

`raven 192.168.0.12 443 --allowed-ip 192.168.0.4 --upload-folder /tmp --organize-uploads`

## Scripted Uploads

Uploading files using PowerShell:

```powershell
# Listener
$Uri = "http://192.168.0.12:443/"

# Target File
$File = Get-Item "C:\Path\To\File"
$Content = [System.IO.File]::ReadAllBytes($File.FullName)
$Boundary = [System.Guid]::NewGuid().ToString()

# Request Headers
$Headers = @{
    "Content-Type" = "multipart/form-data; boundary=$Boundary"
}

# Request Body
$Body = @"
--$Boundary
Content-Disposition: form-data; name="file"; filename="$($File.Name)"
Content-Type: application/octet-stream

$Content

--$Boundary--
"@

# Upload File
Invoke-WebRequest -UseBasicParsing -Uri $Uri -Method "POST" -Headers $Headers -Body $Body
```

Uploading files using Python3:

```python
#!/usr/bin/env python3

import requests
import uuid

# Listener
url = "http://192.168.0.12:443/"

# Target File
file_path = "/path/to/file"
file_name = file_path.split("/")[-1]
with open(file_path, "rb") as file:
    file_content = file.read()
boundary = str(uuid.uuid4())

# Request Headers
headers = {
    "Content-Type": f"multipart/form-data; boundary={boundary}"
}

# Request Body
body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="{file_name}"\r\n'
    "Content-Type: application/octet-stream\r\n\r\n"
    f"{file_content.decode('ISO-8859-1')}\r\n"
    f"--{boundary}--\r\n"
)

# Upload File
requests.post(url, headers=headers, data=body)
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
