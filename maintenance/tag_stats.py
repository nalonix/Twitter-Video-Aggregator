from pymongo import UpdateOne
from datetime import datetime, timezone
from collections import defaultdict
from core.models import Tag, Video
import core.db  # noqa: F401  establishes connection


def ensure_utc(dt):
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def update_tag_metadata():
    """
    Efficiently recalculates and updates total_videos, total_views, and total_size_mb
    for all tags based on the Video collection.
    Uses bulk updates for ~3k+ tags.
    """
    print(f"\n--- Starting Tag Metadata Recalculation ---")

    tag_metrics = defaultdict(lambda: {
        'videos': 0,
        'views': 0,
        'size': 0.0,
    })

    total_videos_processed = 0

    # Step 1: Aggregate metrics
    for video in Video.objects.only('tags', 'view_count', 'size_mb'):
        total_videos_processed += 1

        views = getattr(video, 'view_count', 0)
        size = getattr(video, 'size_mb', 0.0)

        for tag_ref in video.tags:
            if not tag_ref:
                continue  # Skip missing tags

            metrics = tag_metrics[tag_ref.id]
            metrics['videos'] += 1
            metrics['views'] += views
            metrics['size'] += size

        if total_videos_processed % 100 == 0:
            print(f"Processed {total_videos_processed:,} videos...")

    print(f"Aggregated metrics from {total_videos_processed:,} videos.")
    print("Preparing bulk updates...")

    # Step 2: Prepare bulk operations
    bulk_ops = []
    for tag_id, metrics in tag_metrics.items():
        bulk_ops.append(
            UpdateOne(
                {'_id': tag_id},
                {
                    '$set': {
                        'total_videos': metrics['videos'],
                        'total_views': metrics['views'],
                        'total_size_mb': metrics['size'],
                    }
                }
            )
        )

    # Step 3: Run bulk update
    if bulk_ops:
        print(f"Executing bulk update for {len(bulk_ops):,} tags...")
        result = Tag._get_collection().bulk_write(bulk_ops)
        print(f"✅ Updated {result.modified_count:,} Tag records successfully.")
    else:
        print("⚠️ No updates to apply — no tags found in videos.")

    print(f"--- Tag Metadata Recalculation Complete ---\n")


if __name__ == "__main__":
    update_tag_metadata()
