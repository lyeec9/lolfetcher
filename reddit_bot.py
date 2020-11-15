import getpass
import time
import praw
import re
import signal, sys
import json

# Testing bool for deployment purposes
dry_run = True

reddit = praw.Reddit("lolfetcher")

subreddit_string = ''
with open('data/subreddits.txt', 'r') as f:
    for i in f:
        subreddit_string += i.replace("\n", "+")
    subreddit_string = subreddit_string.rstrip("+")

subreddits = reddit.subreddit(subreddit_string)

# This loads the already parsed comments from a backup text file into memory
already_done = []
with open('data/lolfetcher_done.txt', 'r') as f:
    for i in f:
        already_done.append(i.replace("\n", ""))

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

#Construct wiki_url_overrides map
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
            # There's too many colloq items named "Lethality" for instance
            if colloq.lower() in items_by_name.keys():
                del items_by_name[colloq.lower()]
            else:
                items_by_name[colloq.lower()] = item
        # There's We want to add "mercurial" or "rageblade" here but not "of" (from Blade Of The Ruined King)
        for word_in_name in item_name.split():
            if word_in_name.lower() in items_by_name.keys():
                del items_by_name[word_in_name.lower()]
            else:
                items_by_name[word_in_name.lower()] = item
        items_by_name[item_name] = item

def bot_comments():
    ids = []
    sub_comments = subreddits.comments()
    for comment in sub_comments:
        ids.append(comment.id)
        # Checks if the post is not actually the bot itself (since the details include square brackets)
        if comment.id not in already_done and not str(comment.author) == "lolfetcher":
            reply = construct_reply(comment.body)
            if reply:
                try:
                    if dry_run:
                        print(reply)
                    else:
                        comment.reply(reply)
                        already_done.append(comment.id)
                except Exception as e:
                    print(str(e))
    # Finally, return the list of parsed comments
    return ids

# This function is nearly the same as comment parsing, except it takes submissions (should be combined later)
def bot_submissions():
    sub_ids = []
    sub_subs = subreddits.new(limit=5)
    for submission in sub_subs:
        sub_ids.append(submission.id)
        if submission.id not in already_done:
            reply = construct_reply(submission.selftext)
            if reply:
                try:
                    if dry_run:
                        print(reply)
                    else:
                        submission.reply(reply)
                        already_done.append(submission.id)
                except Exception as e:
                    print(str(e))
    return sub_ids

# Constructs the reply to a post or comment
def construct_reply(string):
    # Regex Magic that finds the text encaptured with [[ ]]
    requests = re.findall("\[\[([^\[\]]*)\]\]", string.replace("\\", ""))
    reply = ""
    # Because a comment can only have a max length, limit to only the first 10 requests
    if len(requests) == 0:
        return False
    if len(requests) > 10:
        requests = requests[0:10]
    # We need to remove duplicate objects by their real name, not just the requested name.
    replied_item_names = []
    for index, request in enumerate(requests):
        print(request.lower())
        requested_name = request.lower().split('/')[0]
        # Checks if a corresponding item exists. This is an exact match for now
        if requested_name in items_by_name:
            item = items_by_name[requested_name]
            real_item_name = item.name
            if real_item_name not in replied_item_names:
                reply += "[%s](%s)\n\n%s\n\n" % (item.original_name, item.wiki_url, item.description)
                reply += "-----\n\n"
                replied_item_names.append(real_item_name)
    # Can be empty int
    if reply == "":
        return False
    reply += re.sub(' ', ' ^^', " Call this bot with [[Item Name]].\n\n")
    return reply

# Function that backs up current parsed comments
def write_done():
    with open("data/lolfetcher_done.txt", "w+") as f:
        for i in already_done:
            f.write(str(i) + '\n')

# Function that is called when ctrl-c is pressed. It backups the current parsed comments into a backup file and then quits.
def signal_handler(signal, frame):
    write_done()
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

# Infinite loop that calls the function. The function outputs the post-ID's of all parsed comments.
# The ID's of parsed comments is compared with the already parsed comments so the list stays clean
# and memory is not increased. It sleeps for 15 seconds to wait for new posts.
while True:
    ids = bot_comments()
    time.sleep(5)
    sub_ids = bot_submissions()
    new_done = []
    # Checks for both comments and submissions
    for i in already_done:
        if i in ids:
            new_done.append(i)
        if i in sub_ids:
            new_done.append(i)
    already_done = new_done[:]
    # Back up the parsed comments to a file
    print('loop complete')
    write_done()
    time.sleep(15)