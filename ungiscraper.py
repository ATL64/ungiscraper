import requests
from bs4 import BeautifulSoup
import urllib.parse
from selenium import webdriver
from urllib.parse import urlparse
import time
import re
import os
import requests
import openai
from scipy.spatial.distance import cosine
import pandas as pd
import textwrap

# Initialize the OpenAI client with your API key
def set_api_key(api_key):
    openai.api_key = api_key

def get_subpages_html(url):
    # Send a GET request
    response = requests.get(url)
    # If the GET request is successful, the status code will be 200
    if response.status_code == 200:
        # Get the content of the response
        page_content = response.content
        # Create a BeautifulSoup object and specify the parser
        soup = BeautifulSoup(page_content, 'html.parser')
        # Find all the anchor tags in the HTML
        # Extract the href attribute and add it to the list of links
        links = [urllib.parse.urljoin(url, link.get('href')) for link in soup.find_all('a') if link.get('href')]
        return links
    else:
        return []
    
def get_subpages_selenium(url):
    # Create a new instance of the Firefox driver
    driver = webdriver.Firefox()

    # Go to the page
    driver.get(url)

    # Get the source of the page
    page_content = driver.page_source

    # Create a BeautifulSoup object and specify the parser
    soup = BeautifulSoup(page_content, 'html.parser')

    # Find all the anchor tags in the HTML
    # Extract the href attribute and add it to the list of links
    links = [urllib.parse.urljoin(url, link.get('href')) for link in soup.find_all('a') if link.get('href')]

    # Close the browser
    driver.quit()

    return links

def get_subpages(url):
    # Get all sublinks
    list_urls = get_subpages_html(url)
    # We'll use this to understand if we needed selenium
    is_selenium = 0
    if len(list_urls)==0:
        final_list = get_subpages_selenium(url)
        is_selenium = 1
    else:
        final_list = list_urls
    # We get the domain because we only want the sublinks that correspond to the domain i.e. no external links
    # For www.example.com, this will give example.com
    domain = urlparse(url).netloc
    domain = domain.replace('www.','')
    # Exclude links out of the domain, and email links
    final_list_clean = [url for url in final_list if domain in url and 'mailto:' not in url]
    # Remove trailing slashes (it will help remove duplicates)
    final_list_clean = [url.rstrip('/') for url in final_list_clean]
    # Remove duplicated elements
    final_list_clean = sorted(list(set(final_list_clean)))
    # Remove PDF files
    final_list_clean = [url for url in final_list_clean if not url.endswith('.pdf')]
    return final_list_clean, is_selenium, domain




def get_clean_text_from_html(html):
    soup = BeautifulSoup(html, 'html.parser')

    # kill all script and style elements
    for script in soup(["script", "style"]):
        script.extract()  # rip it out

    # get text
    text = soup.get_text()

    # break into lines and remove leading and trailing space on each
    lines = (line.strip() for line in text.splitlines())
    # break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # drop blank lines
    text = '\n'.join(chunk for chunk in chunks if chunk)

    return text

# Need to check this one
def get_text_from_url_html(url, big_file, smol_file, directory_name):
    # Send a GET request to the URL
    response = requests.get(url)

    # Parse the HTML content of the page with BeautifulSoup 
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find all text within the HTML and convert the generator to a list
    texts = list(soup.stripped_strings)

    # Create a directory named after the domain if it doesn't exist
    if not os.path.exists(directory_name):
        os.makedirs(directory_name)

    # Append the domain to the file paths
    big_file_path = os.path.join(directory_name, big_file)
    smol_file_path = os.path.join(directory_name, smol_file)
    
    # We will write all of the text into one file (which will end up in a vector DB)
    # We write each page in a smaller file each, for the agent to inspect later on.
    
    # Open the existing file in append mode
    with open(big_file_path, 'a') as f:
        for text in texts:
            # Write each piece of text to the file, followed by a newline
            f.write(text + '\n')

    # Check if smol_file exists, if not, create it
    if not os.path.exists(smol_file_path):
        open(smol_file_path, 'w').close()

    # Open the smol file in write mode
    with open(smol_file_path, 'w') as f:
        for text in texts:
            # Write each piece of text to the file, followed by a newline
            f.write(text + '\n')
            


