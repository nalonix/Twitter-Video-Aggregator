# Assuming 'LikedVideoDump' is the MongoEngine Document class, 
# 'target_tweet_id' is the string variable holding the ID,
# and 'datetime' and 'timezone' are imported.

target_tweet_id = '1234567890123456789' # Replace with the actual ID

# Use update_one to efficiently set the field without fetching the document first.
num_modified = LikedVideoDump.objects(tweet_id=target_tweet_id).update_one(
    set__grabbed=True
    # Optional: set__processed_at=datetime.now(timezone.utc)
)

print(f"Documents updated: {num_modified}")