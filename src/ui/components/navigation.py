"""Navigation and state management utilities."""

from typing import Dict, List

import streamlit as st


class AppState:
    """Centralized application state management."""

    def __init__(self):
        if "app_state_initialized" not in st.session_state:
            self._initialize_state()

    def _initialize_state(self):
        """Initialize default session state."""
        st.session_state.app_state_initialized = True
        st.session_state.current_page = "Process Transactions"
        st.session_state.background_tasks = []
        st.session_state.processing_progress = {"active": False}

    @property
    def current_page(self) -> str:
        return st.session_state.get("current_page", "Process Transactions")

    @current_page.setter
    def current_page(self, page: str):
        st.session_state.current_page = page

    @property
    def background_tasks(self) -> List[Dict]:
        return st.session_state.get("background_tasks", [])

    def add_background_task(self, task_id: str, task_name: str, filename: str):
        """Add a background task to tracking."""
        task_info = {
            "task_id": task_id,
            "task_name": task_name,
            "filename": filename,
            "started_at": st.session_state.get("current_time", 0),
            "status": "PENDING",
        }
        if "background_tasks" not in st.session_state:
            st.session_state.background_tasks = []
        st.session_state.background_tasks.append(task_info)

    def update_task_status(self, task_id: str, status_info: Dict):
        """Update status of a specific task."""
        for task_info in st.session_state.background_tasks:
            if task_info.get("task_id") == task_id:
                task_info.update(status_info)
                break

    def get_active_tasks(self) -> List[Dict]:
        """Get currently active background tasks."""
        return [
            task
            for task in self.background_tasks
            if task.get("status") in ["PROGRESS", "PENDING"]
        ]


def create_navigation() -> str:
    """Create navigation with buttons and sliding border effect."""
    # Initialize active page if not set
    if "active_page" not in st.session_state:
        st.session_state.active_page = "Process Transactions"

    # Navigation container with custom div
    st.markdown('<div class="nav-container">', unsafe_allow_html=True)

    # Toggle-style navigation buttons
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])

    with col1:
        if st.button("Process Transactions", key="nav_process"):
            st.session_state.active_page = "Process Transactions"

    with col2:
        if st.button("Analytics", key="nav_analytics"):
            st.session_state.active_page = "Analytics"

    with col3:
        if st.button("Vendor Payments", key="nav_vendor_payments"):
            st.session_state.active_page = "Vendor Payments"

    with col4:
        if st.button("Vendors", key="nav_vendors"):
            st.session_state.active_page = "Vendors"

    with col5:
        if st.button("Database", key="nav_database"):
            st.session_state.active_page = "Database"

    st.markdown("</div>", unsafe_allow_html=True)

    # Add sliding border JavaScript with active page tracking
    active_index = {
        "Process Transactions": 0,
        "Analytics": 1,
        "Vendor Payments": 2,
        "Vendors": 3,
        "Database": 4,
    }.get(st.session_state.active_page, 0)

    st.markdown(
        f"""
    <script>
    function initSlidingBorder() {{
        setTimeout(() => {{
            const navContainer = document.querySelector('.nav-container');
            if (!navContainer || navContainer.querySelector('.sliding-border')) return;

            const slidingBorder = document.createElement('div');
            slidingBorder.className = 'sliding-border';
            navContainer.appendChild(slidingBorder);

            const buttons = navContainer.querySelectorAll('.stButton button');
            const activeIndex = {active_index};

            // Set initial position for active page
            function setActivePosition() {{
                slidingBorder.style.transform = `translateX(${{activeIndex * 100}}%)`;
                slidingBorder.style.opacity = '1';
                slidingBorder.style.visibility = 'visible';
            }}

            // Initialize position immediately
            setActivePosition();

            buttons.forEach((button, index) => {{
                button.addEventListener('mouseenter', () => {{
                    slidingBorder.style.transform = `translateX(${{index * 100}}%)`;
                    slidingBorder.style.opacity = '1';
                    slidingBorder.style.visibility = 'visible';
                }});
            }});

            navContainer.addEventListener('mouseleave', () => {{
                setActivePosition();
            }});

            // Force update every 500ms to ensure border stays visible
            setInterval(setActivePosition, 500);
        }}, 100);
    }}
    initSlidingBorder();
    // Re-run when page changes
    setTimeout(initSlidingBorder, 200);
    setTimeout(initSlidingBorder, 500);
    </script>
    """,
        unsafe_allow_html=True,
    )

    selected_page = st.session_state.active_page

    # Show active background tasks in sidebar
    app_state = AppState()
    active_tasks = app_state.get_active_tasks()

    if active_tasks:
        st.sidebar.markdown("### Background Tasks")
        for task in active_tasks:
            with st.sidebar.expander(f"{task['task_name']}", expanded=True):
                st.sidebar.caption(f"**Status:** {task.get('status', 'Unknown')}")
                if task.get("status") == "PROGRESS":
                    current = task.get("current", 0)
                    total = task.get("total", 1)
                    progress = current / max(total, 1)
                    st.sidebar.progress(progress, text=f"{current}/{total}")
                    st.sidebar.write(f"**Stage:** {task.get('stage', 'Processing...')}")
                else:
                    st.sidebar.write("**Status:** Starting...")
        st.sidebar.markdown("---")

    return selected_page


def show_page_header(title: str, description: str = None):
    """Show standardized page header."""
    st.title(title)
    if description:
        st.markdown(f"*{description}*")
        st.markdown("---")
