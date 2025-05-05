// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize date picker with today as minimum date
    const today = new Date().toISOString().split('T')[0];
    const dateInput = document.getElementById('reservation_date');
    if (dateInput) {
        dateInput.setAttribute('min', today);
        dateInput.value = today;
    }

    // Handle reservation form time and slot selection
    const reservationForm = document.getElementById('reservationForm');
    const slotSelectionDiv = document.getElementById('slotSelection');
    const startTimeInput = document.getElementById('start_time');
    const endTimeInput = document.getElementById('end_time');
    const slotIdInput = document.getElementById('slot_id');
    const slotGrid = document.getElementById('slotGrid');
    const searchSlotsBtn = document.getElementById('searchSlots');

    if (searchSlotsBtn) {
        searchSlotsBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Validate date and time inputs
            if (!validateTimeInputs()) {
                return;
            }
            
            // Show loading indicator
            slotGrid.innerHTML = '<div class="text-center"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>';
            slotSelectionDiv.classList.remove('d-none');
            
            // Get form data
            const formData = new FormData();
            formData.append('reservation_date', dateInput.value);
            formData.append('start_time', startTimeInput.value);
            formData.append('end_time', endTimeInput.value);
            
            // Fetch available slots
            fetch('/get_available_slots', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showErrorMessage(data.error);
                    return;
                }
                displayAvailableSlots(data);
            })
            .catch(error => {
                console.error('Error:', error);
                showErrorMessage('An error occurred while fetching available slots.');
            });
        });
    }

    // Validate time inputs
    function validateTimeInputs() {
        const startTime = startTimeInput.value;
        const endTime = endTimeInput.value;
        
        if (!startTime || !endTime) {
            showErrorMessage('Please enter both start and end times.');
            return false;
        }
        
        // Convert to Date objects for comparison
        const today = new Date().toDateString();
        const startDateTime = new Date(today + ' ' + startTime);
        const endDateTime = new Date(today + ' ' + endTime);
        
        if (endDateTime <= startDateTime) {
            showErrorMessage('End time must be after start time.');
            return false;
        }
        
        // Check if duration is at least 30 minutes and not more than 8 hours
        const durationMs = endDateTime - startDateTime;
        const durationMinutes = durationMs / (1000 * 60);
        
        if (durationMinutes < 30) {
            showErrorMessage('Reservation must be at least 30 minutes.');
            return false;
        }
        
        if (durationMinutes > 480) {
            showErrorMessage('Reservation cannot exceed 8 hours.');
            return false;
        }
        
        return true;
    }

    // Display available slots in a grid
    function displayAvailableSlots(slots) {
        if (slots.length === 0) {
            slotGrid.innerHTML = '<div class="alert alert-warning">No parking slots available for the selected time period.</div>';
            return;
        }
        
        let gridHtml = '<div class="row g-3">';
        
        slots.forEach(slot => {
            gridHtml += `
                <div class="col-md-2 col-sm-3 col-4">
                    <div class="card slot-card" data-slot-id="${slot.id}" onclick="selectSlot(${slot.id}, ${slot.number})">
                        <div class="card-body text-center">
                            <h5 class="card-title mb-0">${slot.number}</h5>
                        </div>
                    </div>
                </div>
            `;
        });
        
        gridHtml += '</div>';
        slotGrid.innerHTML = gridHtml;
    }

    // Display error message
    function showErrorMessage(message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-danger alert-dismissible fade show';
        alertDiv.role = 'alert';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        const alertContainer = document.getElementById('alertContainer');
        if (alertContainer) {
            alertContainer.innerHTML = '';
            alertContainer.appendChild(alertDiv);
        }
        
        // Scroll to alert
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    }

    // Timer functionality for confirmed reservations
    const timerElement = document.getElementById('reservationTimer');
    if (timerElement) {
        const reservationId = timerElement.getAttribute('data-reservation-id');
        if (reservationId) {
            updateTimer(reservationId, timerElement);
            setInterval(() => updateTimer(reservationId, timerElement), 60000); // Update every minute
        }
    }

    // Update reservation timer
    function updateTimer(reservationId, timerElement) {
        fetch(`/get_reservation/${reservationId}`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'confirmed' || data.status === 'checked_in') {
                    const reservationDate = new Date(data.reservation_date + 'T' + data.start_time);
                    const endTime = new Date(data.reservation_date + 'T' + data.end_time);
                    const now = new Date();
                    
                    let timeString = '';
                    let progressPercent = 0;
                    
                    if (now < reservationDate) {
                        // Time until reservation starts
                        const timeUntilStart = reservationDate - now;
                        const hoursUntil = Math.floor(timeUntilStart / (1000 * 60 * 60));
                        const minutesUntil = Math.floor((timeUntilStart % (1000 * 60 * 60)) / (1000 * 60));
                        
                        timeString = `Starts in ${hoursUntil}h ${minutesUntil}m`;
                        progressPercent = 0;
                    } else if (now > endTime) {
                        // Reservation has ended
                        timeString = 'Reservation ended';
                        progressPercent = 100;
                    } else {
                        // Reservation in progress
                        const totalDuration = endTime - reservationDate;
                        const elapsed = now - reservationDate;
                        progressPercent = Math.floor((elapsed / totalDuration) * 100);
                        
                        const timeRemaining = endTime - now;
                        const hoursRemaining = Math.floor(timeRemaining / (1000 * 60 * 60));
                        const minutesRemaining = Math.floor((timeRemaining % (1000 * 60 * 60)) / (1000 * 60));
                        
                        timeString = `${hoursRemaining}h ${minutesRemaining}m remaining`;
                        
                        // If less than 15 minutes remaining, show alert
                        if (timeRemaining < 15 * 60 * 1000) {
                            playAlertSound();
                        }
                    }
                    
                    // Update timer UI
                    document.getElementById('timeRemaining').textContent = timeString;
                    document.getElementById('progressBar').style.width = `${progressPercent}%`;
                    document.getElementById('progressBar').setAttribute('aria-valuenow', progressPercent);
                }
            })
            .catch(error => console.error('Error updating timer:', error));
    }

    // Play alert sound when reservation is ending soon
    function playAlertSound() {
        // Check if we've already played the sound recently
        const lastPlayed = localStorage.getItem('lastAlertPlayed');
        const now = new Date().getTime();
        
        // Only play once every 5 minutes
        if (!lastPlayed || (now - parseInt(lastPlayed)) > 5 * 60 * 1000) {
            const audio = new Audio('https://cdn.freesound.org/previews/80/80921_1022651-lq.mp3');
            audio.play();
            localStorage.setItem('lastAlertPlayed', now.toString());
        }
    }

    // Admin dashboard functionality
    const statusButtons = document.querySelectorAll('.status-btn');
    statusButtons.forEach(button => {
        button.addEventListener('click', function() {
            const reservationId = this.getAttribute('data-reservation-id');
            const newStatus = this.getAttribute('data-status');
            const form = document.getElementById(`statusForm-${reservationId}`);
            
            if (form) {
                const statusInput = form.querySelector('input[name="status"]');
                statusInput.value = newStatus;
                form.submit();
            }
        });
    });
});

// Global function for slot selection
function selectSlot(slotId, slotNumber) {
    // Remove selection from all slots
    document.querySelectorAll('.slot-card').forEach(card => {
        card.classList.remove('selected');
    });
    
    // Add selection to clicked slot
    const selectedCard = document.querySelector(`.slot-card[data-slot-id="${slotId}"]`);
    if (selectedCard) {
        selectedCard.classList.add('selected');
        
        // Update hidden input
        document.getElementById('slot_id').value = slotId;
        
        // Show selected slot number
        const selectedSlotDisplay = document.getElementById('selectedSlotDisplay');
        if (selectedSlotDisplay) {
            selectedSlotDisplay.textContent = `Slot #${slotNumber}`;
            selectedSlotDisplay.classList.remove('d-none');
        }
        
        // Enable submit button
        const submitButton = document.getElementById('submitReservation');
        if (submitButton) {
            submitButton.disabled = false;
        }
    }
}
