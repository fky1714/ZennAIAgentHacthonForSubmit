// Initialize BotUI
const botui = new BotUI('botui-app', {
  vue: Vue // BotUI depends on Vue
});

// Chat widget and UI elements
const chatWidget = document.getElementById('chatBotWidget');
const chatUiContainer = document.getElementById('botui-app');

// Toggle chat UI visibility
chatWidget.addEventListener('click', () => {
  const isChatOpen = chatUiContainer.style.display === 'block';
  chatUiContainer.style.display = isChatOpen ? 'none' : 'block';
  if (!isChatOpen && !initialMessageSent) {
    sendWelcomeMessage();
  }
});

let initialMessageSent = false;

// Function to send a welcome message
function sendWelcomeMessage() {
  botui.message.add({
    content: 'こんにちは！何かお手伝いできることはありますか？',
    delay: 300,
    loading: true
  }).then(() => {
    initialMessageSent = true;
    botui.action.text({
      action: {
        placeholder: 'メッセージを入力...'
      }
    }).then(handleUserInput);
  });
}

// Function to handle user input
function handleUserInput(res) {
  const userMessage = res.value;
  // Display user message - This is now handled by BotUI when action.text resolves.
  // botui.message.add({
  //   human: true,
  //   content: userMessage
  // });

  // Send user message to backend and display bot response
  // Store the promise returned by botui.message.add for the loading message
  let loadingMessagePromise = botui.message.add({
    loading: true,
    content: '考え中...' // Temporary content for loading
  });

  loadingMessagePromise.then(loadingMessageIndex => {
    // `loadingMessageIndex` is the index of the message just added.
    fetch('/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message: userMessage }),
    })
    .then(response => response.json())
    .then(data => {
      // Update the loading message with the actual reply
      // Convert markdown to HTML using marked.js
      const htmlReply = marked(data.reply);
      botui.message.update(loadingMessageIndex, {
        loading: false, // Stop loading animation
        content: htmlReply,
        type: 'html' // Tell BotUI to render content as HTML
      }).then(() => {
        // After bot response, ask for new input
        botui.action.text({
          action: {
            placeholder: 'メッセージを入力...'
          }
        }).then(handleUserInput);
      });
    })
    .catch((error) => {
      console.error('Error:', error);
      // Update the loading message with an error message
      botui.message.update(loadingMessageIndex, {
        loading: false, // Stop loading animation
        content: '申し訳ありません、エラーが発生しました。'
      }).then(() => {
        // After error, ask for new input
        botui.action.text({
          action: {
            placeholder: 'メッセージを入力...'
          }
        }).then(handleUserInput);
      });
    });
  });
}

// Display welcome message when chat is opened for the first time
// (Handled by the click event on chatWidget now)

// Example of how to keep the chat open/closed state across page navigations (using localStorage)
// This is a basic example. More robust state management might be needed for complex SPAs.
document.addEventListener('DOMContentLoaded', () => {
  const chatOpenState = localStorage.getItem('chatOpen');
  if (chatOpenState === 'true') {
    chatUiContainer.style.display = 'block';
    if (!initialMessageSent) {
      sendWelcomeMessage();
    }
  } else {
    chatUiContainer.style.display = 'none';
  }
});

window.addEventListener('beforeunload', () => {
  const isChatOpen = chatUiContainer.style.display === 'block';
  localStorage.setItem('chatOpen', isChatOpen);
});
