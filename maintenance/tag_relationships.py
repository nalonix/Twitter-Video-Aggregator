import core.db  # noqa: F401  establishes connection
import itertools
from collections import defaultdict
from datetime import datetime, timezone
from core.models import RelatedTagEntry, Tag, TagRelationship, Video

# --- Configuration ---
TOP_N_RELATIONSHIPS = 5
TOP_N_TAGS_FOR_CALCULATION = 500  # Only calculate relationships for the most popular 500 tags
LOG_INTERVAL = 200  # Print progress every 200 videos


def calculate_and_store_relationships():
    """
    Calculates tag co-occurrence relationships only for the top N most-used tags.
    Stores results in the TagRelationship collection.
    """

    # --- Phase 0: Identify Top Tags ---
    print(f"\n--- Phase 0: Identifying Top {TOP_N_TAGS_FOR_CALCULATION} Tags ---")

    try:
        top_tags = list(Tag.objects.order_by('-total_videos')[:TOP_N_TAGS_FOR_CALCULATION])
        top_tag_ids = {t.id for t in top_tags}
        print(f"✅ Identified {len(top_tag_ids)} tags for relationship calculation.")
    except Exception as e:
        print(f"❌ ERROR fetching top tags: {e}")
        return

    # --- Phase 1: Co-occurrence Calculation ---
    print(f"\n--- Phase 1: Starting Co-occurrence Analysis ---")
    tag_co_occurrence = defaultdict(lambda: defaultdict(int))

    try:
        total_videos = Video.objects.count()
    except Exception as e:
        print(f"❌ ERROR fetching video count: {e}")
        return

    video_count = 0
    print(f"Total videos to process: {total_videos:,}")

    # Iterate through all videos but only load tags
    for video in Video.objects.only('tags'):
        video_count += 1
        if not video.tags:
            continue

        # Filter to only top 500 tags
        filtered_tags = [t for t in video.tags if t.id in top_tag_ids]
        if len(filtered_tags) < 2:
            continue

        # Count co-occurrences for all unique tag pairs
        for tagA, tagB in itertools.combinations(filtered_tags, 2):
            tag_co_occurrence[tagA.id][tagB.id] += 1
            tag_co_occurrence[tagB.id][tagA.id] += 1

        if video_count % LOG_INTERVAL == 0:
            print(f"Processed {video_count:,}/{total_videos:,} videos...")

    print(f"\n✅ Finished processing {video_count:,} videos.")
    print(f"Generated co-occurrence data for {len(tag_co_occurrence):,} tags.")

    # --- Phase 2: Store Relationships ---
    print(f"\n--- Phase 2: Saving Top {TOP_N_RELATIONSHIPS} Relationships ---")

    # Map Tag IDs to Tag objects for reference
    all_tags_map = {t.id: t for t in Tag.objects.only('id', 'name')}
    update_count = 0

    for primary_tag_id, relations in tag_co_occurrence.items():
        primary_tag_ref = all_tags_map.get(primary_tag_id)
        if not primary_tag_ref:
            continue

        # Sort and limit to strongest relationships
        sorted_relations = sorted(relations.items(), key=lambda x: x[1], reverse=True)
        related_entries = []

        for related_tag_id, weight in sorted_relations[:TOP_N_RELATIONSHIPS]:
            if related_tag_id == primary_tag_id:
                continue
            related_tag_ref = all_tags_map.get(related_tag_id)
            if not related_tag_ref:
                continue

            related_entries.append(RelatedTagEntry(
                tag_ref=related_tag_ref,
                weight=weight,
                tag_name=related_tag_ref.name
            ))

        # Upsert (update if exists, insert if not)
        TagRelationship.objects(primary_tag_ref=primary_tag_ref).update_one(
            upsert=True,
            set__related_tags=related_entries,
            set__last_calculated_at=datetime.now(timezone.utc)
        )
        update_count += 1

    print(f"\n✅ Completed relationship updates for {update_count:,} tags.")
    print(f"Stored top {TOP_N_RELATIONSHIPS} related tags for each of the top {TOP_N_TAGS_FOR_CALCULATION} tags.")


# --- Run ---
if __name__ == "__main__":
    print(f"🏁 Starting processing at {datetime.now(timezone.utc)}")
    calculate_and_store_relationships()
    print(f"🏁 Finished at {datetime.now(timezone.utc)}")
