window.HELP_IMPROVE_VIDEOJS = false;


$(document).ready(function() {
    // Check for click events on the navbar burger icon

    var options = {
			slidesToScroll: 1,
			slidesToShow: 1,
			loop: true,
			infinite: true,
			autoplay: true,
			autoplaySpeed: 5000,
    }

		// Initialize all div with carousel class
    var carousels = bulmaCarousel.attach('.carousel', options);
	
    bulmaSlider.attach();

    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');

    function addMessage(text, sender) {
        const message = document.createElement('div');
        message.classList.add('message');
        if (sender === 'user') {
            message.classList.add('is-user');
        } else {
            message.classList.add('is-primary');
        }

        const messageBody = document.createElement('div');
        messageBody.classList.add('message-body');
        messageBody.textContent = text;
        message.appendChild(messageBody);

        chatMessages.appendChild(message);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function sendMessage() {
        const text = userInput.value.trim();
        if (text) {
            addMessage(text, 'user');
            userInput.value = '';
            // Placeholder for bot response
            setTimeout(() => {
                addMessage('This is a placeholder response from the DM.', 'bot');
            }, 1000);
        }
    }

    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', function(event) {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });
})
