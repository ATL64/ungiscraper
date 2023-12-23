# ungiscraper
Universal web scraper to extract text for GPT text mining.

```
import ungiscraper as ungi
scrape_dict = ungi.scrape_website('https://www.example.com')
```

This will get all non PDF pages of the website (it will consider all domain pages, excluding any external links in the pages), and 
- Download the text of each into a separate text file
- Make a separate text file with all text of all pages together
- Return a dict that maps the filenames and the exact urls of pages scraped

The scraper will handle simple HTML based pages, and detect if there is JS loading HTML dynamically for which it will proceed to use Selenium.

For the big text file, one might want to "ask" a question with GPT, for which we use ADA embeddings provided by OpenAI.
For example,
```
embedded_example = ungi.create_df_from_text_file('examplecom/examplecom.txt')
```
will return a pandas dataframe built in the following manner:
1. Split all the text into chunks (one can specify length of chunks and overlap defaulted at 2500 and 500 characters respectively)
2. Store all of these in rows of a dataframe
3. Make a new column where the embedding of each text snippet is stored

Finally, one can search for snippets that best match an input question. To do so:

```
ungi.search_snippets(embedded_example, 'What does parallel connection mean? ', n=3, pprint=True)
```
which will give the top 3 matching results of text snippets in the dataframe. For more info check the comments in the file.

