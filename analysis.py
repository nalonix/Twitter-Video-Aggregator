from db import *  # MongoEngine connection
from models import Video, TrialLog, Tag
from datetime import datetime
from collections import Counter
import statistics

def show_video_stats_fast():
    print("\n📊 FAST VIDEO UPLOAD PERFORMANCE REPORT")
    print("────────────────────────────────────────────")

    # === Quick counts ===
    total_videos = Video.objects.count()
    total_tags = Tag.objects.count()
    total_trials = TrialLog.objects.count()
    total_completed = Video.objects(completed_at__ne=None).count()
    total_failed = TrialLog.objects(status="failed").count()
    items_left = total_videos - total_completed

    # === Aggregations ===
    # Average duration
    avg_duration = (
        TrialLog.objects(duration_seconds__gt=0).average("duration_seconds") or 0
    )

    # Total views (aggregated)
    total_views = (
        Video.objects.aggregate({"$group": {"_id": None, "views": {"$sum": "$view_count"}}})
    )
    total_views = next(total_views, {}).get("views", 0)

    # === Mechanism breakdown ===
    mech_data = {}
    mech_pipeline = TrialLog.objects.aggregate(
        {"$group": {
            "_id": {"mechanism": "$mechanism_name", "status": "$status"},
            "count": {"$sum": 1}
        }}
    )

    mech_results = {}
    for entry in mech_pipeline:
        mech = entry["_id"]["mechanism"]
        status = entry["_id"]["status"]
        mech_results.setdefault(mech, {"total": 0, "failed": 0, "completed": 0})
        mech_results[mech]["total"] += entry["count"]
        if status == "failed":
            mech_results[mech]["failed"] = entry["count"]
        elif status == "completed":
            mech_results[mech]["completed"] = entry["count"]

    for mech, stats in mech_results.items():
        total = stats["total"]
        failed = stats["failed"]
        mech_data[mech] = {
            "total": total,
            "completed": stats["completed"],
            "failed": failed,
            "fail_rate": (failed / total * 100) if total else 0,
        }

    # === Derived metrics ===
    overall_success_rate = (total_completed / total_trials * 100) if total_trials else 0

    # Compute avg retries and tag coverage with one-pass minimal query
    video_fields = Video.objects.only("tags", "trials")
    retry_counts, tag_counts = [], []
    for v in video_fields:
        retry_counts.append(len(v.trials or []))
        tag_counts.append(len(v.tags or []))

    avg_retries = statistics.mean(retry_counts) if retry_counts else 0
    avg_tags_per_video = statistics.mean(tag_counts) if tag_counts else 0
    tag_coverage_rate = (
        sum(1 for c in tag_counts if c > 0) / total_videos * 100
    ) if total_videos else 0

    # === Throughput calculation ===
    completed_times = list(
        Video.objects(completed_at__ne=None).only("completed_at").scalar("completed_at")
    )
    if len(completed_times) > 1:
        first, last = min(completed_times), max(completed_times)
        hours = (last - first).total_seconds() / 3600
        throughput = total_completed / hours if hours > 0 else 0
    else:
        throughput = 0

    # === Top tag ===
    top_tag_doc = Tag.objects.order_by("-total_videos").first()
    top_tag = top_tag_doc.name if top_tag_doc else "N/A"

    # === Print summary ===
    print(f"Total videos:            {total_videos}")
    print(f"Completed uploads:       {total_completed}")
    print(f"Failed uploads:          {total_failed}")
    print(f"Total trials:            {total_trials}")
    print(f"Total tags:              {total_tags}")
    print(f"Items left:              {items_left}")
    print(f"Total views:             {total_views:,}")
    print(f"Average trial duration:  {avg_duration:.2f}s")
    print()
    print(f"Global success rate:     {overall_success_rate:.2f}%")
    print(f"Average retries/video:   {avg_retries:.2f}")
    print(f"Average tags/video:      {avg_tags_per_video:.2f}")
    print(f"Tag coverage rate:       {tag_coverage_rate:.2f}%")
    print(f"Throughput:              {throughput:.2f} videos/hour")
    print(f"Most frequent tag:       {top_tag}")
    print()

    for mech, stats in mech_data.items():
        print(f"🔹 {mech}")
        print(f"   Total trials:     {stats['total']}")
        print(f"   Completed:        {stats['completed']}")
        print(f"   Failed:           {stats['failed']}")
        print(f"   Failure rate:     {stats['fail_rate']:.2f}%")
        print()

    print(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("────────────────────────────────────────────\n")


if __name__ == "__main__":
    show_video_stats_fast()
