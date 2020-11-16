import json
import re


class Item:
    def __init__(self, original_name, name, id, description, cost, image_url, wiki_url):
        self.original_name = original_name
        self.name = name
        self.id = id
        self.description = description
        self.cost = cost
        self.image_url = image_url
        self.wiki_url = wiki_url


# Map of overrides from
wiki_url_overrides_map = {}
# Map of items by their respective lower case string names, colloq, or unique words within their name.
items_by_name = {}

# Construct wiki_url_overrides map
with open('data/custom_wiki_links_overrides.json') as json_file:
    data = json.load(json_file)
    for entry in data.values():
        wiki_url_overrides_map[entry['original_name']] = entry['wiki_name_override']


def format_description(description):
    # Regex match on first pass: First find key indicators to translate to bold reddit format.
    description = description.replace('<li>', '\n\n')
    description = description.replace('<active>', "**")
    description = description.replace('</active>', "**")
    description = description.replace('<passive>', "**")
    description = description.replace('</passive>', "**")
    description = description.replace('<rarityMythic>', "**")
    description = description.replace('</rarityMythic>', "**")
    # Next, change all <br> to new lines.
    description = description.replace("<br><br>", '\n\n')
    description = description.replace("<br>", '\n\n')
    # Last, we remove all remaining non <br> tags
    description = re.sub("<[^>]*>", '', description)
    return description


# We want to add items if they're unique. But we don't necessarily want "of" from "blade of the ruined king" or
# "lethality" from the list of valid colloq's to match to multiple items.
def add_if_unique(name_to_add, item):
    if name_to_add in items_by_name.keys():
        del items_by_name[name_to_add]
    else:
        items_by_name[name_to_add] = item

# Formats a string to lower case for consistency and removes all apostrophes
def format_and_add(item_name, item):
    add_if_unique(item_name.lower(), item)
    # Do the same action for apostrophes
    if "'" in item_name.lower():
        non_apostrophe_name = item_name.lower().replace("'", "")
        add_if_unique(non_apostrophe_name, item)

# Temporarily use the items_cache.json as the entire source of truth for this program. Load the JSON into a dictionary
# while performing tons of formatting.
with open('data/items_cache.json') as json_file:
    data = json.load(json_file)
    for item_id_key, obj in data['data'].items():
        item_original_name = obj['name']
        item_name = obj['name'].lower()
        id = item_id_key
        description = format_description(obj['description'])
        cost = obj['gold']['total']
        image_url = 'http://ddragon.leagueoflegends.com/cdn/10.23.1/img/item/' + obj['image']['full']
        # Substitute any items found within the wiki_url_overrides_map as needed.
        wiki_url = 'https://leagueoflegends.fandom.com/wiki/'
        if item_original_name in wiki_url_overrides_map:
            wiki_url += wiki_url_overrides_map[item_original_name]
        else:
            wiki_url += re.sub(' ', "_", item_original_name)
        item = Item(item_original_name, item_name, id, description, cost, image_url, wiki_url)
        # colloq always starts with a ";" so we ignore the first entry during split.
        colloq_list = obj['colloq'].split(';')
        for colloq in colloq_list[1:]:
            format_and_add(colloq, item)
        # There's We want to add "mercurial" or "rageblade" here but not "of" (from Blade Of The Ruined King)
        for word_in_name in item_name.split():
            format_and_add(word_in_name, item)
        items_by_name[item_name] = item
