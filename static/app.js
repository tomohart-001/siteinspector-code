class EngineRoomApp {
    constructor() {
        this.isChatMode = false;
        this.currentConversationId = null;
        this.conversationHistory = [];
        this.isTyping = false;
        this.bannerTexts = [
            "Civil 3D: For those who like their surfaces rough… and their software rougher.",
            "SolidWorks: Crash so often you'll start scheduling them into your Gantt chart.",
            "Revit: Because sometimes you just want to update a door and bring down the entire building.",
            "Tekla: Designed for steel detailers, but apparently by someone who hates them.",
            "The only thing more complex than your design? Its licensing agreements.",
            "Revit: Helping you bond with your IT team since day one.",
            "If rage-quitting SolidWorks counted as cardio, I'd be shredded by now."
        ];
        this.currentBannerIndex = 0;

        console.log('[EngineRoomApp] INFO: 🚀 INITIALIZING ENGINEROOM APPLICATION...', '');
        console.log('[EngineRoomApp] INFO: 📊 Initial app state:', {
            isChatMode: this.isChatMode,
            userAgent: navigator.userAgent,
            windowLocation: window.location.href,
            documentReadyState: document.readyState
        });

        this._initialize();
    }

    _initialize() {
        console.log('[EngineRoomApp] INFO: 1️⃣ Initializing UI elements...', '');
        this._initializeUIElements();

        console.log('EngineRoom app is running');

        console.log('[EngineRoomApp] INFO: 2️⃣ Attaching event listeners...', '');
        this._attachEventListeners();

        console.log('[EngineRoomApp] INFO: 3️⃣ Initializing application data...', '');
        this._initializeApplicationData();

        console.log('[EngineRoomApp] INFO: 4️⃣ Optimizing for mobile...', '');
        this._optimizeForMobile();

        console.log('[EngineRoomApp] INFO: 5️⃣ Setting up banner rotation...', '');
        this._setupBannerRotation();
    }

    _initializeUIElements() {
        // Initialize UI state
        this.elements = {
            mainInterface: document.querySelector('.main-interface'),
            chatInterface: document.getElementById('chatInterface'),
            chatInput: document.getElementById('chatInput'),
            chatSendBtn: document.getElementById('chatSendBtn'),
            chatMessages: document.getElementById('chatMessages'),
            buildBtn: document.getElementById('buildBtn')
        };
    }

    _attachEventListeners() {
        console.log('[EngineRoomApp] INFO: 🔧 Starting event listener attachment process', '');
        this._attachChatListeners();
        this._attachKeyboardShortcuts();
        this._attachBuildListener();
        console.log('[EngineRoomApp] INFO: ✅ Event listeners attachment process completed successfully', '');
    }

    _attachChatListeners() {
        const chatInput = this.elements.chatInput;
        const chatSendBtn = this.elements.chatSendBtn;

        if (chatInput) {
            chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this._handleChatSend();
                }
            });

            chatInput.addEventListener('input', () => {
                this._updateChatSendButton();
                this._autoResizeTextarea(chatInput);
            });
        }

        if (chatSendBtn) {
            chatSendBtn.addEventListener('click', () => {
                this._handleChatSend();
            });
        }

        const resetBtn = document.getElementById('resetBtn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this._resetChat();
            });
        }
    }

    _attachKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case '/':
                        e.preventDefault();
                        this._focusSearchInput();
                        break;
                    case 'k':
                        e.preventDefault();
                        this._focusSearchInput();
                        break;
                    case 'Escape':
                        if (this.isChatMode) {
                            this._showMainInterface();
                        }
                        break;
                }
            }
        });
    }

    _attachBuildListener() {
        const buildBtn = this.elements.buildBtn;
        if (buildBtn) {
            buildBtn.addEventListener('click', () => {
                console.log('[EngineRoomApp] INFO: 🚀 Build button clicked, showing city selection', '');
                this.startBuilding();
            });
        }
    }

    startBuilding() {
        console.log('[App] Starting building process...');
        // Always go to the location selection page for a consistent experience
        window.location.href = '/location-selection';
    }

    _initializeApplicationData() {
        this._loadConversations();
    }

    _optimizeForMobile() {
        if (window.innerWidth <= 768) {
            document.body.classList.add('mobile');
        }

        window.addEventListener('resize', () => {
            if (window.innerWidth <= 768) {
                document.body.classList.add('mobile');
            } else {
                document.body.classList.remove('mobile');
            }
        });
    }

    _setupBannerRotation() {
        console.log('[EngineRoomApp] INFO: 🎪 Initializing banner manager...', '');

        if (this.elements.mainSearchInput && this.bannerTexts.length > 0) {
            this._rotateBanner();
            setInterval(() => {
                this._rotateBanner();
            }, 4000);
        }
    }

    _rotateBanner() {
        if (!this.elements.mainSearchInput) return;

        // Only update placeholder if the input is empty (not being typed in)
        if (this.elements.mainSearchInput.value.trim() === '') {
            // Fade out current placeholder more gradually
            this.elements.mainSearchInput.style.opacity = '0.1';

            setTimeout(() => {
                // Change text while faded
                this.elements.mainSearchInput.placeholder = this.bannerTexts[this.currentBannerIndex];

                // Fade back in more gradually
                this.elements.mainSearchInput.style.opacity = '1';

                console.log('[EngineRoomApp] INFO: 🔄 Banner rotated to: "' + this.bannerTexts[this.currentBannerIndex].substring(0, 40) + '..."', '');

                this.currentBannerIndex = (this.currentBannerIndex + 1) % this.bannerTexts.length;
            }, 400);
        }
    }

    _updateMainSearchButton() {
        const mainSearchInput = this.elements.mainSearchInput;
        const mainSearchBtn = this.elements.mainSearchBtn;

        if (mainSearchInput && mainSearchBtn) {
            const hasText = mainSearchInput.value.trim().length > 0;
            mainSearchBtn.disabled = !hasText;
        }
    }

    _updateChatSendButton() {
        const chatInput = this.elements.chatInput;
        const chatSendBtn = this.elements.chatSendBtn;

        if (chatInput && chatSendBtn) {
            const hasText = chatInput.value.trim().length > 0;
            chatSendBtn.disabled = !hasText || this.isTyping;
        }
    }

    _focusSearchInput() {
        if (this.isChatMode && this.elements.chatInput) {
            this.elements.chatInput.focus();
        } else if (this.elements.mainSearchInput) {
            this.elements.mainSearchInput.focus();
        }
    }

    _autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        const newHeight = Math.min(textarea.scrollHeight, 120);
        textarea.style.height = newHeight + 'px';
    }

    async _handleMainSearch() {
        const query = this.elements.mainSearchInput?.value?.trim();
        if (!query) return;

        this._showChatInterface();
        await this._sendMessage(query);
    }

    async _handleChatSend() {
        const query = this.elements.chatInput?.value?.trim();
        if (!query || this.isTyping) return;

        await this._sendMessage(query);
    }

    async _sendMessage(message) {
        try {
            this._addUserMessage(message);
            this._clearInputs();
            this._setTyping(true);

            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    conversation_id: this.currentConversationId
                })
            });

            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            this.currentConversationId = data.conversation_id;
            this._addAssistantMessage(data.response);

        } catch (error) {
            console.error('Chat error:', error);
            this._addErrorMessage('Sorry, there was an error processing your request. Please try again.');
        } finally {
            this._setTyping(false);
        }
    }

    _addUserMessage(message) {
        const messageElement = this._createMessageElement('user', message);
        this.elements.chatMessages?.appendChild(messageElement);
        this._scrollToBottom();
    }

    _addAssistantMessage(message) {
        const messageElement = this._createMessageElement('assistant', message);
        this.elements.chatMessages?.appendChild(messageElement);
        this._scrollToBottom();
    }

    _addErrorMessage(message) {
        const messageElement = this._createMessageElement('error', message);
        this.elements.chatMessages?.appendChild(messageElement);
        this._scrollToBottom();
    }

    _createMessageElement(type, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = content;

        messageDiv.appendChild(contentDiv);
        return messageDiv;
    }

    _setTyping(isTyping) {
        this.isTyping = isTyping;
        this._updateChatSendButton();

        if (isTyping) {
            this._showTypingIndicator();
        } else {
            this._hideTypingIndicator();
        }
    }

    _showTypingIndicator() {
        const existingIndicator = document.querySelector('.typing-indicator');
        if (existingIndicator) return;

        const typingDiv = document.createElement('div');
        typingDiv.className = 'message assistant-message typing-indicator';
        typingDiv.innerHTML = '<div class="message-content">Thinking...</div>';

        this.elements.chatMessages?.appendChild(typingDiv);
        this._scrollToBottom();
    }

    _hideTypingIndicator() {
        const typingIndicator = document.querySelector('.typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    _clearInputs() {
        if (this.elements.mainSearchInput) {
            this.elements.mainSearchInput.value = '';
        }
        if (this.elements.chatInput) {
            this.elements.chatInput.value = '';
            this.elements.chatInput.style.height = 'auto';
        }
        this._updateMainSearchButton();
        this._updateChatSendButton();
    }

    _scrollToBottom() {
        if (this.elements.chatMessages) {
            this.elements.chatMessages.scrollTop = this.elements.chatMessages.scrollHeight;
        }
    }

    _showChatInterface() {
        if (this.isChatMode) return;

        this.isChatMode = true;

        if (this.elements.mainInterface) {
            this.elements.mainInterface.classList.add('chat-active');
        }

        if (this.elements.chatInterface) {
            this.elements.chatInterface.classList.add('active');
        }

        setTimeout(() => {
            this.elements.chatInput?.focus();
        }, 300);
    }

    _showMainInterface() {
        this.isChatMode = false;

        if (this.elements.mainInterface) {
            this.elements.mainInterface.classList.remove('chat-active');
        }

        if (this.elements.chatInterface) {
            this.elements.chatInterface.classList.remove('active');
        }

        setTimeout(() => {
            this.elements.mainSearchInput?.focus();
        }, 300);
    }

    _resetChat() {
        this.currentConversationId = null;
        this.conversationHistory = [];

        if (this.elements.chatMessages) {
            this.elements.chatMessages.innerHTML = '';
        }

        this._clearInputs();
        this._showMainInterface();
    }

    async _loadConversations() {
        try {
            const response = await fetch('/conversations');
            if (response.ok) {
                const conversations = await response.json();
                console.log('[EngineRoomApp] INFO: ✅ Conversations loaded successfully', conversations.length || 0);
            }
        } catch (error) {
            console.log('[EngineRoomApp] ERROR: API Error: loadConversations', {}, {
                status: error.status || 'unknown',
                statusText: error.statusText || 'Unknown error',
                url: error.url || window.location.href + 'conversations'
            });
        }
    }
}

