/**
 * ADAM Chat Widget - Global AI Assistant
 * 
 * ADAM (Automated Design, Analysis and Modelling) is the AI assistant
 * that provides engineering expertise across the EngineRoom platform.
 */

if (typeof ADAMChatWidget === 'undefined') {
class ADAMChatWidget extends BaseManager {
    constructor() {
        super('ADAMChatWidget');

        this.isOpen = false;
        this.isMinimized = false;
        this.currentConversationId = null;
        this.conversationHistory = [];
        this.isTyping = false;

        // Widget configuration
        this.config = {
            position: 'bottom-right',
            zIndex: 9999,
            maxMessages: 50,
            autoGreeting: true,
            userName: this.getUserName()
        };

        this.info('ADAM Chat Widget initializing...');
        this.initialize();
    }

    initialize() {
        try {
            this.createWidgetHTML();
            this.attachEventListeners();
            this.loadRecentConversation();

            if (this.config.autoGreeting) {
                this.showGreeting();
            }

            this.info('ADAM Chat Widget initialized successfully');
            return true;
        } catch (error) {
            this.error('Failed to initialize ADAM Chat Widget', error);
            return false;
        }
    }

    getUserName() {
        // Try to get user name from various sources
        const user = window.user || {};
        return user.first_name || user.username || 'there';
    }

    getTimeBasedGreeting() {
        const hour = new Date().getHours();
        if (hour < 12) return 'Good morning';
        if (hour < 17) return 'Good afternoon';
        return 'Good evening';
    }

    createWidgetHTML() {
        const widgetHTML = `
            <div id="adam-chat-widget" class="adam-chat-widget adam-chat-closed">
                <!-- Chat Toggle Button -->
                <div class="adam-chat-toggle" id="adamChatToggle">
                    <div class="adam-avatar">
                        <div class="adam-avatar-inner">A</div>
                        <div class="adam-status-indicator"></div>
                    </div>
                    <div class="adam-toggle-text">
                        <div class="adam-name">ADAM</div>
                        <div class="adam-tagline">AI Assistant</div>
                    </div>
                </div>

                <!-- Chat Interface -->
                <div class="adam-chat-interface" id="adamChatInterface">
                    <!-- Header -->
                    <div class="adam-chat-header">
                        <div class="adam-header-info">
                            <div class="adam-avatar-small">
                                <div class="adam-avatar-inner">A</div>
                            </div>
                            <div class="adam-header-text">
                                <div class="adam-name">ADAM</div>
                                <div class="adam-subtitle">AI Assistant</div>
                            </div>
                        </div>
                        <div class="adam-header-controls">
                            <button class="adam-control-btn" id="adamMinimizeBtn" title="Minimize">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="minimize-icon">
                                    <line x1="5" y1="12" x2="19" y2="12"></line>
                                </svg>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="expand-icon" style="display: none;">
                                    <polyline points="15,3 21,3 21,9"></polyline>
                                    <polyline points="9,21 3,21 3,15"></polyline>
                                    <line x1="21" y1="3" x2="14" y2="10"></line>
                                    <line x1="3" y1="21" x2="10" y2="14"></line>
                                </svg>
                            </button>
                            <button class="adam-control-btn" id="adamCloseBtn" title="Close">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <line x1="18" y1="6" x2="6" y2="18"></line>
                                    <line x1="6" y1="6" x2="18" y2="18"></line>
                                </svg>
                            </button>
                        </div>
                    </div>

                    <!-- Messages Area -->
                    <div class="adam-messages-container" id="adamMessagesContainer">
                        <div class="adam-messages" id="adamMessages">
                            <!-- Messages will be added here -->
                        </div>
                    </div>

                    <!-- Input Area -->
                    <div class="adam-input-area">
                        <div class="adam-input-container">
                            <textarea 
                                id="adamChatInput" 
                                class="adam-chat-input" 
                                placeholder="Need help, ask ADAM..."
                                rows="1"
                            ></textarea>
                            <button class="adam-send-btn" id="adamSendBtn" disabled>
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <line x1="22" y1="2" x2="11" y2="13"></line>
                                    <polygon points="22,2 15,22 11,13 2,9 22,2"></polygon>
                                </svg>
                            </button>
                        </div>

                        <!-- Quick Actions -->
                        <div class="adam-quick-actions" id="adamQuickActions">
                            <button class="adam-quick-btn" data-action="structural-analysis">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M3 21h18"></path>
                                    <path d="M5 21V7l8-4v18"></path>
                                    <path d="M19 21V11l-6-4"></path>
                                </svg>
                                Structural
                            </button>
                            <button class="adam-quick-btn" data-action="site-analysis">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"></polygon>
                                </svg>
                                Site Analysis
                            </button>
                            <button class="adam-quick-btn" data-action="design-help">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="12" cy="12" r="3"></circle>
                                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1 1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                                </svg>
                                Design Help
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', widgetHTML);

        // Cache DOM elements
        this.elements = {
            widget: document.getElementById('adam-chat-widget'),
            toggle: document.getElementById('adamChatToggle'),
            interface: document.getElementById('adamChatInterface'),
            messages: document.getElementById('adamMessages'),
            messagesContainer: document.getElementById('adamMessagesContainer'),
            input: document.getElementById('adamChatInput'),
            sendBtn: document.getElementById('adamSendBtn'),
            minimizeBtn: document.getElementById('adamMinimizeBtn'),
            closeBtn: document.getElementById('adamCloseBtn'),
            quickActions: document.getElementById('adamQuickActions')
        };
    }

    attachEventListeners() {
        // Toggle chat
        this.elements.toggle.addEventListener('click', () => this.toggleChat());

        // Control buttons
        this.elements.minimizeBtn.addEventListener('click', () => this.toggleMinimize());
        this.elements.closeBtn.addEventListener('click', () => this.closeChat());

        // Input handling
        this.elements.input.addEventListener('input', () => this.handleInputChange());
        this.elements.input.addEventListener('keydown', (e) => this.handleKeyDown(e));
        this.elements.sendBtn.addEventListener('click', () => this.sendMessage());

        // Quick actions
        this.elements.quickActions.addEventListener('click', (e) => {
            if (e.target.closest('.adam-quick-btn')) {
                this.handleQuickAction(e.target.closest('.adam-quick-btn').dataset.action);
            }
        });

        // Auto-resize textarea
        this.elements.input.addEventListener('input', () => {
            this.elements.input.style.height = 'auto';
            this.elements.input.style.height = Math.min(this.elements.input.scrollHeight, 120) + 'px';
        });
    }

    toggleChat() {
        if (this.isOpen) {
            this.closeChat();
        } else if (this.isMinimized) {
            this.openChat();
        } else {
            this.minimizeChat();
        }
    }

    openChat() {
        this.isOpen = true;
        this.isMinimized = false;
        this.elements.widget.classList.remove('adam-chat-closed', 'adam-chat-minimized');
        this.elements.widget.classList.add('adam-chat-open');

        // Update minimize button icon
        const minimizeIcon = this.elements.minimizeBtn.querySelector('.minimize-icon');
        const expandIcon = this.elements.minimizeBtn.querySelector('.expand-icon');
        if (minimizeIcon && expandIcon) {
            minimizeIcon.style.display = 'block';
            expandIcon.style.display = 'none';
        }
        this.elements.minimizeBtn.title = 'Minimize';

        // Focus input
        setTimeout(() => {
            this.elements.input.focus();
        }, 300);

        this.info('ADAM chat opened');
    }

    closeChat() {
        this.isOpen = false;
        this.isMinimized = false;
        this.elements.widget.classList.remove('adam-chat-open', 'adam-chat-minimized');
        this.elements.widget.classList.add('adam-chat-closed');

        this.info('ADAM chat closed');
    }

    toggleMinimize() {
        if (this.isMinimized) {
            this.openChat();
        } else {
            this.minimizeChat();
        }
    }

    minimizeChat() {
        this.isMinimized = true;
        this.isOpen = false;
        this.elements.widget.classList.remove('adam-chat-open');
        this.elements.widget.classList.add('adam-chat-minimized');

        // Update minimize button icon
        const minimizeIcon = this.elements.minimizeBtn.querySelector('.minimize-icon');
        const expandIcon = this.elements.minimizeBtn.querySelector('.expand-icon');
        if (minimizeIcon && expandIcon) {
            minimizeIcon.style.display = 'none';
            expandIcon.style.display = 'block';
        }
        this.elements.minimizeBtn.title = 'Expand';

        // Focus input in minimized state
        setTimeout(() => {
            this.elements.input.focus();
        }, 300);

        this.info('ADAM chat minimized to compact view');
    }

    handleInputChange() {
        const hasText = this.elements.input.value.trim().length > 0;
        this.elements.sendBtn.disabled = !hasText || this.isTyping;
    }

    handleKeyDown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!this.elements.sendBtn.disabled) {
                this.sendMessage();
            }
        }
    }

    async sendMessage() {
        const message = this.elements.input.value.trim();
        if (!message || this.isTyping) return;

        // Auto-expand if currently in minimized state
        if (this.isMinimized) {
            this.openChat();
        }

        this.addUserMessage(message);
        this.elements.input.value = '';
        this.elements.input.style.height = 'auto';
        this.handleInputChange();

        await this.processMessage(message);
    }

    async processMessage(message) {
        this.setTyping(true);

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    conversation_id: this.currentConversationId,
                    agent: 'ADAM'
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            if (data.success) {
                this.currentConversationId = data.conversation_id;
                this.addAssistantMessage(data.response);
            } else {
                throw new Error(data.error || 'Unknown error occurred');
            }

        } catch (error) {
            this.error('Failed to send message to ADAM', error);
            this.addErrorMessage('Sorry, I encountered an error. Please try again.');
        } finally {
            this.setTyping(false);
        }
    }

    addUserMessage(message) {
        const messageElement = this.createMessageElement('user', message);
        this.elements.messages.appendChild(messageElement);
        this.scrollToBottom();
    }

    addAssistantMessage(message) {
        const messageElement = this.createMessageElement('assistant', message);
        this.elements.messages.appendChild(messageElement);
        this.scrollToBottom();
    }

    addErrorMessage(message) {
        const messageElement = this.createMessageElement('error', message);
        this.elements.messages.appendChild(messageElement);
        this.scrollToBottom();
    }

    createMessageElement(type, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `adam-message adam-message-${type}`;

        if (type === 'assistant') {
            messageDiv.innerHTML = `
                <div class="adam-message-avatar">
                    <div class="adam-avatar-tiny">A</div>
                </div>
                <div class="adam-message-content">
                    <div class="adam-message-header">
                        <span class="adam-message-sender">ADAM</span>
                        <span class="adam-message-time">${this.formatTime(new Date())}</span>
                    </div>
                    <div class="adam-message-text">${this.formatMessageContent(content)}</div>
                </div>
            `;
        } else {
            messageDiv.innerHTML = `
                <div class="adam-message-content">
                    <div class="adam-message-text">${this.escapeHtml(content)}</div>
                    <div class="adam-message-time">${this.formatTime(new Date())}</div>
                </div>
            `;
        }

        return messageDiv;
    }

    formatMessageContent(content) {
        // Basic markdown-style formatting
        return this.escapeHtml(content)
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatTime(date) {
        return date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: false 
        });
    }

    setTyping(isTyping) {
        this.isTyping = isTyping;
        this.handleInputChange();

        if (isTyping) {
            this.showTypingIndicator();
        } else {
            this.hideTypingIndicator();
        }
    }

    showTypingIndicator() {
        const existingIndicator = this.elements.messages.querySelector('.adam-typing-indicator');
        if (existingIndicator) return;

        const typingDiv = document.createElement('div');
        typingDiv.className = 'adam-message adam-message-assistant adam-typing-indicator';
        typingDiv.innerHTML = `
            <div class="adam-message-avatar">
                <div class="adam-avatar-tiny">A</div>
            </div>
            <div class="adam-message-content">
                <div class="adam-typing-animation">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;

        this.elements.messages.appendChild(typingDiv);
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        const typingIndicator = this.elements.messages.querySelector('.adam-typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    scrollToBottom() {
        setTimeout(() => {
            this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
        }, 100);
    }

    showGreeting() {
        setTimeout(() => {
            const greeting1 = `Hi there, I'm ADAM — short for Automated Design, Analysis, and Modelling.\n\nI'm not just another algorithm with a PR team. I favour logic, maths, and real engineering methods over buzzwords. When AI makes sense, I'll use it — but when an equation does the job better, that's what you'll get.`;
            this.addAssistantMessage(greeting1);

            // Add second message after a short delay
            setTimeout(() => {
                const greeting2 = `Let's get started. What are we working on?`;
                this.addAssistantMessage(greeting2);
            }, 2000);
        }, 1000);
    }

    handleQuickAction(action) {
        const quickMessages = {
            'structural-analysis': 'I need help with structural analysis for my project.',
            'site-analysis': 'Can you help me analyze site conditions and constraints?',
            'design-help': 'I need design guidance and recommendations.'
        };

        const message = quickMessages[action];
        if (message) {
            this.elements.input.value = message;
            this.elements.input.focus();
            this.handleInputChange();
        }
    }

    async loadRecentConversation() {
        try {
            const response = await fetch('/api/conversations?limit=1&agent=ADAM');
            if (response.ok) {
                const conversations = await response.json();
                if (conversations.length > 0) {
                    this.currentConversationId = conversations[0].id;
                    this.info('Loaded recent ADAM conversation', { id: this.currentConversationId });
                }
            }
        } catch (error) {
            this.warn('Could not load recent conversation', error);
        }
    }
}

// Export to global scope
window.ADAMChatWidget = ADAMChatWidget;
}
// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize on authenticated pages
    if (document.body.classList.contains('authenticated') || window.user) {
        try {
            window.adamChat = new ADAMChatWidget();
        } catch (error) {
            console.error('Failed to initialize ADAM Chat Widget:', error);
        }
    }
});