def get_text_from_url_selenium(url, existing_file, new_file, directory_name):
    # Initialize a new browser
    driver = webdriver.Firefox()

    # Load the webpage
    driver.get(url)
    
    # Wait for the JavaScript to load
    time.sleep(5)

    # Get all text within the body tag
    #soup = BeautifulSoup(driver.page_source, 'html.parser')
    #texts = soup.stripped_strings
    main_html = driver.page_source
    texts = get_clean_text_from_html(main_html)

    # Close the browser
    driver.quit()

    # Create a directory named after the domain if it doesn't exist
    if not os.path.exists(directory_name):
        os.makedirs(directory_name)

    # Append the domain to the file paths
    big_file_path = os.path.join(directory_name, big_file)
    smol_file_path = os.path.join(directory_name, smol_file)
    
    # We will write all of the text into one file (which will end up in a vector DB)
    # We write each page in a smaller file each, for the agent to inspect later on.
    
    # Open the existing file in append mode
    with open(big_file_path, 'a') as f:
        # Write each piece of text to the file, followed by a newline
        f.write(texts + '\n')

    # Check if smol_file exists, if not, create it
    if not os.path.exists(smol_file_path):
        open(smol_file_path, 'w').close()

    # Open the smol file in write mode
    with open(smol_file_path, 'w') as f:
        # Write each piece of text to the file, followed by a newline
        f.write(texts + '\n')          

def get_text_from_url(url, existing_file, new_file, is_selenium, directory_name):
    if is_selenium:
        get_text_from_url_selenium(url, existing_file, new_file, directory_name)
    else:
        get_text_from_url_html(url, existing_file, new_file, directory_name)
            
def list_to_dict(lst, prefix):
    return {f'{prefix}_{i+1}': v for i, v in enumerate(lst)}


def scrape_website(url):
    subpages, is_selenium, domain = get_subpages(url)
    dict_subpages = list_to_dict(subpages, domain.replace('.',''))
    big_file = domain.replace('.','') + '.txt'
    directory_name = domain.replace('.','')
    for index, page in dict_subpages.items():
        smol_file = index +'.txt'
        get_text_from_url(page, big_file, smol_file, is_selenium, directory_name)
    return dict_subpages



def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()
    


def get_embedding(text, model="text-embedding-ada-002"):
    """
    Get the embedding for a given text using the specified model.
    """
    text = text.replace("\n", " ")
    response = openai.embeddings.create(input=[text], model=model)
    return response.model_dump()['data'][0]['embedding']



def split_string(text, length, overlap):
    """
    Splits a string into smaller parts with overlap
    """
    snippets = textwrap.wrap(text, length)
    if overlap > 0:
        snippets = [snippets[i] + snippets[i+1][:overlap] for i in range(len(snippets)-1)] + [snippets[-1]]
    return snippets

def get_embeddings(snippets, model="text-embedding-ada-002"):
    """
    Get embeddings for each snippet
    """
    return [get_embedding(snippet, model=model) for snippet in snippets]

def create_df_from_text_file(file_path, snippet_length=2500, overlap=500):
    """
    Reads a text file, splits it into snippets, generates embeddings for each snippet,
    and returns a DataFrame with the snippets and their embeddings.
    """
    # Read the text file
    with open(file_path, 'r') as file:
        text = file.read()

    # Split the text into snippets
    snippets = split_string(text, snippet_length, overlap)

    # Get embeddings for each snippet
    embeddings = get_embeddings(snippets)

    # Create a DataFrame
    df = pd.DataFrame({
        'snippet_id': range(len(snippets)),
        'text': snippets,
        'embedding': embeddings
    })

    return df


def search_snippets(df, question, n=3, pprint=False):
    # Get the embedding for the input question
    question_embedding = get_embedding(
        question,
        model="text-embedding-ada-002"
    )

    # Compute cosine similarity
    df["similarity"] = df['embedding'].apply(lambda x: 1 - cosine(x, question_embedding))

    # Sort by similarity and get top n results
    results = df.sort_values("similarity", ascending=False).head(n)

    # Pretty print if required
    if pprint:
        for index, row in results.iterrows():
            print(f"Relevant text: {row['text']}\nSnippet ID: {row['snippet_id']}\n ShortText: {row['text'][:200]}\n")

    return results




