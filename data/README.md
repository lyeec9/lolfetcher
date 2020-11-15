## items_cache.json
For the first iteration of this tool, items_cache.json will be the source of truth for items data without going through 
Riot's API. Since this data gets manually updated per version, manual commits to Git are necessary for the time being. 
Likewise, the image URL within reddit_bot.py needs to change to reflect the new data.

## custom_wiki_links_overrides.json
The majority of items named by Riot in their Items API can be translated directly to a wiki link by directly
appending the item's name to the end of the wiki/ url. There are some exceptions (such as "Blade of The Ruined King") 
that need to be mapped manually. Additional testing is needed to ensure that all existing items will continue to map 
to their respective wiki links.
