import time
import praw
import re
import signal, sys
from items import items_by_name

# Testing bool for deployment purposes
dry_run = True

reddit = praw.Reddit("lolfetcher")

# Parse all valid subreddits
subreddit_string = ''
with open('data/subreddits.txt', 'r') as f:
    for i in f:
        subreddit_string += i.replace("\n", "+")
    subreddit_string = subreddit_string.rstrip("+")

subreddits = reddit.subreddit(subreddit_string)

# New comments that are completed with each new loop of the program.
# Gets added to already_done and wiped with each loop. Having a separate new_done cache does not save us memory, but it
# does make writing to the lolfetcher_done.txt file faster since we don't need to rewrite already_done with every loop.
new_done = []
# This loads the already parsed comments from a backup text file into memory
already_done = []
with open('data/lolfetcher_done.txt', 'r') as f:
    for i in f:
        already_done.append(i.replace("\n", ""))


# Lastly, add name overrides to the data file.
def bot_comments():
    ids = []
    sub_comments = subreddits.comments()
    for comment in sub_comments:
        ids.append(comment.id)
        # Checks if the post is not actually the bot itself (since the details include square brackets)
        if comment.id not in already_done and comment.id not in new_done and not str(comment.author) == "lolfetcher":
            reply = construct_reply(comment.body, comment.id)
            if reply:
                try:
                    if dry_run:
                        print(reply)
                    else:
                        comment.reply(reply)
                except Exception as e:
                    print(str(e))
                new_done.append(comment.id)
    # Finally, return the list of parsed comments
    return ids


# This function is nearly the same as comment parsing, except it takes submissions
def bot_submissions():
    sub_ids = []
    sub_subs = subreddits.new(limit=5)
    for submission in sub_subs:
        sub_ids.append(submission.id)
        if submission.id not in already_done and submission.id not in new_done:
            reply = construct_reply(submission.selftext, submission.id)
            if reply:
                try:
                    if dry_run:
                        print(reply)
                    else:
                        submission.reply(reply)
                except Exception as e:
                    print(str(e))
                new_done.append(submission.id)
    return sub_ids


# Constructs the reply to a post or comment.
def construct_reply(string, id):
    # Regex Magic that finds the text encaptured with [[ ]]
    requests = re.findall("\[\[([^\[\]]*)\]\]", string.replace("\\", ""))
    reply = ""
    # Because a comment can only have a max length, limit to only the first 5 requests
    if len(requests) == 0:
        return False
    if len(requests) > 5:
        requests = requests[0:5]
    # We need to remove duplicate objects by their real name, not just the requested name.
    replied_item_names = []
    for index, request in enumerate(requests):
        request = request.lower().strip()
        print(request + " " + id)
        requested_name = request.split('/')[0]
        # Checks if a corresponding item exists. This is an exact match for now
        if requested_name in items_by_name:
            item = items_by_name[requested_name]
            real_item_name = item.name
            if real_item_name not in replied_item_names:
                reply += "[%s](%s)\n\n%s\n\n" % (item.original_name, item.wiki_url, item.description)
                reply += "-----\n\n"
                replied_item_names.append(real_item_name)
    # Empty in the case where requests are not valid. We don't want to attempt these same comments multiple times.
    if reply == "":
        new_done.append(id)
        return False
    reply += re.sub(' ', ' ^^', " Call this bot with [[Item Name]].\n\n")
    return reply


# Function that backs up current parsed comments
def write_done():
    # Add all newly parsed comments to the existing list in memory
    already_done.extend(new_done)
    # Write the newly parsed comments to the text file
    with open("data/lolfetcher_done.txt", "a") as f:
        for new_done_id in new_done:
            f.write(str(new_done_id) + '\n')
    # clear the new comments cache.
    new_done.clear()


# Function that is called when ctrl-c is pressed. Backups the current parsed comments into a backup file and then quits.
def signal_handler(signal, frame):
    write_done()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

loop_counter = 0
# Infinite loop that calls the function. The function outputs the post-ID's of all parsed comments.
while True:
    comment_ids = bot_comments()
    time.sleep(5)
    sub_ids = bot_submissions()
    # Back up the parsed comments to a file
    print('loop complete. %s new comments or posts analyzed.' % (len(new_done)))
    write_done()
    time.sleep(25)
