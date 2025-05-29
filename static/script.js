document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    const currentUser = document.querySelector('.user-header h2').textContent;
    let currentChat = null;
    let currentChatType = null; // 'private' or 'group'
    
    // DOM elements
    const userList = document.getElementById('user-list');
    const groupList = document.getElementById('group-list');
    const messagesContainer = document.getElementById('messages');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const chatTitle = document.getElementById('chat-title');
    const newGroupName = document.getElementById('new-group-name');
    const createGroupButton = document.getElementById('create-group');
    
    // Connect to WebSocket
    socket.on('connect', function() {
        console.log('Connected to WebSocket server');
    });
    
    // Update user list
    socket.on('update_users', function(data) {
        const users = data.users.filter(user => user !== currentUser);
        userList.innerHTML = '';
        
        users.forEach(user => {
            const li = document.createElement('li');
            li.textContent = user;
            li.dataset.username = user;
            li.classList.add('contact');
            li.addEventListener('click', () => openPrivateChat(user));
            userList.appendChild(li);
        });
    });
    
    // Handle new message
    socket.on('new_message', function(data) {
        if ((currentChatType === 'private' && currentChat === data.chat_id) || 
            (data.sender === currentUser && currentChat === data.chat_id)) {
            addMessage(data.sender, data.message, data.timestamp, data.sender === currentUser);
        }
    });
    
    // Handle group message
    socket.on('group_message', function(data) {
        if (currentChatType === 'group' && currentChat === data.chat_id) {
            addMessage(data.sender, data.message, data.timestamp, data.sender === currentUser);
        }
    });
    
    // Load chat history
    socket.on('chat_history', function(data) {
        if (data.chat_id === currentChat) {
            messagesContainer.innerHTML = '';
            data.history.forEach(msg => {
                addMessage(msg.sender, msg.message, msg.timestamp, msg.sender === currentUser);
            });
            scrollToBottom();
        }
    });
    
    // Open private chat
    function openPrivateChat(username) {
        // Highlight selected contact
        document.querySelectorAll('.contact').forEach(el => el.classList.remove('active'));
        document.querySelector(`.contact[data-username="${username}"]`).classList.add('active');
        
        // Set current chat
        currentChat = [currentUser, username].sort().join('_');
        currentChatType = 'private';
        chatTitle.textContent = `Private chat with ${username}`;
        
        // Enable message input
        messageInput.disabled = false;
        sendButton.disabled = false;
        messageInput.focus();
        
        // Clear messages and load history
        messagesContainer.innerHTML = '';
        socket.emit('load_history', { chat_id: currentChat });
    }
    
    // Create group chat
    createGroupButton.addEventListener('click', function() {
        const groupName = newGroupName.value.trim();
        if (groupName) {
            const groupId = `group_${groupName}`;
            
            // Add to group list
            const li = document.createElement('li');
            li.textContent = groupName;
            li.dataset.group = groupName;
            li.classList.add('contact');
            li.addEventListener('click', () => openGroupChat(groupName));
            groupList.appendChild(li);
            
            // Join group
            socket.emit('join_group', { group_name: groupName });
            
            // Clear input
            newGroupName.value = '';
        }
    });
    
    // Open group chat
    function openGroupChat(groupName) {
        // Highlight selected group
        document.querySelectorAll('.contact').forEach(el => el.classList.remove('active'));
        document.querySelector(`.contact[data-group="${groupName}"]`).classList.add('active');
        
        // Set current chat
        currentChat = `group_${groupName}`;
        currentChatType = 'group';
        chatTitle.textContent = `Group: ${groupName}`;
        
        // Enable message input
        messageInput.disabled = false;
        sendButton.disabled = false;
        messageInput.focus();
        
        // Clear messages and load history
        messagesContainer.innerHTML = '';
        socket.emit('load_history', { chat_id: currentChat });
    }
    
    // Send message
    function sendMessage() {
        const message = messageInput.value.trim();
        if (message && currentChat) {
            if (currentChatType === 'private') {
                const recipient = currentChat.split('_').find(u => u !== currentUser);
                socket.emit('private_message', {
                    recipient: recipient,
                    message: message
                });
            } else if (currentChatType === 'group') {
                const groupName = currentChat.replace('group_', '');
                socket.emit('group_message', {
                    group_name: groupName,
                    message: message
                });
            }
            
            messageInput.value = '';
        }
    }
    
    // Send message on button click
    sendButton.addEventListener('click', sendMessage);
    
    // Send message on Enter key
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    // Add message to UI
    function addMessage(sender, message, timestamp, isOutgoing) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(isOutgoing ? 'message-outgoing' : 'message-incoming');
        
        const senderDiv = document.createElement('div');
        senderDiv.classList.add('message-sender');
        senderDiv.textContent = sender;
        
        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content');
        contentDiv.textContent = message;
        
        const timeDiv = document.createElement('div');
        timeDiv.classList.add('message-timestamp');
        timeDiv.textContent = timestamp;
        
        messageDiv.appendChild(senderDiv);
        messageDiv.appendChild(contentDiv);
        messageDiv.appendChild(timeDiv);
        
        messagesContainer.appendChild(messageDiv);
        scrollToBottom();
    }
    
    // Scroll to bottom of messages
    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
});