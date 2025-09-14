# Background tasks for CSV processing
import os
import uuid

from src.celery_app import celery_app
from src.compact_processor import CompactTransactionProcessor


@celery_app.task(bind=True, name="src.tasks.process_csv_async")
def process_csv_async(
    self,
    csv_path: str,
    api_key: str,
    model: str = "gpt-4o-mini",
    provider: str = "OpenAI",
    batch_size: int = 20,
    verify_domains: bool = True,
):
    """Process CSV file asynchronously with progress tracking."""

    try:
        # Update initial status
        print("[PROGRESS] Task started - Reading CSV file...")
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": 0,
                "status": "Reading CSV file...",
                "stage": "initialization",
            },
        )

        # Generate unique batch ID for this processing run
        batch_id = str(uuid.uuid4())

        # Initialize processor
        processor = CompactTransactionProcessor(api_key, verify_domains)
        processor.categorizer.model = model
        processor.categorizer.provider = provider
        processor.categorizer.verify_domains = verify_domains

        # Read CSV using shared utility
        all_transactions = processor.read_csv_file(csv_path)
        total_transactions = len(all_transactions)

        # Update progress
        print(f"[PROGRESS] CSV loaded - Found {total_transactions} transactions")
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": total_transactions,
                "status": f"Processing {total_transactions} transactions...",
                "stage": "processing",
            },
        )

        # Process transactions in batches with progress updates
        results = []
        vendor_cache = {}

        # AI Processing phase
        print(
            f"[PROGRESS] Starting AI categorization for {total_transactions} transactions..."
        )
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": total_transactions,
                "status": "Starting AI categorization...",
                "stage": "ai_processing",
            },
        )

        # Create a progress callback for the AI processing
        def progress_callback(percent, status):
            print(f"[PROGRESS] {percent}% - {status}")
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": int(total_transactions * percent / 100),
                    "total": total_transactions,
                    "status": status,
                    "stage": "ai_processing",
                },
            )

        batch_results = processor.categorizer.categorize_batch_ultra_fast(
            all_transactions, batch_size=batch_size, progress_callback=progress_callback
        )

        # Database saving phase - use optimized processor method
        results = processor.process_transactions_batch(
            all_transactions,
            batch_results,
            vendor_cache,
            progress_callback=lambda current, total, status: self.update_state(
                state="PROGRESS",
                meta={
                    "current": current,
                    "total": total,
                    "status": status,
                    "stage": "database_save",
                },
            ),
            batch_id=batch_id,
        )

        # Database commit is handled by the processor
        print(
            f"[PROGRESS] ✅ Processing completed! {len(results)} transactions processed successfully"
        )
        processor.close()

        # Clean up temporary file if it was uploaded
        if csv_path.startswith("/tmp/"):
            try:
                os.remove(csv_path)
            except OSError:
                pass  # File might have been already removed

        return {
            "status": "completed",
            "total_processed": len(results),
            "vendors_found": len(vendor_cache),
            "results_summary": {
                "vendor_payments": len(
                    [r for r in results if r["category"] == "vendor_payment"]
                ),
                "total_amount": sum([abs(r["amount"]) for r in results]),
                "avg_confidence": sum([r["category_confidence"] for r in results])
                / len(results)
                if results
                else 0,
            },
        }

    except Exception as e:
        # Clean up on error
        if csv_path.startswith("/tmp/"):
            try:
                os.remove(csv_path)
            except OSError:
                pass

        self.update_state(
            state="FAILURE",
            meta={"status": "failed", "error": str(e), "stage": "error"},
        )
        raise


@celery_app.task(name="src.tasks.get_task_status")
def get_task_status(task_id: str):
    """Get the status of a background task."""
    result = celery_app.AsyncResult(task_id)

    if result.state == "PENDING":
        return {"state": "PENDING", "status": "Task is waiting to be processed..."}
    elif result.state == "PROGRESS":
        info = result.info or {}
        return {
            "state": "PROGRESS",
            "current": info.get("current", 0) if isinstance(info, dict) else 0,
            "total": info.get("total", 1) if isinstance(info, dict) else 1,
            "status": info.get("status", "") if isinstance(info, dict) else "",
            "stage": info.get("stage", "") if isinstance(info, dict) else "",
        }
    elif result.state == "SUCCESS":
        return {"state": "SUCCESS", "result": result.info}
    else:
        info = result.info or {}
        return {
            "state": result.state,
            "status": info.get("status", "Unknown error")
            if isinstance(info, dict)
            else str(info),
            "error": info.get("error", "") if isinstance(info, dict) else str(info),
        }