// Global functions for city selection
function selectCity(cityName) {
    console.log(`Selected city: ${cityName}`);
    // Store selection in session storage
    sessionStorage.setItem('selectedCity', cityName);

    // Visual feedback
    document.querySelectorAll('.location-option-btn').forEach(btn => {
        btn.classList.remove('selected');
    });
    event.target.classList.add('selected');

    // City coordinates for New Zealand cities
    const cityCoordinates = {
        'Auckland': { lat: -36.8485, lng: 174.7633, zoom: 14 },
        'Hamilton': { lat: -37.7870, lng: 175.2793, zoom: 14 },
        'Tauranga': { lat: -37.6878, lng: 176.1651, zoom: 14 },
        'Christchurch': { lat: -43.5321, lng: 172.6362, zoom: 14 },
        'Wellington': { lat: -41.2865, lng: 174.7762, zoom: 14 },
        'Queenstown': { lat: -45.0312, lng: 168.6626, zoom: 14 }
    };

    // Store coordinates for use when proceeding to site selection
    if (cityCoordinates[cityName]) {
        const coords = cityCoordinates[cityName];
        sessionStorage.setItem('selectedCityCoords', JSON.stringify(coords));
        localStorage.setItem('engineroom_user_location', `${cityName}, New Zealand`);
        console.log(`Stored coordinates for ${cityName}:`, coords);
    }
}

function proceedToSiteSelection() {
    const selectedCity = sessionStorage.getItem('selectedCity');
    const selectedCoords = sessionStorage.getItem('selectedCityCoords');

    if (selectedCity && selectedCoords) {
        console.log(`Proceeding to site selection for ${selectedCity} with coordinates:`, selectedCoords);
        // Store the coordinates for the map page to use
        localStorage.setItem('autoNavigateToCity', selectedCoords);
    }

    window.location.href = '/site-selection';
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    try {
        window.engineRoomApp = new EngineRoomApp();
    } catch (error) {
        console.error('Failed to initialize EngineRoom app:', error);
    }
});