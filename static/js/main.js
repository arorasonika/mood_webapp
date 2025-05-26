// main.js

import { setupCalendarControlsAndRender } from './calender_renderer.js'; // Adjust path

document.addEventListener('DOMContentLoaded', function () {
    // Check if we are on a page that has the calendar
    const calendarDisplayDiv = document.getElementById('moodCalendar');

    if (calendarDisplayDiv) {
        // Ensure global variables from the template are available
        if (typeof window.moodEntriesByDateGlobal !== 'undefined' && typeof window.todayISOGlobal !== 'undefined') {
            setupCalendarControlsAndRender(window.moodEntriesByDateGlobal, window.todayISOGlobal);
        } else {
            console.error('moodEntriesByDateGlobal or todayISOGlobal not available on window for calendar rendering.');
        }
    }

    const modalElement = document.getElementById('moodModal');
    modalElement.hidden = true;
    const calendarHeaderSection = document.querySelector('.calendar-header-section');

    // If essential elements for this functionality aren't present, exit early.
    if (!modalElement || !calendarDisplayDiv || !calendarHeaderSection) {
        // console.log('Mood modal or calendar elements not found on this page. Skipping modal initialization.');
        return;
    }

    // moodEntriesByDate should be available globally from an inline script in calendar.html
    if (typeof moodEntriesByDate === 'undefined') {
        console.error('moodEntriesByDate is not defined globally. Make sure it is provided in an inline script in calendar.html before main.js is loaded.');
        return;
    }

    // Initialize Bootstrap Modal instance
    const moodModalInstance = new bootstrap.Modal(modalElement);

    // Get references to modal content elements
    const modalDateSpan = document.getElementById('modalDate');
    const modalEmojiElement = document.getElementById('modalEmoji');
    const modalTextResponseElement = document.getElementById('modalTextResponse');

    // --- Function to populate modal content and then show the modal ---
    function populateAndShowModal(isoDate) {
        if (!isoDate) { // Should only be called with a valid isoDate from a date cell
            moodModalInstance.hide(); // Safety hide if called incorrectly
            return;
        }

        const entry = moodEntriesByDate[isoDate]; // Access the global variable

        if (modalDateSpan) {
            try {
                // Format the date for display (e.g., "May 18, 2025")
                const dateObj = new Date(isoDate + 'T00:00:00'); // Ensure it's treated as local date
                const options = { year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC' }; // Use UTC to prevent timezone shifts for date-only display
                modalDateSpan.textContent = dateObj.toLocaleDateString(undefined, options);
            } catch (e) {
                modalDateSpan.textContent = isoDate; // Fallback if formatting fails
                console.warn("Could not format date:", isoDate, e);
            }
        }

        if (entry) {
            if (modalEmojiElement) modalEmojiElement.textContent = entry.emoji || '❓'; // Default if no emoji
            if (modalTextResponseElement) modalTextResponseElement.textContent = entry.text_response || 'No text response recorded.';
        } else {
            if (modalEmojiElement) modalEmojiElement.textContent = ''; // Placeholder for no entry
            if (modalTextResponseElement) modalTextResponseElement.textContent = 'No mood recorded for this day.';
        }

        moodModalInstance.show(); // Show the populated modal
    }

    // --- Event Listener for Calendar Date Clicks ---
    // This listens for clicks on the container that holds your dynamically rendered calendar days.
    calendarDisplayDiv.addEventListener('click', function (event) {
        // Try to find a clicked element that is a date cell and has the ISO date
        const targetCell = event.target.closest('.date-cell'); // ASSUMPTION: Your date cells have class 'date-cell'

        if (targetCell && targetCell.dataset.dateiso) { // ASSUMPTION: Date cells have 'data-dateiso="YYYY-MM-DD"'
            const selectedIsoDate = targetCell.dataset.dateiso;
            populateAndShowModal(selectedIsoDate); // Populate and show the modal
        }
        // If a click happens in calendarDisplayDiv but not on a recognized date cell,
        // the modal will not be shown or affected by this specific click.
        // It will remain hidden or in its current state (if opened by a previous valid date click).
    });

    // --- Logic for "Disappear when user clicks outside the calendar on the page" ---
    document.addEventListener('click', function (event) {
        // Only act if the modal is currently shown
        if (modalElement.classList.contains('show')) {
            const clickedElement = event.target;

            // Define what constitutes "inside the calendar system"
            const isClickInsideModal = modalElement.contains(clickedElement);
            const isClickInsideCalendarDisplay = calendarDisplayDiv.contains(clickedElement);
            const isClickInsideCalendarHeader = calendarHeaderSection.contains(clickedElement);

            // If the click is NOT inside the modal, AND
            // NOT inside the main calendar display area, AND
            // NOT inside the calendar header/navigation...
            if (!isClickInsideModal && !isClickInsideCalendarDisplay && !isClickInsideCalendarHeader) {
                moodModalInstance.hide(); // Then hide the modal
            }
        }
    });

    // --- Fix for "Blocked aria-hidden" warning (improves accessibility) ---
    modalElement.addEventListener('hide.bs.modal', function () {
        if (document.activeElement === modalElement) {
            modalElement.blur(); // Remove focus from modal div before it's hidden
        }
    });

    // --- Initial State ---
    // The modal is hidden by default via Bootstrap CSS (because it doesn't have the 'show' class).
    // The JavaScript logic above ensures it's only shown when a date cell is clicked via `populateAndShowModal`.
});