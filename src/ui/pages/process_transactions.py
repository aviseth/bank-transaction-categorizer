"""Process Transactions page module.

Handles CSV file upload, configuration, duplicate detection, and background processing.
"""

import os
import time
import uuid
from typing import Any, Dict, Optional

import streamlit as st

from src.compact_processor import CompactTransactionProcessor
from src.tasks import get_task_status, process_csv_async
from src.ui.components.navigation import AppState, show_page_header


class ProcessTransactionsPage:
    """Process Transactions page handler with background processing support."""

    def __init__(self):
        self.app_state = AppState()

    def render(self):
        """Render the Process Transactions page."""
        show_page_header(
            "Process Transactions",
            "Upload CSV files and categorize bank transactions with AI",
        )

        # Show background tasks progress
        has_active_tasks = self._show_background_tasks_progress()

        # Configuration section
        config = self._render_configuration()
        if not config:
            return  # Stop if configuration is invalid

        # Initialize processor with user settings
        processor = self._get_processor(config)

        # Handle pending duplicates review
        if self._handle_pending_duplicates(processor, config["batch_size"]):
            return  # Stop if showing duplicates review

        # Show notifications and active tasks
        self._show_notifications()
        self._show_active_tasks()

        # File upload and processing section
        self._render_file_upload(config)

        # Sample data processing section
        self._render_sample_data_processing(config)

        # Auto-refresh for active tasks
        if has_active_tasks:
            time.sleep(3)
            st.rerun()

    def _render_configuration(self) -> Optional[Dict[str, Any]]:
        """Render configuration section and return settings."""
        st.markdown("### Configuration")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            llm_provider = st.selectbox(
                "LLM Provider",
                ["OpenAI", "Anthropic"],
                index=0,
                help="Choose your preferred LLM provider",
            )

        with col2:
            if llm_provider == "OpenAI":
                model_choice = st.selectbox(
                    "AI Model",
                    ["gpt-4o-mini", "gpt-3.5-turbo", "gpt-4"],
                    index=0,
                    help="GPT-4o-mini recommended for speed/cost",
                )
            else:
                model_choice = st.selectbox(
                    "AI Model",
                    [
                        "claude-3-haiku-20240307",
                        "claude-3-sonnet-20240229",
                        "claude-3-opus-20240229",
                    ],
                    index=0,
                    help="Claude-3-haiku recommended for speed/cost",
                )

        with col3:
            batch_size = st.selectbox(
                "Batch Size",
                options=[5, 10, 15, 20],
                index=3,  # Default to 20
                help="Larger batches = faster processing",
            )

        with col4:
            api_key = st.text_input(
                f"{llm_provider} API Key",
                type="password",
                value=os.getenv(f"{llm_provider.upper()}_API_KEY", ""),
                help=f"Your {llm_provider} API key",
            )

        # Advanced settings
        st.subheader("Advanced Settings")
        col5, col6, _, _ = st.columns([2, 2, 2, 2])

        with col5:
            verify_domains = st.checkbox(
                "Verify vendor domains",
                value=True,  # Default to True as requested
                help="Verify vendor domains by testing HTTP connections. ⚠️ Adds ~2 seconds per unique vendor (slower but more accurate). Disable for faster processing.",
            )

        # Settings summary
        domain_status = (
            "✓ Domain verification" if verify_domains else "✗ Skip verification"
        )
        st.caption(
            f"Current: {llm_provider} • {model_choice} • Batch: {batch_size} • {domain_status}"
        )

        # Validate API key
        if not api_key:
            # Try environment fallback
            api_key = os.getenv(f"{llm_provider.upper()}_API_KEY", "")

        if not api_key:
            st.error(
                f"Please enter your {llm_provider} API key in the Configuration section above, or set it in your environment variables."
            )
            st.stop()

        st.markdown("---")

        return {
            "llm_provider": llm_provider,
            "model_choice": model_choice,
            "batch_size": batch_size,
            "api_key": api_key,
            "verify_domains": verify_domains,
        }

    def _get_processor(self, config: Dict[str, Any]) -> CompactTransactionProcessor:
        """Get processor with user configuration."""
        processor = CompactTransactionProcessor(
            config["api_key"], config["verify_domains"]
        )
        processor.categorizer.model = config["model_choice"]
        processor.categorizer.provider = config["llm_provider"]
        processor.categorizer.verify_domains = config["verify_domains"]
        return processor

    def _show_background_tasks_progress(self) -> bool:
        """Show background tasks progress and return if any are active."""
        active_tasks = self.app_state.get_active_tasks()

        if not active_tasks:
            return False

        st.markdown("### Background Processing Status")
        st.caption(f"Debug: Checking {len(active_tasks)} background tasks...")

        for task in active_tasks:
            try:
                task_id = task.get("task_id")
                if not task_id:
                    continue

                status = get_task_status(task_id)
                task_state = status.get("state", "UNKNOWN")
                task_name = task.get("task_name", "Processing...")

                if task_state == "PROGRESS":
                    current = status.get("current", 0)
                    total = status.get("total", 1)
                    progress_percent = int((current / total) * 100) if total > 0 else 0
                    status_text = status.get("status", "Processing...")

                    st.markdown(f"**{task_name}**")
                    st.progress(progress_percent / 100)
                    st.caption(
                        f"Progress: {progress_percent}% ({current}/{total}) - {status_text}"
                    )

                elif task_state == "PENDING":
                    st.markdown(f"**{task_name}**")
                    st.progress(0)
                    st.caption("Task queued, waiting to start...")

            except Exception as e:
                st.warning(f"Could not get status for task {task_id}: {e}")

        st.markdown("---")
        return True

    def _handle_pending_duplicates(
        self, processor: CompactTransactionProcessor, batch_size: int
    ) -> bool:
        """Handle pending duplicates review. Returns True if showing duplicates UI."""
        if (
            "pending_duplicates" not in st.session_state
            or not st.session_state.pending_duplicates
        ):
            return False

        st.markdown("### ⚠️ Review Potential Duplicates")
        st.warning(
            f"Found {len(st.session_state.pending_duplicates)} potential duplicate transactions. Review and select which ones to process."
        )

        # Create selection interface
        selected = []
        st.markdown("#### Select transactions to process anyway:")

        for i, dup in enumerate(st.session_state.pending_duplicates):
            col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 3, 2])

            with col1:
                include = st.checkbox("Process", key=f"dup_{i}", value=False)
                if include:
                    selected.append(dup["index"])

            with col2:
                st.write(f"**{dup['date']}**")
                st.caption(f"Amount: {dup['amount']:.2f}")

            with col3:
                st.write("**New Transaction:**")
                text_preview = (
                    dup["text"][:50] + "..." if len(dup["text"]) > 50 else dup["text"]
                )
                st.caption(text_preview)

            with col4:
                st.write("**Existing Match:**")
                st.caption(f"Date: {dup['existing_date']}")
                existing_text = (
                    dup["existing_text"][:50] + "..."
                    if len(dup["existing_text"]) > 50
                    else dup["existing_text"]
                )
                st.caption(existing_text)

            with col5:
                st.metric("Similarity", f"{dup['similarity']:.2f}")

            st.divider()

        # Action buttons
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("Process Selected", type="primary", width="stretch"):
                self._process_with_duplicates(processor, selected, batch_size)

        with col2:
            if st.button("⏭️ Skip All Duplicates", width="stretch"):
                self._process_with_duplicates(processor, [], batch_size)

        with col3:
            if st.button("❌ Cancel", width="stretch"):
                self._cleanup_pending_duplicates()

        return True

    def _process_with_duplicates(
        self, processor: CompactTransactionProcessor, selected: list, batch_size: int
    ):
        """Process transactions with duplicate handling."""
        temp_path = st.session_state.pending_file
        try:
            results, _ = processor.process_csv_with_duplicate_check(
                temp_path, excluded_indices=selected, batch_size=batch_size
            )

            if results:
                processed_count = len(results)
                skipped_count = len(st.session_state.pending_duplicates) - len(selected)

                if skipped_count > 0:
                    st.success(
                        f"✅ Processed {processed_count} transactions (skipped {skipped_count} duplicates)"
                    )
                else:
                    st.success(f"✅ Processed {processed_count} new transactions")

            self._cleanup_pending_duplicates()
            st.rerun()

        except Exception as e:
            st.error(f"Error processing transactions: {e}")

    def _cleanup_pending_duplicates(self):
        """Clean up pending duplicates session state."""
        temp_path = st.session_state.get("pending_file")
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

        if "pending_duplicates" in st.session_state:
            del st.session_state["pending_duplicates"]
        if "pending_file" in st.session_state:
            del st.session_state["pending_file"]

    def _show_notifications(self):
        """Show recent task notifications."""
        if (
            hasattr(st.session_state, "task_notifications")
            and st.session_state.task_notifications
        ):
            for notification in st.session_state.task_notifications[-3:]:  # Show last 3
                if notification["type"] == "success":
                    st.success(f"✅ {notification['message']}")

    def _show_active_tasks(self):
        """Show active background tasks details."""
        active_tasks = self.app_state.get_active_tasks()
        if active_tasks:
            st.markdown("### ⚡ Active Background Tasks")
            for task in active_tasks:
                task_id = task.get("task_id")
                if task_id:
                    self._display_task_progress(task_id, task)
            st.markdown("---")

    def _display_task_progress(self, task_id: str, task_info: dict):
        """Display progress for a specific task."""
        try:
            status = get_task_status(task_id)
            task_name = task_info.get("task_name", "Processing...")

            if status["state"] == "PROGRESS":
                progress = status["current"] / max(status["total"], 1)
                st.progress(
                    progress,
                    text=f"**{task_name}**: {status['current']}/{status['total']}",
                )
                st.caption(f"Status: {status.get('status', 'Processing...')}")

            elif status["state"] == "SUCCESS":
                st.success(f"✅ {task_name} completed successfully!")
                # Update task info
                self.app_state.update_task_status(
                    task_id, {"status": "SUCCESS", "completed_time": time.time()}
                )

            elif status["state"] == "FAILURE":
                st.error(
                    f"❌ {task_name} failed: {status.get('error', 'Unknown error')}"
                )
                self.app_state.update_task_status(
                    task_id, {"status": "FAILURE", "error": status.get("error", "")}
                )

        except Exception as e:
            st.warning(f"Could not get status for task {task_id}: {e}")

    def _render_file_upload(self, config: Dict[str, Any]):
        """Render file upload section."""
        st.markdown("### Upload CSV File")
        uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])

        if uploaded_file is None:
            return

        st.success(f"✅ File uploaded: {uploaded_file.name}")

        # Save file with unique name
        unique_filename = f"{uuid.uuid4()}_{uploaded_file.name}"
        temp_path = f"/tmp/{unique_filename}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        self._render_background_processing_section(
            temp_path, uploaded_file.name, config, "upload"
        )

    def _render_sample_data_processing(self, config: Dict[str, Any]):
        """Render sample data processing section."""
        csv_files = []
        if os.path.exists("data/raw"):
            csv_files = [f for f in os.listdir("data/raw") if f.endswith(".csv")]

        if not csv_files:
            return

        st.markdown("### Process Sample Data")
        selected_file = st.selectbox("Available files:", csv_files)

        file_path = f"data/raw/{selected_file}"
        self._render_background_processing_section(file_path, selected_file, config, "sample")

    def _render_background_processing_section(
        self, file_path: str, filename: str, config: Dict[str, Any], context: str = "default"
    ):
        """Render background processing section."""
        st.markdown("#### Background Processing")
        st.markdown(
            "*Process in background and continue using the app - refreshing the page won't interrupt processing*"
        )

        try:
            from src.celery_app import celery_app

            CELERY_AVAILABLE = True
        except ImportError:
            CELERY_AVAILABLE = False

        if not CELERY_AVAILABLE:
            st.warning(
                "⚠️ Background processing not available. Install Redis and start Celery worker."
            )
            st.code("pip install redis celery")
            st.code("celery -A src.celery_app worker --loglevel=info")
            return

        button_text = f"Process {filename} in Background"

        # Debug: Show current key and file path
        key = f"bg_process_{context}_{filename.replace(' ', '_').replace('.', '_')}"
        st.caption(f"Debug: Using key '{key}' for file '{filename}' in context '{context}'")

        button_clicked = st.button(
            button_text,
            type="primary",
            width="stretch",
            key=key,
        )

        if button_clicked:
            st.success("✅ Button was clicked! Starting background processing...")
            st.write(f"File path: {file_path}")
            st.write(f"Filename: {filename}")
            self._start_background_processing(file_path, filename, config)
        else:
            st.caption("Button not clicked this render")

    def _start_background_processing(
        self, file_path: str, filename: str, config: Dict[str, Any]
    ):
        """Start background processing task."""
        try:
            task = process_csv_async.delay(
                csv_path=file_path,
                api_key=config["api_key"],
                model=config["model_choice"],
                provider=config["llm_provider"],
                batch_size=config["batch_size"],
                verify_domains=config["verify_domains"],
            )

            # Add to session state tracking
            self.app_state.add_background_task(
                task_id=task.id,
                task_name=f"Processing {filename}",
                filename=filename,
            )

            st.success(f"Background processing started! Task ID: {task.id[:8]}...")
            st.info(
                "You can navigate to other pages while processing continues. Progress will be shown above when you return to this page."
            )

            # Auto-refresh to show progress
            time.sleep(1)
            st.rerun()

        except Exception as e:
            st.error(f"Failed to start background processing: {e}")
            import traceback

            st.code(traceback.format_exc())


def render_process_transactions_page():
    """Entry point for rendering the Process Transactions page."""
    page = ProcessTransactionsPage()
    page.render()
