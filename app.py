import os
import csv
import requests
from flask import Flask, request, redirect, url_for, render_template, send_file
from werkzeug.utils import secure_filename
import pandas as pd
import re

# Initialize Flask app
app = Flask(__name__)
app.config['DEBUG'] = True

# Set upload folder and allowed extensions
UPLOAD_FOLDER = 'uploads/'
OUTPUT_FOLDER = 'output/'
ALLOWED_EXTENSIONS = ['tsv', 'csv']

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route for the homepage
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle file upload and metadata fetching
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)

    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process the uploaded file and fetch metadata
        processed_file = process_file(filepath, request.form.getlist('options'))
        
        # Return the output file as download
        return send_file(processed_file, as_attachment=True)
    return redirect(url_for('index'))

# Function to process the file and fetch MediaWiki metadata
def process_file(filepath, options):
    # Read the uploaded TSV/CSV file
    df = pd.read_csv(filepath, engine='python' , sep=',')

    print(df)
    
    # Create output file
    output_filename = 'output.tsv'
    output_filepath = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
    
    # Open output TSV for writing
    with open(output_filepath, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t')
        
        # Write headers based on selected options
        headers = ['Title']
        if 'description' in options:
            headers.append('Description')
        if 'creation_date' in options:
            headers.append('Creation Date')
        if 'author' in options:
            headers.append('Author')
        if 'license' in options:
            headers.append('License Information')


        writer.writerow(headers)
        
        # Iterate through the titles and fetch metadata from MediaWiki API
        for title in df['Title']:  # Assuming the file has a 'Title' column
            metadata = fetch_metadata(title)
            row = [title]
            if 'description' in options:
                row.append(metadata.get('description', 'N/A'))
            if 'creation_date' in options:
                row.append(metadata.get('creation_date', 'N/A'))
            if 'author' in options:
                row.append(metadata.get('author', 'N/A'))
            if 'license' in options:
                row.append(metadata.get('license', 'N/A'))

            writer.writerow(row)

    return output_filepath

# Function to fetch metadata using the MediaWiki API
def fetch_metadata(title):


    url = f"http://en.wikipedia.org/w/api.php?action=query&prop=imageinfo&iiprop=extmetadata&titles=File%3a{title}&format=json"


    response = requests.get(url)
    data = response.json()
    
    page = next(iter(data['query']['pages'].values()))

    author_html = page['imageinfo'][0]['extmetadata'].get('Artist', {}).get('value', 'N/A')

# Check if the author name is in HTML format
    if '<a ' in author_html:
        # Using regex to extract the name from the HTML
        author_name_match = re.search(r'>(.*?)<', author_html)
        if author_name_match:
            author = author_name_match.group(1)  # Extract the name without HTML tags
        else:
            author = 'N/A'
    else:
        author = author_html
    
    
    metadata = {
        'description': page['imageinfo'][0]['extmetadata'].get('ImageDescription', {}).get('value', 'N/A'),
        'creation_date': page['imageinfo'][0]['extmetadata'].get('DateTime', {}).get('value', 'N/A'),
        'author': author,
        'license': page['imageinfo'][0]['extmetadata'].get('LicenseShortName', {}).get('value', 'N/A'),

    }
    return metadata

if __name__ == '__main__':
    app.run(debug=True)
