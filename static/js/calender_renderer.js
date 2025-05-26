// static/js/calendar_renderer.js (example path)

// This script assumes moodEntriesByDate and todayISO will be passed to its init function.

let currentDisplayedDate; // To keep track of the month/year being shown

/**
 * Renders the calendar grid for a given year and month.
 * @param {number} year - The full year (e.g., 2025).
 * @param {number} month - The month (0-indexed, 0 for January, 11 for December).
 * @param {object} moodEntries - The mood entries object, keyed by ISO date.
 * @param {string} todayDateISO - Today's date in "YYYY-MM-DD" format.
 */
function renderCalendar(year, month, moodEntries, todayDateISO) {
    const calendarDisplayDiv = document.getElementById('moodCalendar');
    const currentMonthYearEl = document.getElementById('currentMonthYear');

    if (!calendarDisplayDiv || !currentMonthYearEl) {
        console.error("Calendar container or month/year element not found for rendering.");
        return;
    }

    calendarDisplayDiv.innerHTML = ''; // Clear previous month's cells

    const firstDayOfMonth = new Date(year, month, 1);
    const daysInMonth = new Date(year, month + 1, 0).getDate(); // Last day of current month

    currentMonthYearEl.textContent = firstDayOfMonth.toLocaleDateString(undefined, { // 'default' locale
        month: 'long',
        year: 'numeric'
    });

    // Day of the week for the first day (0=Sunday, 1=Monday, ..., 6=Saturday)
    let startingDayOfWeek = firstDayOfMonth.getDay();

    // Create header for days of the week (e.g., Sun, Mon, Tue...)
    const daysOfWeek = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const headerRow = document.createElement('div');
    headerRow.className = 'calendar-days-header'; // For styling the row of day names
    daysOfWeek.forEach(dayName => {
        const dayHeaderEl = document.createElement('div');
        dayHeaderEl.className = 'calendar-day-label'; // For styling individual day names
        dayHeaderEl.textContent = dayName;
        headerRow.appendChild(dayHeaderEl);
    });
    calendarDisplayDiv.appendChild(headerRow);

    // Create empty cells for days before the first day of the month to align the grid
    for (let i = 0; i < startingDayOfWeek; i++) {
        const emptyCell = document.createElement('div');
        emptyCell.classList.add('calendar-day', 'empty-cell'); // 'calendar-day' for consistent grid styling
        calendarDisplayDiv.appendChild(emptyCell);
    }

    // Create cells for each day of the current month
    for (let day = 1; day <= daysInMonth; day++) {
        const dayCell = document.createElement('div');
        // Add base class for styling all day cells
        dayCell.classList.add('calendar-day');

        const currentDate = new Date(year, month, day);
        const isoDateString = currentDate.getFullYear() + '-' +
                              String(currentDate.getMonth() + 1).padStart(2, '0') + '-' +
                              String(currentDate.getDate()).padStart(2, '0');

        dayCell.textContent = day;
        // === REQUIRED for main.js modal interaction ===
        dayCell.classList.add('date-cell');
        dayCell.setAttribute('data-dateiso', isoDateString);
        // ===============================================

        // Add class if it's today
        if (isoDateString === todayDateISO) {
            dayCell.classList.add('today');
        }

        // Add class if there's a mood entry for this day for custom styling
        if (moodEntries && moodEntries[isoDateString]) {
            dayCell.classList.add('has-entry');
            // Optional: You could add a small dot or emoji here directly if desired
            dayCell.innerHTML = `${day} <span class="mood-indicator">${moodEntries[isoDateString].emoji || '●'}</span>`;
        }

        calendarDisplayDiv.appendChild(dayCell);
    }
}

/**
 * Sets up the calendar navigation (Prev/Next month buttons) and initial render.
 * This function should be called once the DOM is ready and data is available.
 * @param {object} moodEntries - The mood entries object from your template.
 * @param {string} todayFromFlask - Today's date "YYYY-MM-DD" from your template.
 */
export function setupCalendarControlsAndRender(moodEntries, todayFromFlask) {
    const prevMonthBtn = document.getElementById('prevMonthBtn');
    const nextMonthBtn = document.getElementById('nextMonthBtn');

    // Determine initial date to display
    // Use today's date from Flask if available, otherwise default to client's current date
    let initialYear, initialMonth;
    if (todayFromFlask) {
        const parts = todayFromFlask.split('-');
        initialYear = parseInt(parts[0], 10);
        initialMonth = parseInt(parts[1], 10) - 1; // JS month is 0-indexed
        currentDisplayedDate = new Date(Date.UTC(initialYear, initialMonth, 1)); // Use UTC to avoid timezone shifts from YYYY-MM-DD
    } else {
        const today = new Date();
        initialYear = today.getFullYear();
        initialMonth = today.getMonth();
        currentDisplayedDate = new Date(initialYear, initialMonth, 1);
    }

    if (prevMonthBtn) {
        prevMonthBtn.addEventListener('click', () => {
            currentDisplayedDate.setUTCMonth(currentDisplayedDate.getUTCMonth() - 1);
            renderCalendar(currentDisplayedDate.getUTCFullYear(), currentDisplayedDate.getUTCMonth(), moodEntries, todayFromFlask);
        });
    }

    if (nextMonthBtn) {
        nextMonthBtn.addEventListener('click', () => {
            currentDisplayedDate.setUTCMonth(currentDisplayedDate.getUTCMonth() + 1);
            renderCalendar(currentDisplayedDate.getUTCFullYear(), currentDisplayedDate.getUTCMonth(), moodEntries, todayFromFlask);
        });
    }

    // Initial render of the calendar
    renderCalendar(currentDisplayedDate.getUTCFullYear(), currentDisplayedDate.getUTCMonth(), moodEntries, todayFromFlask);
}