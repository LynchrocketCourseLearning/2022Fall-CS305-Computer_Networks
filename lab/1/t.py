import os

path = 'C:/Users/Lynchrocket/Desktop/照片'
MIME = {
    'html': 'text/html',
    'css': 'text/css',
    'gif': 'image/gif',
    'jpg': 'image/jpeg',
    'png': 'image/png',
    'svg': 'image/svg+xml',
    'mp3': 'audio/mp3',
    'mp4': 'video/mp4',
}
for file_name in os.listdir(path):
    names = file_name.split('.')
    file_format = names[1].lower()
    print(MIME[file_format])
