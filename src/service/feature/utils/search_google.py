import json
from duckduckgo_search import ddg

def google_search(query, num_results=8):
    """
    Return the results of a google search
    """
    search_results = []
    for j in ddg(query, max_results=num_results):
        search_results.append(j)

    return json.dumps(search_results, ensure_ascii=False, indent=4)